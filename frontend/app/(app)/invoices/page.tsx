"use client";

import { Suspense, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FileUp, Plus } from "lucide-react";
import { InvoiceStatusBadge } from "@/components/badges";
import { InvoiceForm } from "@/components/invoice-form";
import { InvoiceReview } from "@/components/invoice-review";
import { NativeSelect } from "@/components/native-select";
import { PageHeader } from "@/components/page-header";
import { AsyncBoundary } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAsync } from "@/hooks/use-async";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import { inr, shortDate } from "@/lib/format";
import type { InvoiceImportResult } from "@/types/api";

function InvoicesView() {
  const router = useRouter();
  const params = useSearchParams();
  const status = params.get("status") ?? "";
  const [q, setQ] = useState("");
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [importResult, setImportResult] = useState<InvoiceImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const list = useAsync(() => api.invoices({ status: status || undefined, q: q || undefined, limit: 100 }), [status, q]);
  const customers = useAsync(() => api.customers(), []);
  const products = useAsync(() => api.products(), []);

  async function upload(file: File) {
    setUploading(true);
    setImportError(null);
    setImportResult(null);
    try {
      const res = await api.importInvoiceFile(file);
      setImportResult(res);
      list.reload();
      const first = res.results.find((r) => r.invoice_id);
      if (res.created === 1 && res.failed === 0 && first?.invoice_id) setReviewId(first.invoice_id);
    } catch (e) {
      setImportError(e instanceof ApiError ? e.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <>
      <PageHeader
        title="Invoices"
        description="Imported and manual invoices are drafts until you approve them."
        actions={
          <>
            <input ref={fileRef} type="file" accept=".json,.csv,.pdf" className="hidden" aria-label="Upload invoice file"
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            <Button variant="outline" disabled={uploading} onClick={() => fileRef.current?.click()}><FileUp /> {uploading ? "Extracting…" : "Import JSON / CSV / PDF"}</Button>
            <Button onClick={() => setCreating(true)}><Plus /> New invoice</Button>
          </>
        }
      />
      {importError && <p role="alert" className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">{importError}</p>}
      {importResult && (
        <div className="mb-4 rounded-md border bg-background p-3 text-sm">
          <p className="font-medium">{importResult.filename}: {importResult.created} draft(s) created, {importResult.failed} failed</p>
          <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
            {importResult.results.filter((r) => r.errors.length).map((r, i) => <li key={i}>{r.invoice_number ?? "Invoice"}: {r.errors.join("; ")}</li>)}
          </ul>
        </div>
      )}
      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Input aria-label="Search invoices" placeholder="Search number or customer" className="w-64" value={q} onChange={(e) => setQ(e.target.value)} />
            <NativeSelect aria-label="Status" value={status} onChange={(e) => router.replace(e.target.value ? `/invoices?status=${e.target.value}` : "/invoices")}>
              <option value="">All statuses</option><option value="draft">Draft (needs review)</option><option value="approved">Approved</option>
              <option value="partially_paid">Partially paid</option><option value="paid">Paid</option><option value="overdue">Overdue</option><option value="rejected">Rejected</option>
            </NativeSelect>
          </div>
          <div className="overflow-x-auto">
            <AsyncBoundary loading={list.loading && !list.data} error={list.error ? "Unable to load invoices." : null} onRetry={list.reload}
              empty={!!list.data && list.data.items.length === 0} emptyTitle="No invoices found" emptyHint="Create an invoice or import a file to get started.">
              <Table>
                <TableHeader><TableRow>
                  <TableHead>Invoice</TableHead><TableHead>Customer</TableHead><TableHead>Date</TableHead><TableHead>Due</TableHead>
                  <TableHead className="text-right">Total</TableHead><TableHead className="text-right">Outstanding</TableHead><TableHead>Status</TableHead><TableHead />
                </TableRow></TableHeader>
                <TableBody>
                  {list.data?.items.map((i) => (
                    <TableRow key={i.id}>
                      <TableCell className="font-medium">{i.invoice_number}</TableCell>
                      <TableCell>{i.customer_name}</TableCell>
                      <TableCell>{shortDate(i.invoice_date)}</TableCell>
                      <TableCell>{shortDate(i.due_date)}</TableCell>
                      <TableCell className="text-right tabular-nums">{inr(i.total)}</TableCell>
                      <TableCell className="text-right tabular-nums">{inr(i.outstanding)}</TableCell>
                      <TableCell><InvoiceStatusBadge status={i.status} /></TableCell>
                      <TableCell><Button size="sm" variant={i.status === "draft" ? "default" : "ghost"} onClick={() => setReviewId(i.id)}>{i.status === "draft" ? "Review" : "View"}</Button></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AsyncBoundary>
          </div>
        </CardContent>
      </Card>

      <InvoiceReview invoiceId={reviewId} onClose={() => setReviewId(null)} onChanged={list.reload} />

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader><DialogTitle>New invoice</DialogTitle></DialogHeader>
          {customers.data && products.data ? (
            <InvoiceForm customers={customers.data} products={products.data} submitLabel="Create draft" onCancel={() => setCreating(false)}
              onSubmit={async (input) => { const inv = await api.createInvoice(input); setCreating(false); list.reload(); setReviewId(inv.id); }} />
          ) : <p className="text-sm text-muted-foreground">Loading catalogue…</p>}
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function InvoicesPage() {
  return <Suspense><InvoicesView /></Suspense>;
}
