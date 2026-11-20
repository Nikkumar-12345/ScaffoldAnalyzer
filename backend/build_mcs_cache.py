"""
Build the precomputed chemical-series / maximum-common-substructure cache.

For every target in the local ChEMBL database that has activity data this
script:

    1. clusters the target's molecules into chemical series
       (Morgan fingerprints + Taylor-Butina clustering),
    2. extracts the maximum common substructure (MCS) of each series,
    3. stores one row per series.

Finding an MCS is NP-hard and takes seconds to minutes for a large target,
so it is done once, here, rather than while a user waits. At runtime
MCSCacheService only reads the result.

The build can be stopped and restarted: targets that are already in the
output file are skipped.

Requirements: RDKit (already needed by the app). Build time only.

Usage (from the backend folder):

    python build_mcs_cache.py <path-to-chembl.db> [output.db] [--workers N]

Rebuild it whenever the ChEMBL database changes.
"""

import gzip
import json
import os
import shutil
import sqlite3
import sys
import time
from multiprocessing import Pool
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

DEFAULT_OUTPUT = BASE_DIR / "precomputed" / "mcs_series.db"

# Settings used for the cached build. A smaller sample and a shorter
# time limit than the library defaults: a series is tight by
# construction, so ten of its most potent members give essentially
# the same core, at about 2.4x less cost.
MCS_SAMPLE_SIZE = 10
MCS_TIMEOUT_SECONDS = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS mcs_targets (
    target_chembl_id TEXT PRIMARY KEY,
    uniprot_id       TEXT,
    target_name      TEXT,
    molecules        INTEGER,
    clustered        INTEGER,
    truncated        INTEGER,
    series_total     INTEGER,
    singletons       INTEGER,
    mcs_success      INTEGER,
    mcs_timeout      INTEGER,
    largest_series   INTEGER
);

CREATE TABLE IF NOT EXISTS mcs_series (
    target_chembl_id TEXT NOT NULL,
    series_no        INTEGER NOT NULL,
    molecules        INTEGER,
    scaffolds        INTEGER,
    status           TEXT,
    smarts           TEXT,
    atoms            INTEGER,
    bonds            INTEGER,
    coverage         REAL,
    pic50_median     REAL,
    pic50_min        REAL,
    pic50_max        REAL,
    pic50_count      INTEGER,
    rep_chembl_id    TEXT,
    rep_smiles       TEXT,
    members          TEXT,
    PRIMARY KEY (target_chembl_id, series_no)
);

CREATE TABLE IF NOT EXISTS mcs_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def load_molecules(conn, target_chembl_id):

    rows = conn.execute(
        """
        SELECT molecule_chembl_id, canonical_smiles, pchembl_value
        FROM activities
        WHERE target_chembl_id = ?
          AND standard_relation = '='
          AND canonical_smiles IS NOT NULL
          AND standard_value IS NOT NULL
        GROUP BY molecule_chembl_id
        """,
        (target_chembl_id,)
    ).fetchall()

    molecules = []

    for chembl_id, smiles, pchembl in rows:

        try:
            pic50 = float(pchembl) if pchembl not in (None, "") else None
        except (TypeError, ValueError):
            pic50 = None

        molecules.append({
            "chembl_id": chembl_id,
            "smiles": smiles,
            "pic50": pic50
        })

    return molecules


_worker_conn = None


def init_worker(database_path):

    global _worker_conn

    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")

    from app.services.mcs_service import MCSService

    MCSService.MCS_SAMPLE_SIZE = MCS_SAMPLE_SIZE
    MCSService.MCS_TIMEOUT_SECONDS = MCS_TIMEOUT_SECONDS

    _worker_conn = sqlite3.connect(
        f"file:{database_path}?mode=ro",
        uri=True
    )


def process_target(job):

    from app.services.mcs_service import MCSService

    target_chembl_id, uniprot_id, target_name = job

    started = time.time()

    try:

        molecules = load_molecules(_worker_conn, target_chembl_id)

        result = MCSService.analyze(
            molecules,
            detail_limit=10 ** 9,
            draw=False
        )

        error = None

    except Exception as exc:  # keep the build going

        molecules = []
        result = None
        error = f"{type(exc).__name__}: {exc}"

    return {
        "job": job,
        "molecules": len(molecules),
        "result": result,
        "error": error,
        "seconds": time.time() - started
    }


def store(out, payload):

    target_chembl_id, uniprot_id, target_name = payload["job"]

    result = payload["result"]

    # An unavailable result (fewer than two valid molecules) is still
    # recorded, so the target is not retried on every restart.

    summary = (result or {}).get("summary") or {}

    out.execute(
        "INSERT OR REPLACE INTO mcs_targets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            target_chembl_id,
            uniprot_id,
            target_name,
            payload["molecules"],
            summary.get("molecules_clustered", 0),
            1 if summary.get("truncated") else 0,
            summary.get("series_total", 0),
            summary.get("singletons", 0),
            summary.get("mcs_success", 0),
            summary.get("mcs_timeout", 0),
            summary.get("largest_series", 0)
        )
    )

    out.execute(
        "DELETE FROM mcs_series WHERE target_chembl_id = ?",
        (target_chembl_id,)
    )

    for entry in (result or {}).get("series", []):

        activity = entry["activity"]

        members = ",".join(
            m["chembl_id"] for m in entry["molecules"]
        )

        out.execute(
            "INSERT INTO mcs_series VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                target_chembl_id,
                entry["id"],
                entry["number_of_molecules"],
                entry["scaffolds_in_series"],
                entry["mcs_status"],
                entry["mcs_smarts"],
                entry["mcs_atoms"],
                entry["mcs_bonds"],
                entry["mcs_coverage"],
                activity.get("median_pic50"),
                activity.get("min_pic50"),
                activity.get("max_pic50"),
                activity.get("count"),
                entry["representative"]["chembl_id"],
                entry["representative"]["smiles"],
                members
            )
        )

    out.commit()


def main():

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    workers = 2

    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
        args = [a for a in args if a != str(workers)]

    if not args:
        print(__doc__)
        sys.exit(1)

    database_path = Path(args[0])

    output = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT

    output.parent.mkdir(parents=True, exist_ok=True)

    out = sqlite3.connect(output)

    out.executescript(SCHEMA)

    source = sqlite3.connect(database_path)

    targets = source.execute(
        """
        SELECT t.target_chembl_id, t.uniprot_id, t.target_name, c.n
        FROM targets t
        JOIN (
            SELECT target_chembl_id, COUNT(DISTINCT molecule_chembl_id) n
            FROM activities
            WHERE standard_relation = '='
              AND canonical_smiles IS NOT NULL
              AND standard_value IS NOT NULL
            GROUP BY target_chembl_id
        ) c ON c.target_chembl_id = t.target_chembl_id
        WHERE t.uniprot_id IS NOT NULL
        ORDER BY c.n
        """
    ).fetchall()

    source.close()

    done = {
        row[0] for row in out.execute(
            "SELECT target_chembl_id FROM mcs_targets"
        )
    }

    jobs = [
        (t[0], t[1], t[2]) for t in targets if t[0] not in done
    ]

    print(
        f"{len(targets)} targets with data, "
        f"{len(done)} already done, {len(jobs)} to build "
        f"({workers} workers)",
        flush=True
    )

    out.execute(
        "INSERT OR REPLACE INTO mcs_meta VALUES (?, ?)",
        (
            "parameters",
            json.dumps({
                "similarity_cutoff": 0.6,
                "fingerprint": "Morgan radius 2, 2048 bits",
                "clustering": "Taylor-Butina on Tanimoto distance",
                "mcs_sample_size": MCS_SAMPLE_SIZE,
                "mcs_timeout_seconds": MCS_TIMEOUT_SECONDS,
                "mcs_threshold": 1.0
            })
        )
    )

    out.commit()

    started = time.time()

    finished = 0

    with Pool(
        workers,
        initializer=init_worker,
        initargs=(str(database_path),)
    ) as pool:

        for payload in pool.imap_unordered(process_target, jobs):

            if payload["error"]:
                print(
                    f"  ! {payload['job'][0]}: {payload['error']}",
                    flush=True
                )
                continue

            store(out, payload)

            finished += 1

            if finished % 25 == 0 or payload["seconds"] > 60:
                elapsed = time.time() - started
                print(
                    f"{finished}/{len(jobs)} targets  "
                    f"last={payload['job'][0]} "
                    f"({payload['molecules']} mols, "
                    f"{payload['seconds']:.0f}s)  "
                    f"elapsed {elapsed / 60:.1f} min",
                    flush=True
                )

    out.execute("VACUUM")
    out.close()

    gz_path = Path(str(output) + ".gz")

    with open(output, "rb") as src, gzip.open(
        gz_path, "wb", compresslevel=9
    ) as dst:
        shutil.copyfileobj(src, dst)

    print(
        f"Done in {(time.time() - started) / 60:.1f} min. "
        f"{output} ({output.stat().st_size / 1e6:.1f} MB), "
        f"{gz_path} ({gz_path.stat().st_size / 1e6:.1f} MB)",
        flush=True
    )


if __name__ == "__main__":
    main()
