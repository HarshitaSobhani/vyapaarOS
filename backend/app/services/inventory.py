"""Deterministic inventory intelligence. Pure functions: no DB, no LLM."""
import math
from dataclasses import dataclass
from enum import StrEnum

VELOCITY_WINDOW_DAYS = 30
CRITICAL_COVERAGE_DAYS = 7
LOW_COVERAGE_DAYS = 14
STOCKOUT_RISK_DAYS = 10
TARGET_COVERAGE_DAYS = 30


class StockStatus(StrEnum):
    healthy = "Healthy"
    low = "Low"
    critical = "Critical"


@dataclass(frozen=True)
class StockAssessment:
    available_quantity: int
    average_daily_sales: float
    stock_coverage_days: float | None   # None: no sales history, coverage undefined
    status: StockStatus
    recommended_order_quantity: int


def assess_stock(
    current_quantity: int, reserved_quantity: int, units_sold_in_window: int,
    reorder_level: int, reorder_quantity: int, window_days: int = VELOCITY_WINDOW_DAYS,
) -> StockAssessment:
    available = max(current_quantity - reserved_quantity, 0)
    avg = round(units_sold_in_window / window_days, 2) if window_days > 0 else 0.0
    coverage = round(available / avg, 1) if avg > 0 else None

    if available == 0 and (avg > 0 or reorder_level > 0):
        status = StockStatus.critical
    elif coverage is not None and coverage <= CRITICAL_COVERAGE_DAYS:
        status = StockStatus.critical
    elif available <= reorder_level or (coverage is not None and coverage <= LOW_COVERAGE_DAYS):
        status = StockStatus.low
    else:
        status = StockStatus.healthy

    qty = 0
    if status is not StockStatus.healthy:
        need = max(math.ceil(avg * TARGET_COVERAGE_DAYS) - available, reorder_level - available, 0)
        need = max(need, reorder_quantity)
        pack = reorder_quantity if reorder_quantity > 0 else 1
        qty = math.ceil(need / pack) * pack
    return StockAssessment(available, avg, coverage, status, qty)


def may_stock_out_soon(a: StockAssessment) -> bool:
    return a.stock_coverage_days is not None and a.stock_coverage_days <= STOCKOUT_RISK_DAYS


def inventory_health_pct(assessments: list[StockAssessment]) -> float:
    if not assessments:
        return 100.0
    healthy = sum(1 for a in assessments if a.status is StockStatus.healthy)
    return round(100 * healthy / len(assessments), 1)
