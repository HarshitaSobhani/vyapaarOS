import type * as T from "@/types/api";
import { request } from "./client";

export const api = {
  login: (email: string, password: string) =>
    request<T.LoginResult>("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  me: () => request<T.User>("/auth/me"),
  settings: () => request<T.AppSettings>("/settings"),

  dashboard: () => request<T.Dashboard>("/dashboard"),
  collections: (q: { priority?: string; overdue_range?: string; q?: string }) =>
    request<T.Collections>("/collections", { query: q }),
  inventory: () => request<T.Inventory>("/inventory"),

  customers: (q?: string) => request<T.Customer[]>("/customers", { query: { q } }),
  customer: (id: string) => request<T.CustomerDetail>(`/customers/${id}`),
  products: (q?: string) => request<T.Product[]>("/products", { query: { q } }),

  invoices: (q: { status?: string; q?: string; limit?: number; offset?: number }) =>
    request<T.Page<T.Invoice>>("/invoices", { query: q }),
  invoice: (id: string) => request<T.InvoiceDetail>(`/invoices/${id}`),
  createInvoice: (body: T.InvoiceInput) => request<T.InvoiceDetail>("/invoices", { method: "POST", body }),
  updateInvoice: (id: string, body: T.InvoiceInput) =>
    request<T.InvoiceDetail>(`/invoices/${id}`, { method: "PUT", body }),
  approveInvoice: (id: string) => request<T.InvoiceDetail>(`/invoices/${id}/approve`, { method: "POST" }),
  rejectInvoice: (id: string, reason?: string) =>
    request<T.InvoiceDetail>(`/invoices/${id}/reject`, { method: "POST", body: { reason } }),
  importInvoiceFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T.InvoiceImportResult>("/invoices/import", { method: "POST", form });
  },

  importPreview: (kind: T.ImportKind, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T.ImportPreview>(`/imports/${kind}/preview`, { method: "POST", form });
  },
  importCommit: (kind: T.ImportKind, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T.ImportResult>(`/imports/${kind}/commit`, { method: "POST", form });
  },

  ask: (question: string) => request<T.AskResult>("/ai/ask", { method: "POST", body: { question } }),
  collectionMessage: (customer_id: string, invoice_id?: string, variant = 0) =>
    request<T.CollectionMessage>("/ai/collection-message", { method: "POST", body: { customer_id, invoice_id, variant } }),
  approveReminder: (customer_id: string, invoice_id: string, message: string) =>
    request<T.SendReminderResult>("/ai/collection-message/send", {
      method: "POST", body: { customer_id, invoice_id, message, approved: true },
    }),
};
