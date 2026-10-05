from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from app.api.deps import DB, CurrentUser, Today
from app.schemas.analytics import (
    CollectionsOut,
    CustomerReceivableOut,
    DashboardOut,
    InventoryOut,
    ProductRiskOut,
)
from app.services.dashboard import build_dashboard
from app.services.inventory_service import ProductRisk, compute_risks, purchase_order_suggestions, summarize
from app.services.receivables import CustomerReceivable
from app.services.receivables_service import build_snapshot

router = APIRouter(tags=["analytics"])

OVERDUE_RANGES: dict[str, tuple[int, int | None]] = {
    "1-7": (1, 7), "8-30": (8, 30), "31-60": (31, 60), "60+": (61, None),
}


def receivable_out(r: CustomerReceivable) -> CustomerReceivableOut:
    return CustomerReceivableOut(
        customer_id=r.customer_id, customer_name=r.customer_name, company_name=r.company_name,
        phone=r.phone, outstanding_amount=r.outstanding_amount, overdue_amount=r.overdue_amount,
        days_overdue=r.days_overdue, average_payment_delay=r.average_payment_delay,
        average_days_to_pay=r.average_days_to_pay, invoice_count=r.invoice_count,
        open_invoice_count=r.open_invoice_count, late_payment_count=r.late_payment_count,
        customer_value=r.customer_value, total_paid=r.total_paid, delay_vs_history=r.delay_vs_history,
        priority=r.priority.value, priority_score=r.score, reasons=r.reasons,
        oldest_overdue_invoice_number=r.oldest_overdue_invoice_number,
        oldest_overdue_invoice_id=r.oldest_overdue_invoice_id,
        oldest_overdue_amount=r.oldest_overdue_amount)


def filter_priorities(
    rows: list[CustomerReceivable], priority: str | None, overdue_range: str | None,
    customer_id: UUID | None, q: str | None,
) -> list[CustomerReceivable]:
    out = rows
    if priority:
        out = [r for r in out if r.priority.value.lower() == priority.lower()]
    if overdue_range and overdue_range in OVERDUE_RANGES:
        lo, hi = OVERDUE_RANGES[overdue_range]
        out = [r for r in out if r.days_overdue >= lo and (hi is None or r.days_overdue <= hi)]
    if customer_id:
        out = [r for r in out if r.customer_id == customer_id]
    if q:
        out = [r for r in out if q.lower() in r.company_name.lower() or q.lower() in r.customer_name.lower()]
    return out


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DB, _: CurrentUser, today: Today) -> DashboardOut:
    return build_dashboard(db, today)


Priority = Annotated[Literal["High", "Medium", "Low"] | None, Query()]
OverdueRange = Annotated[Literal["1-7", "8-30", "31-60", "60+"] | None, Query()]


@router.get("/collections", response_model=CollectionsOut)
def collections(db: DB, _: CurrentUser, today: Today, priority: Priority = None,
                overdue_range: OverdueRange = None, customer_id: UUID | None = None,
                q: Annotated[str | None, Query(max_length=100)] = None) -> CollectionsOut:
    snap = build_snapshot(db, today)
    rows = filter_priorities(snap.priorities, priority, overdue_range, customer_id, q)
    return CollectionsOut(
        total_outstanding=snap.summary.total_outstanding, total_overdue=snap.summary.total_overdue,
        due_soon=snap.summary.due_soon, collection_rate=snap.summary.collection_rate,
        aging=snap.aging,  # type: ignore[arg-type]
        priorities=[receivable_out(r) for r in rows])


@router.get("/collections/priorities", response_model=list[CustomerReceivableOut])
def priorities(db: DB, _: CurrentUser, today: Today, priority: Priority = None,
               overdue_range: OverdueRange = None, customer_id: UUID | None = None,
               q: Annotated[str | None, Query(max_length=100)] = None) -> list[CustomerReceivableOut]:
    snap = build_snapshot(db, today)
    return [receivable_out(r) for r in filter_priorities(snap.priorities, priority, overdue_range, customer_id, q)]


def risk_out(r: ProductRisk) -> ProductRiskOut:
    a = r.assessment
    return ProductRiskOut(
        product_id=r.product.id, sku=r.product.sku, name=r.product.name, category=r.product.category,
        unit=r.product.unit, supplier_name=r.product.supplier_name, current_quantity=r.current_quantity,
        reserved_quantity=r.reserved_quantity, available_quantity=a.available_quantity,
        average_daily_sales=a.average_daily_sales, stock_coverage_days=a.stock_coverage_days,
        status=a.status.value, recommended_order_quantity=a.recommended_order_quantity,
        stock_value=r.stock_value, purchase_price=r.product.purchase_price)


def _risks(db: Session, today: date) -> list[ProductRisk]:
    order = {"Critical": 0, "Low": 1, "Healthy": 2}
    return sorted(compute_risks(db, today), key=lambda r: (
        order[r.assessment.status.value],
        r.assessment.stock_coverage_days if r.assessment.stock_coverage_days is not None else 1e9,
        r.product.name))


@router.get("/inventory", response_model=InventoryOut)
def inventory(db: DB, _: CurrentUser, today: Today) -> InventoryOut:
    risks = _risks(db, today)
    s = summarize(risks)
    return InventoryOut(
        total_products=s.total_products, low_stock=s.low_stock, critical=s.critical, healthy=s.healthy,
        health_pct=s.health_pct, inventory_value=s.inventory_value, stockout_risk_10d=s.stockout_risk_10d,
        purchase_orders=purchase_order_suggestions(s), risks=[risk_out(r) for r in risks])


@router.get("/inventory/risks", response_model=list[ProductRiskOut])
def inventory_risks(
    db: DB, _: CurrentUser, today: Today,
    status: Annotated[Literal["Healthy", "Low", "Critical"] | None, Query()] = None,
    sort: Annotated[Literal["coverage", "name", "stock", "daily_sales"], Query()] = "coverage",
    descending: bool = False,
) -> list[ProductRiskOut]:
    rows = [risk_out(r) for r in _risks(db, today)]
    if status:
        rows = [r for r in rows if r.status == status]
    keys = {
        "coverage": lambda r: r.stock_coverage_days if r.stock_coverage_days is not None else 1e9,
        "name": lambda r: r.name.lower(), "stock": lambda r: r.available_quantity,
        "daily_sales": lambda r: r.average_daily_sales,
    }
    return sorted(rows, key=keys[sort], reverse=descending)
