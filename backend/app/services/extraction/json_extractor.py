import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.extraction.base import ExtractedInvoice, ExtractedLine, ExtractionError, InvoiceExtractor

PARTY_KEYS = ("customer", "customer_name", "party", "party_name", "supplier", "buyer", "company")


def _dec(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").replace("₹", "").strip())
    except InvalidOperation:
        return None


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


class JSONInvoiceExtractor(InvoiceExtractor):
    """Structured JSON: one invoice object, a list, or {"invoices": [...]}."""

    name = "structured-json"
    extensions = (".json",)

    def extract(self, data: bytes) -> list[ExtractedInvoice]:
        try:
            payload = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExtractionError("Invalid JSON file") from exc
        if isinstance(payload, dict) and isinstance(payload.get("invoices"), list):
            payload = payload["invoices"]
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list) or not payload:
            raise ExtractionError("Expected an invoice object or a non-empty list of invoices")
        return [self._one(obj) for obj in payload]

    def _one(self, obj: Any) -> ExtractedInvoice:
        if not isinstance(obj, dict):
            return ExtractedInvoice(None, None, None, None, errors=["Invoice entry is not an object"])
        party = next((str(obj[k]) for k in PARTY_KEYS if obj.get(k)), None)
        inv = ExtractedInvoice(
            invoice_number=str(obj["invoice_number"]).strip() if obj.get("invoice_number") else None,
            party_name=party, invoice_date=_date(obj.get("invoice_date") or obj.get("date")),
            due_date=_date(obj.get("due_date")))
        for key, label in (("invoice_date", "invoice_date"), ("due_date", "due_date")):
            if obj.get(key) and _date(obj[key]) is None:
                inv.errors.append(f"{label} must be YYYY-MM-DD")
        items = obj.get("items") or obj.get("line_items") or []
        if not isinstance(items, list):
            inv.errors.append("items must be a list")
            items = []
        for n, it in enumerate(items, start=1):
            if not isinstance(it, dict):
                inv.errors.append(f"Line {n} is not an object")
                continue
            qty = _dec(it.get("quantity") if "quantity" in it else it.get("qty"))
            price = _dec(it.get("unit_price") if "unit_price" in it else it.get("rate"))
            if qty is None:
                inv.errors.append(f"Line {n}: quantity missing or invalid")
            if it.get("unit_price") not in (None, "") and price is None:
                inv.errors.append(f"Line {n}: unit_price invalid")
            inv.lines.append(ExtractedLine(
                sku=str(it["sku"]).strip() if it.get("sku") else None,
                description=str(it.get("description") or it.get("name") or it.get("product") or "") or None,
                quantity=qty, unit_price=price, row=n))
        return inv
