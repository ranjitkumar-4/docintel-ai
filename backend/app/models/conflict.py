from typing import Optional
from pydantic import BaseModel

class ConflictItem(BaseModel):
    id: str
    topic: str
    document_a_name: str
    document_a_page: int
    document_a_page_approximate: bool = False
    document_a_statement: str
    document_b_name: str
    document_b_page: int
    document_b_page_approximate: bool = False
    document_b_statement: str
    confidence: str = "LOW"
    status: str = "unresolved"  # "unresolved" or "resolved"
    recommendation: Optional[str] = None
    investigation_id: Optional[str] = None
    detected_at: str

class ConflictResolveRequest(BaseModel):
    status: str = "resolved"  # "resolved" or "unresolved"
    notes: Optional[str] = None
