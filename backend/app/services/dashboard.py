from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import InvoiceStatus
from app.repositories.receivables import sales_by_day
from app.schemas.analytics import AgingBucket, AiOperation, DashboardOut, SalesPoint
from app.services.inventory import STOCKOUT_RISK_DAYS
from app.services.inventory_service import compute_risks, summarize
from app.services.invoices import count_by_status
from app.services.receivables_service import build_snapshot


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def build_dashboard(db: Session, today: date) -> DashboardOut:
    snap = build_snapshot(db, today)
    inv = summarize(compute_risks(db, today))
    start = today - timedelta(days=29)
    daily = sales_by_day(db, start, today)
    series = [SalesPoint(date=start + timedelta(days=i), sales=daily.get(start + timedelta(days=i), Decimal(0)))
              for i in range(30)]
    drafts = count_by_status(db, InvoiceStatus.draft)

    follow_ups = len(snap.follow_ups)
    high = sum(1 for r in snap.follow_ups if r.priority.value == "High")
    ops = [
        AiOperation(key="collections", count=follow_ups, severity="high" if high else "medium",
                    title=f"{follow_ups} {_plural(follow_ups, 'customer needs', 'customers need')} collection follow-up",
                    detail=f"{high} high priority · ₹{snap.summary.total_overdue:,.0f} overdue",
                    href="/collections?priority=High"),
        AiOperation(key="stockout", count=inv.stockout_risk_10d, severity="high" if inv.critical else "medium",
                    title=f"{inv.stockout_risk_10d} {_plural(inv.stockout_risk_10d, 'product may', 'products may')} stock out within {STOCKOUT_RISK_DAYS} days",
                    detail=f"{inv.critical} critical · {inv.low_stock} low",
                    href="/inventory?status=Critical"),
        AiOperation(key="purchase_orders", count=len(inv.purchase_orders), severity="medium",
                    title=f"{len(inv.purchase_orders)} purchase {_plural(len(inv.purchase_orders), 'order', 'orders')} should be considered today",
                    detail="Grouped by supplier from current stock cover",
                    href="/inventory?view=orders"),
        AiOperation(key="invoice_review", count=drafts, severity="info",
                    title=f"{drafts} {_plural(drafts, 'invoice requires', 'invoices require')} review",
                    detail="Drafts waiting for approval", href="/invoices?status=draft"),
    ]
    return DashboardOut(
        as_of=today, todays_sales=daily.get(today, Decimal(0)), outstanding=snap.summary.total_outstanding,
        overdue=snap.summary.total_overdue, due_soon=snap.summary.due_soon,
        collection_rate=snap.summary.collection_rate, inventory_health_pct=inv.health_pct,
        inventory_low=inv.low_stock, inventory_critical=inv.critical, inventory_healthy=inv.healthy,
        sales_30d=series, sales_30d_total=sum((p.sales for p in series), Decimal(0)),
        aging=[AgingBucket(**a) for a in snap.aging], operations=ops)  # type: ignore[arg-type]
