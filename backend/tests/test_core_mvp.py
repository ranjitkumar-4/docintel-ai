import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from PIL import Image
from fastapi import UploadFile

from app.config import settings
from app.models.document import DocumentInfo
from app.models.investigation import SourceReference
from app.routes import documents as document_routes
from app.services import ocr, pdf_extractor
from app.services.answer_generator import AnswerGenerator
from app.services.embeddings import embedding_function
from app.services.retriever import Retriever
from app.services.vector_store import VectorStore


def source(
    filename: str,
    text: str,
    chunk_id: str,
    relevance: float = 0.8,
    file_type: str = "pdf",
) -> SourceReference:
    return SourceReference(
        document_id=filename,
        filename=filename,
        page_number=1,
        chunk_id=chunk_id,
        text=text,
        file_type=file_type,
        relevance_score=relevance,
    )


class OCRTests(unittest.TestCase):
    def test_image_ocr_fails_explicitly_without_tesseract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "notice.png"
            Image.new("RGB", (20, 20), "white").save(image_path)
            with patch.object(ocr.pytesseract.pytesseract, "tesseract_cmd", "/missing/tesseract"), \
                    patch.object(ocr.shutil, "which", return_value=None), \
                    patch.object(ocr, "COMMON_TESSERACT_PATHS", ()):
                with self.assertRaisesRegex(ocr.OCRUnavailableError, "Tesseract is not installed"):
                    ocr.extract_text_from_image(str(image_path))

    def test_empty_image_ocr_is_an_error_not_document_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "blank.png"
            Image.new("RGB", (20, 20), "white").save(image_path)
            with patch.object(ocr, "ensure_tesseract_available"), \
                    patch.object(ocr.pytesseract, "image_to_string", return_value=" \n"):
                with self.assertRaisesRegex(ValueError, "found no readable text"):
                    ocr.extract_text_from_image(str(image_path))

    def test_scanned_pdf_without_tesseract_has_no_placeholder_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "scanned.pdf"
            pdf = pymupdf.open()
            pdf.new_page()
            pdf.save(pdf_path)
            pdf.close()

            with patch.object(
                pdf_extractor,
                "ensure_tesseract_available",
                side_effect=ocr.OCRUnavailableError("OCR unavailable: Tesseract is missing."),
            ):
                pages = pdf_extractor.extract_text_from_pdf(str(pdf_path))

            self.assertEqual(pages[0]["text"], "")
            self.assertIn("OCR unavailable", pages[0]["warning"])
            self.assertNotIn("[Page", pages[0]["text"])


class RetrievalTests(unittest.TestCase):
    def test_chroma_cosine_distance_is_converted_to_similarity(self):
        class Collection:
            def count(self):
                return 2

            def query(self, **kwargs):
                self.kwargs = kwargs
                return {
                    "ids": [["first", "second"]],
                    "documents": [["first text", "second text"]],
                    "metadatas": [[
                        {"document_id": "doc-a", "filename": "a.pdf", "page_number": 1, "file_type": "pdf"},
                        {"document_id": "doc-b", "filename": "b.docx", "page_number": 1, "file_type": "docx"},
                    ]],
                    "distances": [[0.2, 0.8]],
                }

        store = VectorStore.__new__(VectorStore)
        store.collection = Collection()
        store.configuration_error = None
        store.collection.metadata = {
            **embedding_function.profile,
            "hnsw:space": "cosine",
        }
        results = store.query("query", n_results=2, document_ids=["doc-a"])
        self.assertAlmostEqual(results[0]["similarity_score"], 0.8)
        self.assertAlmostEqual(results[1]["similarity_score"], 0.2)
        self.assertTrue(results[1]["page_number_approximate"])
        self.assertEqual(store.collection.kwargs["where"], {"document_id": "doc-a"})

    def test_threshold_filters_weak_results_before_top_k(self):
        class Store:
            received_document_ids = None

            def query(self, query_text, n_results, document_ids):
                self.received_document_ids = document_ids
                return [
                    {
                        "chunk_id": "strong-a", "document_id": "doc-a", "filename": "a.pdf",
                        "page_number": 1, "text": "paid leave allowance", "file_type": "pdf",
                        "similarity_score": 0.9,
                    },
                    {
                        "chunk_id": "weak", "document_id": "doc-a", "filename": "a.pdf",
                        "page_number": 1, "text": "unrelated material", "file_type": "pdf",
                        "similarity_score": 0.1,
                    },
                    {
                        "chunk_id": "strong-b", "document_id": "doc-a", "filename": "a.pdf",
                        "page_number": 2, "text": "paid leave policy", "file_type": "pdf",
                        "similarity_score": 0.8,
                    },
                ]

        store = Store()
        retriever = Retriever()
        retriever.vector_store = store
        with patch.object(settings, "SIMILARITY_THRESHOLD", 0.25):
            results = retriever.retrieve("paid leave", document_ids=["doc-a"], top_k=1)

        self.assertEqual(store.received_document_ids, ["doc-a"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk_id, "strong-a")


class GroundingTests(unittest.TestCase):
    def test_leave_conflict_returns_both_sources_without_picking_a_value(self):
        result = AnswerGenerator().generate_investigation(
            "investigation",
            "How many paid leaves are available?",
            [
                source("Employee_Handbook.pdf", "Annual paid leave allowance is 18 days.", "handbook"),
                source("Company_Policy.pdf", "Annual paid leave allowance is 20 days.", "policy"),
            ],
            "now",
        )

        self.assertTrue(result.conflict_detected)
        self.assertEqual(result.confidence, "LOW")
        self.assertEqual(len(result.sources), 2)
        self.assertIn("18 days", result.answer)
        self.assertIn("20 days", result.answer)
        self.assertLess(
            result.answer.index("Company_Policy.pdf"),
            result.answer.index("Employee_Handbook.pdf"),
        )

    def test_partial_topical_overlap_does_not_answer_pet_insurance(self):
        result = AnswerGenerator().generate_investigation(
            "investigation",
            "What is the company's pet insurance policy?",
            [
                source(
                    "Company_Policy.pdf",
                    "Comprehensive medical insurance coverage is provided for all full-time staff.",
                    "insurance",
                )
            ],
            "now",
        )

        self.assertEqual(result.answer, "Information not found.")
        self.assertEqual(result.confidence, "NOT FOUND")
        self.assertTrue(result.is_uncertain_or_not_found)
        self.assertEqual(result.sources, [])
        self.assertTrue(result.uncertainty_reason)

    def test_supported_fact_returns_a_matching_source(self):
        result = AnswerGenerator().generate_investigation(
            "investigation",
            "What is the home office setup stipend for remote work?",
            [
                source(
                    "Remote_Work_Guidelines.docx",
                    "The company provides a one-time home office setup stipend of $500 for ergonomic monitors.",
                    "stipend",
                    file_type="docx",
                )
            ],
            "now",
        )

        self.assertIn("$500", result.answer)
        self.assertEqual(result.confidence, "HIGH")
        self.assertEqual([item.chunk_id for item in result.sources], ["stipend"])


class UploadValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_mixed_upload_batch_reports_per_file_outcomes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_doc = DocumentInfo(
                id="valid",
                filename="policy.txt",
                file_type="txt",
                file_path=str(Path(temp_dir) / "policy.txt"),
                file_size_bytes=3,
                pages=1,
                chunks_count=1,
                text_extracted_chars=3,
                status="indexed",
                upload_status="SUCCESS",
                created_at="now",
                updated_at="now",
            )
            partial_doc = valid_doc.model_copy(update={
                "id": "partial",
                "filename": "notice.png",
                "file_type": "png",
                "upload_status": "PARTIAL",
                "error_message": "Some PDF pages could not be OCRed.",
            })

            files = [
                UploadFile(filename="policy.txt", file=io.BytesIO(b"abc")),
                UploadFile(filename="empty.txt", file=io.BytesIO(b"")),
                UploadFile(filename="legacy.doc", file=io.BytesIO(b"not docx")),
                UploadFile(filename="notice.png", file=io.BytesIO(b"png")),
            ]
            with patch.object(settings, "UPLOAD_DIR", temp_dir), \
                    patch.object(document_routes.document_manager, "process_and_index_file",
                                 side_effect=[valid_doc, partial_doc]):
                results = await document_routes.upload_documents(files)

            self.assertEqual(
                [doc.upload_status for doc in results],
                ["SUCCESS", "FAILED", "FAILED", "PARTIAL"],
            )
            self.assertIn("empty", results[1].error_message.lower())
            self.assertIn(".doc", results[2].error_message)

    async def test_file_size_limit_is_reported_per_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(settings, "UPLOAD_DIR", temp_dir), \
                    patch.object(document_routes, "MAX_FILE_SIZE_BYTES", 3):
                results = await document_routes.upload_documents([
                    UploadFile(filename="large.txt", file=io.BytesIO(b"four"))
                ])
            self.assertEqual(results[0].upload_status, "FAILED")
            self.assertIn("25 MB", results[0].error_message)


if __name__ == "__main__":
    unittest.main()
