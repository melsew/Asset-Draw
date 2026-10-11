import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { BarChart2, Package, PlusCircle, Eye, Users, TrendingUp } from "lucide-react";
import { fetchVendorCampaigns, fetchVendorAssets } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { Badge, statusBadge } from "../components/Badge";
import { ProgressBar } from "../components/ProgressBar";
import { Spinner } from "../components/Spinner";
import type { Campaign } from "../types/campaign";

export function VendorDashboardPage() {
  const { t } = useTranslation();
  const { user, isLoggedIn, loading } = useAuth();
  const [tab, setTab] = useState<"overview" | "campaigns" | "assets">("overview");

  const { data: campaigns } = useQuery({ queryKey: ["vendor-campaigns"], queryFn: fetchVendorCampaigns, enabled: isLoggedIn });
  const { data: assets }    = useQuery({ queryKey: ["vendor-assets"],    queryFn: fetchVendorAssets,    enabled: isLoggedIn });
  const safeCampaigns = Array.isArray(campaigns) ? campaigns : [];
  const safeAssets    = Array.isArray(assets)    ? assets    : [];

  const active    = safeCampaigns.filter((c: Campaign) => c.status === "ACTIVE").length;
  const completed = safeCampaigns.filter((c: Campaign) => c.status === "COMPLETED" || c.status === "DRAW_COMPLETED").length;
  const totalEntries = safeCampaigns.reduce((s: number, c: Campaign) => s + c.entries, 0);

  if (loading) return <Spinner center />;
  if (!isLoggedIn || (user && user.role !== "VENDOR" && user.role !== "ADMIN" && user.role !== "SUPER_ADMIN")) {
    return (
      <div className="ad-container ad-section" style={{ textAlign: "center" }}>
        <h2>{t("vendor.accessDenied")}</h2>
        <p className="ad-text-soft" style={{ marginBottom: 24 }}>{t("vendor.accessDeniedDesc")}</p>
        <Link to="/login" className="ad-btn ad-btn-primary">{t("nav.login")}</Link>
      </div>
    );
  }

  return (
    <div className="ad-dashboard">
      {/* Sidebar */}
      <aside className="ad-sidebar">
        <div className="ad-sidebar-section"><span>{t("vendor.dashboard")}</span></div>
        {[
          { to: "/vendor",         icon: BarChart2,  label: t("vendor.overview"),   tab: "overview" },
          { to: "/vendor/campaigns", icon: TrendingUp, label: t("vendor.campaigns"), tab: "campaigns" },
          { to: "/vendor/assets",  icon: Package,    label: t("vendor.assets"),     tab: "assets" },
        ].map(({ to, icon: Icon, label, tab: tabId }) => (
          <button
            key={to}
            type="button"
            className={`ad-sidebar-link ${tab === tabId ? "active" : ""}`}
            onClick={() => setTab(tabId as typeof tab)}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}
      </aside>

      {/* Main */}
      <main className="ad-dashboard-main">
        <div className="ad-dashboard-header">
          <div>
            <h2 style={{ marginBottom: 4 }}>
              {tab === "overview"   ? t("vendor.overviewTitle")  :
               tab === "campaigns" ? t("vendor.campaignsTitle") :
               t("vendor.assetsTitle")}
            </h2>
            <p className="ad-text-soft ad-text-sm">{t("vendor.welcome", { name: user?.display_name ?? user?.phone })}</p>
          </div>
          {tab === "campaigns" && (
            <Link to="/vendor/campaigns/new" className="ad-btn ad-btn-primary">
              <PlusCircle size={16} />
              {t("vendor.newCampaign")}
            </Link>
          )}
        </div>

        {tab === "overview" && (
          <>
            <div className="ad-stats-row">
              <div className="ad-stat-card">
                <span className="ad-stat-card-label">{t("vendor.totalCampaigns")}</span>
                <span className="ad-stat-card-value">{safeCampaigns.length}</span>
              </div>
              <div className="ad-stat-card">
                <span className="ad-stat-card-label">{t("vendor.activeCampaigns")}</span>
                <span className="ad-stat-card-value">{active}</span>
                <span className="ad-stat-card-change">↑ {t("vendor.live")}</span>
              </div>
              <div className="ad-stat-card">
                <span className="ad-stat-card-label">{t("vendor.totalEntries")}</span>
                <span className="ad-stat-card-value">{totalEntries.toLocaleString()}</span>
              </div>
              <div className="ad-stat-card">
                <span className="ad-stat-card-label">{t("vendor.completedDraws")}</span>
                <span className="ad-stat-card-value">{completed}</span>
              </div>
            </div>

            <h3 style={{ marginBottom: 16 }}>{t("vendor.recentCampaigns")}</h3>
            {safeCampaigns.length === 0 ? (
              <div className="ad-empty">
                <span className="ad-empty-icon">📢</span>
                <h3>{t("vendor.noCampaigns")}</h3>
                <p>{t("vendor.noCampaignsDesc")}</p>
                <Link to="/vendor/campaigns/new" className="ad-btn ad-btn-primary" style={{ marginTop: 16 }}>
                  <PlusCircle size={16} />
                  {t("vendor.newCampaign")}
                </Link>
              </div>
            ) : (
              <div className="ad-table-wrap">
                <table className="ad-table">
                  <thead>
                    <tr>
                      <th>{t("vendor.th.campaign")}</th>
                      <th>{t("vendor.th.prize")}</th>
                      <th>{t("vendor.th.entries")}</th>
                      <th>{t("vendor.th.status")}</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {safeCampaigns.slice(0, 5).map((c: Campaign) => (
                      <tr key={c.id}>
                        <td style={{ fontWeight: 600, color: "var(--ad-navy)" }}>{c.title}</td>
                        <td>{c.prize}</td>
                        <td>
                          <div style={{ minWidth: 120 }}>
                            <ProgressBar current={c.entries} max={c.max_entries} />
                          </div>
                        </td>
                        <td><Badge variant={statusBadge(c.status)}>{c.status}</Badge></td>
                        <td>
                          <Link to={`/campaigns/${c.id}`} className="ad-btn ad-btn-ghost ad-btn-sm">
                            <Eye size={13} /> {t("common.view")}
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {tab === "campaigns" && (
          safeCampaigns.length === 0 ? (
            <div className="ad-empty">
              <span className="ad-empty-icon">📢</span>
              <h3>{t("vendor.noCampaigns")}</h3>
              <Link to="/vendor/campaigns/new" className="ad-btn ad-btn-primary" style={{ marginTop: 16 }}>
                <PlusCircle size={16} /> {t("vendor.newCampaign")}
              </Link>
            </div>
          ) : (
            <div className="ad-campaign-grid">
              {safeCampaigns.map((c: Campaign) => (
                <div key={c.id} className="ad-verify-card">
                  <div className="ad-flex-between ad-mb-4">
                    <Badge variant={statusBadge(c.status)}>{c.status}</Badge>
                    <Link to={`/campaigns/${c.id}`} className="ad-section-link" style={{ fontSize: "0.78rem" }}>
                      <Eye size={13} /> {t("common.view")}
                    </Link>
                  </div>
                  <h3 className="ad-campaign-card-title">{c.title}</h3>
                  <p className="ad-campaign-card-vendor">{c.prize}</p>
                  <div className="ad-divider" />
                  <ProgressBar current={c.entries} max={c.max_entries} />
                </div>
              ))}
            </div>
          )
        )}

        {tab === "assets" && (
          safeAssets.length === 0 ? (
            <div className="ad-empty">
              <span className="ad-empty-icon">📦</span>
              <h3>{t("vendor.noAssets")}</h3>
              <p>{t("vendor.noAssetsDesc")}</p>
            </div>
          ) : (
            <div className="ad-table-wrap">
              <table className="ad-table">
                <thead><tr><th>{t("vendor.th.asset")}</th><th>{t("vendor.th.value")}</th><th>{t("vendor.th.status")}</th></tr></thead>
                <tbody>
                  {safeAssets.map((a) => (
                    <tr key={a.id}>
                      <td style={{ fontWeight: 600, color: "var(--ad-navy)" }}>{a.name}</td>
                      <td>{a.declared_value.toLocaleString()} {t("currency")}</td>
                      <td><Badge variant="blue">{a.status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </main>
    </div>
  );
}
