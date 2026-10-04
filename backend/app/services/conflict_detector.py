import re
import logging
from typing import List, Dict, Any, Optional
from app.models.investigation import SourceReference, ConflictDetectionResult, ConflictingSource
from app.models.conflict import ConflictItem

logger = logging.getLogger(__name__)

class ConflictDetector:
    """
    Detects contradictory statements across different documents for a given topic or query.
    Requires that both conflicting statements share the same domain context and are relevant
    to the user's question.
    """

    def check_conflicts(
        self,
        question: str,
        sources: List[SourceReference]
    ) -> ConflictDetectionResult:
        if not sources or len(sources) < 2:
            return ConflictDetectionResult(conflict_detected=False)

        # Filter sources to only those that have reasonable relevance to the question
        question_words = self._extract_question_keywords(question)
        relevant_sources = [
            s for s in sources 
            if self._source_matches_keywords(s.text, question_words) and s.relevance_score >= 0.15
        ]

        if len(relevant_sources) < 2:
            return ConflictDetectionResult(conflict_detected=False)

        # Group sources by document
        doc_sources: Dict[str, List[SourceReference]] = {}
        for s in relevant_sources:
            doc_sources.setdefault(s.filename, []).append(s)

        # Must have at least 2 distinct documents discussing the relevant subject
        if len(doc_sources) < 2:
            return ConflictDetectionResult(conflict_detected=False)

        filenames = list(doc_sources.keys())

        # Check pairs of different documents
        for i in range(len(filenames)):
            for j in range(i + 1, len(filenames)):
                doc_a = filenames[i]
                doc_b = filenames[j]
                
                chunks_a = doc_sources[doc_a]
                chunks_b = doc_sources[doc_b]

                for ca in chunks_a:
                    for cb in chunks_b:
                        conflict = self._detect_pairwise_conflict(question, ca, cb)
                        if conflict:
                            return conflict

        return ConflictDetectionResult(conflict_detected=False)

    def _detect_pairwise_conflict(
        self,
        question: str,
        source_a: SourceReference,
        source_b: SourceReference
    ) -> Optional[ConflictDetectionResult]:
        text_a = source_a.text
        text_b = source_b.text

        # Target specific conflict topics
        # Topic 1: Leave / Vacation / Time Off
        q_lower = question.lower()
        if any(w in q_lower for w in ["leave", "vacation", "pto", "holiday", "time off"]):
            conflict = self._check_leave_conflict(source_a, source_b)
            if conflict:
                return conflict

        # Topic 2: Probation period
        if "probation" in q_lower:
            conflict = self._check_duration_conflict(source_a, source_b, "probation", "Probation Period")
            if conflict:
                return conflict

        # Topic 3: Notice period
        if "notice" in q_lower:
            conflict = self._check_duration_conflict(source_a, source_b, "notice", "Notice Period")
            if conflict:
                return conflict

        # Topic 4: Working hours
        if any(w in q_lower for w in ["hour", "timing", "schedule"]):
            conflict = self._check_hours_conflict(source_a, source_b)
            if conflict:
                return conflict

        # Topic 5: General numeric policy conflicts where both discuss the EXACT same entity
        q_keywords = self._extract_question_keywords(question)
        if q_keywords:
            conflict = self._check_keyword_numeric_conflict(source_a, source_b, q_keywords)
            if conflict:
                return conflict

        conflict = self._check_related_contradiction(question, source_a, source_b)
        if conflict:
            return conflict

        return None

    def _check_leave_conflict(
        self,
        source_a: SourceReference,
        source_b: SourceReference
    ) -> Optional[ConflictDetectionResult]:
        leave_pat = re.compile(
            r'(?:\b(?P<before>\d+|twenty|eighteen|fifteen|ten|twelve|fourteen|twenty-five)\b\s*'
            r'(?:paid\s+leaves?|days\s+(?:of\s+)?paid\s+leave|annual\s+leaves?|days\s+leave|vacation\s+days)'
            r'|annual\s+paid\s+leave\s+allowance\s*(?:is|:)?\s*'
            r'(?P<after>\d+|twenty|eighteen|fifteen|ten|twelve|fourteen|twenty-five)\s+days?)',
            re.IGNORECASE
        )

        match_a = leave_pat.search(source_a.text)
        match_b = leave_pat.search(source_b.text)

        if match_a and match_b:
            val_a = self._normalize_number(match_a.group("before") or match_a.group("after"))
            val_b = self._normalize_number(match_b.group("before") or match_b.group("after"))

            if val_a != val_b:
                sent_a = self._extract_sentence(source_a.text, match_a.start())
                sent_b = self._extract_sentence(source_b.text, match_b.start())

                return ConflictDetectionResult(
                    conflict_detected=True,
                    conflict_topic="Paid Leave Allowance",
                    summary=(
                        f"Discrepancy detected: {source_a.filename} states {val_a} days of paid leave, "
                        f"while {source_b.filename} states {val_b} days."
                    ),
                    conflicting_sources=[
                        ConflictingSource(
                            document_name=source_a.filename,
                            page_number=source_a.page_number,
                            statement=sent_a,
                            chunk_id=source_a.chunk_id,
                            page_number_approximate=source_a.file_type.lower() == "docx"
                        ),
                        ConflictingSource(
                            document_name=source_b.filename,
                            page_number=source_b.page_number,
                            statement=sent_b,
                            chunk_id=source_b.chunk_id,
                            page_number_approximate=source_b.file_type.lower() == "docx"
                        )
                    ],
                    recommendation="Please verify which document is the latest official policy."
                )
        return None

    def _check_duration_conflict(
        self,
        source_a: SourceReference,
        source_b: SourceReference,
        keyword: str,
        topic_title: str
    ) -> Optional[ConflictDetectionResult]:
        pat = re.compile(
            rf'(\b\d+\b|\b(?:one|two|three|four|five|six|90|thirty|sixty|ninety)\b)\s*(?:months?|weeks?|days?)[^.]*?\b{keyword}\b|\b{keyword}\b[^.]*?(\b\d+\b|\b(?:one|two|three|four|five|six|90|thirty|sixty|ninety)\b)\s*(?:months?|weeks?|days?)',
            re.IGNORECASE
        )
        ma = pat.search(source_a.text)
        mb = pat.search(source_b.text)

        if ma and mb:
            val_a = self._normalize_number(ma.group(1) or ma.group(2))
            val_b = self._normalize_number(mb.group(1) or mb.group(2))
            if val_a != val_b:
                sent_a = self._extract_sentence(source_a.text, ma.start())
                sent_b = self._extract_sentence(source_b.text, mb.start())
                return ConflictDetectionResult(
                    conflict_detected=True,
                    conflict_topic=topic_title,
                    summary=f"Conflicting durations stated for {topic_title}: {val_a} vs {val_b}.",
                    conflicting_sources=[
                        ConflictingSource(
                            document_name=source_a.filename,
                            page_number=source_a.page_number,
                            statement=sent_a,
                            chunk_id=source_a.chunk_id,
                            page_number_approximate=source_a.file_type.lower() == "docx"
                        ),
                        ConflictingSource(
                            document_name=source_b.filename,
                            page_number=source_b.page_number,
                            statement=sent_b,
                            chunk_id=source_b.chunk_id,
                            page_number_approximate=source_b.file_type.lower() == "docx"
                        )
                    ],
                    recommendation="Please consult HR to confirm which guideline is active."
                )
        return None

    def _check_hours_conflict(
        self,
        source_a: SourceReference,
        source_b: SourceReference
    ) -> Optional[ConflictDetectionResult]:
        time_pat = re.compile(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', re.IGNORECASE)
        times_a = time_pat.findall(source_a.text)
        times_b = time_pat.findall(source_b.text)
        if times_a and times_b and set(times_a) != set(times_b):
            # Check if both sentences talk about working/business hours
            if "business hour" in source_a.text.lower() and "business hour" in source_b.text.lower():
                return ConflictDetectionResult(
                    conflict_detected=True,
                    conflict_topic="Working Hours",
                    summary="Conflicting working hours schedule found across documents.",
                    conflicting_sources=[
                        ConflictingSource(
                            document_name=source_a.filename,
                            page_number=source_a.page_number,
                            statement=source_a.text[:150] + "...",
                            chunk_id=source_a.chunk_id,
                            page_number_approximate=source_a.file_type.lower() == "docx"
                        ),
                        ConflictingSource(
                            document_name=source_b.filename,
                            page_number=source_b.page_number,
                            statement=source_b.text[:150] + "...",
                            chunk_id=source_b.chunk_id,
                            page_number_approximate=source_b.file_type.lower() == "docx"
                        )
                    ],
                    recommendation="Confirm the standard working hours with your department head."
                )
        return None

    def _check_keyword_numeric_conflict(
        self,
        source_a: SourceReference,
        source_b: SourceReference,
        keywords: List[str]
    ) -> Optional[ConflictDetectionResult]:
        topic_terms = self._shared_topic_terms(keywords, source_a.text, source_b.text)
        if not topic_terms:
            return None
        number_pattern = re.compile(
            r'(?<!\w)(?:\$|USD\s*)?\d+(?:\.\d+)?\s*'
            r'(?:days?|weeks?|months?|years?|hours?|minutes?|percent|%)?',
            re.IGNORECASE,
        )
        values_a = self._context_values(source_a.text, topic_terms, number_pattern)
        values_b = self._context_values(source_b.text, topic_terms, number_pattern)
        if values_a and values_b and values_a[0][0] != values_b[0][0]:
            return self._build_conflict(
                f"{' '.join(term.title() for term in sorted(topic_terms))} Policy",
                source_a,
                values_a[0][1],
                source_b,
                values_b[0][1],
                f"Related statements differ: {values_a[0][0]} versus {values_b[0][0]}.",
            )
        return None

    def _check_related_contradiction(
        self,
        question: str,
        source_a: SourceReference,
        source_b: SourceReference,
    ) -> Optional[ConflictDetectionResult]:
        topic_terms = self._shared_topic_terms(
            self._extract_question_keywords(question),
            source_a.text,
            source_b.text,
        )
        if not topic_terms:
            return None
        contexts_a = self._context_sentences(source_a.text, topic_terms)
        contexts_b = self._context_sentences(source_b.text, topic_terms)
        categories = {
            "permission": (
                r"\b(?:not\s+allowed|not\s+permitted|prohibited|forbidden|"
                r"may\s+not|cannot|can't|must\s+not)\b",
                r"\b(?:allowed|permitted|may|can)\b",
            ),
            "requirement": (
                r"\b(?:not\s+required|not\s+mandatory|optional|need\s+not|"
                r"not\s+necessary)\b",
                r"\b(?:required|mandatory|must)\b",
            ),
            "inclusion": (
                r"\b(?:excluded|not\s+(?:include(?:d|s)?|cover(?:ed|s)?|provide(?:d|s)?))\b",
                r"\b(?:include(?:d|s)?|cover(?:ed|s)?|provide(?:d|s)?)\b",
            ),
        }
        for topic, (negative_pattern, positive_pattern) in categories.items():
            state_a = self._polarity_state(contexts_a, negative_pattern, positive_pattern)
            state_b = self._polarity_state(contexts_b, negative_pattern, positive_pattern)
            if state_a and state_b and state_a[0] != state_b[0]:
                return self._build_conflict(
                    f"{' '.join(term.title() for term in sorted(topic_terms))} {topic.title()}",
                    source_a,
                    state_a[1],
                    source_b,
                    state_b[1],
                    f"Documents make opposing {topic} claims about the same subject.",
                )

        yes_no_a = self._yes_no_context(contexts_a)
        yes_no_b = self._yes_no_context(contexts_b)
        if yes_no_a and yes_no_b and yes_no_a[0] != yes_no_b[0]:
            return self._build_conflict(
                f"{' '.join(term.title() for term in sorted(topic_terms))} Policy",
                source_a,
                yes_no_a[1],
                source_b,
                yes_no_b[1],
                "Documents provide opposing yes/no claims about the same subject.",
            )
        return None

    @staticmethod
    def _shared_topic_terms(keywords: List[str], text_a: str, text_b: str) -> set[str]:
        relation_words = {
            "allowed", "allow", "permitted", "permit", "prohibited", "forbidden",
            "required", "require", "mandatory", "optional", "included", "excluded",
            "covered", "provided", "policy", "yes", "no",
        }
        tokens_a = set(re.findall(r"\b[a-z0-9]{3,}\b", text_a.lower()))
        tokens_b = set(re.findall(r"\b[a-z0-9]{3,}\b", text_b.lower()))
        return {
            word for word in keywords
            if word not in relation_words and word in tokens_a and word in tokens_b
        }

    @staticmethod
    def _context_sentences(text: str, topic_terms: set[str]) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+|\n+|;", text)
        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
            and any(
                re.search(rf"\b{re.escape(term)}\b", sentence, re.IGNORECASE)
                for term in topic_terms
            )
        ]

    @staticmethod
    def _context_values(
        text: str,
        topic_terms: set[str],
        number_pattern: re.Pattern,
    ) -> List[tuple[str, str]]:
        values = []
        for sentence in ConflictDetector._context_sentences(text, topic_terms):
            match = number_pattern.search(sentence)
            if match:
                value = re.sub(r"\s+", " ", match.group(0)).strip().lower()
                values.append((value, sentence))
        return values

    @staticmethod
    def _polarity_state(
        contexts: List[str],
        negative_pattern: str,
        positive_pattern: str,
    ) -> Optional[tuple[str, str]]:
        negative = re.compile(negative_pattern, re.IGNORECASE)
        positive = re.compile(positive_pattern, re.IGNORECASE)
        for sentence in contexts:
            if negative.search(sentence):
                return "negative", sentence
            if positive.search(sentence):
                return "positive", sentence
        return None

    @staticmethod
    def _yes_no_context(contexts: List[str]) -> Optional[tuple[str, str]]:
        for sentence in contexts:
            match = re.search(r"(?:^|[:\s])\b(yes|no)\b(?:[,.\s]|$)", sentence, re.IGNORECASE)
            if match:
                return match.group(1).lower(), sentence
        return None

    @staticmethod
    def _build_conflict(
        topic: str,
        source_a: SourceReference,
        statement_a: str,
        source_b: SourceReference,
        statement_b: str,
        summary: str,
    ) -> ConflictDetectionResult:
        return ConflictDetectionResult(
            conflict_detected=True,
            conflict_topic=topic,
            summary=summary,
            conflicting_sources=[
                ConflictingSource(
                    document_name=source_a.filename,
                    page_number=source_a.page_number,
                    statement=statement_a,
                    chunk_id=source_a.chunk_id,
                    page_number_approximate=source_a.file_type.lower() == "docx",
                ),
                ConflictingSource(
                    document_name=source_b.filename,
                    page_number=source_b.page_number,
                    statement=statement_b,
                    chunk_id=source_b.chunk_id,
                    page_number_approximate=source_b.file_type.lower() == "docx",
                ),
            ],
            recommendation="Please verify which document is the latest official policy.",
        )

    def _normalize_number(self, num_str: Optional[str]) -> str:
        if not num_str:
            return ""
        mapping = {
            "twenty": "20",
            "eighteen": "18",
            "fifteen": "15",
            "twelve": "12",
            "ten": "10",
            "three": "3",
            "six": "6",
            "ninety": "90"
        }
        clean = num_str.lower().strip()
        return mapping.get(clean, clean)

    def _extract_sentence(self, text: str, index: int) -> str:
        start = max(text.rfind('.', 0, index), text.rfind('\n', 0, index)) + 1
        ends = [
            position for position in (text.find('.', index), text.find('\n', index))
            if position != -1
        ]
        if ends:
            boundary = min(ends)
            end = boundary + (1 if text[boundary] == '.' else 0)
        else:
            end = len(text)
        sentence = text[start:end].replace('\n', ' ').strip()
        return sentence

    def _extract_question_keywords(self, question: str) -> List[str]:
        stop_words = {
            'what', 'when', 'where', 'which', 'how', 'many', 'much', 'does', 'an', 'a', 'the',
            'is', 'are', 'per', 'for', 'in', 'can', 'employee', 'take', 'receive', 'policy', 'about'
        }
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
        return [w for w in words if w not in stop_words]

    def _source_matches_keywords(self, text: str, keywords: List[str]) -> bool:
        if not keywords:
            return True
        t_lower = text.lower()
        return any(k in t_lower for k in keywords)

conflict_detector = ConflictDetector()
