import csv
import io

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.importing.source import AccountingSource, SourceRow

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "customers": {"name", "company_name"},
    "products": {"sku", "name", "category", "purchase_price", "selling_price", "supplier_name"},
    "invoices": {"invoice_number", "customer", "invoice_date", "sku", "quantity"},
    "payments": {"invoice_number", "amount", "payment_date"},
}


def read_csv(kind: str, data: bytes) -> list[SourceRow]:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise AppError("File is too large", 413, "file_too_large")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError("File must be UTF-8 encoded CSV", 422, "invalid_file") from exc
    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or "").strip().lower() for h in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS[kind] - headers
    if missing:
        raise AppError(f"Missing required column(s): {', '.join(sorted(missing))}", 422, "invalid_file")
    rows: list[SourceRow] = []
    for rec in reader:
        clean = {(k or "").strip().lower(): (v or "").strip() for k, v in rec.items() if k is not None}
        if not any(clean.values()):
            continue  # fully blank line
        rows.append(SourceRow(reader.line_num, clean))
        if len(rows) > settings.max_import_rows:
            raise AppError(f"Too many rows (max {settings.max_import_rows})", 422, "invalid_file")
    return rows


class CSVAccountingSource(AccountingSource):
    """Reads uploaded CSV files. Any kind that was not uploaded yields no rows."""

    def __init__(self, **files: bytes | None) -> None:
        self._files = files

    def _rows(self, kind: str) -> list[SourceRow]:
        data = self._files.get(kind)
        return read_csv(kind, data) if data is not None else []

    def get_customers(self) -> list[SourceRow]:
        return self._rows("customers")

    def get_products(self) -> list[SourceRow]:
        return self._rows("products")

    def get_invoices(self) -> list[SourceRow]:
        return self._rows("invoices")

    def get_payments(self) -> list[SourceRow]:
        return self._rows("payments")
