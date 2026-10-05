from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Customer
from app.repositories.receivables import list_customers, load_invoice_facts
from app.services.receivables import (
    CollectionSummary,
    CustomerReceivable,
    InvoiceFacts,
    aging_buckets,
    collection_summary,
    compute_customer_receivable,
    rank_priorities,
)


@dataclass
class ReceivablesSnapshot:
    today: date
    customers: list[CustomerReceivable]       # all customers, unsorted
    invoices: list[InvoiceFacts]
    summary: CollectionSummary
    aging: list[dict[str, object]]

    @property
    def priorities(self) -> list[CustomerReceivable]:
        return rank_priorities(self.customers)

    @property
    def follow_ups(self) -> list[CustomerReceivable]:
        return [r for r in self.priorities if r.priority.value in ("High", "Medium")]


def build_snapshot(db: Session, today: date) -> ReceivablesSnapshot:
    facts = load_invoice_facts(db)
    customers = list_customers(db)
    rows = [
        compute_customer_receivable(c.id, c.name, c.company_name, c.phone, c.credit_limit,
                                    facts.get(c.id, []), today)
        for c in customers
    ]
    all_invoices = [i for invs in facts.values() for i in invs]
    return ReceivablesSnapshot(today, rows, all_invoices, collection_summary(all_invoices, today),
                               aging_buckets(all_invoices, today))


def customer_receivable(db: Session, customer_id: UUID, today: date) -> tuple[Customer, CustomerReceivable]:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer")
    facts = load_invoice_facts(db, customer_id).get(customer_id, [])
    return customer, compute_customer_receivable(
        customer.id, customer.name, customer.company_name, customer.phone, customer.credit_limit,
        facts, today)
