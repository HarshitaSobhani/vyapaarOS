"""Maps extracted names/SKUs onto real customers and products. Reports every problem."""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Invoice, Product
from app.schemas.invoices import InvoiceIn, InvoiceItemIn
from app.services.extraction.base import ExtractedInvoice


class Resolution:
    def __init__(self, invoice: InvoiceIn | None, errors: list[str], rows: list[int]) -> None:
        self.invoice, self.errors, self.rows = invoice, errors, rows


def resolve_invoice(db: Session, ex: ExtractedInvoice, products_by_sku: dict[str, Product] | None = None) -> Resolution:
    errors = list(ex.errors)
    if not ex.party_name:
        errors.append("Customer is missing")
        customer = None
    else:
        customer = db.scalar(select(Customer).where(
            (func.lower(Customer.company_name) == ex.party_name.lower())
            | (func.lower(Customer.name) == ex.party_name.lower())))
        if customer is None:
            errors.append(f"Unknown customer '{ex.party_name}'")
    if ex.invoice_date is None:
        errors.append("invoice_date is missing or invalid")
    if ex.invoice_number and db.scalar(select(Invoice.id).where(Invoice.invoice_number == ex.invoice_number)):
        errors.append(f"Invoice {ex.invoice_number} already exists")
    if ex.due_date and ex.invoice_date and ex.due_date < ex.invoice_date:
        errors.append("due_date is before invoice_date")
    if not ex.lines:
        errors.append("Invoice has no line items")

    items: list[InvoiceItemIn] = []
    for line in ex.lines:
        prefix = f"Line {line.row}: " if line.row else ""
        product = None
        if line.sku:
            product = (products_by_sku or {}).get(line.sku.lower()) or db.scalar(
                select(Product).where(func.lower(Product.sku) == line.sku.lower()))
        if product is None and line.description:
            product = db.scalar(select(Product).where(func.lower(Product.name) == line.description.lower()))
        if product is None:
            errors.append(f"{prefix}unknown product '{line.sku or line.description or ''}'")
            continue
        if line.quantity is None or line.quantity <= 0 or line.quantity != line.quantity.to_integral_value():
            errors.append(f"{prefix}quantity must be a positive whole number")
            continue
        if line.unit_price is not None and line.unit_price < 0:
            errors.append(f"{prefix}unit_price cannot be negative")
            continue
        items.append(InvoiceItemIn(product_id=product.id, quantity=int(line.quantity),
                                   unit_price=line.unit_price))
    if errors or customer is None or ex.invoice_date is None:
        return Resolution(None, errors, ex.rows)
    return Resolution(
        InvoiceIn(invoice_number=ex.invoice_number, customer_id=customer.id,
                  invoice_date=ex.invoice_date, due_date=ex.due_date, items=items), [], ex.rows)


__all__ = ["Resolution", "resolve_invoice", "Decimal"]
