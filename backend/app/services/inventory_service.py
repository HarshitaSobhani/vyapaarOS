from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Product
from app.repositories.inventory import products_with_stock, units_sold_by_product
from app.schemas.analytics import PurchaseOrderLine, PurchaseOrderSuggestion
from app.services.inventory import (
    VELOCITY_WINDOW_DAYS,
    StockAssessment,
    StockStatus,
    assess_stock,
    inventory_health_pct,
    may_stock_out_soon,
)


@dataclass
class ProductRisk:
    product: Product
    current_quantity: int
    reserved_quantity: int
    assessment: StockAssessment

    @property
    def stock_value(self) -> Decimal:
        return self.product.purchase_price * self.current_quantity


def compute_risks(db: Session, today: date) -> list[ProductRisk]:
    start = today - timedelta(days=VELOCITY_WINDOW_DAYS - 1)
    sold = units_sold_by_product(db, start, today)
    risks = []
    for product, inv in products_with_stock(db):
        cur = inv.current_quantity if inv else 0
        res = inv.reserved_quantity if inv else 0
        a = assess_stock(cur, res, sold.get(product.id, 0), product.reorder_level,
                         product.reorder_quantity)
        risks.append(ProductRisk(product, cur, res, a))
    return risks


@dataclass
class InventorySummary:
    total_products: int
    low_stock: int
    critical: int
    healthy: int
    health_pct: float
    inventory_value: Decimal
    stockout_risk_10d: int
    purchase_orders: dict[str, list[ProductRisk]]


def summarize(risks: list[ProductRisk]) -> InventorySummary:
    orders: dict[str, list[ProductRisk]] = {}
    for r in risks:
        if r.assessment.recommended_order_quantity > 0:
            orders.setdefault(r.product.supplier_name, []).append(r)
    return InventorySummary(
        total_products=len(risks),
        low_stock=sum(r.assessment.status is StockStatus.low for r in risks),
        critical=sum(r.assessment.status is StockStatus.critical for r in risks),
        healthy=sum(r.assessment.status is StockStatus.healthy for r in risks),
        health_pct=inventory_health_pct([r.assessment for r in risks]),
        inventory_value=sum((r.stock_value for r in risks), Decimal(0)),
        stockout_risk_10d=sum(may_stock_out_soon(r.assessment) for r in risks),
        purchase_orders=orders,
    )


def find_risk(risks: list[ProductRisk], product_id: UUID) -> ProductRisk | None:
    return next((r for r in risks if r.product.id == product_id), None)


def purchase_order_suggestions(summary: InventorySummary) -> list[PurchaseOrderSuggestion]:
    """Products needing an order, grouped by supplier, with estimated cost at purchase price."""
    out = []
    for supplier, lines in sorted(summary.purchase_orders.items()):
        po_lines = [
            PurchaseOrderLine(
                product_id=r.product.id, name=r.product.name, sku=r.product.sku,
                quantity=r.assessment.recommended_order_quantity, unit=r.product.unit,
                estimated_cost=r.product.purchase_price * r.assessment.recommended_order_quantity)
            for r in lines]
        out.append(PurchaseOrderSuggestion(
            supplier_name=supplier, lines=po_lines,
            estimated_total=sum((line.estimated_cost for line in po_lines), Decimal(0))))
    return out
