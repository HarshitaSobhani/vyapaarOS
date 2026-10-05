"""Roles are enforced by the API itself, not by the UI."""
import pytest
from sqlalchemy import select

from app.models import Invoice, InvoiceStatus

PASSWORD = "test-password-123"
CUSTOMER_CSV = b"name,company_name\nTest Person,Authz Test Traders\n"


def headers(client, email):
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def open_invoice(db):
    return db.scalar(select(Invoice).where(Invoice.status == InvoiceStatus.approved))


@pytest.fixture
def draft(db):
    return db.scalar(select(Invoice).where(Invoice.status == InvoiceStatus.draft))


def test_sales_role_is_read_and_draft_only(client, open_invoice, draft):
    sales = headers(client, "sales@vyapaaros.in")
    pay = {"invoice_id": str(open_invoice.id), "amount": 1, "payment_date": "2026-10-05"}
    assert client.post("/api/payments", headers=sales, json=pay).status_code == 403
    assert client.post(f"/api/customers/{open_invoice.customer_id}/payments", headers=sales,
                       json={"amount": 1, "payment_date": "2026-10-05"}).status_code == 403
    assert client.post(f"/api/invoices/{draft.id}/approve", headers=sales).status_code == 403
    assert client.post(f"/api/invoices/{draft.id}/reject", headers=sales, json={}).status_code == 403
    assert client.post("/api/imports/customers/commit", headers=sales,
                       files={"file": ("c.csv", CUSTOMER_CSV, "text/csv")}).status_code == 403
    # but sales can read and preview
    assert client.get("/api/dashboard", headers=sales).status_code == 200
    assert client.post("/api/imports/customers/preview", headers=sales,
                       files={"file": ("c.csv", CUSTOMER_CSV, "text/csv")}).status_code == 200


def test_manager_can_approve_and_commit(client, draft):
    manager = headers(client, "manager@vyapaaros.in")
    assert client.post("/api/imports/customers/commit", headers=manager,
                       files={"file": ("c.csv", CUSTOMER_CSV, "text/csv")}).json()["imported"] == 1
    assert client.post(f"/api/invoices/{draft.id}/approve", headers=manager).status_code == 200


def test_every_data_route_rejects_anonymous_and_forged_tokens(client):
    for method, path in (("get", "/api/dashboard"), ("get", "/api/collections"), ("get", "/api/inventory"),
                         ("get", "/api/customers"), ("get", "/api/invoices"), ("post", "/api/ai/ask"),
                         ("post", "/api/payments"), ("post", "/api/imports/customers/commit")):
        assert getattr(client, method)(path).status_code == 401, path
    forged = {"Authorization": "Bearer " + "x" * 40}
    assert client.get("/api/dashboard", headers=forged).status_code == 401
