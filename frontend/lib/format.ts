const inrFull = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function inr(value: number): string {
  return `₹${inrFull.format(Math.round(value))}`;
}

/** ₹1.24L / ₹4.8Cr style for KPI tiles. */
export function inrCompact(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e7) return `₹${(value / 1e7).toFixed(2)}Cr`;
  if (abs >= 1e5) return `₹${(value / 1e5).toFixed(2)}L`;
  if (abs >= 1e3) return `₹${(value / 1e3).toFixed(1)}K`;
  return `₹${Math.round(value)}`;
}

export function pct(value: number | null, digits = 0): string {
  return value === null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

export function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export const STATUS_LABEL: Record<string, string> = {
  draft: "Draft", approved: "Approved", partially_paid: "Partially paid", paid: "Paid",
  overdue: "Overdue", rejected: "Rejected",
};
