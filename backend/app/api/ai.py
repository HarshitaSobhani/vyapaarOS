from fastapi import APIRouter

from app.api.deps import AI, DB, CurrentUser, Today
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.models import Customer, ReminderLog
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
from app.services.reminders import build_reminder_context
from app.services.whatsapp import get_whatsapp_provider

router = APIRouter(tags=["ai"])


@router.post("/ai/ask", response_model=AskOut)
def ask(body: AskIn, db: DB, _: CurrentUser, ai: AI, today: Today) -> AskOut:
    intent, facts, result = assistant.ask(db, ai, body.question.strip(), today)
    return AskOut(answer=result.text, intent=intent, provider=result.provider,
                  fallback_used=result.fallback_used, facts=facts)


@router.post("/ai/collection-message", response_model=CollectionMessageOut)
def collection_message(body: CollectionMessageIn, db: DB, _: CurrentUser, ai: AI, today: Today) -> CollectionMessageOut:
    ctx = build_reminder_context(db, body.customer_id, body.invoice_id, today)
    result = ai.write_reminder(ctx.facts, body.variant)
    return CollectionMessageOut(
        message=result.text, customer_id=ctx.customer.id, customer_name=ctx.customer.company_name,
        phone=ctx.customer.phone, invoice_id=ctx.invoice.id, invoice_number=ctx.invoice.invoice_number,
        amount=ctx.amount, due_date=ctx.invoice.due_date, days_overdue=ctx.days_overdue,
        provider=result.provider, fallback_used=result.fallback_used)


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
