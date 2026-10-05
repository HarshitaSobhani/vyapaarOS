# Tally integration (architecture only)

**Status: not implemented.** VyapaarOS has no live Tally connection today. This page describes where one would plug in.

## The boundary

All external accounting data enters through `AccountingSource`
(`backend/app/services/importing/source.py`):

```python
class AccountingSource(ABC):
    def get_customers(self) -> list[SourceRow]: ...
    def get_products(self)  -> list[SourceRow]: ...
    def get_invoices(self)  -> list[SourceRow]: ...
    def get_payments(self)  -> list[SourceRow]: ...
```

A `SourceRow` is `(row, data: dict[str, str])` using the VyapaarOS import column names
(`name`, `company_name`, `sku`, `invoice_number`, `amount`, …). The implemented adapter is
`CSVAccountingSource` (`csv_source.py`).

`ImportService` (`importing/service.py`) owns everything after that: Pydantic validation, duplicate
detection, per-row error reporting, preview vs commit, and persistence. Imported invoices become
**drafts** and need human approval like any other invoice. A new source therefore never touches
business rules.

## What a `TallyAccountingSource` would do

1. **Fetch**: Tally Prime exposes an XML-over-HTTP interface (default port 9000). The adapter would send
   a "Collection" export request for Ledgers (sundry debtors), Stock Items, Sales Vouchers and Receipt
   Vouchers, for a date range.
2. **Map** to flat dicts:
   - Ledger (Sundry Debtors) → `name`, `company_name`, `phone`, `email`, `credit_limit`
   - Stock Item → `sku` (alias or part number), `name`, `category` (stock group), `unit`, rates, GST
   - Sales Voucher → one row per inventory entry: `invoice_number` (voucher number), `customer` (party ledger), `invoice_date`, `sku`, `quantity`, `unit_price`
   - Receipt Voucher → `invoice_number` (bill reference), `amount`, `payment_date`, `payment_method`
3. **Return** rows; `ImportService.preview/commit` do the rest.

## Open questions before building it

- Tally runs on the customer's desktop, so the API (hosted on Railway) cannot reach it directly. A small
  local agent that pushes exports to the API, or a scheduled file export (the CSV path that exists
  today), is more realistic than the API calling Tally.
- Idempotent re-sync: match on voucher number + date rather than only "invoice number exists".
- Voucher edits and cancellations in Tally need a reconciliation strategy.
- Receipt vouchers allocated "on account" rather than against a bill need FIFO allocation. The
  customer-level allocator in `services/invoices.py::allocate_customer_payment` is a starting point.
