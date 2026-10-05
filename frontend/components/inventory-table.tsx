"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { StockBadge } from "@/components/badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ProductRisk } from "@/types/api";

type SortKey = "name" | "available_quantity" | "average_daily_sales" | "stock_coverage_days" | "recommended_order_quantity" | "supplier_name";

const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: "name", label: "Product" },
  { key: "available_quantity", label: "Current stock", numeric: true },
  { key: "average_daily_sales", label: "Daily sales", numeric: true },
  { key: "stock_coverage_days", label: "Coverage", numeric: true },
  { key: "recommended_order_quantity", label: "Recommended order", numeric: true },
  { key: "supplier_name", label: "Supplier" },
];

export function InventoryTable({ rows }: { rows: ProductRisk[] }) {
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean } | null>(null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const dir = sort.desc ? -1 : 1;
    return [...rows].sort((a, b) => {
      const av = a[sort.key] ?? Number.POSITIVE_INFINITY;
      const bv = b[sort.key] ?? Number.POSITIVE_INFINITY;
      if (typeof av === "string" && typeof bv === "string") return av.localeCompare(bv) * dir;
      return (Number(av) - Number(bv)) * dir;
    });
  }, [rows, sort]);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {COLUMNS.slice(0, 1).map((c) => <SortHead key={c.key} col={c} sort={sort} setSort={setSort} />)}
          <TableHead>Status</TableHead>
          {COLUMNS.slice(1).map((c) => <SortHead key={c.key} col={c} sort={sort} setSort={setSort} />)}
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((r) => (
          <TableRow key={r.product_id}>
            <TableCell>
              <div className="font-medium">{r.name}</div>
              <div className="text-xs text-muted-foreground">{r.sku} · {r.category}</div>
            </TableCell>
            <TableCell><StockBadge status={r.status} /></TableCell>
            <TableCell className="text-right tabular-nums">{r.available_quantity}</TableCell>
            <TableCell className="text-right tabular-nums">{r.average_daily_sales.toFixed(1)}</TableCell>
            <TableCell className="text-right tabular-nums">{r.stock_coverage_days === null ? "—" : `${r.stock_coverage_days.toFixed(1)} days`}</TableCell>
            <TableCell className="text-right tabular-nums">{r.recommended_order_quantity ? `${r.recommended_order_quantity} ${r.unit}` : "—"}</TableCell>
            <TableCell>{r.supplier_name}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function SortHead({ col, sort, setSort }: {
  col: { key: SortKey; label: string; numeric?: boolean };
  sort: { key: SortKey; desc: boolean } | null;
  setSort: (s: { key: SortKey; desc: boolean }) => void;
}) {
  const active = sort?.key === col.key;
  return (
    <TableHead className={col.numeric ? "text-right" : undefined} aria-sort={active ? (sort.desc ? "descending" : "ascending") : "none"}>
      <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => setSort({ key: col.key, desc: active ? !sort.desc : false })}>
        {col.label}
        {active && (sort.desc ? <ArrowDown className="size-3" /> : <ArrowUp className="size-3" />)}
      </button>
    </TableHead>
  );
}
