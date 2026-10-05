import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CollectionsTable } from "@/components/collections-table";
import { receivable } from "./fixtures";

vi.mock("next/link", () => ({ default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a> }));

describe("CollectionsTable", () => {
  it("shows amounts in rupees, priority and the reason", () => {
    render(<CollectionsTable rows={[receivable()]} onRemind={() => {}} />);
    expect(screen.getByRole("link", { name: "ABC Electricals" })).toHaveAttribute("href", "/customers/c1");
    expect(screen.getAllByText("₹82,400").length).toBeGreaterThan(0);
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText(/9 days later than their historical average/)).toBeInTheDocument();
  });

  it("offers a reminder only for overdue customers and passes the row back", async () => {
    const onRemind = vi.fn();
    const overdue = receivable();
    const current = receivable({ customer_id: "c2", company_name: "Metro Hardware", days_overdue: 0, overdue_amount: 0, priority: "Low" });
    render(<CollectionsTable rows={[overdue, current]} onRemind={onRemind} />);
    const buttons = screen.getAllByRole("button", { name: "Generate reminder" });
    expect(buttons).toHaveLength(1);
    await userEvent.click(buttons[0]);
    expect(onRemind).toHaveBeenCalledWith(overdue);
  });
});
