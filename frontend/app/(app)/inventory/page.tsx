"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { InventoryTable } from "@/components/inventory-table";
import { KpiCard } from "@/components/kpi-card";
import { NativeSelect } from "@/components/native-select";
import { PageHeader } from "@/components/page-header";
import { AsyncBoundary } from "@/components/page-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api/endpoints";
import { inr, inrCompact } from "@/lib/format";
import { cn } from "@/lib/utils";

function InventoryView() {
  const router = useRouter();
  const params = useSearchParams();
  const status = params.get("status") ?? "";
  const view = params.get("view") === "orders" ? "orders" : "risk";
  const { data, error, loading, reload } = useAsync(() => api.inventory(), []);

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    router.replace(`/inventory?${next.toString()}`);
  }

  const rows = data ? data.risks.filter((r) => !status || r.status === status) : [];

  return (
    <>
      <PageHeader title="Inventory" description="Stock cover is calculated from the last 30 days of approved invoices." />
      <div className="space-y-6">
        <AsyncBoundary loading={loading} error={error ? "Unable to load inventory data." : null} onRetry={reload}>
          {data && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <KpiCard label="Total products" value={String(data.total_products)} />
                <KpiCard label="Low stock" value={String(data.low_stock)} />
                <KpiCard label="Critical" value={String(data.critical)} tone={data.critical ? "danger" : "default"} hint={`${data.stockout_risk_10d} may stock out within 10 days`} />
                <KpiCard label="Inventory value (at cost)" value={inrCompact(data.inventory_value)} hint={inr(data.inventory_value)} />
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div role="tablist" className="inline-flex rounded-lg bg-muted p-0.5 text-sm">
                  {([["risk", "Stock risk"], ["orders", `Purchase suggestions (${data.purchase_orders.length})`]] as const).map(([k, label]) => (
                    <button key={k} role="tab" aria-selected={view === k} onClick={() => setParam("view", k === "orders" ? "orders" : "")}
                      className={cn("rounded-md px-3 py-1.5", view === k ? "bg-background font-medium shadow-sm" : "text-muted-foreground")}>{label}</button>
                  ))}
                </div>
                {view === "risk" && (
                  <NativeSelect aria-label="Status" value={status} onChange={(e) => setParam("status", e.target.value)}>
                    <option value="">All statuses</option><option>Critical</option><option>Low</option><option>Healthy</option>
                  </NativeSelect>
                )}
              </div>
              {view === "risk" ? (
                <Card><CardContent className="overflow-x-auto">
                  {rows.length === 0
                    ? <p className="py-8 text-center text-sm text-muted-foreground">No products match this filter.</p>
                    : <InventoryTable rows={rows} />}
                </CardContent></Card>
              ) : data.purchase_orders.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">No purchase orders needed right now.</p>
              ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                  {data.purchase_orders.map((po) => (
                    <Card key={po.supplier_name}>
                      <CardHeader><CardTitle className="flex justify-between text-sm"><span>{po.supplier_name}</span><span className="tabular-nums text-muted-foreground">{inr(po.estimated_total)}</span></CardTitle></CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader><TableRow><TableHead>Product</TableHead><TableHead className="text-right">Qty</TableHead><TableHead className="text-right">Est. cost</TableHead></TableRow></TableHeader>
                          <TableBody>
                            {po.lines.map((l) => (
                              <TableRow key={l.product_id}><TableCell>{l.name}</TableCell><TableCell className="text-right tabular-nums">{l.quantity} {l.unit}</TableCell><TableCell className="text-right tabular-nums">{inr(l.estimated_cost)}</TableCell></TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </>
          )}
        </AsyncBoundary>
      </div>
    </>
  );
}

export default function InventoryPage() {
  return <Suspense><InventoryView /></Suspense>;
}
