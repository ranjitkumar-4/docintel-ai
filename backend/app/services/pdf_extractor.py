import os
import logging
from typing import List, Dict, Any
import pymupdf  # PyMuPDF
from PIL import Image
import io
import pytesseract
from app.services.ocr import OCRUnavailableError, ensure_tesseract_available

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text page-by-page from a PDF file using PyMuPDF.
    If a page is scanned (empty text), falls back to OCR via page rendering.
    Returns: List of dicts with 'page_number' (1-indexed) and 'text'.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    pages_data: List[Dict[str, Any]] = []

    try:
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)

        if total_pages == 0:
            raise ValueError("The PDF document contains 0 pages.")

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_num = page_idx + 1
            text = page.get_text("text").strip()

            warning = None
            # If page text is very sparse or empty, it might be a scanned page.
            if len(text) < 15:
                try:
                    ensure_tesseract_available()
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes))
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if len(ocr_text) > len(text):
                        text = ocr_text
                    if not ocr_text:
                        warning = f"OCR found no readable text on scanned PDF page {page_num}."
                except OCRUnavailableError as ocr_e:
                    warning = str(ocr_e)
                except pytesseract.TesseractNotFoundError:
                    warning = (
                        "OCR unavailable: Tesseract could not be started. Install Tesseract "
                        "and ensure its executable is on PATH."
                    )
                except pytesseract.TesseractError as ocr_e:
                    warning = f"OCR failed on scanned PDF page {page_num}: {ocr_e}"
                except Exception as pix_e:
                    warning = f"Could not OCR scanned PDF page {page_num}: {pix_e}"

            page_data = {
                "page_number": page_num,
                "text": text
            }
            if warning:
                page_data["warning"] = warning
            pages_data.append(page_data)

        doc.close()
        return pages_data

    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {e}")
        raise ValueError(f"Corrupted or invalid PDF file: {str(e)}")
