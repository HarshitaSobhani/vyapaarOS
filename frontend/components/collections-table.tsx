import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PriorityBadge } from "@/components/badges";
import { inr } from "@/lib/format";
import type { CustomerReceivable } from "@/types/api";

export function CollectionsTable({ rows, onRemind }: { rows: CustomerReceivable[]; onRemind: (r: CustomerReceivable) => void }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Customer</TableHead>
          <TableHead className="text-right">Outstanding</TableHead>
          <TableHead className="text-right">Overdue</TableHead>
          <TableHead className="text-right">Days overdue</TableHead>
          <TableHead className="text-right">Avg. delay</TableHead>
          <TableHead className="text-right">Late pmts</TableHead>
          <TableHead>Priority</TableHead>
          <TableHead className="min-w-64">Why</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.customer_id}>
            <TableCell>
              <Link href={`/customers/${r.customer_id}`} className="font-medium hover:underline">{r.company_name}</Link>
              <div className="text-xs text-muted-foreground">{r.customer_name}</div>
            </TableCell>
            <TableCell className="text-right tabular-nums">{inr(r.outstanding_amount)}</TableCell>
            <TableCell className="text-right tabular-nums">{inr(r.overdue_amount)}</TableCell>
            <TableCell className="text-right tabular-nums">{r.days_overdue || "—"}</TableCell>
            <TableCell className="text-right tabular-nums">{r.average_payment_delay === null ? "—" : `${r.average_payment_delay}d`}</TableCell>
            <TableCell className="text-right tabular-nums">{r.late_payment_count}</TableCell>
            <TableCell><PriorityBadge priority={r.priority} /></TableCell>
            <TableCell className="whitespace-normal text-xs text-muted-foreground">{r.reasons.slice(0, 2).join(" · ")}</TableCell>
            <TableCell>
              {r.days_overdue > 0 && (
                <Button size="sm" variant="outline" onClick={() => onRemind(r)}>Generate reminder</Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
