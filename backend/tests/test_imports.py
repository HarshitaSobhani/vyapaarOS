from sqlalchemy import select

from app.models import Customer, Invoice, InvoiceStatus
from app.services.importing.csv_source import CSVAccountingSource
from app.services.importing.service import ImportService
from tests.conftest import TODAY

CUSTOMERS = (b"name,company_name,phone,email,credit_limit,payment_terms_days\n"
             b"Ramesh Jain,Jain Test Traders,9820000001,ramesh@jain.in,100000,30\n"
             b"Bad Email,Broken Co,9820000002,not-an-email,1000,30\n"
             b"Dup One,ABC Electricals,9820000003,,1000,30\n"
             b"Neg Credit,Negative Co,9820000004,,-5,30\n")

INVOICES = (b"invoice_number,customer,invoice_date,due_date,sku,quantity,unit_price\n"
            b"CSV-1,ABC Electricals,2026-10-01,2026-10-31,LED-B12,10,120\n"
            b"CSV-1,ABC Electricals,2026-10-01,2026-10-31,MCB-S16,5,\n"
            b"CSV-2,ABC Electricals,2026-10-01,,NOPE-SKU,3,10\n"
            b"CSV-2,ABC Electricals,2026-10-01,,LED-B12,2,10\n"
            b"CSV-3,Ghost Customer,2026-10-01,,LED-B12,2,10\n")


def svc(db, **files):
    return ImportService(db, CSVAccountingSource(**files), TODAY)


def test_customer_preview_reports_every_bad_row(db):
    p = svc(db, customers=CUSTOMERS).preview("customers")
    assert (p.total_rows, p.valid_rows, p.error_rows) == (4, 1, 3)
    assert {e.row for e in p.errors} == {3, 4, 5}
    assert any("Duplicate customer" in m for e in p.errors for m in e.errors)
    assert db.scalar(select(Customer).where(Customer.company_name == "Jain Test Traders")) is None  # preview writes nothing


def test_commit_imports_only_valid_rows(db):
    r = svc(db, customers=CUSTOMERS).commit("customers")
    assert r.imported == 1 and r.error_rows == 3
    assert db.scalar(select(Customer).where(Customer.company_name == "Jain Test Traders")) is not None


def test_invoice_with_any_bad_row_is_rejected_whole(db):
    p = svc(db, invoices=INVOICES).preview("invoices")
    assert p.total_rows == 5 and p.valid_rows == 2
    rows_with_errors = {e.row for e in p.errors}
    assert rows_with_errors == {4, 5, 6}   # both CSV-2 rows (one skipped) and CSV-3


def test_invoice_import_creates_drafts_only(db):
    r = svc(db, invoices=INVOICES).commit("invoices")
    assert r.imported == 1
    inv = db.scalar(select(Invoice).where(Invoice.invoice_number == "CSV-1"))
    assert inv.status is InvoiceStatus.draft and len(inv.items) == 2 and inv.source.value == "csv"


def test_missing_columns_are_a_file_level_error(db):
    import pytest

    from app.core.errors import AppError
    with pytest.raises(AppError):
        svc(db, customers=b"name\nfoo\n").preview("customers")


def test_payments_validated_against_outstanding(db):
    inv = db.scalar(select(Invoice).where(Invoice.status == InvoiceStatus.approved))
    csv = (b"invoice_number,amount,payment_date,payment_method,reference\n"
           + f"{inv.invoice_number},1,2026-10-05,upi,R1\n".encode()
           + f"{inv.invoice_number},999999999,2026-10-05,upi,R2\n".encode()
           + b"NOPE-1,10,2026-10-05,upi,R3\n"
           + f"{inv.invoice_number},10,not-a-date,upi,R4\n".encode())
    p = svc(db, payments=csv).preview("payments")
    assert (p.total_rows, p.valid_rows, p.error_rows) == (4, 1, 3)
