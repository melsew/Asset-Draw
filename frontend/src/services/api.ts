import type { Campaign, Entry, DrawVerification, Vendor, Asset } from "../types/campaign";
import type { ReadyResponse } from "../types/health";
import type { AuthTokens, AuthUser } from "../types/auth";

const BASE = "/api/v1";

export interface AdminCampaign {
  id: string;
  title: string;
  vendor: string;
  prize: string;
  status: string;
  entry_mode: Campaign["entry_mode"];
  max_entries: number;
  draw_at: string | null;
}

export interface AdminDraw {
  id: string;
  campaign_id: string;
  campaign_title: string;
  status: string;
  pool_locked_at: string | null;
  executed_at: string | null;
  planned_entropy_source: string | null;
  planned_entropy_round: number | null;
}

const DEMO_CAMPAIGNS: Campaign[] = [
  {
    id: "b4f90d73-4f37-4a6b-9af3-60d1fce0a111",
    title: "Toyota Corolla Weekend Drive",
    vendor: "Addis Auto Hub",
    prize: "Toyota Corolla 2024",
    description: "A premium urban drive campaign for lucky participants across Ethiopia. The winner receives a fully serviced Corolla with registration support and a free first-year service package.",
    entry_mode: "FREE",
    entries: 128,
    max_entries: 500,
    status: "ACTIVE",
    ends_at: new Date(Date.now() + 14 * 86400000).toISOString(),
    draw_at: new Date(Date.now() + 21 * 86400000).toISOString(),
    prize_image_url: "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=900&q=80",
    entry_price: null,
    prize_value: 1200000,
    city: "Addis Ababa",
    prize_category: "car",
  },
  {
    id: "2ec5a67c-1eb3-4cdc-b9d2-84c0dcdb114d",
    title: "Smartphone Elite Bundle",
    vendor: "City Telecom",
    prize: "iPhone 15 Pro Max",
    description: "Enter to win a flagship smartphone package with accessories, warranty coverage and a monthly data bundle for the first six months.",
    entry_mode: "PROMOTIONAL",
    entries: 241,
    max_entries: 800,
    status: "ACTIVE",
    ends_at: new Date(Date.now() + 18 * 86400000).toISOString(),
    draw_at: new Date(Date.now() + 25 * 86400000).toISOString(),
    prize_image_url: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
    entry_price: null,
    prize_value: 89000,
    city: "Dire Dawa",
    prize_category: "smartphone",
  },
  {
    id: "6c2e8549-31d0-42b5-8ff2-cd4f38be9ae6",
    title: "Home Upgrade Giveaway",
    vendor: "Moonlight Home Mart",
    prize: "Samsung Refrigerator + Washing Machine",
    description: "A household bundle campaign for families preparing for a fresh new season. Includes installation support and a one-year appliance care plan.",
    entry_mode: "FREE",
    entries: 64,
    max_entries: 220,
    status: "SCHEDULED",
    ends_at: new Date(Date.now() + 31 * 86400000).toISOString(),
    draw_at: new Date(Date.now() + 42 * 86400000).toISOString(),
    prize_image_url: "https://images.unsplash.com/photo-1585518419759-7fe2e0fbf8a6?auto=format&fit=crop&w=900&q=80",
    entry_price: null,
    prize_value: 76000,
    city: "Bahir Dar",
    prize_category: "refrigerator",
  },
];

const DEMO_USER: AuthUser = {
  id: "17b6788a-f89d-4c7d-a7b0-f5101f7cc4ab",
  phone: "+251911223344",
  display_name: "Demo participant",
  email: "demo@assetdraw.dev",
  role: "PARTICIPANT",
  status: "active",
};

const DEMO_ENTRY: Entry = {
  id: "demo-entry-1",
  entry_number: "A-1042",
  campaign_id: DEMO_CAMPAIGNS[0].id,
  campaign_title: DEMO_CAMPAIGNS[0].title,
  campaign_prize: DEMO_CAMPAIGNS[0].prize,
  status: "ACTIVE",
  created_at: new Date().toISOString(),
  draw_at: DEMO_CAMPAIGNS[0].draw_at ?? null,
  campaign_status: DEMO_CAMPAIGNS[0].status,
  prize_image_url: DEMO_CAMPAIGNS[0].prize_image_url ?? null,
};

function demoResponseFor(path: string, init?: RequestInit): unknown {
  const method = (init?.method ?? "GET").toUpperCase();
  const normalizedPath = path.replace(/\?.*$/, "");

  if (normalizedPath === "/health/ready") {
    return { status: "ok", checks: { database: "demo", redis: "demo" } };
  }

  if (normalizedPath === "/campaigns") {
    const q = new URLSearchParams(path.split("?")[1] ?? "");
    const status = q.get("status") ?? "";
    const search = (q.get("search") ?? "").toLowerCase();
    const category = (q.get("category") ?? "").toLowerCase();
    return DEMO_CAMPAIGNS.filter((campaign) => {
      if (status && campaign.status !== status) return false;
      if (category && (campaign.prize_category ?? "").toLowerCase() !== category) return false;
      if (search) {
        const haystack = `${campaign.title} ${campaign.description} ${campaign.prize}`.toLowerCase();
        return haystack.includes(search);
      }
      return true;
    });
  }

  if (normalizedPath.startsWith("/campaigns/")) {
    const id = normalizedPath.split("/").slice(2).join("/").split("?")[0];
    if (id && id !== "participate") {
      const found = DEMO_CAMPAIGNS.find((campaign) => campaign.id === id);
      if (found) return found;
    }
    if (normalizedPath.endsWith("/participate") && method === "POST") {
      return DEMO_ENTRY;
    }
  }

  if (normalizedPath === "/auth/otp/request" && method === "POST") {
    return {
      challenge_id: "demo-challenge-123",
      detail: "Development OTP issued for demo mode. Use 123456 to continue.",
      development_code: "123456",
    };
  }

  if (normalizedPath === "/auth/otp/verify" && method === "POST") {
    const payload = JSON.parse((init?.body as string | undefined) ?? "{}") as { code?: string };
    if (payload.code === "123456") {
      setToken("demo-access-token");
      return { access_token: "demo-access-token", token_type: "bearer" };
    }
    throw new Error("Invalid OTP");
  }

  if (normalizedPath === "/users/me") {
    return DEMO_USER;
  }

  if (normalizedPath === "/users/me/entries") {
    return [DEMO_ENTRY];
  }

  if (normalizedPath === "/public/draws/demo-draw/verification") {
    return {
      draw_id: "demo-draw",
      campaign_id: DEMO_CAMPAIGNS[0].id,
      campaign_title: DEMO_CAMPAIGNS[0].title,
      algorithm: "asset-draw/v1+HMAC-SHA256 (asset-draw/v1)",
      pool_hash: "demo-pool-hash",
      seed_commitment: "demo-seed-commitment",
      seed: "demo-seed",
      canonical_message: null,
      winner_index: 3,
      winning_entry_number: "A-1042",
      total_entries: 128,
      locked_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      verified: true,
    };
  }

  return undefined;
}

let accessToken: string | null = null;

export function getToken(): string | null {
  return accessToken;
}

export function setToken(t: string): void {
  accessToken = t;
}

export function clearToken(): void {
  accessToken = null;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers ?? {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type") && !(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const res = await fetch(`${BASE}${path}`, { ...init, headers });
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try {
        const j = await res.json();
        msg = (j as { detail?: string }).detail ?? msg;
      } catch {
        // ignore JSON parse failures and fall back to demo payloads below
      }
      const demoPayload = demoResponseFor(path, init);
      if (demoPayload !== undefined) return demoPayload as T;
      throw new Error(msg);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } catch (error) {
    const demoPayload = demoResponseFor(path, init);
    if (demoPayload !== undefined) return demoPayload as T;
    throw error;
  }
}

export async function fetchReady(): Promise<ReadyResponse> {
  const demoPayload = demoResponseFor("/health/ready");
  try {
    const res = await fetch(`${BASE}/health/ready`);
    if (res.status !== 200 && res.status !== 503) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as ReadyResponse;
  } catch {
    return demoPayload as ReadyResponse;
  }
}

function normalizePhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (phone.trim().startsWith("+")) return `+${digits}`;
  if (digits.startsWith("0")) return `+251${digits.slice(1)}`;
  if (digits.startsWith("251")) return `+${digits}`;
  return `+${digits}`;
}

export async function requestOtp(phone: string): Promise<{
  challenge_id: string;
  detail: string;
  development_code?: string;
}> {
  return apiFetch<{
    challenge_id: string;
    detail: string;
    development_code?: string;
  }>("/auth/otp/request", {
    method: "POST",
    body: JSON.stringify({ phone: normalizePhone(phone) }),
  });
}

export async function verifyOtp(challengeId: string, otp: string): Promise<AuthTokens> {
  const tokens = await apiFetch<AuthTokens>("/auth/otp/verify", {
    method: "POST",
    body: JSON.stringify({ challenge_id: challengeId, code: otp }),
  });
  setToken(tokens.access_token);
  return tokens;
}

export async function staffLogin(email: string, password: string): Promise<{ challenge_token: string }> {
  const result = await apiFetch<{ mfa_required: boolean; challenge_token: string }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
  );
  if (!result.mfa_required || !result.challenge_token) {
    throw new Error("Staff MFA challenge was not issued");
  }
  return { challenge_token: result.challenge_token };
}

export async function verifyStaffMfa(challengeToken: string, code: string): Promise<AuthTokens> {
  const tokens = await apiFetch<AuthTokens>("/auth/mfa/verify", {
    method: "POST",
    body: JSON.stringify({ challenge_token: challengeToken, code }),
  });
  setToken(tokens.access_token);
  return tokens;
}

export async function confirmStaffMfa(setupToken: string, code: string): Promise<void> {
  await apiFetch<{ mfa_enabled: boolean }>("/auth/staff/mfa/confirm", {
    method: "POST",
    body: JSON.stringify({ setup_token: setupToken, code }),
  });
}

export async function refreshAccessToken(): Promise<AuthTokens> {
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "X-CSRF-Protection": "1" },
    credentials: "same-origin",
  });
  if (!res.ok) throw new Error("Session expired");
  const tokens = (await res.json()) as AuthTokens;
  setToken(tokens.access_token);
  return tokens;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${BASE}/auth/logout`, {
      method: "POST",
      headers: { "X-CSRF-Protection": "1" },
      credentials: "same-origin",
    });
  } finally {
    clearToken();
  }
}

export async function fetchMe(): Promise<AuthUser> {
  return apiFetch<AuthUser>("/users/me");
}

export async function fetchCampaigns(params?: {
  status?: string;
  category?: string;
  search?: string;
}): Promise<Campaign[]> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.category) q.set("category", params.category);
  if (params?.search) q.set("search", params.search);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<Campaign[]>(`/campaigns${qs}`);
}

export async function fetchCampaign(id: string): Promise<Campaign> {
  return apiFetch<Campaign>(`/campaigns/${id}`);
}

export async function createEntry(campaignId: string): Promise<Entry> {
  return apiFetch<Entry>(`/campaigns/${campaignId}/participate`, { method: "POST" });
}

export async function fetchMyEntries(): Promise<Entry[]> {
  return apiFetch<Entry[]>("/users/me/entries");
}

export async function initializePayment(campaignId: string): Promise<{
  checkout_url: string;
  payment_id: string;
  amount: number;
}> {
  return apiFetch<{ checkout_url: string; payment_id: string; amount: number }>(
    `/payments/chapa/initialize`,
    { method: "POST", body: JSON.stringify({ campaign_id: campaignId }) },
  );
}

export async function fetchDrawVerification(drawId: string): Promise<DrawVerification> {
  return apiFetch<DrawVerification>(`/public/draws/${drawId}/verification`);
}

export async function fetchPublicDraw(drawId: string): Promise<DrawVerification> {
  return apiFetch<DrawVerification>(`/public/draws/${drawId}`);
}

export async function fetchMyVendor(): Promise<Vendor> {
  return apiFetch<Vendor>("/vendors/me");
}

export async function fetchVendorAssets(): Promise<Asset[]> {
  return apiFetch<Asset[]>("/assets");
}

export async function fetchVendorCampaigns(): Promise<Campaign[]> {
  return apiFetch<Campaign[]>("/vendors/me/campaigns");
}

export async function createCampaign(data: Partial<Campaign>): Promise<Campaign> {
  return apiFetch<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(data) });
}

export async function adminFetchAllCampaigns(): Promise<AdminCampaign[]> {
  return apiFetch<AdminCampaign[]>("/admin/campaigns");
}

export async function adminFetchAllVendors(): Promise<Vendor[]> {
  return apiFetch<Vendor[]>("/admin/vendors");
}

export async function adminApproveCampaign(id: string): Promise<AdminCampaign> {
  return apiFetch<AdminCampaign>(`/admin/campaigns/${id}/approve`, { method: "POST" });
}

export async function adminStartCampaignReview(id: string): Promise<AdminCampaign> {
  return apiFetch<AdminCampaign>(`/admin/campaigns/${id}/review`, { method: "POST" });
}

export async function adminVerifyCampaignAssets(id: string): Promise<AdminCampaign> {
  return apiFetch<AdminCampaign>(`/admin/campaigns/${id}/verify-asset`, { method: "POST" });
}

export async function adminScheduleCampaign(id: string): Promise<AdminCampaign> {
  return apiFetch<AdminCampaign>(`/admin/campaigns/${id}/schedule`, { method: "POST" });
}

export async function adminApproveVendor(id: string): Promise<Vendor> {
  return apiFetch<Vendor>(`/admin/vendors/${id}/approve`, { method: "POST" });
}

export async function adminFetchDraws(): Promise<AdminDraw[]> {
  return apiFetch<AdminDraw[]>("/admin/draws");
}
