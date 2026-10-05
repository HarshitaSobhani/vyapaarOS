# Product notes

## Who it is for
Owner-run distributors and retailers (the demo data is an electrical distributor) who invoice on credit,
chase payments by phone/WhatsApp, and reorder stock from memory.

## Problems it targets (and nothing more)
1. **Invoice intake**: invoices arrive as files or are typed in. VyapaarOS extracts structured data and
   puts a human approval step in front of the ledger.
2. **Stock-outs**: which products will run out before the next order arrives, and how much to order.
3. **Receivables**: who to chase first, why, and a polite message to send.

It is deliberately not an ERP, not a Tally replacement, and does not do GST filing, e-invoicing or
multi-warehouse stock.

## Business rules (all deterministic, in `backend/app/services`)

| Concept | Definition |
|---------|-----------|
| Business invoice | status `approved`, `partially_paid` or `paid`. Drafts and rejected invoices never count. |
| Outstanding | invoice total − payments |
| Overdue | outstanding on invoices with due date before today. The `overdue` status is derived, never stored. |
| Days overdue (customer) | age past due date of the oldest unpaid overdue invoice |
| Average days to pay | mean days from invoice date to final payment over settled invoices |
| Late payments | settled invoices paid after due date + currently overdue invoices |
| Priority score (0–100) | amount (30) + days overdue (35) + behaviour (20) + customer value (15). High ≥ 60, Medium ≥ 35. A customer with nothing overdue is always Low. |
| Collection rate | paid share of invoices that fell due in the last 90 days |
| Average daily sales | units invoiced in the last 30 days ÷ 30 |
| Coverage | available stock ÷ average daily sales |
| Stock status | Critical: coverage ≤ 7 days or zero stock. Low: coverage ≤ 14 days or at/below reorder level. Else Healthy. |
| Recommended order | enough to reach 30 days of cover, at least the reorder quantity, rounded up to whole reorder packs. 0 when Healthy. |
| Purchase order suggestion | products needing an order, grouped by supplier |

Thresholds are constants at the top of `receivables.py` and `inventory.py`.

## AI operations card logic
Every number on the dashboard's AI Operations card comes from the same functions as the detail pages
and links to the filtered list behind it (collections, stock-risk, purchase suggestions, draft invoices).
