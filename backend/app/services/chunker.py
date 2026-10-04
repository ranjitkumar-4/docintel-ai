import re
from typing import List, Dict, Any
from app.models.document import DocumentChunk
from app.config import settings

def chunk_document_pages(
    document_id: str,
    filename: str,
    file_type: str,
    pages_data: List[Dict[str, Any]],
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[DocumentChunk]:
    """
    Chunks document pages into semantic chunks while preserving page numbers and source metadata.
    Uses paragraph and sentence boundary splitting with configurable size and overlap.
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = settings.CHUNK_OVERLAP
    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Chunk overlap must be non-negative and smaller than chunk size.")

    chunks: List[DocumentChunk] = []
    chunk_global_idx = 0

    for page_item in pages_data:
        page_num = page_item.get("page_number", 1)
        raw_text = page_item.get("text", "").strip()

        if not raw_text:
            continue

        # Split page text into paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n{2,}|\r\n{2,}', raw_text) if p.strip()]
        
        # If paragraphs are too large, further split into sentences
        units: List[str] = []
        for p in paragraphs:
            if len(p) <= chunk_size:
                units.append(p)
            else:
                sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p) if s.strip()]
                for sentence in sentences:
                    if len(sentence) <= chunk_size:
                        units.append(sentence)
                        continue
                    words = sentence.split()
                    segment = ""
                    for word in words:
                        if len(word) > chunk_size:
                            if segment:
                                units.append(segment)
                                segment = ""
                            units.extend(
                                word[start:start + chunk_size]
                                for start in range(0, len(word), chunk_size)
                            )
                            continue
                        candidate = f"{segment} {word}".strip()
                        if segment and len(candidate) > chunk_size:
                            units.append(segment)
                            segment = word
                        else:
                            segment = candidate
                    if segment:
                        units.append(segment)

        current_chunk_parts: List[str] = []
        current_len = 0

        for unit in units:
            unit_len = len(unit)
            if current_len + unit_len + 1 > chunk_size and current_chunk_parts:
                chunk_text = "\n".join(current_chunk_parts).strip()
                chunk_global_idx += 1
                chunk_id = f"{document_id}_p{page_num}_c{chunk_global_idx}"
                
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    filename=filename,
                    page_number=page_num,
                    text=chunk_text,
                    file_type=file_type,
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "page_number": page_num,
                        "chunk_id": chunk_id,
                        "file_type": file_type,
                    }
                ))

                # Slide window with overlap
                overlap_parts: List[str] = []
                overlap_len = 0
                for part in reversed(current_chunk_parts):
                    if overlap_len + len(part) <= chunk_overlap:
                        overlap_parts.insert(0, part)
                        overlap_len += len(part)
                    else:
                        break
                if overlap_len + unit_len + 1 > chunk_size:
                    overlap_parts = []
                    overlap_len = 0
                current_chunk_parts = overlap_parts
                current_len = overlap_len

            current_chunk_parts.append(unit)
            current_len += unit_len + 1

        # Add remaining parts
        if current_chunk_parts:
            chunk_text = "\n".join(current_chunk_parts).strip()
            if chunk_text:
                chunk_global_idx += 1
                chunk_id = f"{document_id}_p{page_num}_c{chunk_global_idx}"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    filename=filename,
                    page_number=page_num,
                    text=chunk_text,
                    file_type=file_type,
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "page_number": page_num,
                        "chunk_id": chunk_id,
                        "file_type": file_type,
                    }
                ))

    return chunks
