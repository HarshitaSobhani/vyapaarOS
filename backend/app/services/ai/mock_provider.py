"""Deterministic provider: renders fixed templates from facts. Used without an API key and as the fallback."""
from app.services.ai.provider import AIProvider, Facts


def _bullets(items: list[str]) -> str:
    return "\n".join(f"• {i}" for i in items)


class MockAIProvider(AIProvider):
    name = "mock"

    def answer(self, question: str, facts: Facts) -> str:
        intent = facts.get("intent")
        render = getattr(self, f"_a_{intent}", self._a_overview)
        return render(facts)

    # ----- assistant intents -----
    def _a_priorities(self, f: Facts) -> str:
        rows = f["customers"]
        if not rows:
            return "No customers need collection follow-up right now."
        lines = [f"{c['company']}: {c['outstanding_display']} outstanding, {c['days_overdue']} days overdue "
                 f"({c['priority']} priority)" for c in rows]
        return (f"{f['follow_up_count']} customers need follow-up. Start with:\n{_bullets(lines)}\n"
                f"Total overdue: {f['total_overdue_display']}.")

    def _a_customer(self, f: Facts) -> str:
        c = f["customer"]
        if c["outstanding"] <= 0:
            return f"{c['company']} has nothing outstanding."
        head = f"{c['company']} is {c['priority']} priority ({c['outstanding_display']} outstanding"
        head += f", oldest invoice {c['days_overdue']} days overdue)." if c["days_overdue"] else ", none overdue)."
        action = (f"Suggested next step: send a reminder for invoice {c['oldest_overdue_invoice']}."
                  if c["oldest_overdue_invoice"] else "Suggested next step: monitor until the due date.")
        return f"{head}\nWhy:\n{_bullets(c['reasons'])}\n{action}"

    def _a_worst_payers(self, f: Facts) -> str:
        rows = f["customers"]
        if not rows:
            return "There is not enough payment history to rank customers yet."
        lines = []
        for c in rows:
            delay = (f"averages {c['average_payment_delay']} days past due" if c["average_payment_delay"] is not None
                     else "has no settled invoices yet")
            lines.append(f"{c['company']}: {c['late_payment_count']} late payments, {delay}")
        return f"Weakest payment behaviour:\n{_bullets(lines)}"

    def _a_overdue_causes(self, f: Facts) -> str:
        top = f["top_overdue"]
        lines = [f"{f['total_overdue_display']} is overdue across {f['overdue_customer_count']} customers."]
        if top:
            lines.append(f"Concentration: {top[0]['company']} alone owes {top[0]['overdue_display']} "
                         f"({f['top_share_pct']}% of overdue).")
        old = f["over_30_days_display"]
        lines.append(f"{old} is more than 30 days past due.")
        lines.append(f"{f['habitual_late_count']} overdue customers have 3 or more late payments on record.")
        return "Main drivers:\n" + _bullets(lines)

    def _a_inventory(self, f: Facts) -> str:
        rows = f["products"]
        head = (f"{f['stockout_risk_count']} products may stock out within 10 days; "
                f"{f['critical_count']} are critical and {f['low_count']} are low.")
        if not rows:
            return head
        lines = [f"{p['name']}: {p['available']} in stock, {p['coverage_days']} days of cover, "
                 f"order {p['recommended_order']} {p['unit']} from {p['supplier']}" for p in rows]
        return f"{head}\nMost urgent:\n{_bullets(lines)}"

    def _a_overview(self, f: Facts) -> str:
        return _bullets([
            f"{f['follow_up_count']} customers need collection follow-up ({f['total_overdue_display']} overdue)",
            f"{f['stockout_risk_count']} products may stock out within 10 days",
            f"{f['purchase_order_count']} purchase orders should be considered",
            f"{f['draft_invoice_count']} invoices require review",
        ])

    # ----- explanations -----
    def explain_priority(self, facts: Facts) -> str:
        return self._a_customer({"customer": facts})

    # ----- reminders -----
    def write_reminder(self, facts: Facts, variant: int = 0) -> str:
        name, inv, amt = facts["customer_name"], facts["invoice_number"], facts["amount_display"]
        due, days = facts["due_date"], facts["days_overdue"]
        templates = (
            f"Hi {name},\n\nJust a reminder regarding invoice {inv} for {amt}, which was due on {due} "
            f"and is now {days} days overdue.\n\nPlease let us know if you need any clarification "
            f"regarding the invoice or payment.\n\nThank you.",
            f"Hello {name},\n\nHope you are doing well. Our records show invoice {inv} for {amt} "
            f"(due {due}) is still open, {days} days past the due date.\n\nCould you share the "
            f"expected payment date? Happy to help if anything is unclear.\n\nThank you.",
            f"Dear {name},\n\nA gentle follow-up on invoice {inv} of {amt}, due on {due}. "
            f"It is currently {days} days overdue.\n\nKindly arrange the payment at your earliest "
            f"convenience, or reply if you have any questions.\n\nThanks and regards.",
        )
        return templates[variant % len(templates)]
