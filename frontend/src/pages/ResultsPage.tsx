import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Trophy, Shield, ChevronRight } from "lucide-react";
import { fetchCampaigns } from "../services/api";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import type { Campaign } from "../types/campaign";

export function ResultsPage() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["campaigns-completed"],
    queryFn: () => fetchCampaigns({ status: "COMPLETED" }),
    staleTime: 60_000,
  });
  const campaigns = Array.isArray(data) ? data : [];

  return (
    <div>
      <div className="ad-page-header">
        <div className="ad-container">
          <h1>{t("results.title")}</h1>
          <p>{t("results.subtitle")}</p>
        </div>
      </div>

      <div className="ad-container ad-section">
        {isLoading ? <Spinner center /> : isError ? (
          <div className="ad-alert ad-alert-error">{t("results.loadError")}</div>
        ) : campaigns.length === 0 ? (
          <div className="ad-empty">
            <span className="ad-empty-icon">🏆</span>
            <h3>{t("results.empty")}</h3>
            <p>{t("results.emptyDesc")}</p>
          </div>
        ) : (
          <div className="ad-entry-list">
            {campaigns.map((c: Campaign) => (
              <div key={c.id} className="ad-entry-item">
                <Trophy size={32} color="var(--ad-gold)" />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, color: "var(--ad-navy)" }}>{c.title}</div>
                  <div className="ad-text-soft ad-text-sm">{c.vendor} · {c.prize}</div>
                </div>
                <Badge variant="navy">{t(`status.${c.status}`, { defaultValue: c.status })}</Badge>
                <Link to={`/verify`} className="ad-btn ad-btn-ghost ad-btn-sm" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Shield size={14} />
                  {t("results.verify")}
                  <ChevronRight size={14} />
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
