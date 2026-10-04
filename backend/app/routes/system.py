from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from app.config import settings
from app.services.document_manager import document_manager
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_function, EmbeddingConfigurationError
from app.services.ocr import tesseract_available

router = APIRouter(prefix="/api", tags=["system"])

class SettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_provider: str
    chunk_size: int = 500
    chunk_overlap: int = 100

@router.get("/health")
async def health_check():
    """Report backend, index, embedding profile, OCR, and persistence readiness."""
    vector_error = vector_store.configuration_error
    if not vector_error:
        try:
            vector_store.ensure_compatible()
        except Exception as exc:
            vector_error = str(exc)
    try:
        indexed_chunks = vector_store.collection.count() if not vector_error else 0
    except Exception as exc:
        vector_error = str(exc)
        indexed_chunks = 0
    ready = not vector_error and not document_manager.restoration_error
    profile = embedding_function.profile if not vector_error else None
    return {
        "status": "healthy" if ready else "degraded",
        "service": "DocIntel AI",
        "backend_online": True,
        "operational": ready,
        "indexed_chunks": indexed_chunks,
        "total_documents": len(document_manager.get_all_documents()),
        "llm_provider": settings.LLM_PROVIDER,
        "ocr_available": tesseract_available(),
        "vector_store_ready": not vector_error,
        "vector_store_error": vector_error,
        "persistence_error": document_manager.restoration_error,
        "embedding_profile": profile,
        "reset_enabled": (
            settings.ALLOW_DESTRUCTIVE_RESET
            and settings.APP_ENV.lower() != "production"
        ),
    }

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Returns summarized stats for dashboard display."""
    docs = document_manager.get_all_documents()
    chunks_count = vector_store.get_chunk_count()
    investigations = document_manager.get_investigations()
    conflicts = document_manager.get_conflicts()

    return {
        "documents_count": len(docs),
        "indexed_sections_count": chunks_count,
        "questions_asked_count": len(investigations),
        "conflicts_detected_count": len(conflicts),
        "recent_investigations": investigations[:5]
    }

@router.get("/settings")
async def get_settings():
    """Returns non-sensitive current settings."""
    try:
        embedding_dimension = embedding_function.profile["embedding_dimension"]
    except EmbeddingConfigurationError as exc:
        embedding_dimension = None
        embedding_error = str(exc)
    else:
        embedding_error = vector_store.configuration_error
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "embedding_model": settings.EMBEDDING_MODEL,
        "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_dimension": embedding_dimension,
        "vector_store_ready": not embedding_error,
        "vector_store_error": embedding_error,
        "reset_enabled": (
            settings.ALLOW_DESTRUCTIVE_RESET
            and settings.APP_ENV.lower() != "production"
        ),
    }

@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Updates settings in memory and config."""
    if settings.APP_ENV.lower() == "production":
        raise HTTPException(
            status_code=403,
            detail="Runtime settings updates are disabled in production; configure backend environment variables instead.",
        )
    if req.llm_provider.lower() not in {"local", "openai", "gemini"}:
        raise HTTPException(status_code=422, detail="Unsupported LLM provider.")
    if req.llm_provider.lower() == "openai" and not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=422, detail="Configure OPENAI_API_KEY on the backend first.")
    if req.llm_provider.lower() == "gemini" and not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=422, detail="Configure GEMINI_API_KEY on the backend first.")
    if req.chunk_size < 50 or req.chunk_overlap < 0 or req.chunk_overlap >= req.chunk_size:
        raise HTTPException(
            status_code=422,
            detail="Chunk size must be at least 50 and overlap must be non-negative and smaller than chunk size.",
        )
    settings.LLM_PROVIDER = req.llm_provider.lower()
    settings.CHUNK_SIZE = req.chunk_size
    settings.CHUNK_OVERLAP = req.chunk_overlap
    return {"message": "Settings updated successfully."}

@router.post("/system/reset")
async def reset_database():
    """Clears all documents, vector indices, investigations, and conflicts."""
    if settings.APP_ENV.lower() == "production" or not settings.ALLOW_DESTRUCTIVE_RESET:
        raise HTTPException(
            status_code=403,
            detail="Database reset is disabled. Enable ALLOW_DESTRUCTIVE_RESET only for a trusted local development environment.",
        )
    vector_store.clear_all()
    document_manager.documents.clear()
    document_manager.doc_chunks.clear()
    document_manager.investigations.clear()
    document_manager.conflicts.clear()
    document_manager._save_state()
    return {"message": "All document data and vector indices have been reset."}
