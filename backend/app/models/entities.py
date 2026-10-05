import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedMixin, IdMixin, utcnow


class UserRole(enum.StrEnum):
    owner = "owner"
    manager = "manager"
    sales = "sales"


class InvoiceStatus(enum.StrEnum):
    draft = "draft"
    approved = "approved"
    partially_paid = "partially_paid"
    paid = "paid"
    overdue = "overdue"  # derived at read time; never persisted
    rejected = "rejected"


class InvoiceSource(enum.StrEnum):
    manual = "manual"
    csv = "csv"
    document = "document"


class PaymentMethod(enum.StrEnum):
    upi = "upi"
    bank_transfer = "bank_transfer"
    cheque = "cheque"
    cash = "cash"


def _enum(e: type[enum.Enum], name: str) -> Enum:
    return Enum(e, name=name, native_enum=False, length=20, values_callable=lambda x: [m.value for m in x])


class User(IdMixin, CreatedMixin, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"))


class Customer(IdMixin, CreatedMixin, Base):
    __tablename__ = "customers"
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(160), unique=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)

    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class Product(IdMixin, CreatedMixin, Base):
    __tablename__ = "products"
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(20), default="pcs")
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=0)
    supplier_name: Mapped[str] = mapped_column(String(160))

    inventory: Mapped["Inventory"] = relationship(back_populates="product", uselist=False)


class Inventory(IdMixin, Base):
    __tablename__ = "inventory"
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), unique=True)
    current_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product: Mapped[Product] = relationship(back_populates="inventory")


class Invoice(IdMixin, CreatedMixin, Base):
    __tablename__ = "invoices"
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[InvoiceStatus] = mapped_column(_enum(InvoiceStatus, "invoice_status"), index=True)
    source: Mapped[InvoiceSource] = mapped_column(_enum(InvoiceSource, "invoice_source"))
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.line_no")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice", order_by="Payment.payment_date")


class InvoiceItem(IdMixin, Base):
    __tablename__ = "invoice_items"
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer, default=0)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    invoice: Mapped[Invoice] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class Payment(IdMixin, CreatedMixin, Base):
    __tablename__ = "payments"
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[PaymentMethod] = mapped_column(_enum(PaymentMethod, "payment_method"))
    reference: Mapped[str | None] = mapped_column(String(80))

    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class ReminderLog(IdMixin, CreatedMixin, Base):
    """Audit trail of reminders a user explicitly approved for sending."""
    __tablename__ = "reminder_logs"
    __table_args__ = (UniqueConstraint("id"),)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"))
    approved_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp")
    message: Mapped[str] = mapped_column(Text)
