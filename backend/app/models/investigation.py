from typing import List, Optional
from pydantic import BaseModel, Field

class SourceReference(BaseModel):
    document_id: str
    filename: str
    page_number: int
    chunk_id: str
    text: str
    file_type: str
    relevance_score: float = 0.0
    page_number_approximate: bool = False

class ConflictingSource(BaseModel):
    document_name: str
    page_number: int
    statement: str
    chunk_id: Optional[str] = None
    page_number_approximate: bool = False

class ConflictDetectionResult(BaseModel):
    conflict_detected: bool = False
    conflict_topic: Optional[str] = None
    summary: Optional[str] = None
    conflicting_sources: List[ConflictingSource] = Field(default_factory=list)
    recommendation: Optional[str] = None

class InvestigationRequest(BaseModel):
    question: str
    document_ids: Optional[List[str]] = None

class InvestigationResult(BaseModel):
    id: str
    question: str
    answer: str
    confidence: str  # "HIGH", "MEDIUM", "LOW", or "NOT FOUND"
    confidence_reason: str
    uncertainty_reason: Optional[str] = None
    sources: List[SourceReference] = Field(default_factory=list)
    conflict_detected: bool = False
    conflict_topic: Optional[str] = None
    conflict_summary: Optional[str] = None
    conflicting_sources: List[ConflictingSource] = Field(default_factory=list)
    recommendation: Optional[str] = None
    is_uncertain_or_not_found: bool = False
    processing_time_ms: int = 0
    created_at: str

class ShareInvestigationResponse(BaseModel):
    investigation_id: str
    share_url: str
    created_at: str
