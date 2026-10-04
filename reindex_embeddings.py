#!/usr/bin/env python3
"""Build a new Chroma collection for the configured embedding profile, then activate it."""

import logging
import sys
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.chunker import chunk_document_pages
from app.services.docx_extractor import extract_text_from_docx
from app.services.document_manager import document_manager
from app.services.embeddings import embedding_function
from app.services.ocr import extract_text_from_image
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.vector_store import VectorStore, vector_store
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reindex_embeddings")


def extract_pages(file_path: str, file_type: str):
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    if file_type == "docx":
        return extract_text_from_docx(file_path)
    if file_type in {"jpg", "jpeg", "png"}:
        return [{"page_number": 1, "text": extract_text_from_image(file_path)}]
    if file_type in {"txt", "md", "csv", "json"}:
        return [{
            "page_number": 1,
            "text": Path(file_path).read_text(encoding="utf-8", errors="strict"),
        }]
    raise ValueError(f"Unsupported document type for reindexing: {file_type}")


def main() -> int:
    indexed_documents = [
        document for document in document_manager.get_all_documents()
        if document.status == "indexed" and document.chunks_count > 0
    ]
    missing_files = [
        document.filename for document in indexed_documents
        if not Path(document.file_path).is_file()
    ]
    if missing_files:
        logger.error(
            "Cannot reindex safely because source files are missing: %s",
            ", ".join(missing_files),
        )
        return 1

    profile = embedding_function.profile
    staging_name = f"docintel_reindex_{uuid.uuid4().hex[:12]}"
    staging_store = VectorStore(
        persist_dir=settings.CHROMA_PERSIST_DIR,
        collection_name=staging_name,
    )
    expected_chunks = 0

    try:
        for document in indexed_documents:
            pages = extract_pages(document.file_path, document.file_type.lower())
            pages_with_text = [page for page in pages if page.get("text", "").strip()]
            chunks = chunk_document_pages(
                document_id=document.id,
                filename=document.filename,
                file_type=document.file_type.lower(),
                pages_data=pages_with_text,
            )
            if not chunks:
                raise ValueError(f"No readable content could be reindexed for {document.filename}.")
            staging_store.add_chunks(chunks)
            expected_chunks += len(chunks)
            logger.info("Staged %s: %d chunks", document.filename, len(chunks))

        actual_chunks = staging_store.get_chunk_count()
        if actual_chunks != expected_chunks:
            raise RuntimeError(
                f"Staged index contains {actual_chunks} chunks; expected {expected_chunks}."
            )
        vector_store.activate_collection(staging_name)
        logger.info(
            "Activated collection %s using %s/%s (%d dimensions); previous collections were preserved.",
            staging_name,
            profile["embedding_provider"],
            profile["embedding_model"],
            profile["embedding_dimension"],
        )
        return 0
    except Exception:
        logger.exception(
            "Embedding reindex failed. The active collection was not intentionally deleted; "
            "the staging collection may be removed after investigation."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
