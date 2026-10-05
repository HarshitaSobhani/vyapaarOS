"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CollectionsTable } from "@/components/collections-table";
import { KpiCard } from "@/components/kpi-card";
import { NativeSelect } from "@/components/native-select";
import { PageHeader } from "@/components/page-header";
import { AsyncBoundary } from "@/components/page-state";
import { ReminderDialog } from "@/components/reminder-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api/endpoints";
import { inr, inrCompact, pct } from "@/lib/format";

const BUCKET_COLORS = ["#94a3b8", "#fbbf24", "#f59e0b", "#ef4444", "#b91c1c"];

function CollectionsView() {
  const router = useRouter();
  const params = useSearchParams();
  const priority = params.get("priority") ?? "";
  const range = params.get("range") ?? "";
  const [q, setQ] = useState(params.get("q") ?? "");
  const [remindFor, setRemindFor] = useState<{ customerId: string; invoiceId: string | null } | null>(null);

  const { data, error, loading, reload } = useAsync(
    () => api.collections({ priority: priority || undefined, overdue_range: range || undefined, q: q || undefined }),
    [priority, range, q],
  );

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    router.replace(`/collections?${next.toString()}`);
  }

  return (
    <>
      <PageHeader title="Collections" description="Who to chase first, and why. Scores are calculated from invoice and payment history." />
      <div className="space-y-6">
        <AsyncBoundary loading={loading && !data} error={error ? "Unable to load collection data." : null} onRetry={reload}>
          {data && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <KpiCard label="Total outstanding" value={inrCompact(data.total_outstanding)} hint={inr(data.total_outstanding)} />
                <KpiCard label="Total overdue" value={inrCompact(data.total_overdue)} tone="danger" hint={inr(data.total_overdue)} />
                <KpiCard label="Due in 7 days" value={inrCompact(data.due_soon)} />
                <KpiCard label="Collection rate" value={pct(data.collection_rate)} hint="Paid share of invoices due in last 90 days" />
              </div>
              <Card>
                <CardHeader><CardTitle className="text-sm">Aging of open invoices</CardTitle></CardHeader>
                <CardContent>
                  <div className="h-56" role="img" aria-label="Receivables aging buckets">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={data.aging} margin={{ left: 0, right: 8, top: 8 }}>
                        <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="bucket" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                        <YAxis tickFormatter={inrCompact} width={56} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                        <Tooltip cursor={{ fill: "rgba(148,163,184,0.12)" }} formatter={(v, _n, p) => [`${inr(Number(v))} · ${p.payload.invoice_count} invoices`, "Outstanding"]} />
                        <Bar dataKey="amount" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                          {data.aging.map((_, i) => <Cell key={i} fill={BUCKET_COLORS[i]} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </AsyncBoundary>

        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center justify-between gap-3 text-sm">
              <span>Customer priority</span>
              <span className="flex flex-wrap items-center gap-2 font-normal">
                <Input aria-label="Search customer" placeholder="Search customer" className="h-8 w-48" value={q} onChange={(e) => setQ(e.target.value)} />
                <NativeSelect aria-label="Priority" value={priority} onChange={(e) => setParam("priority", e.target.value)}>
                  <option value="">All priorities</option>
                  <option>High</option><option>Medium</option><option>Low</option>
                </NativeSelect>
                <NativeSelect aria-label="Overdue range" value={range} onChange={(e) => setParam("range", e.target.value)}>
                  <option value="">Any overdue range</option>
                  <option value="1-7">1–7 days</option><option value="8-30">8–30 days</option>
                  <option value="31-60">31–60 days</option><option value="60+">60+ days</option>
                </NativeSelect>
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <AsyncBoundary loading={loading && !data} error={error ? "Unable to load collection data." : null} onRetry={reload}
              empty={!!data && data.priorities.length === 0} emptyTitle="No customers match these filters" emptyHint="Clear a filter to see more.">
              {data && (
                <CollectionsTable rows={data.priorities} onRemind={(r) => setRemindFor({ customerId: r.customer_id, invoiceId: r.oldest_overdue_invoice_id })} />
              )}
            </AsyncBoundary>
          </CardContent>
        </Card>
      </div>
      <ReminderDialog customerId={remindFor?.customerId ?? null} invoiceId={remindFor?.invoiceId} onOpenChange={(o) => !o && setRemindFor(null)} />
    </>
  );
}

export default function CollectionsPage() {
  return <Suspense><CollectionsView /></Suspense>;
}
