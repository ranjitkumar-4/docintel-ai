import os
import json
import uuid
import logging
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings
from app.models.document import DocumentInfo, DocumentDetail, DocumentChunk
from app.models.investigation import InvestigationResult
from app.models.conflict import ConflictItem
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.docx_extractor import extract_text_from_docx
from app.services.ocr import extract_text_from_image
from app.services.chunker import chunk_document_pages
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

DOCS_FILE = os.path.join(settings.DATA_DIR, "documents.json")
INVESTIGATIONS_FILE = os.path.join(settings.DATA_DIR, "investigations.json")
CONFLICTS_FILE = os.path.join(settings.DATA_DIR, "conflicts.json")

class DocumentManager:
    def __init__(self):
        self.documents: Dict[str, DocumentInfo] = {}
        self.doc_chunks: Dict[str, List[DocumentChunk]] = {}
        self.investigations: List[InvestigationResult] = []
        self.conflicts: List[ConflictItem] = []
        self.restoration_error: Optional[str] = None
        self._load_state()
        self._restore_document_chunks()

    def _load_state(self):
        for path, loader in (
            (DOCS_FILE, self._load_documents),
            (INVESTIGATIONS_FILE, self._load_investigations),
            (CONFLICTS_FILE, self._load_conflicts),
        ):
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                loader(data)
            except (OSError, ValueError, TypeError) as e:
                message = f"Unable to restore persisted state from {path}: {e}"
                logger.exception(message)
                self.restoration_error = message

    def _load_documents(self, data: List[Dict[str, Any]]) -> None:
        for item in data:
            if "upload_status" not in item:
                item["upload_status"] = (
                    "FAILED" if item.get("status") == "failed" else "SUCCESS"
                )
            document = DocumentInfo(**item)
            self.documents[document.id] = document

    def _load_investigations(self, data: List[Dict[str, Any]]) -> None:
        self.investigations = [InvestigationResult(**item) for item in data]

    def _load_conflicts(self, data: List[Dict[str, Any]]) -> None:
        self.conflicts = [ConflictItem(**item) for item in data]

    def _restore_document_chunks(self) -> None:
        for document in self.documents.values():
            if document.status != "indexed" or document.chunks_count == 0:
                continue
            try:
                chunks = vector_store.get_document_chunks(document.id)
                if len(chunks) != document.chunks_count:
                    raise RuntimeError(
                        f"Registry has {document.chunks_count} chunks but the vector index "
                        f"restored {len(chunks)} for {document.filename}."
                    )
                self.doc_chunks[document.id] = chunks
            except Exception as exc:
                message = f"Unable to restore indexed chunks for {document.filename}: {exc}"
                logger.error(message)
                self.restoration_error = message

    def _save_state(self):
        self._save_json_atomic(
            DOCS_FILE,
            [doc.model_dump() for doc in self.documents.values()],
        )
        self._save_json_atomic(
            INVESTIGATIONS_FILE,
            [investigation.model_dump() for investigation in self.investigations],
        )
        self._save_json_atomic(
            CONFLICTS_FILE,
            [conflict.model_dump() for conflict in self.conflicts],
        )

    @staticmethod
    def _save_json_atomic(path: str, data: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=os.path.dirname(path),
                delete=False,
            ) as state_file:
                temporary_path = state_file.name
                json.dump(data, state_file, indent=2)
                state_file.flush()
                os.fsync(state_file.fileno())
            os.replace(temporary_path, path)
        except OSError:
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise

    def get_all_documents(self) -> List[DocumentInfo]:
        return list(self.documents.values())

    def get_document(self, doc_id: str) -> Optional[DocumentDetail]:
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        chunks = self.doc_chunks.get(doc_id)
        if chunks is None and doc.status == "indexed":
            chunks = vector_store.get_document_chunks(doc_id)
            if len(chunks) != doc.chunks_count:
                raise RuntimeError(
                    f"Document index is incomplete for {doc.filename}; reindex the document "
                    "after resolving the vector-store configuration."
                )
            self.doc_chunks[doc_id] = chunks
        chunks = chunks or []
        return DocumentDetail(**doc.model_dump(), chunks=chunks)

    def process_and_index_file(
        self,
        file_path: str,
        filename: str,
        file_type: str,
        doc_id: Optional[str] = None,
        scan_conflicts: bool = True
    ) -> DocumentInfo:
        if not doc_id:
            doc_id = str(uuid.uuid4())[:8]

        file_size = os.path.getsize(file_path)
        now_str = datetime.now().isoformat()

        doc_info = DocumentInfo(
            id=doc_id,
            filename=filename,
            file_type=file_type.lower(),
            file_path=file_path,
            file_size_bytes=file_size,
            pages=1,
            chunks_count=0,
            text_extracted_chars=0,
            status="extracting",
            upload_status="FAILED",
            created_at=now_str,
            updated_at=now_str
        )
        self.documents[doc_id] = doc_info
        self._save_state()

        try:
            # 1. Extraction
            pages_data: List[Dict[str, Any]] = []
            ext = file_type.lower().replace('.', '')

            if ext == 'pdf':
                pages_data = extract_text_from_pdf(file_path)
            elif ext == 'docx':
                pages_data = extract_text_from_docx(file_path)
            elif ext in ['jpg', 'jpeg', 'png']:
                img_text = extract_text_from_image(file_path)
                pages_data = [{"page_number": 1, "text": img_text}]
            elif ext in ['txt', 'md', 'csv', 'json']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    txt_content = f.read()
                pages_data = [{"page_number": 1, "text": txt_content}]
            else:
                raise ValueError(f"Unsupported file type: {ext}")

            total_pages = len(pages_data)
            warnings = [p["warning"] for p in pages_data if p.get("warning")]
            pages_with_text = [
                p for p in pages_data if p.get("text", "").strip()
            ]
            if not pages_with_text:
                if warnings:
                    raise ValueError("; ".join(dict.fromkeys(warnings)))
                raise ValueError("No readable text was extracted from the document.")

            total_chars = sum(len(p.get("text", "")) for p in pages_with_text)

            doc_info.pages = total_pages
            doc_info.text_extracted_chars = total_chars
            doc_info.status = "chunking"
            self._save_state()

            # 2. Chunking
            chunks = chunk_document_pages(
                document_id=doc_id,
                filename=filename,
                file_type=ext,
                pages_data=pages_with_text
            )
            if not chunks:
                raise ValueError("No readable text could be split into indexable chunks.")
            self.doc_chunks[doc_id] = chunks

            doc_info.chunks_count = len(chunks)
            doc_info.status = "indexing"
            self._save_state()

            # 3. Vector Indexing
            vector_store.delete_document_chunks(doc_id)
            vector_store.add_chunks(chunks)

            doc_info.status = "indexed"
            doc_info.upload_status = "PARTIAL" if warnings else "SUCCESS"
            doc_info.error_message = "; ".join(dict.fromkeys(warnings)) if warnings else None
            doc_info.updated_at = datetime.now().isoformat()
            self._save_state()

            # 4. Background conflict scan across all docs
            if scan_conflicts:
                self.scan_and_record_conflicts()

            return doc_info

        except Exception as e:
            logger.error(f"Failed processing file {filename}: {e}")
            try:
                vector_store.delete_document_chunks(doc_id)
            except Exception as cleanup_error:
                logger.error(
                    "Could not remove failed chunks for %s while the index is unavailable: %s",
                    filename,
                    cleanup_error,
                )
            self.doc_chunks.pop(doc_id, None)
            doc_info.status = "failed"
            doc_info.upload_status = "FAILED"
            doc_info.chunks_count = 0
            doc_info.text_extracted_chars = 0
            doc_info.error_message = str(e)
            doc_info.updated_at = datetime.now().isoformat()
            self._save_state()
            return doc_info

    def seed_demo_corpus(self, reset: bool = False) -> List[DocumentInfo]:
        from app.services.demo_data import generate_demo_files

        demo_files = generate_demo_files()
        demo_names = {filename for _, filename, _ in demo_files}
        canonical_ids = {
            filename: f"demo-{os.path.splitext(filename)[0].lower().replace('_', '-')}"
            for filename in demo_names
        }

        # Remove legacy duplicate records for the known demo filenames only.
        # The reset operation deliberately leaves all non-demo documents and files intact.
        for doc_id, doc in list(self.documents.items()):
            canonical_id = canonical_ids.get(doc.filename)
            if canonical_id and (reset or doc_id != canonical_id):
                self.documents.pop(doc_id, None)
                self.doc_chunks.pop(doc_id, None)
                vector_store.delete_document_chunks(doc_id)

        self.conflicts = [
            conflict for conflict in self.conflicts
            if conflict.document_a_name not in demo_names
            and conflict.document_b_name not in demo_names
        ]
        self._save_state()

        results = [
            self.process_and_index_file(
                file_path=file_path,
                filename=filename,
                file_type=file_type,
                doc_id=canonical_ids[filename],
                scan_conflicts=False
            )
            for file_path, filename, file_type in demo_files
        ]
        self.scan_and_record_conflicts()
        return results

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self.documents:
            doc = self.documents.pop(doc_id)
            self.doc_chunks.pop(doc_id, None)
            vector_store.delete_document_chunks(doc_id)
            
            # Remove file if exists
            if os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except Exception as e:
                    logger.warning(f"Could not delete physical file: {e}")

            # Re-scan conflicts
            self.scan_and_record_conflicts()
            self._save_state()
            return True
        return False

    def reindex_document(self, doc_id: str) -> Optional[DocumentInfo]:
        doc = self.documents.get(doc_id)
        if not doc or not os.path.exists(doc.file_path):
            return None
        return self.process_and_index_file(doc.file_path, doc.filename, doc.file_type, doc_id=doc.id)

    def add_investigation(self, result: InvestigationResult):
        # Insert at front of history
        self.investigations.insert(0, result)
        if len(self.investigations) > 100:
            self.investigations = self.investigations[:100]
        
        # If conflict was detected during investigation, record it in conflicts table
        if result.conflict_detected and result.conflicting_sources and len(result.conflicting_sources) >= 2:
            src_a = result.conflicting_sources[0]
            src_b = result.conflicting_sources[1]
            conflict_id = f"conf_{uuid.uuid4().hex[:6]}"
            
            # Check if this pair already exists
            existing = any(
                c.topic == result.conflict_topic and c.document_a_name == src_a.document_name and c.document_b_name == src_b.document_name
                for c in self.conflicts
            )
            if not existing:
                self.conflicts.insert(0, ConflictItem(
                    id=conflict_id,
                    topic=result.conflict_topic or "Disputed Policy",
                    document_a_name=src_a.document_name,
                    document_a_page=src_a.page_number,
                    document_a_page_approximate=src_a.page_number_approximate,
                    document_a_statement=src_a.statement,
                    document_b_name=src_b.document_name,
                    document_b_page=src_b.page_number,
                    document_b_page_approximate=src_b.page_number_approximate,
                    document_b_statement=src_b.statement,
                    confidence="LOW",
                    status="unresolved",
                    recommendation=result.recommendation,
                    investigation_id=result.id,
                    detected_at=result.created_at
                ))
        self._save_state()

    def get_investigations(self) -> List[InvestigationResult]:
        return self.investigations

    def get_investigation_by_id(self, inv_id: str) -> Optional[InvestigationResult]:
        for inv in self.investigations:
            if inv.id == inv_id:
                return inv
        return None

    def get_conflicts(self) -> List[ConflictItem]:
        return self.conflicts

    def resolve_conflict(self, conflict_id: str, status: str = "resolved") -> Optional[ConflictItem]:
        for c in self.conflicts:
            if c.id == conflict_id:
                c.status = status
                self._save_state()
                return c
        return None

    def scan_and_record_conflicts(self):
        """
        Scans across indexed documents for known or detected contradictions.
        """
        # Built-in heuristic check across all indexed text
        all_docs = list(self.documents.values())
        if len(all_docs) < 2:
            return

        # Common cross-document probe questions
        probes = [
            "How many paid leaves can an employee take?",
            "What is the probation period for new employees?",
            "What is the notice period for resignation?"
        ]

        from app.services.retriever import retriever
        from app.services.conflict_detector import conflict_detector

        for probe in probes:
            sources = retriever.retrieve(probe, top_k=4)
            conflict_res = conflict_detector.check_conflicts(probe, sources)
            if conflict_res.conflict_detected and len(conflict_res.conflicting_sources) >= 2:
                src_a = conflict_res.conflicting_sources[0]
                src_b = conflict_res.conflicting_sources[1]
                
                # Check duplicate
                exists = any(
                    c.document_a_name == src_a.document_name and c.document_b_name == src_b.document_name and c.topic == conflict_res.conflict_topic
                    for c in self.conflicts
                )
                if not exists:
                    self.conflicts.append(ConflictItem(
                        id=f"conf_{uuid.uuid4().hex[:6]}",
                        topic=conflict_res.conflict_topic or "Discrepancy",
                        document_a_name=src_a.document_name,
                        document_a_page=src_a.page_number,
                        document_a_page_approximate=src_a.page_number_approximate,
                        document_a_statement=src_a.statement,
                        document_b_name=src_b.document_name,
                        document_b_page=src_b.page_number,
                        document_b_page_approximate=src_b.page_number_approximate,
                        document_b_statement=src_b.statement,
                        confidence="LOW",
                        status="unresolved",
                        recommendation=conflict_res.recommendation,
                        detected_at=datetime.now().isoformat()
                    ))
        self._save_state()

document_manager = DocumentManager()
