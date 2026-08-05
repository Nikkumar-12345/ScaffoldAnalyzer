from fastapi import APIRouter

from app.schemas.analyze_schema import AnalyzeRequest
from app.services.analysis_service import AnalysisService

router = APIRouter(
    prefix="/analyze",
    tags=["Analyze"]
)

analysis = AnalysisService()


@router.post("/")
def analyze(request: AnalyzeRequest):

    return analysis.analyze(
        request.uniprot_id
    )