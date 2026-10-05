from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Inventory, Invoice, InvoiceItem, Product
from app.repositories.receivables import BUSINESS_STATUSES


def units_sold_by_product(db: Session, start: date, end: date) -> dict[UUID, int]:
    rows = db.execute(
        select(InvoiceItem.product_id, func.sum(InvoiceItem.quantity))
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(Invoice.status.in_(BUSINESS_STATUSES), Invoice.invoice_date.between(start, end))
        .group_by(InvoiceItem.product_id))
    return {pid: int(q) for pid, q in rows}


def products_with_stock(db: Session) -> list[tuple[Product, Inventory | None]]:
    rows = db.execute(
        select(Product, Inventory).outerjoin(Inventory, Inventory.product_id == Product.id)
        .order_by(Product.name))
    return [(p, inv) for p, inv in rows]
