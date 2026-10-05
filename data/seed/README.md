# Sample files

Demo database content is generated deterministically by `python -m app.seed` (see `backend/app/seed.py`).
The files here are inputs for trying the import features against the seeded database:

| File | Use | Expected preview |
|------|-----|------------------|
| `sample_invoice.json` | Invoices → Import JSON / CSV / PDF | 1 draft, ₹9,600 + ₹1,368 GST = ₹10,968 |
| `sample_invoices.csv` | Invoices → Import, or Settings → Import data → Invoices | 2 valid invoices (3 rows), 2 rejected invoices with row errors |
| `sample_customers.csv` | Settings → Import data → Customers | 4 rows: 2 valid, 2 errors (bad email, duplicate company) |
| `sample_products.csv` | Settings → Import data → Products | 3 rows: 2 valid, 1 error (duplicate SKU) |
