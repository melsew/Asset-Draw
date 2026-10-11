import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Search, Award } from "lucide-react";
import { useCampaigns } from "../hooks/useCampaigns";
import { Countdown } from "../components/Countdown";
import { ProgressBar } from "../components/ProgressBar";
import { Badge, entryModeBadge, statusBadge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import type { Campaign } from "../types/campaign";

const CATEGORIES = ["car", "smartphone", "laptop", "tablet", "tv", "refrigerator", "washingMachine", "travel", "other"];
const STATUSES   = ["ACTIVE", "SCHEDULED", "DRAW_COMPLETED", "COMPLETED"];
const MODES      = ["FREE", "PROMOTIONAL", "PURCHASE"];

function formatDate(value: string, lang: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat(lang === "am" ? "am-ET" : "en-ET", { dateStyle: "medium", timeZone: "Africa/Addis_Ababa" }).format(d);
}

export function CampaignListPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "am";
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [search,   setSearch]   = useState(searchParams.get("search") ?? "");
  const [category, setCategory] = useState(searchParams.get("category") ?? "");
  const [status,   setStatus]   = useState(searchParams.get("status") ?? "");
  const [mode,     setMode]     = useState(searchParams.get("mode") ?? "");

  const { data, isLoading, isError } = useCampaigns({ status: status || undefined, category: category || undefined, search: search || undefined });
  const campaigns = (Array.isArray(data) ? data : []).filter((c: Campaign) => !mode || c.entry_mode === mode);

  function applySearch(val: string) {
    setSearch(val);
    const p = new URLSearchParams(searchParams);
    if (val) p.set("search", val); else p.delete("search");
    setSearchParams(p);
  }

  return (
    <div>
      {/* Page header */}
      <div className="ad-page-header">
        <div className="ad-container">
          <div className="ad-breadcrumb">
            <Link to="/">{t("app.name")}</Link>
            <span className="ad-breadcrumb-sep">›</span>
            <span>{t("nav.campaigns")}</span>
          </div>
          <h1>{t("campaigns.pageTitle")}</h1>
          <p>{t("campaigns.pageDesc")}</p>
        </div>
      </div>

      {/* Filter bar */}
      <div className="ad-filter-bar">
        <div className="ad-container">
          <div className="ad-filter-bar-inner">
            {/* Search */}
            <div className="ad-search-wrap">
              <Search size={16} />
              <input
                type="search"
                className="ad-input"
                placeholder={t("campaigns.searchPlaceholder")}
                value={search}
                onChange={(e) => applySearch(e.target.value)}
              />
            </div>

            {/* Category */}
            <select className="ad-select" value={category} onChange={(e) => { setCategory(e.target.value); }}>
              <option value="">{t("campaigns.allCategories")}</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{t(`categories.items.${c}`)}</option>)}
            </select>

            {/* Status */}
            <select className="ad-select" value={status} onChange={(e) => { setStatus(e.target.value); }}>
              <option value="">{t("campaigns.allStatuses")}</option>
              {STATUSES.map((s) => <option key={s} value={s}>{t(`status.${s}`, { defaultValue: s })}</option>)}
            </select>

            {/* Mode */}
            <select className="ad-select" value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="">{t("campaigns.allModes")}</option>
              {MODES.map((m) => <option key={m} value={m}>{t(`entryMode.${m}`, { defaultValue: m })}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="ad-container ad-section">
        {isLoading ? (
          <Spinner center />
        ) : isError ? (
          <div className="ad-alert ad-alert-error">{t("campaigns.loadError")}</div>
        ) : campaigns.length === 0 ? (
          <div className="ad-empty">
            <span className="ad-empty-icon">🔍</span>
            <h3>{t("campaigns.noResults")}</h3>
            <p>{t("campaigns.noResultsDesc")}</p>
          </div>
        ) : (
          <>
            <p className="ad-text-soft ad-text-sm ad-mb-4">
              {t("campaigns.resultCount", { count: campaigns.length })}
            </p>
            <div className="ad-campaign-grid">
              {campaigns.map((c: Campaign) => (
                <article key={c.id} className="ad-campaign-card">
                  <div className="ad-campaign-card-img">
                    {c.prize_image_url ? (
                      <img src={c.prize_image_url} alt={c.prize} loading="lazy" />
                    ) : (
                      <div style={{ height: "100%", background: "linear-gradient(135deg,#001f5b,#0484c0)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Award size={60} color="rgba(255,255,255,0.2)" />
                      </div>
                    )}
                    <div className="ad-campaign-card-badge">
                      <Badge variant={entryModeBadge(c.entry_mode)}>{t(`entryMode.${c.entry_mode}`, { defaultValue: c.entry_mode })}</Badge>
                      <Badge variant={statusBadge(c.status)}>{t(`status.${c.status}`, { defaultValue: c.status })}</Badge>
                    </div>
                    <button type="button" className="ad-campaign-card-action-btn" onClick={() => navigate(`/campaigns/${c.id}`)}>
                      {t("campaign.participate")}
                    </button>
                    <div className="ad-campaign-card-prize-overlay">
                      <span>{c.vendor}</span>
                      <strong>{c.prize}</strong>
                    </div>
                  </div>
                  <div className="ad-campaign-card-body">
                    <h3 className="ad-campaign-card-title">{c.title}</h3>
                    <ProgressBar current={c.entries} max={c.max_entries} />
                    <Countdown drawAt={c.draw_at} status={c.status} />
                    <div className="ad-campaign-card-footer">
                      <span className="ad-text-soft ad-text-sm">{t("campaign.closes", { date: formatDate(c.ends_at, lang) })}</span>
                      <Link to={`/campaigns/${c.id}`} className="ad-section-link">{t("campaign.details")} →</Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
