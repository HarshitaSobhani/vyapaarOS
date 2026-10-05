import { Badge } from "@/components/ui/badge";
import { STATUS_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";

const TONES: Record<string, string> = {
  High: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  Critical: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  overdue: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  rejected: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  Medium: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  Low: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  partially_paid: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  draft: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  Healthy: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  paid: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  approved: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  None: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

function Pill({ tone, children }: { tone: string; children: React.ReactNode }) {
  return <Badge variant="secondary" className={cn("font-medium", TONES[tone])}>{children}</Badge>;
}

export function PriorityBadge({ priority }: { priority: string }) {
  // For priority, "Low" reads as calm, not as a warning.
  return <Pill tone={priority === "Low" ? "None" : priority}>{priority === "None" ? "—" : priority}</Pill>;
}

export function StockBadge({ status }: { status: string }) {
  return <Pill tone={status}>{status}</Pill>;
}

export function InvoiceStatusBadge({ status }: { status: string }) {
  return <Pill tone={status}>{STATUS_LABEL[status] ?? status}</Pill>;
}
