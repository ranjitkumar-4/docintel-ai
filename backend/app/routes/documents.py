import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.config import settings
from app.models.document import DocumentInfo, DocumentDetail
from app.services.document_manager import document_manager

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

def _failed_upload(filename: str, file_type: str, size: int, message: str) -> DocumentInfo:
    now = datetime.now().isoformat()
    return DocumentInfo(
        id=str(uuid.uuid4())[:8],
        filename=filename,
        file_type=file_type,
        file_path="",
        file_size_bytes=size,
        pages=0,
        chunks_count=0,
        text_extracted_chars=0,
        status="failed",
        upload_status="FAILED",
        error_message=message,
        created_at=now,
        updated_at=now,
    )


@router.post("/upload", response_model=List[DocumentInfo])
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Accepts multiple documents, extracts text, chunks them, and indexes into ChromaDB.
    Supported formats: PDF, DOCX, TXT, JPG, JPEG, PNG.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    processed_docs: List[DocumentInfo] = []

    for file in files:
        original_filename = Path(file.filename or "unnamed").name
        ext = os.path.splitext(original_filename)[1].lower()
        content = await file.read(MAX_FILE_SIZE_BYTES + 1)
        if ext not in ALLOWED_EXTENSIONS:
            processed_docs.append(_failed_upload(
                original_filename,
                ext.lstrip(".") or "unknown",
                len(content),
                f"Unsupported file type '{ext or '(none)'}'. Supported formats: PDF, DOCX, TXT, JPG, JPEG, PNG. "
                "Legacy .doc files are not supported."
            ))
            continue

        if len(content) > MAX_FILE_SIZE_BYTES:
            processed_docs.append(_failed_upload(
                original_filename,
                ext.lstrip("."),
                len(content),
                "File exceeds the maximum allowed size of 25 MB."
            ))
            continue
        if not content:
            processed_docs.append(_failed_upload(
                original_filename,
                ext.lstrip("."),
                0,
                "File is empty."
            ))
            continue

        safe_filename = original_filename.replace(" ", "_")
        doc_id = str(uuid.uuid4())[:8]
        dest_filename = f"{doc_id}_{safe_filename}"
        dest_path = os.path.join(settings.UPLOAD_DIR, dest_filename)

        try:
            with open(dest_path, "wb") as f:
                f.write(content)
        except OSError as exc:
            logger.exception("Unable to save upload %s", original_filename)
            processed_docs.append(_failed_upload(
                original_filename,
                ext.lstrip("."),
                len(content),
                f"Unable to save uploaded file: {exc}"
            ))
            continue

        doc_info = document_manager.process_and_index_file(
            file_path=dest_path,
            filename=original_filename,
            file_type=ext.replace('.', ''),
            doc_id=doc_id
        )
        processed_docs.append(doc_info)

    return processed_docs

@router.get("", response_model=List[DocumentInfo])
async def get_all_documents():
    """Returns list of all registered documents and their status."""
    return document_manager.get_all_documents()

@router.get("/{doc_id}", response_model=DocumentDetail)
async def get_document(doc_id: str):
    """Returns detailed information and all chunks for a document."""
    doc = document_manager.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Deletes a document, its physical file, and its vector chunks."""
    success = document_manager.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"message": f"Document {doc_id} successfully deleted."}

@router.post("/{doc_id}/reindex", response_model=DocumentInfo)
async def reindex_document(doc_id: str):
    """Re-extracts, re-chunks, and re-indexes a document."""
    doc = document_manager.reindex_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or file missing.")
    return doc

@router.post("/seed-demo", response_model=List[DocumentInfo])
async def seed_demo_documents(reset: bool = Query(False)):
    """Idempotently generates and indexes the canonical demo corpus."""
    return document_manager.seed_demo_corpus(reset=reset)
