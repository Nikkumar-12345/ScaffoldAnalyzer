from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    uniprot_id: str