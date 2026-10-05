"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import type { ImportKind, ImportPreview } from "@/types/api";

const HINTS: Record<ImportKind, string> = {
  customers: "name, company_name, phone, email, credit_limit, payment_terms_days",
  products: "sku, name, category, unit, purchase_price, selling_price, gst_rate, reorder_level, reorder_quantity, supplier_name, opening_stock",
  invoices: "invoice_number, customer, invoice_date, due_date, sku, quantity, unit_price (one row per line item; imported as drafts)",
  payments: "invoice_number, amount, payment_date, payment_method, reference",
};

export function CsvImport({ kind }: { kind: ImportKind }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [showErrors, setShowErrors] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  async function choose(f: File) {
    setFile(f);
    setPreview(null);
    setMessage(null);
    setError(null);
    setShowErrors(false);
    setBusy(true);
    try {
      setPreview(await api.importPreview(kind, f));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Unable to read this file.");
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.importCommit(kind, file);
      setMessage(`Imported ${res.imported} row(s). ${res.error_rows} row(s) with errors were not imported.`);
      setPreview(null);
      setFile(null);
      if (ref.current) ref.current.value = "";
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Import failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <p className="text-muted-foreground">Columns: {HINTS[kind]}</p>
      <input ref={ref} type="file" accept=".csv" aria-label={`${kind} CSV file`} onChange={(e) => e.target.files?.[0] && choose(e.target.files[0])} />
      {busy && <p role="status" className="text-muted-foreground">Working…</p>}
      {error && <p role="alert" className="text-red-600">{error}</p>}
      {message && <p className="text-emerald-700">{message}</p>}
      {preview && (
        <div className="space-y-3 rounded-md border p-4">
          <p className="font-medium">Import preview</p>
          <ul>
            <li>{preview.total_rows} rows found</li>
            <li className="text-emerald-700">{preview.valid_rows} valid</li>
            <li className={preview.error_rows ? "text-red-700" : ""}>{preview.error_rows} errors</li>
          </ul>
          <div className="flex gap-2">
            {preview.error_rows > 0 && <Button variant="outline" size="sm" onClick={() => setShowErrors((s) => !s)}>{showErrors ? "Hide errors" : "View errors"}</Button>}
            <Button size="sm" disabled={preview.valid_rows === 0 || busy} onClick={commit}>Import valid rows</Button>
          </div>
          {showErrors && (
            <Table>
              <TableHeader><TableRow><TableHead>Row</TableHead><TableHead>Problem</TableHead></TableRow></TableHeader>
              <TableBody>
                {preview.errors.map((e) => <TableRow key={e.row}><TableCell>{e.row}</TableCell><TableCell className="whitespace-normal">{e.errors.join("; ")}</TableCell></TableRow>)}
              </TableBody>
            </Table>
          )}
        </div>
      )}
    </div>
  );
}
