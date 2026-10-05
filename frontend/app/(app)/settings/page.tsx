"use client";

import { useState } from "react";
import { CsvImport } from "@/components/csv-import";
import { PageHeader } from "@/components/page-header";
import { AsyncBoundary } from "@/components/page-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api/endpoints";
import type { ImportKind } from "@/types/api";
import { cn } from "@/lib/utils";

const KINDS: ImportKind[] = ["customers", "products", "invoices", "payments"];

export default function SettingsPage() {
  const { data, error, loading, reload } = useAsync(() => api.settings(), []);
  const [kind, setKind] = useState<ImportKind>("customers");

  return (
    <>
      <PageHeader title="Settings" />
      <AsyncBoundary loading={loading} error={error ? "Unable to load settings." : null} onRetry={reload}>
        {data && (
          <div className="max-w-3xl space-y-6">
            <Card>
              <CardHeader><CardTitle className="text-sm">Account</CardTitle></CardHeader>
              <CardContent className="text-sm">
                <p className="font-medium">{data.user.name}</p>
                <p className="text-muted-foreground">{data.user.email} · {data.user.role}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-sm">AI and messaging</CardTitle></CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>AI provider: <strong>{data.ai_provider}</strong> {data.ai_provider === "openai" && !data.ai_configured && <span className="text-amber-700">(no API key: using built-in templates)</span>}</p>
                <p className="text-muted-foreground">All figures are computed by the backend. The model only words explanations and reminders, and its output is validated.</p>
                <p>WhatsApp: reminders open a pre-filled WhatsApp chat after you approve. VyapaarOS does not send messages itself.</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-sm">Import data (CSV)</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div role="tablist" className="inline-flex rounded-lg bg-muted p-0.5 text-sm">
                  {KINDS.map((k) => (
                    <button key={k} role="tab" aria-selected={kind === k} onClick={() => setKind(k)}
                      className={cn("rounded-md px-3 py-1.5 capitalize", kind === k ? "bg-background font-medium shadow-sm" : "text-muted-foreground")}>{k}</button>
                  ))}
                </div>
                <CsvImport key={kind} kind={kind} />
                <p className="text-xs text-muted-foreground">Max file size {data.max_upload_mb} MB. Importing requires an owner or manager account.</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-sm">Accounting integrations</CardTitle></CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                CSV import is the supported source today. The importer sits behind an <code>AccountingSource</code> interface so a Tally adapter can be added later; there is no live Tally sync.
              </CardContent>
            </Card>
          </div>
        )}
      </AsyncBoundary>
    </>
  );
}
