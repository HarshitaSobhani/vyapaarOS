"use client";

import { useState } from "react";
import { InvoiceStatusBadge } from "@/components/badges";
import { InvoiceForm } from "@/components/invoice-form";
import { AsyncBoundary } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAsync } from "@/hooks/use-async";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import { inr, shortDate } from "@/lib/format";

const SOURCE_LABEL = { manual: "Manual entry", csv: "CSV import", document: "Document upload" } as const;

export function InvoiceReview({ invoiceId, onClose, onChanged }: { invoiceId: string | null; onClose: () => void; onChanged: () => void }) {
  return (
    <Dialog open={invoiceId !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        {invoiceId && <ReviewBody key={invoiceId} invoiceId={invoiceId} onClose={onClose} onChanged={onChanged} />}
      </DialogContent>
    </Dialog>
  );
}

function ReviewBody({ invoiceId, onClose, onChanged }: { invoiceId: string; onClose: () => void; onChanged: () => void }) {
  const detail = useAsync(() => api.invoice(invoiceId), [invoiceId]);
  const customers = useAsync(() => api.customers(), []);
  const products = useAsync(() => api.products(), []);
  const [mode, setMode] = useState<"view" | "edit" | "reject">("view");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inv = detail.data;

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
      detail.reload();
      setMode("view");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Action failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>{inv ? `Invoice ${inv.invoice_number}` : "Invoice"}</DialogTitle>
        <DialogDescription>
          {inv?.status === "draft" ? "Review the extracted data. Nothing enters your business data until you approve." : "Invoice details"}
        </DialogDescription>
      </DialogHeader>
      <AsyncBoundary loading={detail.loading && !inv} error={detail.error ? "Unable to load this invoice." : null} onRetry={detail.reload}>
        {inv && mode === "edit" && customers.data && products.data && (
          <InvoiceForm
            customers={customers.data} products={products.data} submitLabel="Save changes" onCancel={() => setMode("view")}
            initial={{ customer_id: inv.customer_id, invoice_number: inv.invoice_number, invoice_date: inv.invoice_date, items: inv.items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })) }}
            onSubmit={async (input) => { await api.updateInvoice(inv.id, input); onChanged(); detail.reload(); setMode("view"); }}
          />
        )}
        {inv && mode !== "edit" && (
          <div className="space-y-4 text-sm">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
              <InvoiceStatusBadge status={inv.status} />
              <span><span className="text-muted-foreground">Customer </span>{inv.customer_name}</span>
              <span><span className="text-muted-foreground">Date </span>{shortDate(inv.invoice_date)}</span>
              <span><span className="text-muted-foreground">Due </span>{shortDate(inv.due_date)}</span>
              <span><span className="text-muted-foreground">Source </span>{SOURCE_LABEL[inv.source]}</span>
            </div>
            <Table>
              <TableHeader><TableRow><TableHead>Item</TableHead><TableHead className="text-right">Qty × Price</TableHead><TableHead className="text-right">GST</TableHead><TableHead className="text-right">Total</TableHead></TableRow></TableHeader>
              <TableBody>
                {inv.items.map((i) => (
                  <TableRow key={i.id}>
                    <TableCell>{i.product_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{i.quantity} × {inr(i.unit_price)}</TableCell>
                    <TableCell className="text-right tabular-nums">{inr(i.tax)}</TableCell>
                    <TableCell className="text-right tabular-nums">{inr(i.total)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <dl className="ml-auto w-56 space-y-1 tabular-nums">
              <div className="flex justify-between"><dt className="text-muted-foreground">Subtotal</dt><dd>{inr(inv.subtotal)}</dd></div>
              <div className="flex justify-between"><dt className="text-muted-foreground">GST</dt><dd>{inr(inv.tax)}</dd></div>
              <div className="flex justify-between border-t pt-1 font-semibold"><dt>Total</dt><dd>{inr(inv.total)}</dd></div>
            </dl>
            {inv.rejection_reason && <p className="text-muted-foreground">Rejected: {inv.rejection_reason}</p>}
            {error && <p role="alert" className="text-red-600">{error}</p>}
            {inv.status === "draft" && mode === "view" && (
              <div className="flex gap-2">
                <Button disabled={busy} onClick={() => act(() => api.approveInvoice(inv.id))}>Approve Invoice</Button>
                <Button variant="outline" disabled={busy} onClick={() => setMode("edit")}>Edit</Button>
                <Button variant="outline" disabled={busy} onClick={() => setMode("reject")}>Reject</Button>
              </div>
            )}
            {mode === "reject" && (
              <div className="flex gap-2">
                <Input aria-label="Rejection reason" placeholder="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
                <Button variant="destructive" disabled={busy} onClick={() => act(() => api.rejectInvoice(inv.id, reason || undefined))}>Confirm reject</Button>
                <Button variant="ghost" onClick={() => setMode("view")}>Cancel</Button>
              </div>
            )}
            {inv.status !== "draft" && <Button variant="outline" onClick={onClose}>Close</Button>}
          </div>
        )}
      </AsyncBoundary>
    </>
  );
}
