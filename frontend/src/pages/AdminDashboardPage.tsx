import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart2, CheckCircle2, Eye, Gavel, Search, ShieldCheck, Users } from "lucide-react";
import {
  adminApproveCampaign,
  adminApproveVendor,
  adminFetchAllCampaigns,
  adminFetchAllVendors,
  adminFetchDraws,
  adminScheduleCampaign,
  adminStartCampaignReview,
  adminVerifyCampaignAssets,
} from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { Badge, statusBadge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import type { AdminCampaign, AdminDraw } from "../services/api";
import type { Vendor } from "../types/campaign";

type Tab = "campaigns" | "vendors" | "draws";

export function AdminDashboardPage() {
  const { t } = useTranslation();
  const { user, isLoggedIn, loading } = useAuth();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("campaigns");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const role = user?.role;
  const canReviewCampaigns = role === "ADMIN" || role === "SUPER_ADMIN" || role === "CAMPAIGN_MANAGER";
  const canApproveCampaigns = role === "ADMIN" || role === "SUPER_ADMIN";
  const canManageVendors = canApproveCampaigns;
  const canViewDraws = canApproveCampaigns || role === "AUDITOR";
  const canViewDashboard = canReviewCampaigns || canViewDraws;

  const campaignsQuery = useQuery({
    queryKey: ["admin-campaigns"],
    queryFn: adminFetchAllCampaigns,
    enabled: canViewDashboard,
  });
  const vendorsQuery = useQuery({
    queryKey: ["admin-vendors"],
    queryFn: adminFetchAllVendors,
    enabled: canManageVendors,
  });
  const drawsQuery = useQuery({
    queryKey: ["admin-draws"],
    queryFn: adminFetchDraws,
    enabled: canViewDraws && tab === "draws",
  });

  const refreshCampaigns = () => queryClient.invalidateQueries({ queryKey: ["admin-campaigns"] });
  const reviewMutation = useMutation({
    mutationFn: adminStartCampaignReview,
    onSuccess: refreshCampaigns,
  });
  const approveCampaignMutation = useMutation({
    mutationFn: adminApproveCampaign,
    onSuccess: refreshCampaigns,
  });
  const verifyAssetsMutation = useMutation({
    mutationFn: adminVerifyCampaignAssets,
    onSuccess: refreshCampaigns,
  });
  const scheduleCampaignMutation = useMutation({
    mutationFn: adminScheduleCampaign,
    onSuccess: refreshCampaigns,
  });
  const approveVendorMutation = useMutation({
    mutationFn: adminApproveVendor,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-vendors"] }),
  });

  const campaigns = campaignsQuery.data ?? [];
  const vendors = vendorsQuery.data ?? [];
  const draws = drawsQuery.data ?? [];
  const pendingCampaigns = campaigns.filter((campaign) =>
    ["SUBMITTED", "UNDER_REVIEW"].includes(campaign.status),
  );
  const filteredCampaigns = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase();
    return campaigns.filter((campaign) => {
      const matchesStatus = statusFilter === "ALL" || campaign.status === statusFilter;
      const matchesSearch = !normalizedSearch
        || `${campaign.title} ${campaign.vendor} ${campaign.prize}`.toLocaleLowerCase().includes(normalizedSearch);
      return matchesStatus && matchesSearch;
    });
  }, [campaigns, search, statusFilter]);

  if (loading) return <Spinner center />;
  if (!isLoggedIn || !canViewDashboard) {
    return (
      <div className="ad-container ad-section" style={{ textAlign: "center" }}>
        <ShieldCheck size={52} color="var(--ad-text-soft)" style={{ margin: "0 auto 16px" }} />
        <h2>{t("admin.accessDenied")}</h2>
        <p className="ad-text-soft">{t("admin.accessDeniedDesc")}</p>
        <Link to="/staff/login" className="ad-btn ad-btn-primary" style={{ marginTop: 16 }}>
          {t("auth.staffLoginLink")}
        </Link>
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: typeof BarChart2 }[] = [
    { id: "campaigns", label: t("admin.campaigns"), icon: BarChart2 },
    ...(canManageVendors ? [{ id: "vendors" as const, label: t("admin.vendors"), icon: Users }] : []),
    ...(canViewDraws ? [{ id: "draws" as const, label: t("admin.draws"), icon: Gavel }] : []),
  ];
  const actionError = reviewMutation.error
    || approveCampaignMutation.error
    || verifyAssetsMutation.error
    || scheduleCampaignMutation.error
    || approveVendorMutation.error;
  const campaignActionPending = reviewMutation.isPending
    || approveCampaignMutation.isPending
    || verifyAssetsMutation.isPending
    || scheduleCampaignMutation.isPending;

  return (
    <div className="ad-dashboard">
      <aside className="ad-sidebar" aria-label={t("admin.panel")}>
        <div className="ad-sidebar-section"><span>{t("admin.panel")}</span></div>
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`ad-sidebar-link ${tab === id ? "active" : ""}`}
            aria-current={tab === id ? "page" : undefined}
            onClick={() => setTab(id)}
          >
            <Icon size={17} aria-hidden="true" />
            {label}
          </button>
        ))}
      </aside>

      <main className="ad-dashboard-main">
        <div className="ad-dashboard-header">
          <div>
            <h2 style={{ marginBottom: 4 }}>{t("admin.title")}</h2>
            <p className="ad-text-soft ad-text-sm">
              {t("admin.subtitle", { name: user?.display_name ?? user?.email ?? user?.phone ?? "" })}
            </p>
          </div>
          {pendingCampaigns.length > 0 && (
            <div className="ad-alert ad-alert-warning" role="status" style={{ padding: "8px 14px" }}>
              <ShieldCheck size={16} aria-hidden="true" />
              {t("admin.pendingAlert", { count: pendingCampaigns.length })}
            </div>
          )}
        </div>

        {campaignsQuery.isError && (
          <div className="ad-alert ad-alert-error" role="alert">
            {t("admin.loadCampaignsError")}
            <button type="button" className="ad-btn ad-btn-ghost ad-btn-sm" onClick={() => void campaignsQuery.refetch()}>
              {t("admin.retry")}
            </button>
          </div>
        )}

        <div className="ad-stats-row" style={{ marginBottom: 28 }}>
          <Stat label={t("admin.totalCampaigns")} value={campaigns.length} />
          <Stat label={t("admin.pendingReview")} value={pendingCampaigns.length} highlight />
          {canManageVendors && <Stat label={t("admin.totalVendors")} value={vendors.length} />}
          <Stat label={t("admin.activeCampaigns")} value={campaigns.filter((c) => c.status === "ACTIVE").length} />
        </div>

        {actionError && (
          <div className="ad-alert ad-alert-error" role="alert">
            {actionError instanceof Error ? actionError.message : t("admin.actionError")}
          </div>
        )}

        {tab === "campaigns" && (
          <section aria-label={t("admin.campaigns")}>
            <div className="ad-admin-toolbar">
              <label className="ad-admin-search">
                <Search size={16} aria-hidden="true" />
                <span className="ad-visually-hidden">{t("admin.searchCampaigns")}</span>
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={t("admin.searchCampaigns")}
                />
              </label>
              <label>
                <span className="ad-visually-hidden">{t("admin.filterStatus")}</span>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="ALL">{t("admin.allStatuses")}</option>
                  {[...new Set(campaigns.map((campaign) => campaign.status))].sort().map((status) => (
                    <option key={status} value={status}>{t(`status.${status}`, status)}</option>
                  ))}
                </select>
              </label>
            </div>
            {campaignsQuery.isLoading ? <Spinner center /> : campaignsQuery.isError && campaigns.length === 0 ? null : filteredCampaigns.length === 0 ? (
              <div className="ad-empty">
                <h3>{campaigns.length === 0 ? t("admin.noCampaigns") : t("admin.noMatchingCampaigns")}</h3>
              </div>
            ) : (
              <div className="ad-table-wrap">
                <table className="ad-table">
                  <thead>
                    <tr>
                      <th>{t("admin.th.campaign")}</th>
                      <th>{t("admin.th.vendor")}</th>
                      <th>{t("admin.th.prize")}</th>
                      <th>{t("admin.th.entryMode")}</th>
                      <th>{t("admin.th.status")}</th>
                      <th>{t("admin.th.actions")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCampaigns.map((campaign) => (
                      <tr key={campaign.id}>
                        <td style={{ fontWeight: 600, color: "var(--ad-navy)" }}>{campaign.title}</td>
                        <td>{campaign.vendor}</td>
                        <td>{campaign.prize}</td>
                        <td>{t(`entryMode.${campaign.entry_mode}`, campaign.entry_mode)}</td>
                        <td><Badge variant={statusBadge(campaign.status)}>{t(`status.${campaign.status}`, campaign.status)}</Badge></td>
                        <td>
                          <div className="ad-admin-actions">
                            <Link to={`/campaigns/${campaign.id}`} className="ad-btn ad-btn-ghost ad-btn-sm" aria-label={t("admin.viewCampaign", { title: campaign.title })}>
                              <Eye size={14} aria-hidden="true" />
                            </Link>
                            {canReviewCampaigns && campaign.status === "SUBMITTED" && (
                              <button
                                type="button"
                                className="ad-btn ad-btn-primary ad-btn-sm"
                                disabled={campaignActionPending}
                                onClick={() => reviewMutation.mutate(campaign.id)}
                              >
                                {t("admin.startReview")}
                              </button>
                            )}
                            {canApproveCampaigns && campaign.status === "UNDER_REVIEW" && (
                              <button
                                type="button"
                                className="ad-btn ad-btn-primary ad-btn-sm"
                                disabled={campaignActionPending}
                                onClick={() => approveCampaignMutation.mutate(campaign.id)}
                              >
                                <CheckCircle2 size={14} aria-hidden="true" />
                                {t("admin.approve")}
                              </button>
                            )}
                            {canApproveCampaigns && campaign.status === "APPROVED" && (
                              <button
                                type="button"
                                className="ad-btn ad-btn-primary ad-btn-sm"
                                disabled={campaignActionPending}
                                onClick={() => verifyAssetsMutation.mutate(campaign.id)}
                              >
                                {t("admin.verifyAssets")}
                              </button>
                            )}
                            {role === "CAMPAIGN_MANAGER" && campaign.status === "ASSET_VERIFIED" && (
                              <button
                                type="button"
                                className="ad-btn ad-btn-primary ad-btn-sm"
                                disabled={campaignActionPending}
                                onClick={() => scheduleCampaignMutation.mutate(campaign.id)}
                              >
                                {t("admin.schedule")}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {tab === "vendors" && canManageVendors && (
          <section aria-label={t("admin.vendors")}>
            {vendorsQuery.isError && (
              <div className="ad-alert ad-alert-error" role="alert">
                {t("admin.loadVendorsError")}
                <button type="button" className="ad-btn ad-btn-ghost ad-btn-sm" onClick={() => void vendorsQuery.refetch()}>
                  {t("admin.retry")}
                </button>
              </div>
            )}
            {vendorsQuery.isLoading ? <Spinner center /> : vendorsQuery.isError && vendors.length === 0 ? null : vendors.length === 0 ? (
              <div className="ad-empty"><h3>{t("admin.noVendors")}</h3></div>
            ) : (
              <div className="ad-table-wrap">
                <table className="ad-table">
                  <thead>
                    <tr>
                      <th>{t("admin.th.vendor")}</th>
                      <th>{t("admin.th.legalName")}</th>
                      <th>{t("admin.th.status")}</th>
                      <th>{t("admin.th.contact")}</th>
                      <th>{t("admin.th.actions")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vendors.map((vendor) => (
                      <VendorRow
                        key={vendor.id}
                        vendor={vendor}
                        pending={approveVendorMutation.isPending}
                        onApprove={() => approveVendorMutation.mutate(vendor.id)}
                        approveLabel={t("admin.approveVendor")}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {tab === "draws" && (
          <section aria-label={t("admin.draws")}>
            {drawsQuery.isError && (
              <div className="ad-alert ad-alert-error" role="alert">
                {t("admin.loadDrawsError")}
                <button type="button" className="ad-btn ad-btn-ghost ad-btn-sm" onClick={() => void drawsQuery.refetch()}>
                  {t("admin.retry")}
                </button>
              </div>
            )}
            {drawsQuery.isLoading ? <Spinner center /> : drawsQuery.isError && draws.length === 0 ? null : draws.length === 0 ? (
              <div className="ad-empty">
                <Gavel size={40} color="var(--ad-text-soft)" aria-hidden="true" />
                <h3>{t("admin.noDraws")}</h3>
                <p>{t("admin.drawsNote")}</p>
              </div>
            ) : (
              <div className="ad-table-wrap">
                <table className="ad-table">
                  <thead>
                    <tr>
                      <th>{t("admin.th.campaign")}</th>
                      <th>{t("admin.th.status")}</th>
                      <th>{t("admin.th.entropy")}</th>
                      <th>{t("admin.th.lockedAt")}</th>
                      <th>{t("admin.th.actions")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {draws.map((draw) => <DrawRow key={draw.id} draw={draw} />)}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value, highlight = false }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="ad-stat-card">
      <span className="ad-stat-card-label">{label}</span>
      <span className="ad-stat-card-value" style={highlight ? { color: "var(--ad-gold)" } : undefined}>{value}</span>
    </div>
  );
}

function VendorRow({
  vendor,
  pending,
  onApprove,
  approveLabel,
}: {
  vendor: Vendor;
  pending: boolean;
  onApprove: () => void;
  approveLabel: string;
}) {
  const { t } = useTranslation();
  return (
    <tr>
      <td style={{ fontWeight: 600, color: "var(--ad-navy)" }}>{vendor.display_name}</td>
      <td>{vendor.legal_name}</td>
      <td><Badge variant={vendor.status === "APPROVED" ? "green" : vendor.status === "PENDING" ? "gold" : "gray"}>{vendor.status}</Badge></td>
      <td className="ad-text-soft ad-text-sm">{vendor.contact_email || t("admin.notProvided")}</td>
      <td>
        {vendor.status === "PENDING" && (
          <button type="button" className="ad-btn ad-btn-primary ad-btn-sm" disabled={pending} onClick={onApprove}>
            <CheckCircle2 size={14} aria-hidden="true" />
            {approveLabel}
          </button>
        )}
      </td>
    </tr>
  );
}

function DrawRow({ draw }: { draw: AdminDraw }) {
  const { t, i18n } = useTranslation();
  return (
    <tr>
      <td style={{ fontWeight: 600, color: "var(--ad-navy)" }}>{draw.campaign_title}</td>
      <td><Badge variant={statusBadge(draw.status)}>{t(`status.${draw.status}`, draw.status)}</Badge></td>
      <td>{draw.planned_entropy_round ? `${draw.planned_entropy_source ?? ""} #${draw.planned_entropy_round}` : t("admin.notPlanned")}</td>
      <td>
        {draw.pool_locked_at
          ? new Intl.DateTimeFormat(i18n.language === "am" ? "am-ET" : "en-ET", {
              dateStyle: "medium",
              timeStyle: "short",
              timeZone: "Africa/Addis_Ababa",
            }).format(new Date(draw.pool_locked_at))
          : t("admin.notLocked")}
      </td>
      <td>
        {draw.status === "COMPLETED"
          ? (
            <Link to={`/verify/${draw.id}`} className="ad-btn ad-btn-ghost ad-btn-sm">
              <Eye size={14} aria-hidden="true" />
              {t("admin.viewVerification")}
            </Link>
          )
          : <span className="ad-text-soft ad-text-sm">{t("admin.notPublished")}</span>}
      </td>
    </tr>
  );
}
