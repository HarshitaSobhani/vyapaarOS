import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "@/app/(app)/dashboard/page";
import { api } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { dashboard } from "./fixtures";

vi.mock("@/lib/api/endpoints", () => ({ api: { dashboard: vi.fn() } }));
vi.mock("next/link", () => ({ default: ({ href, children, ...p }: { href: string; children: React.ReactNode }) => <a href={href} {...p}>{children}</a> }));
vi.mock("@/components/sales-chart", () => ({ SalesChart: () => <div data-testid="chart" /> }));

describe("Dashboard", () => {
  beforeEach(() => vi.resetAllMocks());

  it("renders KPIs and linked AI operations from the API", async () => {
    vi.mocked(api.dashboard).mockResolvedValue(dashboard);
    render(<DashboardPage />);
    expect(await screen.findByText("₹1.24L")).toBeInTheDocument();
    expect(screen.getByText("84%")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /7 customers need collection follow-up/i });
    expect(link).toHaveAttribute("href", "/collections?priority=High");
    expect(screen.getByTestId("chart")).toBeInTheDocument();
  });

  it("shows a loading state, then a retryable error", async () => {
    vi.mocked(api.dashboard).mockRejectedValue(new ApiError("boom", 500));
    render(<DashboardPage />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load the dashboard.");
    vi.mocked(api.dashboard).mockResolvedValue(dashboard);
    screen.getByRole("button", { name: "Retry" }).click();
    await waitFor(() => expect(screen.getByText("₹1.24L")).toBeInTheDocument());
  });
});
