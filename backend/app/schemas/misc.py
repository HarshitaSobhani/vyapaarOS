from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import UserRole
from app.schemas.analytics import CustomerReceivableOut
from app.schemas.common import ORM, Money
from app.schemas.invoices import InvoiceOut, PaymentOut


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class UserOut(ORM):
    id: UUID
    name: str
    email: str
    role: UserRole


class LoginOut(BaseModel):
    user: UserOut
    access_token: str


class CustomerOut(BaseModel):
    id: UUID
    name: str
    company_name: str
    phone: str | None
    email: str | None
    credit_limit: Money
    payment_terms_days: int
    outstanding_amount: Money
    overdue_amount: Money
    days_overdue: int
    priority: str


class CustomerDetail(BaseModel):
    customer: CustomerOut
    receivable: CustomerReceivableOut
    invoices: list[InvoiceOut]
    payments: list[PaymentOut]


class ProductOut(BaseModel):
    id: UUID
    sku: str
    name: str
    category: str
    unit: str
    purchase_price: Money
    selling_price: Money
    gst_rate: Money
    reorder_level: int
    reorder_quantity: int
    supplier_name: str
    current_quantity: int
    reserved_quantity: int


class CollectionMessageIn(BaseModel):
    customer_id: UUID
    invoice_id: UUID | None = None
    variant: int = Field(default=0, ge=0, le=50)


class CollectionMessageOut(BaseModel):
    message: str
    customer_id: UUID
    customer_name: str
    phone: str | None
    invoice_id: UUID
    invoice_number: str
    amount: Money
    due_date: date
    days_overdue: int
    provider: str
    fallback_used: bool


class SendReminderIn(BaseModel):
    customer_id: UUID
    invoice_id: UUID | None = None
    message: str = Field(min_length=1, max_length=1000)
    approved: bool = False


class SendReminderOut(BaseModel):
    mode: str
    url: str | None
    detail: str


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class AskOut(BaseModel):
    answer: str
    intent: str
    provider: str
    fallback_used: bool
    facts: dict | None = None


class SettingsOut(BaseModel):
    user: UserOut
    ai_provider: str
    ai_configured: bool
    whatsapp_mode: str
    environment: str
    max_upload_mb: float
