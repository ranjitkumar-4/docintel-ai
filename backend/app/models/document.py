from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    document_id: str
    filename: str
    page_number: int
    chunk_id: str
    file_type: str
    total_pages: Optional[int] = 1

class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    text: str
    file_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    file_path: str
    file_size_bytes: int
    pages: int = 1
    chunks_count: int = 0
    text_extracted_chars: int = 0
    status: str = "indexed"  # "uploading", "extracting", "chunking", "indexing", "indexed", "failed"
    upload_status: Literal["SUCCESS", "FAILED", "PARTIAL"] = "SUCCESS"
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

class DocumentDetail(DocumentInfo):
    chunks: List[DocumentChunk] = Field(default_factory=list)
