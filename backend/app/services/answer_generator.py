import re
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings
from app.models.investigation import (
    SourceReference,
    InvestigationResult,
    ConflictDetectionResult
)
from app.services.conflict_detector import conflict_detector

logger = logging.getLogger(__name__)

class AnswerProviderError(RuntimeError):
    """Raised when the configured external answer provider cannot produce an answer."""


GENERIC_WORDS = {
    'policy', 'policies', 'guideline', 'guidelines', 'rule', 'rules', 'office', 'company',
    'work', 'working', 'employee', 'employees', 'what', 'when', 'where', 'which', 'how',
    'many', 'much', 'does', 'an', 'a', 'the', 'is', 'are', 'per', 'for', 'in', 'can',
    'take', 'receive', 'about', 'with', 'from', 'have', 'been', 'their', 'there', 'tell',
    'show', 'give', 'bringing', 'bring', 'standard', 'standards', 'general', 'procedure',
    'procedures', 'internal', 'corporate', 'organization', 'provide', 'provided', 'available'
}

class AnswerGenerator:
    """
    Generates evidence-grounded answers from retrieved chunks, abstains when evidence
    is insufficient, and surfaces detected conflicts with LOW confidence.
    """

    def generate_investigation(
        self,
        investigation_id: str,
        question: str,
        sources: List[SourceReference],
        created_at: str
    ) -> InvestigationResult:
        # Step 1: Check if any sources were retrieved
        if not sources or len(sources) == 0:
            return self._build_not_found_result(investigation_id, question, created_at)

        # Require evidence for most of the question's substantive terms; a shared
        # generic term (e.g. "insurance") alone cannot support a narrower claim.
        specific_keywords = self._extract_specific_keywords(question)
        matching_sources = []
        if specific_keywords:
            minimum_matches = min(2, len(specific_keywords))
            for source in sources:
                matches = self._matched_keywords(source.text, specific_keywords)
                coverage = len(matches) / len(specific_keywords)
                if len(matches) >= minimum_matches and coverage >= 0.65:
                    matching_sources.append(source)
        else:
            matching_sources = [
                s for s in sources
                if s.relevance_score >= settings.SIMILARITY_THRESHOLD
            ]

        if not matching_sources:
            return self._build_not_found_result(investigation_id, question, created_at)

        # Step 3: Run Conflict Detection across matching relevant sources
        conflict_result = conflict_detector.check_conflicts(question, matching_sources)
        if conflict_result.conflict_detected:
            conflict_chunk_ids = {
                source.chunk_id for source in conflict_result.conflicting_sources
                if source.chunk_id
            }
            supporting_sources = [
                source for source in matching_sources
                if source.chunk_id in conflict_chunk_ids
            ]
            return self._build_conflict_result(
                investigation_id,
                question,
                supporting_sources,
                conflict_result,
                created_at
            )

        # Step 4: Answer generation via LLM or Local Grounded Engine
        provider = settings.LLM_PROVIDER.lower()
        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise AnswerProviderError("OpenAI is selected but OPENAI_API_KEY is not configured on the backend.")
            try:
                return self._generate_openai_answer(investigation_id, question, matching_sources, created_at)
            except Exception as e:
                logger.exception("OpenAI answer generation failed.")
                raise AnswerProviderError(
                    "OpenAI answer generation failed. Check the backend API key, provider availability, "
                    "and network connection; no local fallback answer was generated."
                ) from e

        if provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise AnswerProviderError("Gemini is selected but GEMINI_API_KEY is not configured on the backend.")
            try:
                return self._generate_gemini_answer(investigation_id, question, matching_sources, created_at)
            except Exception as e:
                logger.exception("Gemini answer generation failed.")
                raise AnswerProviderError(
                    "Gemini answer generation failed. Check the backend API key, provider availability, "
                    "and network connection; no local fallback answer was generated."
                ) from e

        if provider == "local":
            return self._generate_local_grounded_answer(
                investigation_id, question, matching_sources, created_at
            )
        raise AnswerProviderError(
            f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. Use local, openai, or gemini."
        )

    def _extract_specific_keywords(self, question: str) -> List[str]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
        specific = [w for w in words if w not in GENERIC_WORDS]
        return specific

    def _matched_keywords(self, text: str, keywords: List[str]) -> List[str]:
        text_words = {
            self._normalize_word(word)
            for word in re.findall(r'\b[a-zA-Z0-9]{3,}\b', text.lower())
        }
        return [
            keyword for keyword in keywords
            if self._normalize_word(keyword) in text_words
        ]

    @staticmethod
    def _normalize_word(word: str) -> str:
        return word[:-1] if len(word) > 4 and word.endswith("s") else word

    @staticmethod
    def _confidence_for_sources(sources: List[SourceReference]) -> str:
        if not sources:
            return "NOT FOUND"
        strongest_relevance = max(source.relevance_score for source in sources)
        independent_documents = len({source.document_id for source in sources})
        if strongest_relevance >= 0.65 and independent_documents >= 2:
            return "HIGH"
        if strongest_relevance >= 0.55:
            return "HIGH"
        if strongest_relevance >= settings.SIMILARITY_THRESHOLD:
            return "MEDIUM"
        return "LOW"

    def _build_not_found_result(
        self,
        investigation_id: str,
        question: str,
        created_at: str
    ) -> InvestigationResult:
        return InvestigationResult(
            id=investigation_id,
            question=question,
            answer="Information not found.",
            confidence="NOT FOUND",
            confidence_reason="No document in the knowledge base contains relevant facts or policies addressing this query.",
            uncertainty_reason="No sufficiently relevant supporting evidence was found in the uploaded documents.",
            sources=[],
            conflict_detected=False,
            is_uncertain_or_not_found=True,
            created_at=created_at
        )

    def _build_conflict_result(
        self,
        investigation_id: str,
        question: str,
        sources: List[SourceReference],
        conflict: ConflictDetectionResult,
        created_at: str
    ) -> InvestigationResult:
        statements_lines = []
        for c in sorted(conflict.conflicting_sources, key=lambda item: item.document_name.lower()):
            statements_lines.append(f"• **{c.document_name}** (Page {c.page_number}): \"{c.statement}\"")

        answer_text = (
            f"⚠ **CONFLICT DETECTED**\n\n"
            f"Conflicting information was found across your documents regarding **{conflict.conflict_topic}**:\n\n"
            + "\n".join(statements_lines) + "\n\n"
            f"**Recommendation**: {conflict.recommendation or 'Please verify which document is the latest official policy.'}\n"
            f"DocIntel AI does not choose one value over another when sources disagree."
        )

        return InvestigationResult(
            id=investigation_id,
            question=question,
            answer=answer_text,
            confidence="LOW",
            confidence_reason="Discrepancy detected across multiple official documents on this topic.",
            sources=sources,
            conflict_detected=True,
            conflict_topic=conflict.conflict_topic,
            conflict_summary=conflict.summary,
            conflicting_sources=conflict.conflicting_sources,
            recommendation=conflict.recommendation or "Please verify which document is the latest official policy.",
            is_uncertain_or_not_found=False,
            created_at=created_at
        )

    def _generate_local_grounded_answer(
        self,
        investigation_id: str,
        question: str,
        sources: List[SourceReference],
        created_at: str
    ) -> InvestigationResult:
        top_source = sources[0]
        q_words = self._extract_specific_keywords(question)
        if not q_words:
            q_words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())

        def split_sentences(text: str) -> List[str]:
            return [
                sentence.strip()
                for sentence in re.split(r'(?<=[.!?])\s+|\n+', text)
                if len(sentence.strip()) > 10
            ]

        sentences = split_sentences(top_source.text)
        scored = []
        for s in sentences:
            score = len(self._matched_keywords(s, q_words))
            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        minimum_sentence_matches = min(2, len(q_words))

        if scored and scored[0][0] >= minimum_sentence_matches:
            matching_sents = [
                s[1] for s in scored if s[0] == scored[0][0]
            ][:2]
            answer_text = " ".join(matching_sents)
            supporting_sources = [
                source for source in sources
                if any(
                    len(self._matched_keywords(sentence, q_words)) >= minimum_sentence_matches
                    for sentence in split_sentences(source.text)
                )
            ]
            best_coverage = scored[0][0] / max(len(q_words), 1)
            if (
                top_source.relevance_score >= 0.55
                and best_coverage >= 0.7
                and supporting_sources
            ):
                confidence = "HIGH"
            elif (
                top_source.relevance_score >= settings.SIMILARITY_THRESHOLD
                and best_coverage >= 0.5
                and supporting_sources
            ):
                confidence = "MEDIUM"
            else:
                return self._build_not_found_result(investigation_id, question, created_at)
            confidence_reason = (
                f"Evidence relevance {top_source.relevance_score:.2f}; "
                f"question-term coverage {best_coverage:.0%}; "
                f"{len(supporting_sources)} supporting source(s)."
            )
        else:
            return self._build_not_found_result(investigation_id, question, created_at)

        return InvestigationResult(
            id=investigation_id,
            question=question,
            answer=answer_text,
            confidence=confidence,
            confidence_reason=confidence_reason,
            sources=supporting_sources,
            conflict_detected=False,
            is_uncertain_or_not_found=False,
            created_at=created_at
        )

    def _generate_openai_answer(
        self,
        investigation_id: str,
        question: str,
        sources: List[SourceReference],
        created_at: str
    ) -> InvestigationResult:
        context_blocks = "\n\n".join(
            f"--- Document: {s.filename} (Page {s.page_number}, Chunk {s.chunk_id}) ---\n{s.text}"
            for s in sources
        )

        prompt = f"""You are DocIntel AI, a strict, factual document investigator.
Answer the user's question using ONLY the provided document excerpts below.

CRITICAL INSTRUCTIONS:
1. Ground your answer strictly in the context. Do NOT invent facts or hallucinate.
2. If the context does not contain enough information to answer, state clearly: "I could not find reliable information about this question in the uploaded documents."
3. Cite the document name and page number for supporting facts.
4. If there is a contradiction between documents, explicitly highlight both viewpoints and express uncertainty.

Context:
{context_blocks}

Question:
{question}
"""

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a professional document intelligence assistant. Never hallucinate."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            answer_text = data["choices"][0]["message"]["content"].strip()

        is_not_found = "could not find reliable information" in answer_text.lower() or "not mentioned" in answer_text.lower()
        confidence = "NOT FOUND" if is_not_found else self._confidence_for_sources(sources)

        return InvestigationResult(
            id=investigation_id,
            question=question,
            answer=answer_text,
            confidence=confidence,
            confidence_reason="Generated with OpenAI gpt-4o-mini strictly grounded on retrieved source chunks.",
            sources=[] if is_not_found else sources,
            conflict_detected=False,
            is_uncertain_or_not_found=is_not_found,
            uncertainty_reason=(
                "The generated response did not identify supporting evidence in the retrieved excerpts."
                if is_not_found else None
            ),
            created_at=created_at
        )

    def _generate_gemini_answer(
        self,
        investigation_id: str,
        question: str,
        sources: List[SourceReference],
        created_at: str
    ) -> InvestigationResult:
        context_blocks = "\n\n".join(
            f"--- Document: {s.filename} (Page {s.page_number}, Chunk {s.chunk_id}) ---\n{s.text}"
            for s in sources
        )

        prompt = f"""You are DocIntel AI, a strict, factual document investigator.
Answer the user's question using ONLY the provided document excerpts below.

CRITICAL INSTRUCTIONS:
1. Answer only from the provided context. Do not invent facts.
2. If the context does not contain the answer, say: "I could not find reliable information about this question in the uploaded documents."
3. Cite the document filename and page number.
4. If sources conflict, explicitly mention the conflict.

Context:
{context_blocks}

Question:
{question}
"""

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            answer_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        is_not_found = "could not find reliable information" in answer_text.lower() or "not mentioned" in answer_text.lower()
        confidence = "NOT FOUND" if is_not_found else self._confidence_for_sources(sources)

        return InvestigationResult(
            id=investigation_id,
            question=question,
            answer=answer_text,
            confidence=confidence,
            confidence_reason="Generated with Google Gemini 1.5 Flash strictly grounded on retrieved sources.",
            sources=[] if is_not_found else sources,
            conflict_detected=False,
            is_uncertain_or_not_found=is_not_found,
            uncertainty_reason=(
                "The generated response did not identify supporting evidence in the retrieved excerpts."
                if is_not_found else None
            ),
            created_at=created_at
        )

answer_generator = AnswerGenerator()
