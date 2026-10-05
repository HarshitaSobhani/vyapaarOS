"""Best-effort text-PDF extraction (no OCR). Scanned images are rejected explicitly."""
import io
import re
from datetime import datetime
from decimal import Decimal

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.extraction.base import ExtractedInvoice, ExtractedLine, ExtractionError, InvoiceExtractor

LINE_RE = re.compile(r"^(?P<sku>[A-Z0-9][A-Z0-9\-]{2,})\s+(?P<desc>.+?)\s+(?P<qty>\d+)\s*[x×]\s*₹?(?P<price>[\d,]+(?:\.\d+)?)\s*$")
FIELD_RES = {
    "invoice_number": re.compile(r"Invoice(?:\s*No\.?|\s*Number|:)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]+)", re.I),
    "party": re.compile(r"(?:Bill\s*To|Customer|Buyer)\s*:\s*(.+)", re.I),
    "invoice_date": re.compile(r"(?<!Due )Date\s*:\s*(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w{3}\s+\d{4})", re.I),
    "due_date": re.compile(r"Due\s*Date\s*:\s*(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w{3}\s+\d{4})", re.I),
}


def _parse_date(raw: str | None):
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d %b %Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


class PDFInvoiceExtractor(InvoiceExtractor):
    name = "pdf-text"
    extensions = (".pdf",)

    def extract(self, data: bytes) -> list[ExtractedInvoice]:
        try:
            text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages)
        except (PdfReadError, ValueError, OSError) as exc:
            raise ExtractionError("Could not read PDF") from exc
        if not text.strip():
            raise ExtractionError("PDF has no extractable text (scanned documents need OCR, which "
                                  "is not enabled). Upload JSON or CSV instead.")
        m: dict[str, str | None] = {}
        for key, rx in FIELD_RES.items():
            found = rx.search(text)
            m[key] = found.group(1).strip() if found else None
        inv = ExtractedInvoice(m["invoice_number"], m["party"], _parse_date(m["invoice_date"]),
                               _parse_date(m["due_date"]))
        for n, line in enumerate(text.splitlines(), start=1):
            lm = LINE_RE.match(line.strip())
            if lm:
                inv.lines.append(ExtractedLine(lm["sku"], lm["desc"], Decimal(lm["qty"]),
                                               Decimal(lm["price"].replace(",", "")), n))
        if not inv.lines:
            inv.errors.append("No line items recognised in the PDF")
        return [inv]
