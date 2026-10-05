from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Invoice, InvoiceStatus, Payment
from app.services.receivables import InvoiceFacts

# Only approved invoices (and their payment lifecycle) count as business data.
BUSINESS_STATUSES = (InvoiceStatus.approved, InvoiceStatus.partially_paid, InvoiceStatus.paid)


def load_invoice_facts(
    db: Session, customer_id: UUID | None = None,
) -> dict[UUID, list[InvoiceFacts]]:
    """Approved invoices grouped by customer id, with paid totals."""
    paid = (
        select(Payment.invoice_id, func.sum(Payment.amount).label("paid"),
               func.max(Payment.payment_date).label("last_paid"))
        .group_by(Payment.invoice_id).subquery()
    )
    stmt = (
        select(Invoice.id, Invoice.customer_id, Invoice.invoice_number, Invoice.invoice_date,
               Invoice.due_date, Invoice.total, paid.c.paid, paid.c.last_paid)
        .outerjoin(paid, paid.c.invoice_id == Invoice.id)
        .where(Invoice.status.in_(BUSINESS_STATUSES))
        .order_by(Invoice.invoice_date)
    )
    if customer_id is not None:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    out: dict[UUID, list[InvoiceFacts]] = {}
    for inv_id, cust_id, number, inv_date, due, total, paid_amt, last_paid in db.execute(stmt):
        out.setdefault(cust_id, []).append(
            InvoiceFacts(inv_id, number, inv_date, due, total, paid_amt or Decimal(0), last_paid))
    return out


def list_customers(db: Session) -> list[Customer]:
    return list(db.scalars(select(Customer).order_by(Customer.company_name)))


def sales_by_day(db: Session, start: date, end: date) -> dict[date, Decimal]:
    rows = db.execute(
        select(Invoice.invoice_date, func.sum(Invoice.total))
        .where(Invoice.status.in_(BUSINESS_STATUSES), Invoice.invoice_date.between(start, end))
        .group_by(Invoice.invoice_date))
    return {d: t for d, t in rows}
