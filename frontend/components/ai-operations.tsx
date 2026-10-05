import Link from "next/link";
import { ChevronRight, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AiOperation } from "@/types/api";

const DOT: Record<string, string> = { high: "bg-red-500", medium: "bg-amber-500", info: "bg-sky-500" };

export function AiOperations({ operations }: { operations: AiOperation[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Sparkles className="size-4 text-emerald-600" /> AI Operations
        </CardTitle>
      </CardHeader>
      <CardContent className="divide-y">
        {operations.map((op) => (
          <Link key={op.key} href={op.href} className="group flex items-center gap-3 py-3 first:pt-0 last:pb-0 hover:bg-muted/40">
            <span className={`size-2 shrink-0 rounded-full ${DOT[op.severity]}`} aria-hidden />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{op.title}</span>
              <span className="block text-xs text-muted-foreground">{op.detail}</span>
            </span>
            <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
