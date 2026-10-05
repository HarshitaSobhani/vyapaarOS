import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { InvoiceReview } from "@/components/invoice-review";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import { draftInvoice } from "./fixtures";

vi.mock("@/lib/api/endpoints", () => ({
  api: { invoice: vi.fn(), customers: vi.fn(), products: vi.fn(), approveInvoice: vi.fn(), rejectInvoice: vi.fn(), updateInvoice: vi.fn() },
}));

describe("Invoice approval flow", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.customers).mockResolvedValue([]);
    vi.mocked(api.products).mockResolvedValue([]);
  });

  it("shows extracted draft with totals and approves it", async () => {
    vi.mocked(api.invoice).mockResolvedValueOnce(draftInvoice()).mockResolvedValue(draftInvoice("approved"));
    vi.mocked(api.approveInvoice).mockResolvedValue(draftInvoice("approved"));
    const onChanged = vi.fn();
    render(<InvoiceReview invoiceId="inv1" onClose={() => {}} onChanged={onChanged} />);
    expect(await screen.findByText("Invoice DOC-1001")).toBeInTheDocument();
    expect(screen.getByText(/Nothing enters your business data until you approve/)).toBeInTheDocument();
    expect(screen.getByText("₹10,968")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve Invoice" }));
    await waitFor(() => expect(api.approveInvoice).toHaveBeenCalledWith("inv1"));
    expect(onChanged).toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Approve Invoice" })).not.toBeInTheDocument());
  });

  it("rejects with a reason", async () => {
    vi.mocked(api.invoice).mockResolvedValue(draftInvoice());
    vi.mocked(api.rejectInvoice).mockResolvedValue(draftInvoice("rejected"));
    render(<InvoiceReview invoiceId="inv1" onClose={() => {}} onChanged={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "Reject" }));
    await userEvent.type(screen.getByLabelText("Rejection reason"), "Wrong customer");
    await userEvent.click(screen.getByRole("button", { name: "Confirm reject" }));
    await waitFor(() => expect(api.rejectInvoice).toHaveBeenCalledWith("inv1", "Wrong customer"));
  });

  it("shows the server's message when approval is not permitted", async () => {
    vi.mocked(api.invoice).mockResolvedValue(draftInvoice());
    vi.mocked(api.approveInvoice).mockRejectedValue(new ApiError("You do not have permission to do this", 403));
    render(<InvoiceReview invoiceId="inv1" onClose={() => {}} onChanged={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "Approve Invoice" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("do not have permission");
  });
});
