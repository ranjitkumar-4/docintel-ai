import time
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.models.investigation import (
    InvestigationRequest,
    InvestigationResult,
    ShareInvestigationResponse
)
from app.services.retriever import retriever
from app.services.answer_generator import answer_generator
from app.services.document_manager import document_manager

router = APIRouter(prefix="/api/investigation", tags=["investigation"])

@router.post("/ask", response_model=InvestigationResult)
async def ask_question(request: InvestigationRequest):
    """
    Core RAG Investigation Pipeline:
    1. Query embedding and semantic search
    2. Hybrid retrieval of top relevant chunks with page metadata
    3. Cross-document conflict detection
    4. Grounded answer generation or uncertainty handling
    5. History storage
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    start_time = time.time()
    investigation_id = f"inv_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now().isoformat()

    # Retrieve relevant sources
    sources = retriever.retrieve(
        query=question,
        document_ids=request.document_ids
    )

    # Generate answer with conflict checks and uncertainty handling
    result = answer_generator.generate_investigation(
        investigation_id=investigation_id,
        question=question,
        sources=sources,
        created_at=created_at
    )

    result.processing_time_ms = int((time.time() - start_time) * 1000)

    # Persist in investigation history
    document_manager.add_investigation(result)

    return result

@router.get("/history", response_model=List[InvestigationResult])
async def get_investigation_history():
    """Returns previous investigations in reverse chronological order."""
    return document_manager.get_investigations()

@router.get("/{investigation_id}", response_model=InvestigationResult)
async def get_investigation(investigation_id: str):
    """Retrieves a single investigation by ID for viewing or sharing."""
    inv = document_manager.get_investigation_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return inv

@router.post("/{investigation_id}/share", response_model=ShareInvestigationResponse)
async def share_investigation(investigation_id: str):
    """Generates a shareable URL for a persisted investigation."""
    inv = document_manager.get_investigation_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    
    return ShareInvestigationResponse(
        investigation_id=investigation_id,
        share_url=f"/#investigation-{investigation_id}",
        created_at=inv.created_at
    )
