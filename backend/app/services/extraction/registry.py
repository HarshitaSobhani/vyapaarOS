from pathlib import PurePath

from app.core.errors import AppError
from app.services.extraction.base import InvoiceExtractor
from app.services.extraction.json_extractor import JSONInvoiceExtractor
from app.services.extraction.pdf_extractor import PDFInvoiceExtractor

EXTRACTORS: tuple[InvoiceExtractor, ...] = (JSONInvoiceExtractor(), PDFInvoiceExtractor())
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".tiff")


def extractor_for(filename: str) -> InvoiceExtractor:
    ext = PurePath(filename.lower()).suffix
    for ex in EXTRACTORS:
        if ext in ex.extensions:
            return ex
    if ext in IMAGE_EXTENSIONS:
        raise AppError("Image invoices need an OCR extractor, which is not configured. "
                       "Upload JSON, CSV or a text PDF.", 415, "unsupported_file")
    raise AppError("Unsupported file type. Upload .json, .csv or .pdf", 415, "unsupported_file")
