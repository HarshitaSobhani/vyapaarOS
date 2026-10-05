"use client";

import Link from "next/link";
import { AiOperations } from "@/components/ai-operations";
import { KpiCard } from "@/components/kpi-card";
import { AsyncBoundary } from "@/components/page-state";
import { PageHeader } from "@/components/page-header";
import { SalesChart } from "@/components/sales-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api/endpoints";
import { inr, inrCompact, pct, shortDate } from "@/lib/format";

export default function DashboardPage() {
  const { data, error, loading, reload } = useAsync(() => api.dashboard(), []);

  return (
    <>
      <PageHeader title="Dashboard" description={data ? `As of ${shortDate(data.as_of)}` : "Business overview"} />
      <AsyncBoundary loading={loading} error={error ? "Unable to load the dashboard." : null} onRetry={reload}>
        {data && (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard label="Today's sales" value={inrCompact(data.todays_sales)} hint={inr(data.todays_sales)} />
              <KpiCard label="Outstanding receivables" value={inrCompact(data.outstanding)} hint={`${inrCompact(data.due_soon)} due in 7 days`} />
              <KpiCard label="Overdue" value={inrCompact(data.overdue)} tone="danger" hint={`${pct(data.outstanding ? data.overdue / data.outstanding : 0)} of outstanding`} />
              <KpiCard label="Inventory health" value={`${data.inventory_health_pct.toFixed(0)}%`} hint={`${data.inventory_healthy} healthy · ${data.inventory_low} low · ${data.inventory_critical} critical`} />
            </div>
            <div className="grid gap-6 xl:grid-cols-3">
              <Card className="xl:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-baseline justify-between text-sm">
                    <span>Sales, last 30 days</span>
                    <span className="text-xs font-normal text-muted-foreground">{inr(data.sales_30d_total)} total</span>
                  </CardTitle>
                </CardHeader>
                <CardContent><SalesChart data={data.sales_30d} /></CardContent>
              </Card>
              <AiOperations operations={data.operations} />
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader><CardTitle className="text-sm">Receivables</CardTitle></CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <Row label="Outstanding" value={inr(data.outstanding)} />
                  <Row label="Overdue" value={inr(data.overdue)} danger />
                  <Row label="Due in next 7 days" value={inr(data.due_soon)} />
                  <Row label="Collection rate (invoices due in last 90 days)" value={pct(data.collection_rate)} />
                  <Link href="/collections" className="inline-block pt-2 text-xs font-medium text-emerald-700 hover:underline">Open collections →</Link>
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-sm">Inventory health</CardTitle></CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <Row label="Healthy" value={String(data.inventory_healthy)} />
                  <Row label="Low stock" value={String(data.inventory_low)} />
                  <Row label="Critical" value={String(data.inventory_critical)} danger={data.inventory_critical > 0} />
                  <Link href="/inventory" className="inline-block pt-2 text-xs font-medium text-emerald-700 hover:underline">Open inventory →</Link>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </AsyncBoundary>
    </>
  );
}

function Row({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-medium tabular-nums ${danger ? "text-red-700 dark:text-red-400" : ""}`}>{value}</span>
    </div>
  );
}
