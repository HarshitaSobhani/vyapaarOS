export type Priority = "High" | "Medium" | "Low";
export type StockStatus = "Healthy" | "Low" | "Critical";
export type InvoiceStatus = "draft" | "approved" | "partially_paid" | "paid" | "overdue" | "rejected";
export type InvoiceSource = "manual" | "csv" | "document";
export type ImportKind = "customers" | "products" | "invoices" | "payments";

export interface User { id: string; name: string; email: string; role: "owner" | "manager" | "sales" }
export interface LoginResult { user: User; access_token: string }

export interface AgingBucket { bucket: string; amount: number; invoice_count: number }
export interface AiOperation { key: string; count: number; title: string; detail: string; href: string; severity: "high" | "medium" | "info" }
export interface SalesPoint { date: string; sales: number }
export interface Dashboard {
  as_of: string; todays_sales: number; outstanding: number; overdue: number; due_soon: number;
  collection_rate: number | null; inventory_health_pct: number; inventory_low: number;
  inventory_critical: number; inventory_healthy: number; sales_30d: SalesPoint[];
  sales_30d_total: number; aging: AgingBucket[]; operations: AiOperation[];
}

export interface CustomerReceivable {
  customer_id: string; customer_name: string; company_name: string; phone: string | null;
  outstanding_amount: number; overdue_amount: number; days_overdue: number;
  average_payment_delay: number | null; average_days_to_pay: number | null; invoice_count: number;
  open_invoice_count: number; late_payment_count: number; customer_value: number; total_paid: number;
  delay_vs_history: number | null; priority: Priority; priority_score: number; reasons: string[];
  oldest_overdue_invoice_number: string | null; oldest_overdue_invoice_id: string | null;
  oldest_overdue_amount: number;
}
export interface Collections {
  total_outstanding: number; total_overdue: number; due_soon: number; collection_rate: number | null;
  aging: AgingBucket[]; priorities: CustomerReceivable[];
}

export interface ProductRisk {
  product_id: string; sku: string; name: string; category: string; unit: string; supplier_name: string;
  current_quantity: number; reserved_quantity: number; available_quantity: number;
  average_daily_sales: number; stock_coverage_days: number | null; status: StockStatus;
  recommended_order_quantity: number; stock_value: number; purchase_price: number;
}
export interface PurchaseOrder {
  supplier_name: string; estimated_total: number;
  lines: { product_id: string; name: string; sku: string; quantity: number; unit: string; estimated_cost: number }[];
}
export interface Inventory {
  total_products: number; low_stock: number; critical: number; healthy: number; health_pct: number;
  inventory_value: number; stockout_risk_10d: number; purchase_orders: PurchaseOrder[]; risks: ProductRisk[];
}

export interface Customer {
  id: string; name: string; company_name: string; phone: string | null; email: string | null;
  credit_limit: number; payment_terms_days: number; outstanding_amount: number; overdue_amount: number;
  days_overdue: number; priority: Priority | "None";
}
export interface Product {
  id: string; sku: string; name: string; category: string; unit: string; purchase_price: number;
  selling_price: number; gst_rate: number; supplier_name: string; current_quantity: number;
}
export interface Payment { id: string; invoice_id: string; amount: number; payment_date: string; payment_method: string; reference: string | null }
export interface Invoice {
  id: string; invoice_number: string; customer_id: string; customer_name: string; invoice_date: string;
  due_date: string; subtotal: number; tax: number; total: number; paid: number; outstanding: number;
  status: InvoiceStatus; source: InvoiceSource; days_overdue: number; rejection_reason: string | null;
}
export interface InvoiceItem { id: string; product_id: string; product_name: string; sku: string; quantity: number; unit_price: number; tax: number; total: number }
export interface InvoiceDetail extends Invoice { items: InvoiceItem[]; payments: Payment[] }
export interface Page<T> { items: T[]; total: number }
export interface CustomerDetail { customer: Customer; receivable: CustomerReceivable; invoices: Invoice[]; payments: Payment[] }

export interface InvoiceInput {
  invoice_number?: string | null; customer_id: string; invoice_date: string; due_date?: string | null;
  items: { product_id: string; quantity: number; unit_price?: number | null }[];
}
export interface InvoiceImportResult {
  filename: string; extractor: string; created: number; failed: number;
  results: { invoice_number: string | null; status: string; invoice_id: string | null; errors: string[] }[];
}

export interface RowError { row: number; errors: string[]; data: Record<string, string> }
export interface ImportPreview { kind: ImportKind; total_rows: number; valid_rows: number; error_rows: number; errors: RowError[] }
export interface ImportResult extends ImportPreview { imported: number }

export interface AskResult { answer: string; intent: string; provider: string; fallback_used: boolean; facts: Record<string, unknown> | null }
export interface CollectionMessage {
  message: string; customer_id: string; customer_name: string; phone: string | null; invoice_id: string;
  invoice_number: string; amount: number; due_date: string; days_overdue: number; provider: string; fallback_used: boolean;
}
export interface SendReminderResult { mode: string; url: string | null; detail: string }
export interface AppSettings {
  user: User; ai_provider: string; ai_configured: boolean; whatsapp_mode: string; environment: string; max_upload_mb: number;
}
