import gzip

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.schemas.analyze_schema import AnalyzeRequest
from app.services.errors import AnalysisError
from app.services.job_service import job_manager

router = APIRouter(
    prefix="/analyze",
    tags=["Analyze"]
)


def json_gzip_response(request: Request, data_gz: bytes):
    """Send pre-gzipped JSON, or plain JSON if gzip isn't accepted."""

    accepts = request.headers.get("accept-encoding", "")

    if "gzip" in accepts.lower():

        return Response(
            content=data_gz,
            media_type="application/json",
            headers={
                "Content-Encoding": "gzip",
                "Vary": "Accept-Encoding"
            }
        )

    return Response(
        content=gzip.decompress(data_gz),
        media_type="application/json"
    )


# --------------------------------------------------
# ORIGINAL SYNCHRONOUS ENDPOINT (unchanged contract)
# --------------------------------------------------

@router.post("/")
def analyze(request: AnalyzeRequest, http_request: Request):

    try:

        data = job_manager.run_sync(
            request.uniprot_id
        )

    except AnalysisError as error:

        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    return json_gzip_response(http_request, data)


# --------------------------------------------------
# BACKGROUND JOB + PROGRESS
# --------------------------------------------------

@router.post("/start")
def start_analysis(request: AnalyzeRequest):

    if not (request.uniprot_id or "").strip():

        raise HTTPException(
            status_code=400,
            detail="Please enter a UniProt ID (for example P00533)."
        )

    job = job_manager.start(
        request.uniprot_id
    )

    return job_manager.status(job.id)


@router.get("/status/{job_id}")
def analysis_status(job_id: str):

    status = job_manager.status(job_id)

    if status is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "This analysis job no longer exists (the server may "
                "have restarted). Please start the analysis again."
            )
        )

    return status


@router.get("/result/{job_id}")
def analysis_result(job_id: str, request: Request):

    job = job_manager.get(job_id)

    if job is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "This analysis job no longer exists (the server may "
                "have restarted). Please start the analysis again."
            )
        )

    if job.status == "error":

        raise HTTPException(
            status_code=job.error.get("http_status", 500),
            detail=job.error["message"]
        )

    if job.status != "done":

        raise HTTPException(
            status_code=409,
            detail="The analysis is still running."
        )

    return json_gzip_response(request, job.result_gz)
