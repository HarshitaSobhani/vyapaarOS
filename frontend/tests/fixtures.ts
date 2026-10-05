import type { CustomerReceivable, Dashboard, InvoiceDetail, ProductRisk } from "@/types/api";

export const receivable = (over: Partial<CustomerReceivable> = {}): CustomerReceivable => ({
  customer_id: "c1", customer_name: "Rajesh Agarwal", company_name: "ABC Electricals", phone: "9820011001",
  outstanding_amount: 82400, overdue_amount: 82400, days_overdue: 24, average_payment_delay: 9.5,
  average_days_to_pay: 15, invoice_count: 8, open_invoice_count: 2, late_payment_count: 4, customer_value: 428000,
  total_paid: 300000, delay_vs_history: 9, priority: "High", priority_score: 84,
  reasons: ["Large outstanding balance (₹82,400)", "Payment is 9 days later than their historical average"],
  oldest_overdue_invoice_number: "INV-2609-0042", oldest_overdue_invoice_id: "i1", oldest_overdue_amount: 50000, ...over,
});

export const risk = (over: Partial<ProductRisk> = {}): ProductRisk => ({
  product_id: "p1", sku: "LED-B12", name: "LED Bulb 12W", category: "Lighting", unit: "pcs", supplier_name: "Philips Lighting India",
  current_quantity: 37, reserved_quantity: 0, available_quantity: 37, average_daily_sales: 6.2, stock_coverage_days: 6,
  status: "Critical", recommended_order_quantity: 200, stock_value: 2294, purchase_price: 62, ...over,
});

export const dashboard: Dashboard = {
  as_of: "2026-10-05", todays_sales: 124000, outstanding: 482000, overdue: 113000, due_soon: 60000, collection_rate: 0.82,
  inventory_health_pct: 84, inventory_low: 4, inventory_critical: 2, inventory_healthy: 35,
  sales_30d: Array.from({ length: 30 }, (_, i) => ({ date: `2026-09-${String(i + 1).padStart(2, "0")}`, sales: 1000 * (i + 1) })),
  sales_30d_total: 465000, aging: [],
  operations: [
    { key: "collections", count: 7, title: "7 customers need collection follow-up", detail: "3 high priority", href: "/collections?priority=High", severity: "high" },
    { key: "stockout", count: 12, title: "12 products may stock out within 10 days", detail: "2 critical", href: "/inventory?status=Critical", severity: "high" },
    { key: "invoice_review", count: 3, title: "3 invoices require review", detail: "Drafts", href: "/invoices?status=draft", severity: "info" },
  ],
};

export const draftInvoice = (status: InvoiceDetail["status"] = "draft"): InvoiceDetail => ({
  id: "inv1", invoice_number: "DOC-1001", customer_id: "c1", customer_name: "ABC Electricals", invoice_date: "2026-10-04",
  due_date: "2026-11-03", subtotal: 9600, tax: 1368, total: 10968, paid: 0, outstanding: 0, status, source: "document",
  days_overdue: 0, rejection_reason: null, payments: [],
  items: [{ id: "it1", product_id: "p1", product_name: "LED Bulb 12W", sku: "LED-B12", quantity: 50, unit_price: 120, tax: 720, total: 6720 }],
});
