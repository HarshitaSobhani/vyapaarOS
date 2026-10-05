from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, Approver, CurrentUser, Today
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Customer, Invoice, InvoiceSource, InvoiceStatus
from app.schemas.common import Page
from app.schemas.invoices import (
    ImportInvoiceResult,
    InvoiceDetail,
    InvoiceImportOut,
    InvoiceIn,
    InvoiceOut,
    InvoicePaymentIn,
    PaymentOut,
    RejectIn,
)
from app.services import invoices as svc
from app.services.extraction.base import ExtractionError
from app.services.extraction.registry import extractor_for
from app.services.extraction.resolver import resolve_invoice
from app.services.importing.csv_source import CSVAccountingSource
from app.services.importing.service import ImportService

router = APIRouter(tags=["invoices"])

StatusFilter = Literal["draft", "approved", "partially_paid", "paid", "overdue", "rejected"]


@router.get("/invoices", response_model=Page[InvoiceOut])
def list_invoices(
    db: DB, _: CurrentUser, today: Today,
    status: Annotated[StatusFilter | None, Query()] = None,
    customer_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50, offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[InvoiceOut]:
    stmt = select(Invoice).join(Customer)
    if status == "overdue":
        stmt = stmt.where(Invoice.status.in_((InvoiceStatus.approved, InvoiceStatus.partially_paid)),
                          Invoice.due_date < today)
    elif status:
        stmt = stmt.where(Invoice.status == InvoiceStatus(status))
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Invoice.invoice_number.ilike(like), Customer.company_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.options(selectinload(Invoice.payments), selectinload(Invoice.customer))
                      .order_by(Invoice.invoice_date.desc(), Invoice.invoice_number.desc())
                      .limit(limit).offset(offset)).all()
    return Page[InvoiceOut](items=[svc.to_out(i, today) for i in rows], total=total)


@router.post("/invoices", response_model=InvoiceDetail, status_code=201)
def create_invoice(body: InvoiceIn, db: DB, _: CurrentUser, today: Today) -> InvoiceDetail:
    """Creates a draft. Nothing counts as business data until it is approved."""
    return svc.to_detail(svc.create_draft(db, body, InvoiceSource.manual), today)


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(invoice_id: UUID, db: DB, _: CurrentUser, today: Today) -> InvoiceDetail:
    return svc.to_detail(svc.get_invoice(db, invoice_id), today)


@router.put("/invoices/{invoice_id}", response_model=InvoiceDetail)
def update_invoice(invoice_id: UUID, body: InvoiceIn, db: DB, _: CurrentUser, today: Today) -> InvoiceDetail:
    return svc.to_detail(svc.update_draft(db, invoice_id, body), today)


@router.post("/invoices/{invoice_id}/approve", response_model=InvoiceDetail)
def approve_invoice(invoice_id: UUID, db: DB, user: Approver, today: Today) -> InvoiceDetail:
    return svc.to_detail(svc.approve_invoice(db, invoice_id, user), today)


@router.post("/invoices/{invoice_id}/reject", response_model=InvoiceDetail)
def reject_invoice(invoice_id: UUID, body: RejectIn, db: DB, _: Approver, today: Today) -> InvoiceDetail:
    return svc.to_detail(svc.reject_invoice(db, invoice_id, body.reason), today)


@router.post("/payments", response_model=PaymentOut, status_code=201)
def record_payment(body: InvoicePaymentIn, db: DB, _: CurrentUser):  # type: ignore[no-untyped-def]
    return svc.record_payment(db, body.invoice_id, body)


@router.post("/invoices/import", response_model=InvoiceImportOut, status_code=201)
async def import_invoices(db: DB, _: CurrentUser, today: Today, file: Annotated[UploadFile, File()]) -> InvoiceImportOut:
    """Extracts invoices from JSON, CSV or a text PDF and stores each as a draft for review."""
    settings = get_settings()
    filename = file.filename or "upload"
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise AppError("File is too large", 413, "file_too_large")
    if not data:
        raise AppError("File is empty", 422, "invalid_file")

    if filename.lower().endswith(".csv"):
        result = ImportService(db, CSVAccountingSource(invoices=data), today).commit("invoices")
        csv_results = [ImportInvoiceResult(invoice_number=None, status="error",
                                           errors=[f"Row {e.row}: {m}" for m in e.errors]) for e in result.errors]
        return InvoiceImportOut(filename=filename, extractor="csv", created=result.imported,
                                failed=len(csv_results), results=csv_results)

    extractor = extractor_for(filename)
    try:
        extracted = extractor.extract(data)
    except ExtractionError as exc:
        raise AppError(str(exc), 422, "extraction_failed") from exc
    source = InvoiceSource.document
    results: list[ImportInvoiceResult] = []
    for ex in extracted:
        res = resolve_invoice(db, ex)
        if res.invoice is None:
            results.append(ImportInvoiceResult(invoice_number=ex.invoice_number, status="error", errors=res.errors))
            continue
        draft = svc.create_draft(db, res.invoice, source)
        results.append(ImportInvoiceResult(invoice_number=draft.invoice_number, status="draft_created",
                                           invoice_id=draft.id))
    created = sum(r.status == "draft_created" for r in results)
    return InvoiceImportOut(filename=filename, extractor=extractor.name, created=created,
                            failed=len(results) - created, results=results)


