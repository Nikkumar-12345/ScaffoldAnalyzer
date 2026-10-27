"""
Background analysis jobs with progress reporting.

    start(uniprot_id)  -> job (runs in a background thread)
    status(job_id)     -> progress / stage / error
    result(job_id)     -> gzipped JSON bytes of the finished analysis

Finished results are kept (gzipped) per UniProt ID, so analysing the
same target again is instant. Only one analysis runs at a time by
default (ANALYSIS_WORKERS), which keeps memory use safe on small
instances such as Render's free tier; additional requests queue.
"""

import gzip
import json
import os
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from app.services.analysis_service import AnalysisService
from app.services.errors import AnalysisError, normalize_uniprot_id


def serialize_result(result):

    raw = json.dumps(
        result,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    return gzip.compress(raw, compresslevel=6)


class Job:

    def __init__(self, uniprot_id):

        self.id = uuid.uuid4().hex
        self.uniprot_id = uniprot_id
        self.status = "queued"
        self.progress = 0.0
        self.stage = "Waiting to start"
        self.error = None
        self.result_gz = None
        self.created_at = time.time()
        self.started_at = None
        self.finished_at = None

    def to_dict(self, queue_position=None):

        now = time.time()

        data = {
            "job_id": self.id,
            "uniprot_id": self.uniprot_id,
            "status": self.status,
            "progress": round(self.progress, 1),
            "stage": self.stage,
            "elapsed_seconds": round(
                (self.finished_at or now)
                - (self.started_at or self.created_at),
                1
            ),
            "error": self.error,
        }

        if queue_position is not None:
            data["queue_position"] = queue_position

        return data


class JobManager:

    JOB_TTL_SECONDS = 2 * 60 * 60

    def __init__(self):

        workers = int(os.getenv("ANALYSIS_WORKERS", "1"))
        self.cache_size = int(os.getenv("RESULT_CACHE_SIZE", "12"))

        self.executor = ThreadPoolExecutor(
            max_workers=max(1, workers),
            thread_name_prefix="analysis"
        )

        self.analysis = AnalysisService()
        self.lock = threading.Lock()
        self.jobs = {}
        self.active_by_target = {}
        self.queue = []
        self.results = OrderedDict()   # uniprot_id -> gzipped JSON

    # --------------------------------------------------
    # RESULT CACHE
    # --------------------------------------------------

    def _cache_get(self, uniprot_id):

        with self.lock:

            data = self.results.get(uniprot_id)

            if data is not None:
                self.results.move_to_end(uniprot_id)

            return data

    def _cache_put(self, uniprot_id, data):

        with self.lock:

            self.results[uniprot_id] = data
            self.results.move_to_end(uniprot_id)

            while len(self.results) > self.cache_size:
                self.results.popitem(last=False)

    # --------------------------------------------------
    # SYNCHRONOUS (original POST /analyze/ endpoint)
    # --------------------------------------------------

    def run_sync(self, uniprot_id):
        """Returns gzipped JSON bytes; raises AnalysisError."""

        key = normalize_uniprot_id(uniprot_id)

        cached = self._cache_get(key)

        if cached is not None:
            return cached

        job = self.start(uniprot_id)

        while job.status in ("queued", "running"):
            time.sleep(0.25)

        if job.status == "error":
            raise AnalysisError(
                job.error["code"],
                job.error["message"],
                job.error.get("http_status", 500)
            )

        return job.result_gz

    # --------------------------------------------------
    # ASYNC JOBS
    # --------------------------------------------------

    def start(self, uniprot_id):

        key = normalize_uniprot_id(uniprot_id)

        self._cleanup()

        with self.lock:

            # Same target already queued/running -> share that job
            existing_id = self.active_by_target.get(key)

            if existing_id and existing_id in self.jobs:
                return self.jobs[existing_id]

            job = Job(key)
            self.jobs[job.id] = job

            cached = self.results.get(key)

            if cached is not None:

                self.results.move_to_end(key)
                job.status = "done"
                job.progress = 100.0
                job.stage = "Loaded from cache"
                job.result_gz = cached
                job.started_at = job.finished_at = time.time()
                return job

            self.active_by_target[key] = job.id
            self.queue.append(job.id)

        self.executor.submit(self._run, job, uniprot_id)

        return job

    def _run(self, job, raw_uniprot_id):

        with self.lock:
            if job.id in self.queue:
                self.queue.remove(job.id)

        job.status = "running"
        job.started_at = time.time()
        job.stage = "Starting analysis"

        def progress(percent, message):
            # Never move the bar backwards
            job.progress = max(job.progress, min(float(percent), 99.0))
            job.stage = message

        try:

            result = self.analysis.analyze(
                raw_uniprot_id,
                progress=progress
            )

            progress(99, "Preparing results")

            data = serialize_result(result)
            result = None

            self._cache_put(job.uniprot_id, data)

            job.result_gz = data
            job.progress = 100.0
            job.stage = "Analysis complete"
            job.status = "done"

        except AnalysisError as error:

            job.error = {
                **error.to_dict(),
                "http_status": error.status_code
            }
            job.stage = "Failed"
            job.status = "error"

        except Exception as error:

            traceback.print_exc()

            job.error = {
                "code": "analysis_failed",
                "message": (
                    "The analysis failed unexpectedly: "
                    f"{error}"
                ),
                "http_status": 500
            }
            job.stage = "Failed"
            job.status = "error"

        finally:

            job.finished_at = time.time()

            with self.lock:
                if self.active_by_target.get(job.uniprot_id) == job.id:
                    del self.active_by_target[job.uniprot_id]

    # --------------------------------------------------
    # QUERIES
    # --------------------------------------------------

    def get(self, job_id):

        with self.lock:
            return self.jobs.get(job_id)

    def status(self, job_id):

        job = self.get(job_id)

        if job is None:
            return None

        position = None

        with self.lock:
            if job.id in self.queue:
                position = self.queue.index(job.id) + 1

        data = job.to_dict(queue_position=position)

        if data["error"]:
            data["error"] = {
                k: v for k, v in data["error"].items()
                if k != "http_status"
            }

        return data

    def _cleanup(self):

        cutoff = time.time() - self.JOB_TTL_SECONDS

        with self.lock:

            for job_id in [
                j.id for j in self.jobs.values()
                if j.finished_at and j.finished_at < cutoff
            ]:
                del self.jobs[job_id]


job_manager = JobManager()
