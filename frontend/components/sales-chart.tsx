"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { inr, inrCompact } from "@/lib/format";
import type { SalesPoint } from "@/types/api";

export function SalesChart({ data }: { data: SalesPoint[] }) {
  return (
    <div className="h-64 w-full" role="img" aria-label="Sales over the last 30 days">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="sales" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#059669" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#059669" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" tickFormatter={(d: string) => d.slice(8) + "/" + d.slice(5, 7)} tick={{ fontSize: 11 }} interval={4} tickLine={false} axisLine={false} />
          <YAxis tickFormatter={inrCompact} tick={{ fontSize: 11 }} width={56} tickLine={false} axisLine={false} />
          <Tooltip formatter={(v) => [inr(Number(v)), "Sales"]} labelFormatter={(d) => String(d)} />
          <Area isAnimationActive={false} type="monotone" dataKey="sales" stroke="#059669" strokeWidth={2} fill="url(#sales)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
