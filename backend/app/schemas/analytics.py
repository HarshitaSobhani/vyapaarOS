from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import Money


class CustomerReceivableOut(BaseModel):
    customer_id: UUID
    customer_name: str
    company_name: str
    phone: str | None
    outstanding_amount: Money
    overdue_amount: Money
    days_overdue: int
    average_payment_delay: float | None
    average_days_to_pay: float | None
    invoice_count: int
    open_invoice_count: int
    late_payment_count: int
    customer_value: Money
    total_paid: Money
    delay_vs_history: int | None
    priority: str
    priority_score: int
    reasons: list[str]
    oldest_overdue_invoice_number: str | None
    oldest_overdue_invoice_id: UUID | None
    oldest_overdue_amount: Money


class AgingBucket(BaseModel):
    bucket: str
    amount: Money
    invoice_count: int


class CollectionsOut(BaseModel):
    total_outstanding: Money
    total_overdue: Money
    due_soon: Money
    collection_rate: float | None
    aging: list[AgingBucket]
    priorities: list[CustomerReceivableOut]


class ProductRiskOut(BaseModel):
    product_id: UUID
    sku: str
    name: str
    category: str
    unit: str
    supplier_name: str
    current_quantity: int
    reserved_quantity: int
    available_quantity: int
    average_daily_sales: float
    stock_coverage_days: float | None
    status: str
    recommended_order_quantity: int
    stock_value: Money
    purchase_price: Money


class PurchaseOrderLine(BaseModel):
    product_id: UUID
    name: str
    sku: str
    quantity: int
    unit: str
    estimated_cost: Money


class PurchaseOrderSuggestion(BaseModel):
    supplier_name: str
    lines: list[PurchaseOrderLine]
    estimated_total: Money


class InventoryOut(BaseModel):
    total_products: int
    low_stock: int
    critical: int
    healthy: int
    health_pct: float
    inventory_value: Money
    stockout_risk_10d: int
    purchase_orders: list[PurchaseOrderSuggestion]
    risks: list[ProductRiskOut]


class Kpi(BaseModel):
    label: str
    value: Money | float
    kind: str  # currency | percent
    hint: str | None = None


class SalesPoint(BaseModel):
    date: date
    sales: Money


class AiOperation(BaseModel):
    key: str
    count: int
    title: str
    detail: str
    href: str
    severity: str  # high | medium | info


class DashboardOut(BaseModel):
    as_of: date
    todays_sales: Money
    outstanding: Money
    overdue: Money
    due_soon: Money
    collection_rate: float | None
    inventory_health_pct: float
    inventory_low: int
    inventory_critical: int
    inventory_healthy: int
    sales_30d: list[SalesPoint]
    sales_30d_total: Money
    aging: list[AgingBucket]
    operations: list[AiOperation]
