import json

import pytest

from app.core.errors import AppError
from app.services.extraction.base import ExtractionError
from app.services.extraction.json_extractor import JSONInvoiceExtractor
from app.services.extraction.pdf_extractor import PDFInvoiceExtractor
from app.services.extraction.registry import extractor_for
from app.services.extraction.resolver import resolve_invoice


def make_pdf(lines: list[str]) -> bytes:
    """Minimal single-page text PDF (pypdf rebuilds the xref table itself)."""
    text = "BT /F1 11 Tf 40 780 Td 14 TL " + " ".join(f"({ln}) Tj T*" for ln in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text)} >>\nstream\n{text}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = "%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{off:010d} 00000 n \n" for off in offsets)
    out += f"trailer\n<< /Root 1 0 R /Size {len(objs) + 1} >>\nstartxref\n{xref}\n%%EOF"
    return out.encode()


def test_json_extractor_accepts_aliases_and_flags_bad_lines():
    data = json.dumps({"invoices": [{"invoice_number": "X1", "supplier": "ABC Electricals", "date": "2026-10-01",
                                     "items": [{"sku": "LED-B12", "qty": "5", "rate": "1,200"}, {"sku": "A", "quantity": "many"}]}]})
    [inv] = JSONInvoiceExtractor().extract(data.encode())
    assert inv.party_name == "ABC Electricals" and str(inv.lines[0].unit_price) == "1200"
    assert any("quantity" in e for e in inv.errors)


def test_json_extractor_rejects_garbage():
    with pytest.raises(ExtractionError):
        JSONInvoiceExtractor().extract(b"not json")


def test_resolver_reports_all_problems(db):
    [ex] = JSONInvoiceExtractor().extract(json.dumps({"customer": "Nobody", "items": [{"sku": "ZZZ", "quantity": 1}]}).encode())
    res = resolve_invoice(db, ex)
    assert res.invoice is None
    assert len(res.errors) >= 3  # unknown customer, missing date, unknown product


def test_pdf_text_extraction_end_to_end(db):
    pdf = make_pdf(["Invoice No: PDF-77", "Bill To: ABC Electricals", "Date: 2026-10-04",
                    "LED-B12 LED Bulb 12W 50 x 120", "MCB-S16 MCB 16A Single Pole 20 x 180"])
    [ex] = PDFInvoiceExtractor().extract(pdf)
    assert ex.invoice_number == "PDF-77" and ex.party_name == "ABC Electricals" and len(ex.lines) == 2
    res = resolve_invoice(db, ex)
    assert res.invoice is not None and [i.quantity for i in res.invoice.items] == [50, 20]


def test_registry_rejects_unsupported_and_image_files():
    assert extractor_for("a.JSON").name == "structured-json"
    for name in ("scan.png", "virus.exe"):
        with pytest.raises(AppError) as exc:
            extractor_for(name)
        assert exc.value.status_code == 415
