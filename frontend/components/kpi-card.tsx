import { Card, CardContent } from "@/components/ui/card";

export function KpiCard({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "danger" | "default" }) {
  return (
    <Card>
      <CardContent className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className={`text-2xl font-semibold tabular-nums ${tone === "danger" ? "text-red-700 dark:text-red-400" : ""}`}>{value}</p>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
