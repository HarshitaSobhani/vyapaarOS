"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { InvoiceStatusBadge, PriorityBadge } from "@/components/badges";
import { PageHeader } from "@/components/page-header";
import { AsyncBoundary, EmptyState } from "@/components/page-state";
import { ReminderDialog } from "@/components/reminder-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api/endpoints";
import { inr, shortDate } from "@/lib/format";

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading, reload } = useAsync(() => api.customer(id), [id]);
  const [remind, setRemind] = useState(false);
  const r = data?.receivable;

  return (
    <>
      <Link href="/customers" className="mb-3 inline-block text-xs text-muted-foreground hover:underline">← Customers</Link>
      <AsyncBoundary loading={loading} error={error ? "Unable to load this customer." : null} onRetry={reload}>
        {data && r && (
          <div className="space-y-6">
            <PageHeader
              title={data.customer.company_name}
              description={`${data.customer.name} · ${data.customer.phone ?? "no phone"} · ${data.customer.payment_terms_days}-day terms`}
              actions={r.days_overdue > 0 ? <Button onClick={() => setRemind(true)}>Generate reminder</Button> : undefined}
            />
            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader><CardTitle className="flex items-center gap-3 text-sm">Collection priority <PriorityBadge priority={r.outstanding_amount > 0 ? r.priority : "None"} /></CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
                    <Stat label="Outstanding" value={inr(r.outstanding_amount)} />
                    <Stat label="Days overdue" value={r.days_overdue ? `${r.days_overdue}` : "—"} />
                    <Stat label="Avg. days to pay" value={r.average_days_to_pay === null ? "—" : `${Math.round(r.average_days_to_pay)}`} />
                    <Stat label="Late payments" value={String(r.late_payment_count)} />
                  </dl>
                  <div>
                    <p className="mb-1 text-sm font-medium">Why</p>
                    <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                      {r.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-sm">Account</CardTitle></CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <Stat label="Lifetime invoiced" value={inr(r.customer_value)} />
                  <Stat label="Total paid" value={inr(r.total_paid)} />
                  <Stat label="Credit limit" value={inr(data.customer.credit_limit)} />
                </CardContent>
              </Card>
            </div>
            <Card>
              <CardHeader><CardTitle className="text-sm">Invoices</CardTitle></CardHeader>
              <CardContent className="overflow-x-auto">
                {data.invoices.length === 0 ? <EmptyState title="No invoices yet" hint="Approved invoices for this customer will appear here." /> : (
                <Table>
                  <TableHeader><TableRow>
                    <TableHead>Invoice</TableHead><TableHead>Date</TableHead><TableHead>Due</TableHead>
                    <TableHead className="text-right">Total</TableHead><TableHead className="text-right">Outstanding</TableHead><TableHead>Status</TableHead>
                  </TableRow></TableHeader>
                  <TableBody>
                    {data.invoices.map((i) => (
                      <TableRow key={i.id}>
                        <TableCell className="font-medium">{i.invoice_number}</TableCell>
                        <TableCell>{shortDate(i.invoice_date)}</TableCell>
                        <TableCell>{shortDate(i.due_date)}</TableCell>
                        <TableCell className="text-right tabular-nums">{inr(i.total)}</TableCell>
                        <TableCell className="text-right tabular-nums">{inr(i.outstanding)}</TableCell>
                        <TableCell><InvoiceStatusBadge status={i.status} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </AsyncBoundary>
      <ReminderDialog customerId={remind ? id : null} invoiceId={r?.oldest_overdue_invoice_id} onOpenChange={setRemind} />
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}
