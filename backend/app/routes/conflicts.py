from typing import List
from fastapi import APIRouter, HTTPException
from app.models.conflict import ConflictItem, ConflictResolveRequest
from app.services.document_manager import document_manager

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])

@router.get("", response_model=List[ConflictItem])
async def get_conflicts():
    """Returns all detected cross-document conflicts."""
    return document_manager.get_conflicts()

@router.post("/{conflict_id}/resolve", response_model=ConflictItem)
async def resolve_conflict(conflict_id: str, request: ConflictResolveRequest):
    """Marks a conflict as resolved or unresolved."""
    item = document_manager.resolve_conflict(conflict_id, status=request.status)
    if not item:
        raise HTTPException(status_code=404, detail="Conflict record not found.")
    return item

@router.post("/scan")
async def trigger_conflict_scan():
    """Runs a proactive conflict scan across all indexed documents."""
    document_manager.scan_and_record_conflicts()
    return {"message": "Conflict scan completed.", "total_conflicts": len(document_manager.get_conflicts())}
