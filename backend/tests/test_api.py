import json

from sqlalchemy import select

from app.core.config import Settings
from app.models import Invoice, InvoiceStatus


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/db").json() == {"status": "ok"}


def test_database_url_is_adapted_for_psycopg():
    for raw in ("postgres://u:p@h:5432/d", "postgresql://u:p@h:5432/d"):
        assert Settings(database_url=raw, _env_file=None).database_url == "postgresql+psycopg://u:p@h:5432/d"


def test_cors_origins_from_env():
    s = Settings(cors_origins="http://localhost:3000, https://my-app.vercel.app/", _env_file=None)
    assert s.cors_origin_list == ["http://localhost:3000", "https://my-app.vercel.app"]


def test_cors_preflight_allows_configured_origin_only(client):
    ok = client.options("/api/dashboard", headers={"Origin": "http://localhost:3000",
                                                   "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options("/api/dashboard", headers={"Origin": "https://evil.example",
                                                    "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_auth_required_and_login_errors(client):
    r = client.get("/api/dashboard")
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"
    bad = client.post("/api/auth/login", json={"email": "demo@vyapaaros.in", "password": "wrong"})
    assert bad.status_code == 401 and "password" not in bad.text.lower().replace("incorrect email or password", "")


def test_dashboard_is_derived_from_data(client, auth):
    d = client.get("/api/dashboard", headers=auth).json()
    assert d["outstanding"] > d["overdue"] > 0
    assert len(d["sales_30d"]) == 30
    ops = {o["key"]: o for o in d["operations"]}
    assert ops["invoice_review"]["count"] == 3
    assert ops["collections"]["count"] == len(client.get("/api/collections/priorities", headers=auth).json()) - sum(
        1 for r in client.get("/api/collections/priorities", headers=auth).json() if r["priority"] == "Low")


def test_collections_filters(client, auth):
    high = client.get("/api/collections/priorities?priority=High", headers=auth).json()
    assert high and all(r["priority"] == "High" for r in high)
    abc = client.get("/api/collections?q=ABC Electricals", headers=auth).json()
    assert [r["company_name"] for r in abc["priorities"]] == ["ABC Electricals"]
    assert len(abc["aging"]) == 5
    bad = client.get("/api/collections?priority=Urgent", headers=auth)
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "validation_error"


def test_inventory_risks_sorted_and_computed(client, auth):
    inv = client.get("/api/inventory", headers=auth).json()
    assert inv["total_products"] == 41 and inv["critical"] + inv["low_stock"] + inv["healthy"] == 41
    risks = client.get("/api/inventory/risks?status=Critical", headers=auth).json()
    assert risks and all(r["status"] == "Critical" and r["recommended_order_quantity"] > 0 for r in risks)
    by_name = client.get("/api/inventory/risks?sort=name", headers=auth).json()
    assert [r["name"].lower() for r in by_name] == sorted(r["name"].lower() for r in by_name)


def test_assistant_answers_with_grounded_facts(client, auth):
    r = client.post("/api/ai/ask", headers=auth, json={"question": "Why is ABC Electricals high priority?"}).json()
    assert r["intent"] == "customer" and r["provider"] == "mock"
    assert r["facts"]["customer"]["company"] == "ABC Electricals"
    assert r["facts"]["customer"]["outstanding_display"] in r["answer"]
    off = client.post("/api/ai/ask", headers=auth, json={"question": "Write me a poem about cats"}).json()
    assert off["intent"] == "none" and off["facts"] is None


def test_reminder_generation_and_explicit_approval(client, auth):
    cust = client.get("/api/customers?q=ABC Electricals", headers=auth).json()[0]
    msg = client.post("/api/ai/collection-message", headers=auth, json={"customer_id": cust["id"]}).json()
    assert msg["invoice_number"] in msg["message"] and msg["days_overdue"] > 0
    other = client.post("/api/ai/collection-message", headers=auth, json={"customer_id": cust["id"], "variant": 1}).json()
    assert other["message"] != msg["message"]
    send = {"customer_id": cust["id"], "message": msg["message"], "approved": False}
    assert client.post("/api/ai/collection-message/send", headers=auth, json=send).status_code == 422
    ok = client.post("/api/ai/collection-message/send", headers=auth, json={**send, "approved": True}).json()
    assert ok["url"].startswith("https://wa.me/91")


def test_document_import_review_and_approve(client, auth):
    doc = {"invoice_number": "DOC-1001", "customer": "ABC Electricals", "invoice_date": "2026-10-04",
           "items": [{"sku": "LED-B12", "quantity": 50, "unit_price": 120}, {"sku": "MCB-S16", "quantity": 20, "unit_price": 180}]}
    res = client.post("/api/invoices/import", headers=auth,
                      files={"file": ("inv.json", json.dumps(doc), "application/json")})
    assert res.status_code == 201 and res.json()["created"] == 1
    inv_id = res.json()["results"][0]["invoice_id"]
    detail = client.get(f"/api/invoices/{inv_id}", headers=auth).json()
    assert detail["status"] == "draft" and detail["source"] == "document"
    assert (detail["subtotal"], detail["tax"], detail["total"]) == (9600, 1368, 10968)
    before = client.get("/api/dashboard", headers=auth).json()["outstanding"]
    approved = client.post(f"/api/invoices/{inv_id}/approve", headers=auth).json()
    assert approved["status"] == "approved"
    assert client.get("/api/dashboard", headers=auth).json()["outstanding"] == round(before + 10968, 2)


def test_import_rejects_bad_files(client, auth):
    bad = client.post("/api/invoices/import", headers=auth, files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 415
    unknown = client.post("/api/invoices/import", headers=auth, files={"file": ("a.json", json.dumps(
        {"customer": "Nobody", "invoice_date": "2026-10-04", "items": [{"sku": "ZZZ", "quantity": 1}]}), "application/json")})
    body = unknown.json()
    assert body["failed"] == 1 and any("Unknown customer" in e for e in body["results"][0]["errors"])


def test_sales_role_cannot_approve(client, db):
    token = client.post("/api/auth/login", json={"email": "sales@vyapaaros.in", "password": "test-password-123"}).json()["access_token"]
    draft = db.scalar(select(Invoice).where(Invoice.status == InvoiceStatus.draft))
    r = client.post(f"/api/invoices/{draft.id}/approve", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_errors_do_not_leak_internals(client, auth):
    r = client.get("/api/invoices/not-a-uuid", headers=auth)
    assert r.status_code == 422 and "Traceback" not in r.text


def test_production_config_is_strict():
    import pytest

    base = {"environment": "production", "secret_key": "x" * 32, "_env_file": None}
    good = Settings(database_url="postgres://u:p@db.railway.internal:5432/r", cors_origins="https://a.vercel.app", **base)
    good.validate_for_runtime()
    for bad in (
        dict(database_url="postgres://u:p@localhost:5432/r", cors_origins="https://a.vercel.app"),
        dict(database_url="postgres://u:p@h:5432/r", cors_origins=""),
        dict(database_url="postgres://u:p@h:5432/r", cors_origins="*"),
    ):
        with pytest.raises(RuntimeError):
            Settings(**bad, **base).validate_for_runtime()
