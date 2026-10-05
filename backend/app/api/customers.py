from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.analytics import receivable_out
from app.api.deps import DB, Approver, CurrentUser, Today
from app.models import Customer, Invoice, InvoiceStatus, Payment
from app.schemas.invoices import CustomerPaymentIn, PaymentOut
from app.schemas.misc import CustomerDetail, CustomerOut
from app.services import invoices as invoice_service
from app.services.receivables_service import build_snapshot, customer_receivable

router = APIRouter(prefix="/customers", tags=["customers"])


def _out(c: Customer, outstanding, overdue, days, priority) -> CustomerOut:  # type: ignore[no-untyped-def]
    return CustomerOut(id=c.id, name=c.name, company_name=c.company_name, phone=c.phone, email=c.email,
                       credit_limit=c.credit_limit, payment_terms_days=c.payment_terms_days,
                       outstanding_amount=outstanding, overdue_amount=overdue, days_overdue=days,
                       priority=priority)


@router.get("", response_model=list[CustomerOut])
def list_customers(db: DB, _: CurrentUser, today: Today,
                   q: Annotated[str | None, Query(max_length=100)] = None) -> list[CustomerOut]:
    snap = build_snapshot(db, today)
    by_id = {r.customer_id: r for r in snap.customers}
    stmt = select(Customer).order_by(Customer.company_name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Customer.company_name.ilike(like) | Customer.name.ilike(like))
    return [_out(c, by_id[c.id].outstanding_amount, by_id[c.id].overdue_amount, by_id[c.id].days_overdue,
                 by_id[c.id].priority.value if by_id[c.id].outstanding_amount > 0 else "None")
            for c in db.scalars(stmt)]


@router.get("/{customer_id}", response_model=CustomerDetail)
def customer_detail(customer_id: UUID, db: DB, _: CurrentUser, today: Today) -> CustomerDetail:
    customer, r = customer_receivable(db, customer_id, today)
    invoices = db.scalars(
        select(Invoice).where(Invoice.customer_id == customer_id)
        .options(selectinload(Invoice.payments), selectinload(Invoice.customer))
        .order_by(Invoice.invoice_date.desc()).limit(50)).all()
    payments = db.scalars(
        select(Payment).join(Invoice).where(Invoice.customer_id == customer_id)
        .order_by(Payment.payment_date.desc()).limit(20)).all()
    return CustomerDetail(
        customer=_out(customer, r.outstanding_amount, r.overdue_amount, r.days_overdue,
                      r.priority.value if r.outstanding_amount > 0 else "None"),
        receivable=receivable_out(r),
        invoices=[invoice_service.to_out(i, today) for i in invoices if i.status is not InvoiceStatus.rejected],
        payments=[PaymentOut.model_validate(p) for p in payments])


@router.post("/{customer_id}/payments", response_model=list[PaymentOut], status_code=201)
def record_customer_payment(customer_id: UUID, body: CustomerPaymentIn, db: DB, _: Approver) -> list[Payment]:
    """Allocates the payment to the oldest open invoices first."""
    return invoice_service.allocate_customer_payment(db, customer_id, body)
