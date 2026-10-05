from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import InvoiceSource, InvoiceStatus, PaymentMethod
from app.schemas.common import ORM, Money


class InvoiceItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=1_000_000)
    unit_price: Decimal | None = Field(default=None, ge=0, le=Decimal("10000000"))


class InvoiceIn(BaseModel):
    invoice_number: str | None = Field(default=None, min_length=1, max_length=40)
    customer_id: UUID
    invoice_date: date
    due_date: date | None = None
    items: list[InvoiceItemIn] = Field(min_length=1, max_length=200)

    @field_validator("invoice_number")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if v else v

    @model_validator(mode="after")
    def _dates(self) -> "InvoiceIn":
        if self.due_date and self.due_date < self.invoice_date:
            raise ValueError("due_date cannot be before invoice_date")
        return self


class InvoiceItemOut(ORM):
    id: UUID
    product_id: UUID
    product_name: str
    sku: str
    quantity: int
    unit_price: Money
    tax: Money
    total: Money


class PaymentOut(ORM):
    id: UUID
    invoice_id: UUID
    amount: Money
    payment_date: date
    payment_method: PaymentMethod
    reference: str | None


class InvoiceOut(BaseModel):
    id: UUID
    invoice_number: str
    customer_id: UUID
    customer_name: str
    invoice_date: date
    due_date: date
    subtotal: Money
    tax: Money
    total: Money
    paid: Money
    outstanding: Money
    status: InvoiceStatus
    source: InvoiceSource
    days_overdue: int
    rejection_reason: str | None = None


class InvoiceDetail(InvoiceOut):
    items: list[InvoiceItemOut]
    payments: list[PaymentOut]


class RejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0, le=Decimal("100000000"))
    payment_date: date
    payment_method: PaymentMethod = PaymentMethod.bank_transfer
    reference: str | None = Field(default=None, max_length=80)


class InvoicePaymentIn(PaymentIn):
    invoice_id: UUID


class CustomerPaymentIn(PaymentIn):
    pass


class ImportInvoiceResult(BaseModel):
    invoice_number: str | None
    status: str  # draft_created | error
    invoice_id: UUID | None = None
    errors: list[str] = []


class InvoiceImportOut(BaseModel):
    filename: str
    extractor: str
    created: int
    failed: int
    results: list[ImportInvoiceResult]
