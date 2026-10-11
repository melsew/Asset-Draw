import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";
import { useAuth } from "../hooks/useAuth";
import i18n from "../i18n";
import {
  adminApproveCampaign,
  adminApproveVendor,
  adminFetchAllCampaigns,
  adminFetchAllVendors,
  adminFetchDraws,
  adminStartCampaignReview,
} from "../services/api";
import type { AuthUser } from "../types/auth";
import { AdminDashboardPage } from "./AdminDashboardPage";

vi.mock("../hooks/useAuth", () => ({ useAuth: vi.fn() }));
vi.mock("../services/api", () => ({
  adminApproveCampaign: vi.fn(),
  adminApproveVendor: vi.fn(),
  adminFetchAllCampaigns: vi.fn(),
  adminFetchAllVendors: vi.fn(),
  adminFetchDraws: vi.fn(),
  adminScheduleCampaign: vi.fn(),
  adminStartCampaignReview: vi.fn(),
  adminVerifyCampaignAssets: vi.fn(),
}));

const campaignRows = [
  {
    id: "campaign-draft",
    title: "Draft campaign",
    vendor: "North Vendor",
    prize: "Laptop",
    status: "DRAFT",
    entry_mode: "PROMOTIONAL" as const,
    max_entries: 200,
    draw_at: null,
  },
  {
    id: "campaign-review",
    title: "Review campaign",
    vendor: "East Vendor",
    prize: "Phone",
    status: "SUBMITTED",
    entry_mode: "FREE" as const,
    max_entries: 100,
    draw_at: null,
  },
];

const vendorRows = [
  {
    id: "vendor-pending",
    legal_name: "Example Trading PLC",
    display_name: "Example Trading",
    status: "PENDING",
    contact_email: "contact@example.test",
  },
];

function setCurrentUser(role: AuthUser["role"] = "ADMIN") {
  vi.mocked(useAuth).mockReturnValue({
    user: {
      id: "staff-id",
      phone: null,
      email: "admin@example.test",
      role,
      status: "active",
    },
    loading: false,
    refresh: vi.fn(),
    signOut: vi.fn(),
    isLoggedIn: true,
  });
}

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  vi.clearAllMocks();
  setCurrentUser();
  vi.mocked(adminFetchAllCampaigns).mockResolvedValue(campaignRows);
  vi.mocked(adminFetchAllVendors).mockResolvedValue(vendorRows);
  vi.mocked(adminFetchDraws).mockResolvedValue([]);
  vi.mocked(adminStartCampaignReview).mockResolvedValue(campaignRows[1]);
  vi.mocked(adminApproveCampaign).mockResolvedValue(campaignRows[1]);
  vi.mocked(adminApproveVendor).mockResolvedValue(vendorRows[0]);
});

describe("AdminDashboardPage", () => {
  it("shows campaign data and offers only the valid next review action", async () => {
    renderDashboard();

    const draftRow = await screen.findByRole("row", { name: /draft campaign/i });
    const submittedRow = await screen.findByRole("row", { name: /review campaign/i });
    expect(within(draftRow).queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(within(draftRow).queryByRole("button", { name: "Start review" })).not.toBeInTheDocument();
    expect(within(submittedRow).getByRole("button", { name: "Start review" })).toBeInTheDocument();

    fireEvent.click(within(submittedRow).getByRole("button", { name: "Start review" }));
    await waitFor(() => expect(vi.mocked(adminStartCampaignReview).mock.calls[0]?.[0]).toBe("campaign-review"));
  });

  it("shows completed draw evidence through public verification only", async () => {
    vi.mocked(adminFetchDraws).mockResolvedValue([
      {
        id: "draw-complete",
        campaign_id: "campaign-review",
        campaign_title: "Verified campaign",
        status: "COMPLETED",
        pool_locked_at: "2026-10-01T10:00:00Z",
        executed_at: "2026-10-01T11:00:00Z",
        planned_entropy_source: "drand:test",
        planned_entropy_round: 42,
      },
    ]);
    renderDashboard();

    fireEvent.click(screen.getByRole("button", { name: "Draw operations" }));
    expect(await screen.findByText("Verified campaign")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Verify" })).toHaveAttribute("href", "/verify/draw-complete");
    expect(screen.getByText("drand:test #42")).toBeInTheDocument();
  });

  it("allows vendor approval from the vendor list", async () => {
    renderDashboard();
    fireEvent.click(screen.getByRole("button", { name: "Vendors" }));

    const vendorRow = await screen.findByRole("row", { name: /example trading/i });
    fireEvent.click(within(vendorRow).getByRole("button", { name: "Approve vendor" }));
    await waitFor(() => expect(vi.mocked(adminApproveVendor).mock.calls[0]?.[0]).toBe("vendor-pending"));
  });

  it("does not expose vendor or draw tabs to campaign managers", async () => {
    setCurrentUser("CAMPAIGN_MANAGER");
    renderDashboard();

    expect(await screen.findByRole("button", { name: "Campaigns" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Vendors" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Draw operations" })).not.toBeInTheDocument();
    expect(adminFetchAllVendors).not.toHaveBeenCalled();
    expect(adminFetchDraws).not.toHaveBeenCalled();
  });

  it("surfaces API failures and provides a retry", async () => {
    vi.mocked(adminFetchAllCampaigns).mockRejectedValueOnce(new Error("API unavailable"));
    renderDashboard();

    expect(await screen.findByRole("alert")).toHaveTextContent("Campaigns could not be loaded.");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(adminFetchAllCampaigns).toHaveBeenCalledTimes(2));
  });
});
