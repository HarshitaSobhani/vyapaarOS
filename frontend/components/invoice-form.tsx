"use client";

import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { z } from "zod";
import { NativeSelect } from "@/components/native-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import type { Customer, InvoiceInput, Product } from "@/types/api";

const schema = z.object({
  customer_id: z.string().min(1, "Select a customer"),
  invoice_number: z.string().max(40).optional(),
  invoice_date: z.string().min(1, "Select a date"),
  items: z.array(z.object({
    product_id: z.string().min(1, "Select a product"),
    quantity: z.number({ error: "Enter a quantity" }).int("Whole numbers only").positive("Must be at least 1"),
  })).min(1, "Add at least one item"),
});
export type InvoiceFormValues = z.infer<typeof schema>;

interface Props {
  customers: Customer[];
  products: Product[];
  initial?: InvoiceFormValues;
  submitLabel: string;
  onSubmit: (input: InvoiceInput) => Promise<void>;
  onCancel?: () => void;
}

export function InvoiceForm({ customers, products, initial, submitLabel, onSubmit, onCancel }: Props) {
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, control, handleSubmit, formState: { errors, isSubmitting } } = useForm<InvoiceFormValues>({
    resolver: zodResolver(schema),
    defaultValues: initial ?? {
      customer_id: "", invoice_number: "", invoice_date: new Date().toISOString().slice(0, 10),
      items: [{ product_id: "", quantity: 1 }],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "items" });

  async function submit(v: InvoiceFormValues) {
    setServerError(null);
    try {
      await onSubmit({
        customer_id: v.customer_id, invoice_number: v.invoice_number || null, invoice_date: v.invoice_date,
        items: v.items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
      });
    } catch (e) {
      setServerError(e instanceof ApiError ? e.message : "Unable to save the invoice. Please try again.");
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="customer_id">Customer</Label>
          <NativeSelect id="customer_id" className="w-full" {...register("customer_id")}>
            <option value="">Select…</option>
            {customers.map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
          </NativeSelect>
          {errors.customer_id && <p className="text-xs text-red-600">{errors.customer_id.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="invoice_number">Invoice no. (optional)</Label>
          <Input id="invoice_number" placeholder="Auto-generated" {...register("invoice_number")} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="invoice_date">Invoice date</Label>
          <Input id="invoice_date" type="date" {...register("invoice_date")} />
          {errors.invoice_date && <p className="text-xs text-red-600">{errors.invoice_date.message}</p>}
        </div>
      </div>
      <div className="space-y-2">
        <Label>Items</Label>
        {fields.map((f, idx) => (
          <div key={f.id} className="flex items-start gap-2">
            <div className="flex-1">
              <NativeSelect aria-label={`Product ${idx + 1}`} className="w-full" {...register(`items.${idx}.product_id`)}>
                <option value="">Select product…</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name} (₹{p.selling_price})</option>)}
              </NativeSelect>
              {errors.items?.[idx]?.product_id && <p className="text-xs text-red-600">{errors.items[idx]?.product_id?.message}</p>}
            </div>
            <div className="w-24">
              <Input aria-label={`Quantity ${idx + 1}`} type="number" min={1} {...register(`items.${idx}.quantity`, { valueAsNumber: true })} />
              {errors.items?.[idx]?.quantity && <p className="text-xs text-red-600">{errors.items[idx]?.quantity?.message}</p>}
            </div>
            <Button type="button" variant="ghost" size="icon" aria-label={`Remove item ${idx + 1}`} onClick={() => remove(idx)} disabled={fields.length === 1}><Trash2 /></Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" onClick={() => append({ product_id: "", quantity: 1 })}><Plus /> Add item</Button>
        <p className="text-xs text-muted-foreground">Prices, GST and totals are calculated by the server from the product catalogue.</p>
      </div>
      {serverError && <p role="alert" className="text-sm text-red-600">{serverError}</p>}
      <div className="flex gap-2">
        <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : submitLabel}</Button>
        {onCancel && <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  );
}
