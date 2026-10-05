from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.errors import AppError, ConflictError
from app.models import Customer, Inventory, InvoiceSource, InvoiceStatus, Product, User
from app.schemas.invoices import InvoiceIn, InvoiceItemIn, PaymentIn
from app.services import invoices as svc
from app.services.receivables_service import customer_receivable
from tests.conftest import TODAY


@pytest.fixture
def customer(db):
    c = Customer(name="Test Owner", company_name="Zeta Test Electricals", credit_limit=Decimal(100000),
                 payment_terms_days=30)
    db.add(c)
    db.commit()
    return c


@pytest.fixture
def product(db):
    p = Product(sku="TST-001", name="Test Switch", category="Test", unit="pcs", purchase_price=Decimal(50),
                selling_price=Decimal(100), gst_rate=Decimal(18), reorder_level=5, reorder_quantity=10,
                supplier_name="Test Supplier")
    db.add(p)
    db.flush()
    db.add(Inventory(product_id=p.id, current_quantity=100))
    db.commit()
    return p


def draft(db, customer, product, qty=10, days_ago=40):
    return svc.create_draft(db, InvoiceIn(
        customer_id=customer.id, invoice_date=TODAY - timedelta(days=days_ago),
        items=[InvoiceItemIn(product_id=product.id, quantity=qty)]), InvoiceSource.manual)


def test_totals_are_computed_server_side(db, customer, product):
    inv = draft(db, customer, product, qty=10)
    assert (inv.subtotal, inv.tax, inv.total) == (Decimal("1000.00"), Decimal("180.00"), Decimal("1180.00"))
    assert inv.status is InvoiceStatus.draft
    assert inv.due_date == inv.invoice_date + timedelta(days=30)


def test_draft_is_excluded_from_business_data_until_approved(db, customer, product):
    inv = draft(db, customer, product)
    _, r = customer_receivable(db, customer.id, TODAY)
    assert r.outstanding_amount == 0
    user = db.scalar(select(User))
    svc.approve_invoice(db, inv.id, user)
    _, r = customer_receivable(db, customer.id, TODAY)
    assert r.outstanding_amount == Decimal("1180.00") and r.days_overdue == 10


def test_approval_deducts_stock_once_and_is_not_repeatable(db, customer, product):
    inv = draft(db, customer, product, qty=30)
    user = db.scalar(select(User))
    svc.approve_invoice(db, inv.id, user)
    assert db.scalar(select(Inventory.current_quantity).where(Inventory.product_id == product.id)) == 70
    with pytest.raises(ConflictError):
        svc.approve_invoice(db, inv.id, user)


def test_rejected_invoice_never_enters_dataset(db, customer, product):
    inv = draft(db, customer, product)
    svc.reject_invoice(db, inv.id, "Wrong customer")
    with pytest.raises(ConflictError):
        svc.approve_invoice(db, inv.id, db.scalar(select(User)))
    assert db.scalar(select(Inventory.current_quantity).where(Inventory.product_id == product.id)) == 100


def test_only_drafts_are_editable(db, customer, product):
    inv = draft(db, customer, product)
    edited = svc.update_draft(db, inv.id, InvoiceIn(
        customer_id=customer.id, invoice_date=inv.invoice_date, items=[InvoiceItemIn(product_id=product.id, quantity=5)]))
    assert edited.total == Decimal("590.00")
    svc.approve_invoice(db, inv.id, db.scalar(select(User)))
    with pytest.raises(ConflictError):
        svc.update_draft(db, inv.id, InvoiceIn(customer_id=customer.id, invoice_date=inv.invoice_date,
                                               items=[InvoiceItemIn(product_id=product.id, quantity=1)]))


def test_payment_updates_status_and_rejects_overpayment(db, customer, product):
    inv = draft(db, customer, product)
    svc.approve_invoice(db, inv.id, db.scalar(select(User)))
    svc.record_payment(db, inv.id, PaymentIn(amount=Decimal(500), payment_date=TODAY))
    assert svc.get_invoice(db, inv.id).status is InvoiceStatus.partially_paid
    with pytest.raises(AppError):
        svc.record_payment(db, inv.id, PaymentIn(amount=Decimal(1000), payment_date=TODAY))
    svc.record_payment(db, inv.id, PaymentIn(amount=Decimal(680), payment_date=TODAY))
    assert svc.get_invoice(db, inv.id).status is InvoiceStatus.paid


def test_customer_payment_is_allocated_oldest_first(db, customer, product):
    user = db.scalar(select(User))
    old = draft(db, customer, product, qty=10, days_ago=60)     # 1180
    new = draft(db, customer, product, qty=10, days_ago=20)     # 1180
    for i in (old, new):
        svc.approve_invoice(db, i.id, user)
    parts = svc.allocate_customer_payment(db, customer.id, PaymentIn(amount=Decimal(1500), payment_date=TODAY))
    assert [p.amount for p in parts] == [Decimal("1180.00"), Decimal("320.00")]
    assert svc.get_invoice(db, old.id).status is InvoiceStatus.paid
    assert svc.get_invoice(db, new.id).status is InvoiceStatus.partially_paid
    with pytest.raises(AppError):
        svc.allocate_customer_payment(db, customer.id, PaymentIn(amount=Decimal(5000), payment_date=TODAY))


def test_overdue_is_derived_not_stored(db, customer, product):
    inv = draft(db, customer, product, days_ago=60)
    svc.approve_invoice(db, inv.id, db.scalar(select(User)))
    out = svc.to_out(svc.get_invoice(db, inv.id), TODAY)
    assert out.status is InvoiceStatus.overdue and out.days_overdue == 30
