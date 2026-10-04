import re
import logging
from typing import List, Optional
from app.models.investigation import SourceReference
from app.services.vector_store import vector_store
from app.config import settings

logger = logging.getLogger(__name__)

QUERY_STOP_WORDS = {
    "what", "when", "where", "which", "how", "many", "much", "does", "an", "the",
    "is", "are", "per", "for", "in", "can", "to", "of", "a", "and", "with", "from",
    "company", "employee", "employees", "available",
}


def _normalize_word(word: str) -> str:
    return word[:-1] if len(word) > 4 and word.endswith("s") else word


class Retriever:
    def __init__(self):
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = None
    ) -> List[SourceReference]:
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        if top_k <= 0:
            return []

        raw_results = self.vector_store.query(
            query_text=query,
            n_results=top_k * 3,
            document_ids=document_ids
        )

        if not raw_results:
            return []

        # Hybrid Keyword + Semantic Scoring
        query_words = {
            _normalize_word(word)
            for word in re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower())
            if word not in QUERY_STOP_WORDS
        }
        
        scored_sources = []
        for r in raw_results:
            text = r["text"]
            text_words = {
                _normalize_word(word)
                for word in re.findall(r'\b[a-zA-Z0-9]{3,}\b', text.lower())
            }
            word_hits = len(query_words & text_words)
            keyword_score = (word_hits / len(query_words)) if query_words else 0.0

            # Combined score: 60% semantic similarity, 40% keyword match
            combined_score = (0.6 * r["similarity_score"]) + (0.4 * keyword_score)
            if combined_score < settings.SIMILARITY_THRESHOLD:
                continue

            scored_sources.append({
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "filename": r["filename"],
                "page_number": r["page_number"],
                "text": text,
                "file_type": r["file_type"],
                "page_number_approximate": r.get("page_number_approximate", False),
                "relevance_score": round(combined_score, 4)
            })

        # Sort by combined score descending
        scored_sources.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Pick top_k and convert to SourceReference
        selected = scored_sources[:top_k]

        return [
            SourceReference(
                document_id=s["document_id"],
                filename=s["filename"],
                page_number=s["page_number"],
                chunk_id=s["chunk_id"],
                text=s["text"],
                file_type=s["file_type"],
                relevance_score=s["relevance_score"],
                page_number_approximate=s["page_number_approximate"]
            )
            for s in selected
        ]

retriever = Retriever()
