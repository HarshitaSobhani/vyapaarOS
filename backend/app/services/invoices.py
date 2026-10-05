"""Invoice lifecycle: totals, draft creation, approval, rejection, payments."""
import re
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models import (
    Customer,
    Inventory,
    Invoice,
    InvoiceItem,
    InvoiceSource,
    InvoiceStatus,
    Payment,
    Product,
    User,
)
from app.schemas.invoices import InvoiceDetail, InvoiceIn, InvoiceItemOut, InvoiceOut, PaymentIn, PaymentOut

CENT = Decimal("0.01")
ZERO = Decimal("0")


def q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def line_amounts(quantity: int, unit_price: Decimal, gst_rate: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """Returns (net, tax, total) for one line. Pure and deterministic."""
    net = q(unit_price * quantity)
    tax = q(net * gst_rate / Decimal(100))
    return net, tax, net + tax


def effective_status(status: InvoiceStatus, due: date, outstanding: Decimal, today: date) -> InvoiceStatus:
    if status in (InvoiceStatus.approved, InvoiceStatus.partially_paid) and outstanding > 0 and due < today:
        return InvoiceStatus.overdue
    return status


def next_invoice_number(db: Session, invoice_date: date) -> str:
    prefix = f"INV-{invoice_date:%y%m}-"
    last = db.scalar(select(Invoice.invoice_number).where(Invoice.invoice_number.like(f"{prefix}%"))
                     .order_by(Invoice.invoice_number.desc()).limit(1))
    n = int(last.rsplit("-", 1)[1]) + 1 if last and re.search(r"-\d+$", last) else 1
    return f"{prefix}{n:04d}"


def create_draft(db: Session, data: InvoiceIn, source: InvoiceSource, today: date | None = None) -> Invoice:
    customer = db.get(Customer, data.customer_id)
    if customer is None:
        raise NotFoundError("Customer")
    number = data.invoice_number or next_invoice_number(db, data.invoice_date)
    if db.scalar(select(Invoice.id).where(Invoice.invoice_number == number)):
        raise ConflictError(f"Invoice number {number} already exists")
    due = data.due_date or data.invoice_date + timedelta(days=customer.payment_terms_days)
    inv = Invoice(invoice_number=number, customer_id=customer.id, invoice_date=data.invoice_date,
                  due_date=due, subtotal=ZERO, tax=ZERO, total=ZERO,
                  status=InvoiceStatus.draft, source=source)
    _set_items(db, inv, data)
    db.add(inv)
    db.commit()
    return get_invoice(db, inv.id)


def _set_items(db: Session, inv: Invoice, data: InvoiceIn) -> None:
    products = {p.id: p for p in db.scalars(
        select(Product).where(Product.id.in_({i.product_id for i in data.items})))}
    items: list[InvoiceItem] = []
    subtotal = tax = ZERO
    for n, it in enumerate(data.items, start=1):
        product = products.get(it.product_id)
        if product is None:
            raise AppError(f"Unknown product on line {n}", 422, "validation_error")
        price = it.unit_price if it.unit_price is not None else product.selling_price
        net, line_tax, total = line_amounts(it.quantity, price, product.gst_rate)
        subtotal += net
        tax += line_tax
        items.append(InvoiceItem(product_id=product.id, line_no=n, quantity=it.quantity,
                                 unit_price=q(price), tax=line_tax, total=total))
    inv.items = items
    inv.subtotal, inv.tax, inv.total = subtotal, tax, subtotal + tax


def update_draft(db: Session, invoice_id: UUID, data: InvoiceIn) -> Invoice:
    inv = get_invoice(db, invoice_id)
    if inv.status is not InvoiceStatus.draft:
        raise ConflictError("Only draft invoices can be edited")
    if data.invoice_number and data.invoice_number != inv.invoice_number:
        if db.scalar(select(Invoice.id).where(Invoice.invoice_number == data.invoice_number)):
            raise ConflictError(f"Invoice number {data.invoice_number} already exists")
        inv.invoice_number = data.invoice_number
    customer = db.get(Customer, data.customer_id)
    if customer is None:
        raise NotFoundError("Customer")
    inv.customer_id = customer.id
    inv.invoice_date = data.invoice_date
    inv.due_date = data.due_date or data.invoice_date + timedelta(days=customer.payment_terms_days)
    _set_items(db, inv, data)
    db.commit()
    return get_invoice(db, invoice_id)


def approve_invoice(db: Session, invoice_id: UUID, user: User) -> Invoice:
    inv = get_invoice(db, invoice_id)
    if inv.status is not InvoiceStatus.draft:
        raise ConflictError(f"Invoice is already {inv.status.value}")
    # Stock moves only when the invoice enters the approved dataset.
    for item in inv.items:
        stock = db.scalar(select(Inventory).where(Inventory.product_id == item.product_id).with_for_update())
        if stock is not None:
            stock.current_quantity = max(stock.current_quantity - item.quantity, 0)
    inv.status = InvoiceStatus.approved
    inv.approved_at = datetime.now(UTC)
    db.commit()
    return get_invoice(db, invoice_id)


def reject_invoice(db: Session, invoice_id: UUID, reason: str | None) -> Invoice:
    inv = get_invoice(db, invoice_id)
    if inv.status is not InvoiceStatus.draft:
        raise ConflictError(f"Invoice is already {inv.status.value}")
    inv.status = InvoiceStatus.rejected
    inv.rejection_reason = reason
    db.commit()
    return get_invoice(db, invoice_id)


def paid_amount(inv: Invoice) -> Decimal:
    return sum((p.amount for p in inv.payments), ZERO)


def record_payment(db: Session, invoice_id: UUID, data: PaymentIn, commit: bool = True) -> Payment:
    inv = get_invoice(db, invoice_id)
    if inv.status not in (InvoiceStatus.approved, InvoiceStatus.partially_paid):
        raise ConflictError("Payments can only be recorded against approved, unpaid invoices")
    outstanding = inv.total - paid_amount(inv)
    amount = q(data.amount)
    if amount > outstanding:
        raise AppError(f"Payment exceeds outstanding amount ({outstanding})", 422, "validation_error")
    payment = Payment(invoice_id=inv.id, amount=amount, payment_date=data.payment_date,
                      payment_method=data.payment_method, reference=data.reference)
    db.add(payment)
    inv.payments.append(payment)
    inv.status = InvoiceStatus.paid if amount == outstanding else InvoiceStatus.partially_paid
    if commit:
        db.commit()
    return payment


def allocate_customer_payment(db: Session, customer_id: UUID, data: PaymentIn) -> list[Payment]:
    """FIFO allocation: settle the oldest-due open invoices first."""
    if db.get(Customer, customer_id) is None:
        raise NotFoundError("Customer")
    open_invoices = list(db.scalars(
        select(Invoice).options(selectinload(Invoice.payments))
        .where(Invoice.customer_id == customer_id,
               Invoice.status.in_((InvoiceStatus.approved, InvoiceStatus.partially_paid)))
        .order_by(Invoice.due_date, Invoice.invoice_date)))
    total_open = sum((i.total - paid_amount(i) for i in open_invoices), ZERO)
    remaining = q(data.amount)
    if remaining > total_open:
        raise AppError(f"Payment exceeds total outstanding ({total_open})", 422, "validation_error")
    created: list[Payment] = []
    for inv in open_invoices:
        if remaining <= 0:
            break
        due = inv.total - paid_amount(inv)
        portion = min(due, remaining)
        part = data.model_copy(update={"amount": portion})
        created.append(record_payment(db, inv.id, part, commit=False))
        remaining -= portion
    db.commit()
    return created


def get_invoice(db: Session, invoice_id: UUID) -> Invoice:
    inv = db.scalar(select(Invoice).where(Invoice.id == invoice_id).options(
        selectinload(Invoice.items).selectinload(InvoiceItem.product),
        selectinload(Invoice.payments), selectinload(Invoice.customer)))
    if inv is None:
        raise NotFoundError("Invoice")
    return inv


def to_out(inv: Invoice, today: date) -> InvoiceOut:
    paid = paid_amount(inv)
    outstanding = max(inv.total - paid, ZERO) if inv.status not in (
        InvoiceStatus.draft, InvoiceStatus.rejected) else ZERO
    status = effective_status(inv.status, inv.due_date, outstanding, today)
    return InvoiceOut(
        id=inv.id, invoice_number=inv.invoice_number, customer_id=inv.customer_id,
        customer_name=inv.customer.company_name, invoice_date=inv.invoice_date, due_date=inv.due_date,
        subtotal=inv.subtotal, tax=inv.tax, total=inv.total, paid=paid, outstanding=outstanding,
        status=status, source=inv.source,
        days_overdue=(today - inv.due_date).days if status is InvoiceStatus.overdue else 0,
        rejection_reason=inv.rejection_reason)


def to_detail(inv: Invoice, today: date) -> InvoiceDetail:
    base = to_out(inv, today)
    return InvoiceDetail(
        **base.model_dump(),
        items=[InvoiceItemOut(id=i.id, product_id=i.product_id, product_name=i.product.name,
                              sku=i.product.sku, quantity=i.quantity, unit_price=i.unit_price,
                              tax=i.tax, total=i.total) for i in inv.items],
        payments=[PaymentOut.model_validate(p) for p in inv.payments])


def count_by_status(db: Session, status: InvoiceStatus) -> int:
    return db.scalar(select(func.count()).select_from(Invoice).where(Invoice.status == status)) or 0
