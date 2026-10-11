import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, vi } from "vitest";
import { Countdown } from "../components/Countdown";
import { LanguageToggle } from "../components/LanguageToggle";
import { fetchReady } from "../services/api";
import i18n from "../i18n";
import { LandingPage } from "./LandingPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("LandingPage", () => {
  it("switches between Amharic and English and persists the selected language", async () => {
    await i18n.changeLanguage("am");
    render(<LanguageToggle />);

    fireEvent.click(screen.getByRole("button", { name: "Switch to English" }));
    await waitFor(() => expect(document.documentElement).toHaveAttribute("lang", "en"));
    expect(localStorage.getItem("asset-draw.lang")).toBe("en");
    expect(screen.getByRole("button", { name: "Switch to Amharic" })).toBeInTheDocument();
  });

  it("returns healthy readiness data from the API", async () => {
    const body = { status: "ok", checks: { database: "ok", redis: "ok" } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 200, json: async () => body }));

    await expect(fetchReady()).resolves.toEqual(body);
  });

  it("returns degraded readiness data when a dependency is unavailable", async () => {
    const body = { status: "degraded", checks: { database: "ok", redis: "unavailable" } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 503, json: async () => body }));

    await expect(fetchReady()).resolves.toEqual(body);
  });

  it("shows all requested prize categories and the draw process", async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ status: 200, json: async () => ({ status: "ok", checks: {} }) }),
    );
    renderPage();

    const categories = screen.getByRole("region", { name: "Prize categories" });
    for (const category of [
      "Car",
      "Smartphone",
      "Laptop",
      "Tablet",
      "TV",
      "Refrigerator",
      "Washing Machine",
      "Travel",
      "Other",
    ]) {
      expect(within(categories).getByText(category)).toBeInTheDocument();
    }
    const howItWorks = screen.getByRole("region", { name: "How a draw works" });
    expect(within(howItWorks).getByRole("heading", { name: "Verify the result" })).toBeInTheDocument();
    expect(within(howItWorks).getByRole("link", { name: /Verify a completed draw/ })).toHaveAttribute("href", "/verify");
    expect(screen.getByRole("link", { name: "Browse Campaigns" })).toHaveAttribute("href", "/campaigns");
  });

  it("shows countdown units for a published draw date and a pending state otherwise", async () => {
    await i18n.changeLanguage("en");
    const scheduled = render(
      <Countdown drawAt={new Date(Date.now() + 5 * 86400_000).toISOString()} status="ACTIVE" />,
    );
    const countdown = scheduled.container.querySelector(".ad-countdown");
    expect(countdown).not.toBeNull();
    expect(within(countdown as HTMLElement).getByText("Days")).toBeInTheDocument();
    expect(within(countdown as HTMLElement).getByText("Hrs")).toBeInTheDocument();
    expect(within(countdown as HTMLElement).getByText("Min")).toBeInTheDocument();
    expect(within(countdown as HTMLElement).getByText("Sec")).toBeInTheDocument();
    scheduled.unmount();

    render(<Countdown status="ACTIVE" />);
    expect(screen.getByText("Draw date not set")).toBeInTheDocument();
  });

  it("renders campaign cards from the backend", async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/health/ready")) {
          return Promise.resolve({ status: 200, json: async () => ({ status: "ok", checks: {} }) });
        }

        if (url.endsWith("/campaigns") || url.includes("/campaigns?")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [
              {
                id: "AD-2026-001",
                title: "Asset-Draw Grand Prize",
                vendor: "Partner Vendor",
                prize: "New Laptop",
                description: "Transparent promotional campaign",
                entry_mode: "PROMOTIONAL",
                entries: 128,
                max_entries: 500,
                status: "ACTIVE",
                ends_at: "2026-10-30T18:00:00Z",
                prize_image_url: "/uploads/vendor/new-laptop.webp",
              },
            ],
          });
        }

        return Promise.reject(new Error(`Unexpected fetch: ${url}`));
      }),
    );

    renderPage();
    const campaignSection = screen.getByRole("region", { name: "Active campaigns" });

    await waitFor(() => expect(within(campaignSection).getByText("Asset-Draw Grand Prize")).toBeInTheDocument());
    expect(within(campaignSection).getByText("New Laptop")).toBeInTheDocument();
    expect(within(campaignSection).getByText("128 / 500 entries")).toBeInTheDocument();
    expect(within(campaignSection).getByRole("img", { name: "New Laptop" })).toHaveAttribute(
      "src",
      "/uploads/vendor/new-laptop.webp",
    );
    expect(within(campaignSection).getByRole("button", { name: "Participate" })).toBeInTheDocument();
    expect(within(campaignSection).getByRole("link", { name: "Details →" })).toHaveAttribute(
      "href",
      "/campaigns/AD-2026-001",
    );
  });
});
