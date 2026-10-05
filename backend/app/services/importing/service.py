"""Validate and persist rows from an AccountingSource. Preview never writes."""
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    Customer,
    Inventory,
    Invoice,
    InvoiceSource,
    InvoiceStatus,
    PaymentMethod,
    Product,
)
from app.schemas.imports import ImportPreview, ImportResult, RowError
from app.schemas.invoices import PaymentIn
from app.services import invoices as invoice_service
from app.services.extraction.base import ExtractedInvoice, ExtractedLine
from app.services.extraction.resolver import resolve_invoice
from app.services.importing.source import AccountingSource, SourceRow

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-]{8,15}$")
KINDS = ("customers", "products", "invoices", "payments")


class CustomerRow(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company_name: str = Field(min_length=1, max_length=160)
    phone: str | None = None
    email: str | None = None
    credit_limit: Decimal = Field(default=Decimal(0), ge=0, le=Decimal("100000000"))
    payment_terms_days: int = Field(default=30, ge=0, le=365)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        if v and not EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v or None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v and not PHONE_RE.match(v):
            raise ValueError("invalid phone number")
        return v or None


class ProductRow(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    unit: str = "pcs"
    purchase_price: Decimal = Field(ge=0, le=Decimal("10000000"))
    selling_price: Decimal = Field(ge=0, le=Decimal("10000000"))
    gst_rate: Decimal = Field(default=Decimal(18), ge=0, le=28)
    reorder_level: int = Field(default=0, ge=0)
    reorder_quantity: int = Field(default=0, ge=0)
    supplier_name: str = Field(min_length=1, max_length=160)
    opening_stock: int = Field(default=0, ge=0)


class PaymentRow(BaseModel):
    invoice_number: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, le=Decimal("100000000"))
    payment_date: date
    payment_method: PaymentMethod = PaymentMethod.bank_transfer
    reference: str | None = Field(default=None, max_length=80)


def _blank_to_none(d: dict[str, str]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v != ""}


def _messages(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" if e["loc"] else e["msg"]
            for e in exc.errors()]


class ImportService:
    def __init__(self, db: Session, source: AccountingSource, today: date | None = None) -> None:
        self.db, self.source, self.today = db, source, today or date.today()

    # ----- public API -----
    def preview(self, kind: str) -> ImportPreview:
        total, valid, errors, _ = self._validate(kind)
        return ImportPreview(kind=kind, total_rows=total, valid_rows=len(valid) if kind != "invoices"
                             else sum(len(v[1]) for v in valid), error_rows=len({e.row for e in errors}),
                             errors=errors)

    def commit(self, kind: str) -> ImportResult:
        total, valid, errors, _ = self._validate(kind)
        imported = self._persist(kind, valid)
        preview = ImportPreview(kind=kind, total_rows=total,
                                valid_rows=sum(len(v[1]) for v in valid) if kind == "invoices" else len(valid),
                                error_rows=len({e.row for e in errors}), errors=errors)
        return ImportResult(**preview.model_dump(), imported=imported)

    # ----- validation -----
    def _rows(self, kind: str) -> list[SourceRow]:
        getter = {"customers": self.source.get_customers, "products": self.source.get_products,
                  "invoices": self.source.get_invoices, "payments": self.source.get_payments}.get(kind)
        if getter is None:
            raise AppError(f"Unknown import type '{kind}'", 404, "not_found")
        return getter()

    def _validate(self, kind: str) -> tuple[int, list[Any], list[RowError], list[SourceRow]]:
        rows = self._rows(kind)
        if kind == "invoices":
            valid, errors = self._validate_invoices(rows)
        else:
            valid, errors = getattr(self, f"_validate_{kind}")(rows)
        return len(rows), valid, errors, rows

    def _validate_customers(self, rows: list[SourceRow]) -> tuple[list[CustomerRow], list[RowError]]:
        existing = {n.lower() for n in self.db.scalars(select(Customer.company_name))}
        seen: set[str] = set()
        valid, errors = [], []
        for r in rows:
            try:
                item = CustomerRow(**_blank_to_none(r.data))
            except ValidationError as exc:
                errors.append(RowError(row=r.row, errors=_messages(exc), data=r.data))
                continue
            key = item.company_name.lower()
            if key in existing or key in seen:
                errors.append(RowError(row=r.row, errors=[f"Duplicate customer '{item.company_name}'"], data=r.data))
                continue
            seen.add(key)
            valid.append(item)
        return valid, errors

    def _validate_products(self, rows: list[SourceRow]) -> tuple[list[ProductRow], list[RowError]]:
        existing = {s.lower() for s in self.db.scalars(select(Product.sku))}
        seen: set[str] = set()
        valid, errors = [], []
        for r in rows:
            try:
                item = ProductRow(**_blank_to_none(r.data))
            except ValidationError as exc:
                errors.append(RowError(row=r.row, errors=_messages(exc), data=r.data))
                continue
            key = item.sku.lower()
            if key in existing or key in seen:
                errors.append(RowError(row=r.row, errors=[f"Duplicate SKU '{item.sku}'"], data=r.data))
                continue
            seen.add(key)
            valid.append(item)
        return valid, errors

    def _validate_payments(self, rows: list[SourceRow]) -> tuple[list[tuple[SourceRow, PaymentRow]], list[RowError]]:
        invoices = {i.invoice_number: i for i in self.db.scalars(select(Invoice))}
        remaining: dict[str, Decimal] = {}
        valid, errors = [], []
        for r in rows:
            try:
                item = PaymentRow(**_blank_to_none(r.data))
            except ValidationError as exc:
                errors.append(RowError(row=r.row, errors=_messages(exc), data=r.data))
                continue
            inv = invoices.get(item.invoice_number)
            if inv is None:
                errors.append(RowError(row=r.row, errors=[f"Unknown invoice '{item.invoice_number}'"], data=r.data))
                continue
            if inv.status not in (InvoiceStatus.approved, InvoiceStatus.partially_paid):
                errors.append(RowError(row=r.row, errors=[f"Invoice is {inv.status.value}; only approved unpaid invoices accept payments"], data=r.data))
                continue
            if item.invoice_number not in remaining:
                paid = sum((p.amount for p in inv.payments), Decimal(0))
                remaining[item.invoice_number] = inv.total - paid
            if item.amount > remaining[item.invoice_number]:
                errors.append(RowError(row=r.row, errors=[f"Amount exceeds outstanding {remaining[item.invoice_number]}"], data=r.data))
                continue
            remaining[item.invoice_number] -= item.amount
            valid.append((r, item))
        return valid, errors

    def _validate_invoices(self, rows: list[SourceRow]) -> tuple[list[tuple[Any, list[SourceRow]]], list[RowError]]:
        """Groups line rows by invoice_number; an invoice with any bad row is rejected whole."""
        groups: dict[str, list[SourceRow]] = defaultdict(list)
        errors: list[RowError] = []
        for r in rows:
            groups[r.data.get("invoice_number", "")].append(r)
        products = {p.sku.lower(): p for p in self.db.scalars(select(Product))}
        valid: list[tuple[Any, list[SourceRow]]] = []
        for number, group in groups.items():
            if not number:
                errors += [RowError(row=r.row, errors=["invoice_number is missing"], data=r.data) for r in group]
                continue
            ex, row_errors = self._extract_group(number, group)
            if not row_errors:
                res = resolve_invoice(self.db, ex, products)
                if res.invoice is None:
                    row_errors = _attach_errors(res.errors, group)
                else:
                    valid.append((res.invoice, group))
                    continue
            errors += _merge_row_errors(row_errors, group)
        return valid, sorted(errors, key=lambda e: e.row)

    @staticmethod
    def _extract_group(number: str, group: list[SourceRow]) -> tuple[ExtractedInvoice, dict[int, list[str]]]:
        row_errors: dict[int, list[str]] = defaultdict(list)
        first = group[0].data
        ex = ExtractedInvoice(number, first.get("customer"), None, None, rows=[r.row for r in group])
        for field_name, attr in (("invoice_date", "invoice_date"), ("due_date", "due_date")):
            raw = first.get(field_name, "")
            if raw:
                try:
                    setattr(ex, attr, date.fromisoformat(raw))
                except ValueError:
                    row_errors[group[0].row].append(f"{field_name} must be YYYY-MM-DD")
        for r in group:
            if r.data.get("customer") != first.get("customer") or r.data.get("invoice_date") != first.get("invoice_date"):
                row_errors[r.row].append("Customer/date differ from the first row of this invoice")
            try:
                qty = Decimal(r.data.get("quantity", ""))
            except InvalidOperation:
                row_errors[r.row].append("quantity must be a number")
                qty = None
            price = None
            if r.data.get("unit_price"):
                try:
                    price = Decimal(r.data["unit_price"])
                except InvalidOperation:
                    row_errors[r.row].append("unit_price must be a number")
            ex.lines.append(ExtractedLine(r.data.get("sku") or None, None, qty, price, row=r.row))
        return ex, row_errors

    # ----- persistence -----
    def _persist(self, kind: str, valid: list[Any]) -> int:
        settings = get_settings()
        if kind == "customers":
            self.db.add_all(Customer(name=v.name, company_name=v.company_name, phone=v.phone,
                                     email=v.email, credit_limit=v.credit_limit,
                                     payment_terms_days=v.payment_terms_days) for v in valid)
        elif kind == "products":
            for v in valid:
                product = Product(sku=v.sku, name=v.name, category=v.category, unit=v.unit,
                                  purchase_price=v.purchase_price, selling_price=v.selling_price,
                                  gst_rate=v.gst_rate or Decimal(str(settings.default_gst_rate)),
                                  reorder_level=v.reorder_level, reorder_quantity=v.reorder_quantity,
                                  supplier_name=v.supplier_name)
                self.db.add(product)
                self.db.flush()
                self.db.add(Inventory(product_id=product.id, current_quantity=v.opening_stock))
        elif kind == "invoices":
            for invoice_in, _rows in valid:
                invoice_service.create_draft(self.db, invoice_in, InvoiceSource.csv)
            return len(valid)
        elif kind == "payments":
            by_number = {i.invoice_number: i.id for i in self.db.scalars(select(Invoice))}
            for _row, p in valid:
                invoice_service.record_payment(
                    self.db, by_number[p.invoice_number],
                    PaymentIn(amount=p.amount, payment_date=p.payment_date,
                              payment_method=p.payment_method, reference=p.reference), commit=False)
        self.db.commit()
        return len(valid)


def _attach_errors(messages: list[str], group: list[SourceRow]) -> dict[int, list[str]]:
    """Resolver messages mention 'Line <row>:' when row-specific; otherwise apply to first row."""
    out: dict[int, list[str]] = defaultdict(list)
    rows = {r.row for r in group}
    for m in messages:
        mt = re.match(r"Line (\d+): (.*)", m)
        if mt and int(mt.group(1)) in rows:
            out[int(mt.group(1))].append(mt.group(2))
        else:
            out[group[0].row].append(m)
    return out


def _merge_row_errors(row_errors: dict[int, list[str]], group: list[SourceRow]) -> list[RowError]:
    by_row = {r.row: r for r in group}
    result = [RowError(row=row, errors=msgs, data=by_row[row].data) for row, msgs in row_errors.items()]
    flagged = {e.row for e in result}
    # rows that were fine on their own but belong to a rejected invoice are reported too
    result += [RowError(row=r.row, errors=["Skipped: another row of this invoice has errors"], data=r.data)
               for r in group if r.row not in flagged]
    return result

