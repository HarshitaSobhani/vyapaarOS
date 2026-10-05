import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { InventoryTable } from "@/components/inventory-table";
import { risk } from "./fixtures";

const rows = [
  risk(),
  risk({ product_id: "p2", name: "Havells Switch", sku: "SW", status: "Healthy", available_quantity: 900, stock_coverage_days: 45, average_daily_sales: 20, recommended_order_quantity: 0 }),
  risk({ product_id: "p3", name: "Crompton Fan", sku: "FN", status: "Low", available_quantity: 12, stock_coverage_days: 12, average_daily_sales: 1, recommended_order_quantity: 30 }),
];
const names = () => screen.getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0].textContent ?? "");

describe("InventoryTable", () => {
  it("shows stock, coverage, status and recommended order", () => {
    render(<InventoryTable rows={rows} />);
    expect(screen.getByText("LED Bulb 12W")).toBeInTheDocument();
    expect(screen.getByText("6.0 days")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("200 pcs")).toBeInTheDocument();
  });

  it("sorts by coverage ascending then descending", async () => {
    render(<InventoryTable rows={rows} />);
    await userEvent.click(screen.getByRole("button", { name: /Coverage/ }));
    expect(names().map((n) => n.split("LED-B12")[0].slice(0, 3))).toEqual(["LED", "Cro", "Hav"]);
    await userEvent.click(screen.getByRole("button", { name: /Coverage/ }));
    expect(names()[0]).toMatch(/^Havells/);
  });
});
