"""Deterministic demo data for an Indian electrical distributor.

Usage: python -m app.seed [--reset]
Dates are relative to today so the demo always looks current; the random stream is fixed.
Refuses to run on a non-empty database unless --reset is passed (never use --reset in production).
"""
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    Customer,
    Inventory,
    Invoice,
    InvoiceItem,
    InvoiceSource,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    Product,
    ReminderLog,
    User,
    UserRole,
)
from app.services.invoices import line_amounts

# sku, name, category, unit, buy, sell, gst, reorder_level, reorder_qty, supplier, qty_range, popularity, stock_cover_days
PRODUCTS = [
    ("LED-B12", "LED Bulb 12W", "Lighting", "pcs", 62, 120, 12, 100, 200, "Philips Lighting India", (20, 120), 10, 6),
    ("LED-B09", "LED Bulb 9W", "Lighting", "pcs", 48, 95, 12, 100, 200, "Philips Lighting India", (20, 100), 8, 20),
    ("LED-T20", "LED Tube Light 20W", "Lighting", "pcs", 140, 260, 12, 40, 100, "Syska LED Distributors", (10, 60), 5, 11),
    ("LED-P15", "LED Panel Light 15W", "Lighting", "pcs", 210, 380, 12, 30, 60, "Syska LED Distributors", (5, 40), 4, 25),
    ("LED-F50", "LED Flood Light 50W", "Lighting", "pcs", 520, 890, 18, 10, 20, "Syska LED Distributors", (2, 15), 2, 28),
    ("WIR-F15", "Finolex 1.5mm Wire 90m", "Wires & Cables", "coil", 1180, 1480, 18, 25, 50, "Finolex Cables Ltd", (5, 40), 9, 5),
    ("WIR-F25", "Finolex 2.5mm Wire 90m", "Wires & Cables", "coil", 1890, 2350, 18, 20, 40, "Finolex Cables Ltd", (4, 30), 8, 16),
    ("WIR-F40", "Finolex 4mm Wire 90m", "Wires & Cables", "coil", 2980, 3650, 18, 10, 20, "Finolex Cables Ltd", (2, 15), 4, 24),
    ("CAB-P25", "Polycab 2.5mm Cable 90m", "Wires & Cables", "coil", 1950, 2420, 18, 20, 40, "Polycab India", (4, 30), 7, 9),
    ("CAB-P40", "Polycab 4mm Cable 90m", "Wires & Cables", "coil", 3050, 3780, 18, 10, 20, "Polycab India", (2, 12), 4, 26),
    ("CAB-PC3", "Polycab 3-Core Flexible Cable 100m", "Wires & Cables", "coil", 4200, 5150, 18, 8, 16, "Polycab India", (1, 8), 3, 30),
    ("SWI-H6A", "Havells Modular Switch 6A", "Switches & Sockets", "pcs", 42, 78, 18, 150, 300, "Havells India", (20, 150), 9, 15),
    ("SWI-H16", "Havells Modular Switch 16A", "Switches & Sockets", "pcs", 68, 125, 18, 80, 200, "Havells India", (10, 80), 6, 23),
    ("SWI-HBL", "Havells Bell Push Switch", "Switches & Sockets", "pcs", 55, 98, 18, 40, 100, "Havells India", (5, 40), 3, 27),
    ("SOC-AR5", "Anchor Roma Socket 5A", "Switches & Sockets", "pcs", 38, 72, 18, 100, 250, "Anchor by Panasonic", (15, 100), 7, 8),
    ("SOC-AR6", "Anchor Roma 6A 3-Pin Socket", "Switches & Sockets", "pcs", 46, 85, 18, 100, 200, "Anchor by Panasonic", (15, 90), 5, 18),
    ("PLT-AR2", "Anchor Roma Plate 2 Module", "Switches & Sockets", "pcs", 24, 48, 18, 80, 200, "Anchor by Panasonic", (10, 80), 4, 29),
    ("MCB-S16", "MCB 16A Single Pole", "Protection", "pcs", 105, 180, 18, 60, 120, "Schneider Electric India", (10, 60), 8, 7),
    ("MCB-S32", "MCB 32A Double Pole", "Protection", "pcs", 340, 560, 18, 30, 60, "Schneider Electric India", (4, 30), 5, 19),
    ("MCB-SDB", "MCB Distribution Box 8-Way", "Protection", "pcs", 620, 980, 18, 12, 24, "Schneider Electric India", (2, 12), 3, 21),
    ("RCC-40A", "RCCB 40A 30mA", "Protection", "pcs", 980, 1560, 18, 10, 20, "Schneider Electric India", (1, 10), 3, 22),
    ("FAN-C12", "Crompton Ceiling Fan 1200mm", "Fans", "pcs", 1450, 1980, 18, 15, 30, "Crompton Greaves Consumer", (1, 8), 6, 4),
    ("FAN-C14", "Crompton High Speed Fan 1400mm", "Fans", "pcs", 1680, 2290, 18, 10, 20, "Crompton Greaves Consumer", (1, 6), 4, 17),
    ("FAN-EX", "Havells Exhaust Fan 150mm", "Fans", "pcs", 720, 1050, 18, 12, 24, "Havells India", (1, 8), 3, 26),
    ("FAN-TB", "Crompton Table Fan 400mm", "Fans", "pcs", 1250, 1720, 18, 8, 16, "Crompton Greaves Consumer", (1, 5), 2, 31),
    ("CON-PVC", "Precision PVC Conduit Pipe 25mm 3m", "Conduits", "pcs", 38, 64, 18, 200, 400, "Precision Pipes", (30, 200), 6, 12),
    ("CON-BND", "PVC Conduit Bend 25mm", "Conduits", "pcs", 6, 12, 18, 300, 600, "Precision Pipes", (50, 300), 3, 33),
    ("CON-JBX", "PVC Junction Box 4x4", "Conduits", "pcs", 14, 28, 18, 200, 400, "Precision Pipes", (20, 150), 4, 24),
    ("TAP-INS", "Insulation Tape Black", "Accessories", "pcs", 9, 18, 18, 200, 500, "Steelgrip Tapes", (30, 200), 5, 13),
    ("TAP-TFL", "Teflon Tape 10m", "Accessories", "pcs", 7, 15, 18, 100, 300, "Steelgrip Tapes", (20, 150), 2, 35),
    ("HLD-B22", "Bulb Holder B22 Batten", "Accessories", "pcs", 11, 24, 18, 200, 400, "Anchor by Panasonic", (20, 150), 4, 20),
    ("MTR-DIG", "Digital Multimeter DT830", "Tools", "pcs", 310, 520, 18, 8, 16, "Motwane Instruments", (1, 6), 1, 30),
    ("TST-NEO", "Neon Line Tester", "Tools", "pcs", 14, 30, 18, 60, 150, "Motwane Instruments", (5, 50), 2, 34),
    ("WRS-PLR", "Wire Stripper Pliers", "Tools", "pcs", 95, 170, 18, 20, 40, "Taparia Tools", (2, 15), 2, 28),
    ("EXT-4S", "Extension Board 4 Socket 3m", "Accessories", "pcs", 190, 340, 18, 25, 50, "Anchor by Panasonic", (3, 25), 4, 14),
    ("STB-V6", "Voltage Stabilizer 6A", "Appliances", "pcs", 640, 980, 18, 6, 12, "V-Guard Industries", (1, 6), 2, 25),
    ("INV-ES", "Inverter Battery 150Ah", "Appliances", "pcs", 9800, 12800, 28, 4, 8, "Exide Industries", (1, 3), 1, 30),
    ("GEY-V15", "Havells Storage Geyser 15L", "Appliances", "pcs", 5400, 7350, 18, 5, 10, "Havells India", (1, 3), 1, 32),
    ("DBL-WP", "Waterproof Outdoor Junction Box", "Conduits", "pcs", 48, 92, 18, 60, 120, "Precision Pipes", (5, 40), 2, 29),
    ("BTN-DOR", "Anchor Door Bell Ding-Dong", "Switches & Sockets", "pcs", 130, 235, 18, 20, 40, "Anchor by Panasonic", (2, 15), 2, 27),
    ("LED-ST5", "LED Strip Light 5m", "Lighting", "pcs", 260, 450, 12, 15, 30, "Syska LED Distributors", (2, 12), 2, 22),
]

# contact, company, phone, credit_limit, terms, avg_delay_days (past due), invoices_in_180d, spend_scale
CUSTOMERS = [
    ("Rajesh Agarwal", "ABC Electricals", "9820011001", 400000, 30, 12, 11, 2.2),
    ("Mahesh Kumar", "Kumar Electrical & Hardware", "9811022002", 250000, 30, 6, 10, 1.4),
    ("Jignesh Patel", "Patel Traders", "9825033003", 300000, 30, 3, 9, 1.6),
    ("Ganesh Shetty", "Shree Ganesh Electricals", "9833044004", 250000, 30, 15, 9, 1.5),
    ("Sunil Mehra", "Metro Hardware", "9810055005", 350000, 45, 9, 8, 1.8),
    ("Sai Prasad Rao", "Sai Enterprises", "9848066006", 150000, 30, 20, 8, 1.0),
    ("Vikram Singh", "Singh Electric Works", "9815077007", 200000, 30, 2, 8, 1.2),
    ("Anil Gupta", "Gupta Electricals & Co", "9899088008", 180000, 30, 8, 7, 1.1),
    ("Deepak Joshi", "Joshi Electronics", "9422099009", 120000, 30, 1, 7, 0.9),
    ("Imran Sheikh", "Sheikh Electricals", "9004100010", 200000, 30, 25, 7, 1.0),
    ("Naresh Reddy", "Reddy Power Solutions", "9866111011", 300000, 45, 5, 7, 1.7),
    ("Pradeep Nair", "Nair Electrical Stores", "9847122012", 100000, 30, 4, 6, 0.8),
    ("Harpreet Bedi", "Bedi Hardware Mart", "9876133013", 160000, 30, 10, 6, 1.0),
    ("Suresh Iyer", "Iyer Lighting House", "9840144014", 140000, 30, 0, 6, 0.9),
    ("Mohan Das", "Das Brothers Electricals", "9830155015", 220000, 30, 14, 6, 1.1),
    ("Ravi Tiwari", "Tiwari Electric Traders", "9415166016", 90000, 30, 18, 5, 0.7),
    ("Kiran Desai", "Desai Wire House", "9825177017", 260000, 30, 3, 6, 1.3),
    ("Amit Bansal", "Bansal Electricals", "9811188018", 130000, 30, 7, 5, 0.9),
    ("Yusuf Khan", "Khan Electrical Agencies", "9893199019", 110000, 30, 22, 5, 0.8),
    ("Sandeep Pawar", "Pawar Switchgear", "9822200020", 280000, 45, 2, 6, 1.5),
    ("Lakshmi Narayan", "Lakshmi Electricals", "9444211021", 120000, 30, 6, 5, 0.8),
    ("Manoj Chauhan", "Chauhan Lighting Centre", "9837222022", 100000, 30, 11, 5, 0.7),
    ("Faisal Ansari", "Ansari Electric Hub", "9936233023", 150000, 30, 16, 5, 0.9),
    ("Gopal Verma", "Verma Power & Lighting", "9926244024", 170000, 30, 4, 5, 1.0),
    ("Tarun Malhotra", "Malhotra Electricals", "9818255025", 200000, 30, 5, 5, 1.1),
]

HORIZON_DAYS = 180
METHODS = [PaymentMethod.upi, PaymentMethod.bank_transfer, PaymentMethod.bank_transfer,
           PaymentMethod.cheque, PaymentMethod.cash]


def seed(db: Session, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    rng = random.Random(20260401)
    settings = get_settings()

    owner_pw = settings.demo_user_password
    if not owner_pw:
        raise SystemExit("Set DEMO_USER_PASSWORD before seeding (see .env.example).")
    pw_hash = hash_password(owner_pw)
    for name, email, role in (
        ("Demo Owner", settings.demo_user_email, UserRole.owner),
        ("Priya Manager", "manager@vyapaaros.in", UserRole.manager),
        ("Arjun Sales", "sales@vyapaaros.in", UserRole.sales),
    ):
        db.add(User(name=name, email=email, password_hash=pw_hash, role=role))

    products: list[Product] = []
    meta: dict[str, tuple[tuple[int, int], int, int]] = {}
    for sku, name, cat, unit, buy, sell, gst, rl, rq, sup, qr, pop, cover in PRODUCTS:
        p = Product(sku=sku, name=name, category=cat, unit=unit, purchase_price=Decimal(buy),
                    selling_price=Decimal(sell), gst_rate=Decimal(gst), reorder_level=rl,
                    reorder_quantity=rq, supplier_name=sup, description=f"{name} ({cat})")
        db.add(p)
        products.append(p)
        meta[sku] = (qr, pop, cover)
    customers: list[Customer] = []
    for contact, company, phone, limit, terms, _d, _n, _s in CUSTOMERS:
        c = Customer(name=contact, company_name=company, phone=phone, credit_limit=Decimal(limit),
                     payment_terms_days=terms,
                     email=f"accounts@{''.join(ch for ch in company.lower() if ch.isalnum())}.in")
        db.add(c)
        customers.append(c)
    db.flush()

    weights = [meta[p.sku][1] for p in products]
    n_invoice = 0
    n_items = 0
    n_payments = 0
    units_30d: dict[str, int] = {p.sku: 0 for p in products}

    def make_invoice(cust: Customer, inv_date: date, status: InvoiceStatus, source: InvoiceSource,
                     scale: float) -> Invoice:
        nonlocal n_invoice, n_items
        n_invoice += 1
        inv = Invoice(invoice_number=f"INV-{inv_date:%y%m}-{n_invoice:04d}", customer_id=cust.id,
                      invoice_date=inv_date, due_date=inv_date + timedelta(days=cust.payment_terms_days),
                      subtotal=Decimal(0), tax=Decimal(0), total=Decimal(0), status=status, source=source)
        chosen: list[Product] = []
        while len(chosen) < rng.randint(2, 5):
            p = rng.choices(products, weights)[0]
            if p not in chosen:
                chosen.append(p)
        sub = tax = Decimal(0)
        for line_no, p in enumerate(chosen, start=1):
            lo, hi = meta[p.sku][0]
            qty = max(1, round(rng.randint(lo, hi) * scale * rng.uniform(0.6, 1.0)))
            net, t, tot = line_amounts(qty, p.selling_price, p.gst_rate)
            inv.items.append(InvoiceItem(product_id=p.id, line_no=line_no, quantity=qty,
                                         unit_price=p.selling_price, tax=t, total=tot))
            sub += net
            tax += t
            n_items += 1
            if status is not InvoiceStatus.draft and (today - inv_date).days < 30:
                units_30d[p.sku] += qty
        inv.subtotal, inv.tax, inv.total = sub, tax, sub + tax
        db.add(inv)
        return inv

    for cust, (_c, _co, _ph, _l, terms, delay_mean, count, scale) in zip(customers, CUSTOMERS, strict=True):
        days_list = sorted(rng.sample(range(2, HORIZON_DAYS), count), reverse=True)
        # Slow payers carry a few genuinely stale unpaid invoices (stress scenario for collections).
        forced_open = 3 if cust.company_name == "ABC Electricals" else (2 if delay_mean >= 11 else 0)
        for age in days_list:
            inv_date = today - timedelta(days=age)
            inv = make_invoice(cust, inv_date, InvoiceStatus.approved, InvoiceSource.manual, scale)
            inv.approved_at = None
            if forced_open and terms + 8 <= age <= 80:
                forced_open -= 1
                continue
            pay_after = terms + round(rng.gauss(delay_mean, 3 if delay_mean < 20 else 5))
            pay_date = inv_date + timedelta(days=max(pay_after, 5))
            if pay_date > today:
                # still open: sometimes partially paid
                if rng.random() < 0.25 and (today - inv_date).days > 10:
                    part = (inv.total * Decimal(rng.choice([30, 40, 50, 60]) / 100)).quantize(Decimal("0.01"))
                    db.add(Payment(invoice=inv, amount=part, payment_date=min(today, inv_date + timedelta(days=rng.randint(8, 20))),
                                   payment_method=rng.choice(METHODS), reference=f"UTR{rng.randint(10**9, 10**10 - 1)}"))
                    inv.status = InvoiceStatus.partially_paid
                    n_payments += 1
                continue
            # settled, sometimes in two instalments
            if rng.random() < 0.15 and inv.total > 5000:
                first = (inv.total * Decimal("0.5")).quantize(Decimal("0.01"))
                early = inv_date + timedelta(days=max(3, pay_after - rng.randint(5, 12)))
                db.add(Payment(invoice=inv, amount=first, payment_date=min(early, pay_date), payment_method=rng.choice(METHODS),
                               reference=f"UTR{rng.randint(10**9, 10**10 - 1)}"))
                db.add(Payment(invoice=inv, amount=inv.total - first, payment_date=pay_date, payment_method=rng.choice(METHODS),
                               reference=f"UTR{rng.randint(10**9, 10**10 - 1)}"))
                n_payments += 2
            else:
                db.add(Payment(invoice=inv, amount=inv.total, payment_date=pay_date, payment_method=rng.choice(METHODS),
                               reference=f"UTR{rng.randint(10**9, 10**10 - 1)}"))
                n_payments += 1
            inv.status = InvoiceStatus.paid

    # Recent sales so "today" and the 30-day chart are populated.
    for cust in rng.sample(customers, 4):
        make_invoice(cust, today, InvoiceStatus.approved, InvoiceSource.manual, 0.8)
    for back in range(1, 30):
        make_invoice(rng.choice(customers), today - timedelta(days=back), InvoiceStatus.approved,
                     InvoiceSource.manual, 0.7)
    # Drafts awaiting review (do not affect any metrics or stock).
    for cust, src, back in ((customers[0], InvoiceSource.csv, 0), (customers[4], InvoiceSource.document, 1),
                            (customers[10], InvoiceSource.document, 2)):
        make_invoice(cust, today - timedelta(days=back), InvoiceStatus.draft, src, 0.6)
    db.flush()

    # Stock levels chosen from each product's recent velocity and a target cover.
    for p in products:
        sold = units_30d[p.sku]
        velocity = sold / 30
        cover = meta[p.sku][2]
        qty = max(int(round(velocity * cover)), 0) if velocity > 0 else p.reorder_level * 3
        if cover > 14:
            qty = max(qty, p.reorder_level * 2)  # comfortably above reorder level
        db.add(Inventory(product_id=p.id, current_quantity=qty, reserved_quantity=0))
    db.commit()
    return {"users": 3, "products": len(products), "customers": len(customers), "invoices": n_invoice,
            "invoice_items": n_items, "payments": n_payments}


def main() -> None:
    reset = "--reset" in sys.argv
    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(User)) or 0
        if existing and not reset:
            print("Database already has data; nothing seeded. Use --reset to wipe demo data (development only).")
            return
        if reset:
            if get_settings().environment == "production":
                raise SystemExit("Refusing --reset in production.")
            for model in (ReminderLog, Payment, InvoiceItem, Invoice, Inventory, Product, Customer, User):
                db.execute(delete(model))
            db.commit()
        print("Seeded:", seed(db))


if __name__ == "__main__":
    main()
