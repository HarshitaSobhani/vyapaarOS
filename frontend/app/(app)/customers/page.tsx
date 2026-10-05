"use client";

import Link from "next/link";
import { useState } from "react";
import { PriorityBadge } from "@/components/badges";
import { PageHeader } from "@/components/page-header";
import { AsyncBoundary } from "@/components/page-state";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api/endpoints";
import { inr } from "@/lib/format";

export default function CustomersPage() {
  const [q, setQ] = useState("");
  const { data, error, loading, reload } = useAsync(() => api.customers(q || undefined), [q]);
  return (
    <>
      <PageHeader title="Customers" actions={<Input aria-label="Search customers" placeholder="Search customers" className="w-56" value={q} onChange={(e) => setQ(e.target.value)} />} />
      <Card>
        <CardContent className="overflow-x-auto">
          <AsyncBoundary loading={loading && !data} error={error ? "Unable to load customers." : null} onRetry={reload}
            empty={!!data && data.length === 0} emptyTitle="No customers found" emptyHint="Import customers from Settings.">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead><TableHead>Phone</TableHead>
                  <TableHead className="text-right">Credit limit</TableHead>
                  <TableHead className="text-right">Outstanding</TableHead>
                  <TableHead className="text-right">Overdue</TableHead>
                  <TableHead>Priority</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <Link href={`/customers/${c.id}`} className="font-medium hover:underline">{c.company_name}</Link>
                      <div className="text-xs text-muted-foreground">{c.name}</div>
                    </TableCell>
                    <TableCell>{c.phone ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{inr(c.credit_limit)}</TableCell>
                    <TableCell className="text-right tabular-nums">{inr(c.outstanding_amount)}</TableCell>
                    <TableCell className="text-right tabular-nums">{inr(c.overdue_amount)}</TableCell>
                    <TableCell><PriorityBadge priority={c.priority} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </AsyncBoundary>
        </CardContent>
      </Card>
    </>
  );
}
