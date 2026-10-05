"use client";

import { useState } from "react";
import { Check, Copy, MessageCircle, Pencil, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useAsync } from "@/hooks/use-async";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import { inr, shortDate } from "@/lib/format";

interface Props {
  customerId: string | null;
  invoiceId?: string | null;
  onOpenChange: (open: boolean) => void;
}

export function ReminderDialog({ customerId, invoiceId, onOpenChange }: Props) {
  return (
    <Dialog open={customerId !== null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {customerId && <ReminderBody key={`${customerId}:${invoiceId ?? ""}`} customerId={customerId} invoiceId={invoiceId} />}
      </DialogContent>
    </Dialog>
  );
}

function ReminderBody({ customerId, invoiceId }: { customerId: string; invoiceId?: string | null }) {
  const [variant, setVariant] = useState(0);
  const draft = useAsync(() => api.collectionMessage(customerId, invoiceId ?? undefined, variant), [customerId, invoiceId, variant]);
  const [edited, setEdited] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const meta = draft.data;
  const loading = draft.loading;
  const message = edited ?? meta?.message ?? "";
  const error = actionError ?? draft.error;
  const setError = setActionError;

  function regenerate() {
    setVariant((v) => v + 1);
    setEdited(null);
    setEditing(false);
    setError(null);
    setNotice(null);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copy failed. Select the text and copy it manually.");
    }
  }

  async function openWhatsApp() {
    if (!meta) return;
    setError(null);
    try {
      const res = await api.approveReminder(customerId, meta.invoice_id, message);
      if (res.url) window.open(res.url, "_blank", "noopener,noreferrer");
      setNotice("Approval recorded. Review and press Send inside WhatsApp; VyapaarOS does not send messages itself.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Unable to prepare the message.");
    }
  }

  return (
    <>
        <DialogHeader>
          <DialogTitle>WhatsApp reminder{meta ? ` · ${meta.customer_name}` : ""}</DialogTitle>
          <DialogDescription>
            {meta
              ? `Invoice ${meta.invoice_number} · ${inr(meta.amount)} · due ${shortDate(meta.due_date)} · ${meta.days_overdue} days overdue`
              : "Drafting a reminder from the invoice facts…"}
          </DialogDescription>
        </DialogHeader>
        {loading ? (
          <div role="status" className="h-40 animate-pulse rounded-md bg-muted" aria-label="Generating reminder" />
        ) : (
          <Textarea
            aria-label="Reminder message"
            value={message}
            readOnly={!editing}
            onChange={(e) => setEdited(e.target.value)}
            rows={9}
            className="font-sans"
          />
        )}
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        {notice && <p className="text-sm text-emerald-700">{notice}</p>}
        {meta && (
          <p className="text-xs text-muted-foreground">
            Drafted by {meta.provider === "mock" ? "the built-in template engine" : meta.provider}
            {meta.fallback_used ? " (AI output was rejected by validation)" : ""}. Nothing is sent until you approve.
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={loading} onClick={regenerate}>
            <RefreshCw /> Regenerate
          </Button>
          <Button variant="outline" size="sm" onClick={() => setEditing((e) => !e)}>
            <Pencil /> {editing ? "Done editing" : "Edit"}
          </Button>
          <Button variant="outline" size="sm" onClick={copy} disabled={!message}>
            {copied ? <Check /> : <Copy />} {copied ? "Copied" : "Copy message"}
          </Button>
          <Button size="sm" className="ml-auto" onClick={openWhatsApp} disabled={!message || !meta}>
            <MessageCircle /> Approve &amp; open WhatsApp
          </Button>
        </div>
    </>
  );
}
