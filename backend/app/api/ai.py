from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AI, DB, CurrentUser, Today
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.models import Customer, Invoice, InvoiceStatus, ReminderLog
from app.schemas.misc import (
    AskIn,
    AskOut,
    CollectionMessageIn,
    CollectionMessageOut,
    SendReminderIn,
    SendReminderOut,
    SettingsOut,
    UserOut,
)
from app.services import assistant
from app.services.invoices import paid_amount
from app.services.receivables import format_inr
from app.services.whatsapp import get_whatsapp_provider

router = APIRouter(tags=["ai"])


@router.post("/ai/ask", response_model=AskOut)
def ask(body: AskIn, db: DB, _: CurrentUser, ai: AI, today: Today) -> AskOut:
    intent, facts, result = assistant.ask(db, ai, body.question.strip(), today)
    return AskOut(answer=result.text, intent=intent, provider=result.provider,
                  fallback_used=result.fallback_used, facts=facts)


def _pick_invoice(db: DB, customer_id: UUID, invoice_id: UUID | None, today) -> Invoice:  # type: ignore[no-untyped-def]
    if invoice_id:
        inv = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.customer_id == customer_id)
                        .options(selectinload(Invoice.payments)))
        if inv is None:
            raise NotFoundError("Invoice")
        return inv
    rows = db.scalars(select(Invoice).where(
        Invoice.customer_id == customer_id,
        Invoice.status.in_((InvoiceStatus.approved, InvoiceStatus.partially_paid)),
        Invoice.due_date < today).options(selectinload(Invoice.payments)).order_by(Invoice.due_date)).all()
    if not rows:
        raise AppError("This customer has no overdue invoices to remind about", 422, "no_overdue_invoice")
    return rows[0]


@router.post("/ai/collection-message", response_model=CollectionMessageOut)
def collection_message(body: CollectionMessageIn, db: DB, _: CurrentUser, ai: AI, today: Today) -> CollectionMessageOut:
    customer = db.get(Customer, body.customer_id)
    if customer is None:
        raise NotFoundError("Customer")
    inv = _pick_invoice(db, customer.id, body.invoice_id, today)
    if inv.status not in (InvoiceStatus.approved, InvoiceStatus.partially_paid):
        raise AppError("Reminders are only for approved, unpaid invoices", 422, "invalid_invoice")
    amount = inv.total - paid_amount(inv)
    if amount <= 0:
        raise AppError("Invoice is already paid", 422, "invalid_invoice")
    days = max((today - inv.due_date).days, 0)
    facts = {"customer_name": customer.name.split()[0], "invoice_number": inv.invoice_number,
             "amount": amount, "amount_display": format_inr(amount),
             "due_date": inv.due_date.strftime("%d %b %Y"), "days_overdue": days}
    result = ai.write_reminder(facts, body.variant)
    return CollectionMessageOut(
        message=result.text, customer_id=customer.id, customer_name=customer.company_name,
        phone=customer.phone, invoice_id=inv.id, invoice_number=inv.invoice_number, amount=amount,
        due_date=inv.due_date, days_overdue=days, provider=result.provider,
        fallback_used=result.fallback_used)


@router.post("/ai/collection-message/send", response_model=SendReminderOut)
def send_reminder(body: SendReminderIn, db: DB, user: CurrentUser) -> SendReminderOut:
    """Requires explicit approval. Records the approval and returns a WhatsApp link; nothing is auto-sent."""
    if not body.approved:
        raise AppError("Message must be explicitly approved before sending", 422, "approval_required")
    customer = db.get(Customer, body.customer_id)
    if customer is None:
        raise NotFoundError("Customer")
    db.add(ReminderLog(customer_id=customer.id, invoice_id=body.invoice_id, approved_by_id=user.id,
                       message=body.message.strip()))
    db.commit()
    d = get_whatsapp_provider().dispatch(customer.phone, body.message.strip())
    return SendReminderOut(mode=d.mode, url=d.url, detail=d.detail)


@router.get("/settings", response_model=SettingsOut)
def app_settings(user: CurrentUser) -> SettingsOut:
    s = get_settings()
    return SettingsOut(user=UserOut.model_validate(user), ai_provider=s.ai_provider,
                       ai_configured=s.ai_provider == "openai" and bool(s.openai_api_key),
                       whatsapp_mode="deep_link", environment=s.environment,
                       max_upload_mb=s.max_upload_bytes / 1024 / 1024)
