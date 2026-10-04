import os
import logging
import shutil
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)
COMMON_TESSERACT_PATHS = (
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/opt/local/bin/tesseract",
)

class OCRUnavailableError(RuntimeError):
    """Raised when the pytesseract wrapper cannot find the Tesseract executable."""


def ensure_tesseract_available() -> None:
    executable = pytesseract.pytesseract.tesseract_cmd
    resolved_executable = shutil.which(executable) or (
        executable if os.path.isfile(executable) and os.access(executable, os.X_OK) else None
    )
    if not resolved_executable:
        resolved_executable = shutil.which("tesseract")
    if not resolved_executable:
        resolved_executable = next(
            (
                path
                for path in COMMON_TESSERACT_PATHS
                if os.path.isfile(path) and os.access(path, os.X_OK)
            ),
            None,
        )
    if not resolved_executable:
        raise OCRUnavailableError(
            "OCR unavailable: Tesseract is not installed or could not be found. "
            "Install it with `brew install tesseract` on macOS or `sudo apt-get install "
            "tesseract-ocr` on Debian/Ubuntu, then restart the backend."
        )
    pytesseract.pytesseract.tesseract_cmd = resolved_executable
    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError, OSError) as exc:
        raise OCRUnavailableError(
            f"OCR unavailable: Tesseract was found at '{resolved_executable}' but could not "
            f"run successfully ({exc}). Check the installation and language data."
        ) from exc


def tesseract_available() -> bool:
    try:
        ensure_tesseract_available()
    except OCRUnavailableError:
        return False
    return True


def extract_text_from_image(image_path: str) -> str:
    """
    Extracts text from an image file (JPG, JPEG, PNG).
    Uses pytesseract and fails explicitly when OCR is unavailable or finds no text.
    """
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        ensure_tesseract_available()
        with Image.open(image_path) as source_image:
            image = source_image.copy()
        if image.mode not in ('L', 'RGB'):
            image = image.convert('RGB')
        try:
            text = pytesseract.image_to_string(image)
            text = text.strip()
            if text:
                return text
        except pytesseract.TesseractNotFoundError as ocr_err:
            raise OCRUnavailableError(
                "OCR unavailable: Tesseract could not be started. Install Tesseract "
                "and ensure its executable is on PATH."
            ) from ocr_err
        except pytesseract.TesseractError as ocr_err:
            raise ValueError(f"OCR failed while reading image: {ocr_err}") from ocr_err

        raise ValueError("OCR completed but found no readable text in the image.")

    except OCRUnavailableError:
        raise
    except Exception as e:
        logger.error(f"Error extracting text from image {image_path}: {e}")
        raise ValueError(f"Failed to process image: {str(e)}")
