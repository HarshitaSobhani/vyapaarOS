"""Selects the invoice a reminder is about and assembles the facts the AI may use."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError
from app.models import Customer, Invoice, InvoiceStatus
from app.services.invoices import paid_amount
from app.services.receivables import format_inr

OPEN_STATUSES = (InvoiceStatus.approved, InvoiceStatus.partially_paid)


@dataclass
class ReminderContext:
    customer: Customer
    invoice: Invoice
    amount: Decimal
    days_overdue: int
    facts: dict[str, object]


def _pick_invoice(db: Session, customer_id: UUID, invoice_id: UUID | None, today: date) -> Invoice:
    stmt = select(Invoice).where(Invoice.customer_id == customer_id).options(selectinload(Invoice.payments))
    if invoice_id:
        inv = db.scalar(stmt.where(Invoice.id == invoice_id))
        if inv is None:
            raise NotFoundError("Invoice")
        return inv
    overdue = db.scalars(stmt.where(Invoice.status.in_(OPEN_STATUSES), Invoice.due_date < today)
                         .order_by(Invoice.due_date)).all()
    if not overdue:
        raise AppError("This customer has no overdue invoices to remind about", 422, "no_overdue_invoice")
    return overdue[0]


def build_reminder_context(db: Session, customer_id: UUID, invoice_id: UUID | None, today: date) -> ReminderContext:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer")
    inv = _pick_invoice(db, customer.id, invoice_id, today)
    if inv.status not in OPEN_STATUSES:
        raise AppError("Reminders are only for approved, unpaid invoices", 422, "invalid_invoice")
    amount = inv.total - paid_amount(inv)
    if amount <= 0:
        raise AppError("Invoice is already paid", 422, "invalid_invoice")
    days = max((today - inv.due_date).days, 0)
    facts: dict[str, object] = {
        "customer_name": customer.name.split()[0], "invoice_number": inv.invoice_number,
        "amount": amount, "amount_display": format_inr(amount),
        "due_date": inv.due_date.strftime("%d %b %Y"), "days_overdue": days,
    }
    return ReminderContext(customer, inv, amount, days, facts)
