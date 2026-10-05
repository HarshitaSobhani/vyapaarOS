"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import type { AskResult } from "@/types/api";

const SUGGESTIONS = [
  "Which customers should I follow up with today?",
  "What is causing my overdue receivables?",
  "Which customer has the worst payment behavior?",
  "Why is ABC Electricals high priority?",
  "Which products may stock out soon?",
];

interface Turn { question: string; result?: AskResult; error?: string }

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);

  async function ask(text: string) {
    const q = text.trim();
    if (q.length < 2 || busy) return;
    setBusy(true);
    setQuestion("");
    setTurns((t) => [{ question: q }, ...t]);
    try {
      const result = await api.ask(q);
      setTurns((t) => [{ question: q, result }, ...t.slice(1)]);
    } catch (e) {
      setTurns((t) => [{ question: q, error: e instanceof ApiError ? e.message : "Unable to answer right now. Please try again." }, ...t.slice(1)]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="AI Assistant" description="Answers questions about your receivables, collections and stock. Figures come from your data, not from the model." />
      <div className="max-w-3xl space-y-4">
        <form onSubmit={(e) => { e.preventDefault(); void ask(question); }} className="flex gap-2">
          <Input aria-label="Question" placeholder="Ask about collections, overdue invoices or stock…" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500} />
          <Button type="submit" disabled={busy || question.trim().length < 2}><Send /> Ask</Button>
        </form>
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" disabled={busy} onClick={() => void ask(s)}
              className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50">{s}</button>
          ))}
        </div>
        {turns.length === 0 && <p className="pt-6 text-center text-sm text-muted-foreground">Pick a suggestion or type a question to begin.</p>}
        {turns.map((t, i) => (
          <Card key={`${i}-${t.question}`}>
            <CardContent className="space-y-3">
              <p className="text-sm font-medium">{t.question}</p>
              {!t.result && !t.error && <p role="status" className="text-sm text-muted-foreground">Looking at your data…</p>}
              {t.error && <p role="alert" className="text-sm text-red-600">{t.error}</p>}
              {t.result && (
                <>
                  <p className="whitespace-pre-line text-sm leading-relaxed">{t.result.answer}</p>
                  <p className="text-xs text-muted-foreground">
                    Source: {t.result.provider === "mock" ? "built-in rules" : t.result.provider === "rules" ? "built-in rules" : t.result.provider}
                    {t.result.fallback_used ? " (AI output failed validation)" : ""}
                  </p>
                  {t.result.facts && (
                    <details className="text-xs">
                      <summary className="cursor-pointer text-muted-foreground">Facts used</summary>
                      <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-muted p-3">{JSON.stringify(t.result.facts, null, 2)}</pre>
                    </details>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
