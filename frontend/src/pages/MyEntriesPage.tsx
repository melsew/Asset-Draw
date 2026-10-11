import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Trophy, Calendar, CheckCircle2, Clock, XCircle } from "lucide-react";
import { useMyEntries } from "../hooks/useCampaigns";
import { useAuth } from "../hooks/useAuth";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import type { Entry } from "../types/campaign";

function entryStatusVariant(s: string) {
  if (s === "WINNER")    return "gold" as const;
  if (s === "ELIGIBLE")  return "green" as const;
  if (s === "ACTIVE")    return "blue" as const;
  if (s === "CANCELLED") return "red" as const;
  return "gray" as const;
}

function formatDate(value: string, lang: string) {
  return new Intl.DateTimeFormat(lang === "am" ? "am-ET" : "en-ET", { dateStyle: "medium", timeStyle: "short", timeZone: "Africa/Addis_Ababa" }).format(new Date(value));
}

export function MyEntriesPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "am";
  const { isLoggedIn, loading: authLoading } = useAuth();
  const { data: entries, isLoading, isError } = useMyEntries();
  const safeEntries = Array.isArray(entries) ? entries : [];

  if (authLoading) return <Spinner center />;

  if (!isLoggedIn) {
    return (
      <div className="ad-container ad-section" style={{ textAlign: "center" }}>
        <Trophy size={52} color="var(--ad-text-soft)" style={{ margin: "0 auto 16px" }} />
        <h2>{t("entries.loginRequired")}</h2>
        <p className="ad-text-soft" style={{ marginBottom: 24 }}>{t("entries.loginRequiredDesc")}</p>
        <Link to="/login" className="ad-btn ad-btn-primary ad-btn-lg">{t("nav.login")}</Link>
      </div>
    );
  }

  return (
    <div className="ad-entries-page">
      <div className="ad-page-header">
        <div className="ad-container">
          <div className="ad-breadcrumb">
            <Link to="/">{t("app.name")}</Link>
            <span className="ad-breadcrumb-sep">›</span>
            <span>{t("nav.myEntries")}</span>
          </div>
          <h1>{t("entries.title")}</h1>
          <p>{t("entries.subtitle")}</p>
        </div>
      </div>

      <div className="ad-container" style={{ marginTop: 32 }}>
        {isLoading ? (
          <Spinner center />
        ) : isError ? (
          <div className="ad-alert ad-alert-error">{t("entries.loadError")}</div>
        ) : safeEntries.length === 0 ? (
          <div className="ad-empty">
            <span className="ad-empty-icon">🎫</span>
            <h3>{t("entries.empty")}</h3>
            <p>{t("entries.emptyDesc")}</p>
            <Link to="/campaigns" className="ad-btn ad-btn-primary" style={{ marginTop: 16 }}>{t("nav.campaigns")}</Link>
          </div>
        ) : (
          <div className="ad-entry-list">
            {safeEntries.map((entry: Entry) => (
              <div key={entry.id} className="ad-entry-item">
                {/* Entry number */}
                <div className="ad-entry-number">#{entry.entry_number}</div>

                {/* Details */}
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
                  <div style={{ fontWeight: 700, color: "var(--ad-navy)", fontSize: "1rem" }}>
                    {entry.campaign_title}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--ad-text-soft)", fontSize: "0.82rem" }}>
                    <Trophy size={13} />
                    {entry.campaign_prize}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--ad-text-soft)", fontSize: "0.78rem" }}>
                    <Calendar size={13} />
                    {t("entries.entered", { date: formatDate(entry.created_at, lang) })}
                  </div>
                </div>

                {/* Status */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                  <Badge variant={entryStatusVariant(entry.status)}>
                    {entry.status === "WINNER"   && <><CheckCircle2 size={11} /> {t("entries.winner")}</>}
                    {entry.status === "ELIGIBLE" && <><CheckCircle2 size={11} /> {t("entries.eligible")}</>}
                    {entry.status === "ACTIVE"   && <><Clock size={11} /> {t("entries.active")}</>}
                    {entry.status === "CANCELLED"&& <><XCircle size={11} /> {t("entries.cancelled")}</>}
                  </Badge>
                  {entry.draw_at && entry.status === "ACTIVE" && (
                    <span className="ad-text-soft ad-text-xs">
                      {t("entries.drawAt", { date: formatDate(entry.draw_at, lang) })}
                    </span>
                  )}
                  <Link to={`/campaigns/${entry.campaign_id}`} className="ad-section-link" style={{ fontSize: "0.78rem" }}>
                    {t("campaign.viewCampaign")} →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
