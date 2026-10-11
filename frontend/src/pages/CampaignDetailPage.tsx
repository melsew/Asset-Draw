import { useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Award, Building2, Calendar, Users, CheckCircle2, AlertCircle, Info } from "lucide-react";
import { useCampaign } from "../hooks/useCampaigns";
import { useAuth } from "../hooks/useAuth";
import { createEntry, initializePayment } from "../services/api";
import { Countdown } from "../components/Countdown";
import { ProgressBar } from "../components/ProgressBar";
import { Badge, entryModeBadge, statusBadge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { Modal } from "../components/Modal";

function formatDate(value: string, lang: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return new Intl.DateTimeFormat(lang === "am" ? "am-ET" : "en-ET", { dateStyle: "long", timeZone: "Africa/Addis_Ababa" }).format(d);
}

export function CampaignDetailPage() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "am";
  const { user, isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: campaign, isLoading, isError } = useCampaign(id);
  const [successEntry, setSuccessEntry] = useState<{ entry_number: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const entryMutation = useMutation({
    mutationFn: () => createEntry(id),
    onSuccess: (entry) => {
      setSuccessEntry(entry);
      void qc.invalidateQueries({ queryKey: ["campaign", id] });
      void qc.invalidateQueries({ queryKey: ["my-entries"] });
    },
    onError: (e: Error) => setErrorMsg(e.message),
  });

  const payMutation = useMutation({
    mutationFn: () => initializePayment(id),
    onSuccess: (res) => { window.location.href = res.checkout_url; },
    onError: (e: Error) => setErrorMsg(e.message),
  });

  if (isLoading) return <Spinner center />;
  if (isError || !campaign) return (
    <div className="ad-container ad-section">
      <div className="ad-alert ad-alert-error">
        <AlertCircle size={18} />
        {t("campaign.notFound")}
      </div>
    </div>
  );

  const isActive     = campaign.status === "ACTIVE";
  const isFree       = campaign.entry_mode === "FREE";
  const isPromo      = campaign.entry_mode === "PROMOTIONAL";
  const needsPayment = campaign.entry_mode === "PURCHASE" || campaign.entry_mode === "PAID_ENTRY";
  const isFull       = campaign.entries >= campaign.max_entries;

  function handleParticipate() {
    if (!isLoggedIn) { navigate("/login?next=" + encodeURIComponent(`/campaigns/${id}`)); return; }
    if (needsPayment) { payMutation.mutate(); return; }
    entryMutation.mutate();
  }

  return (
    <div className="ad-detail-page">
      {/* Hero */}
      <div className="ad-detail-hero">
        <div className="ad-container">
          <div className="ad-breadcrumb">
            <Link to="/">{t("app.name")}</Link>
            <span className="ad-breadcrumb-sep">›</span>
            <Link to="/campaigns">{t("nav.campaigns")}</Link>
            <span className="ad-breadcrumb-sep">›</span>
            <span>{campaign.title}</span>
          </div>
          <div className="ad-detail-hero-inner">
            <div className="ad-detail-hero-info">
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Badge variant={entryModeBadge(campaign.entry_mode)}>{t(`entryMode.${campaign.entry_mode}`, { defaultValue: campaign.entry_mode })}</Badge>
                <Badge variant={statusBadge(campaign.status)}>{t(`status.${campaign.status}`, { defaultValue: campaign.status })}</Badge>
              </div>
              <h1 className="ad-detail-hero h1" style={{ color: "white" }}>{campaign.title}</h1>
              <p style={{ color: "rgba(255,255,255,0.75)" }}>{campaign.description}</p>
              <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginTop: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "rgba(255,255,255,0.7)", fontSize: "0.88rem" }}>
                  <Building2 size={15} />
                  {campaign.vendor}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "rgba(255,255,255,0.7)", fontSize: "0.88rem" }}>
                  <Calendar size={15} />
                  {t("campaign.closes", { date: formatDate(campaign.ends_at, lang) })}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "rgba(255,255,255,0.7)", fontSize: "0.88rem" }}>
                  <Users size={15} />
                  {t("campaign.entryCount", { count: campaign.entries, max: campaign.max_entries })}
                </div>
              </div>
            </div>
            <div className="ad-detail-hero-img">
              {campaign.prize_image_url ? (
                <img src={campaign.prize_image_url} alt={campaign.prize} />
              ) : (
                <div style={{ height: "100%", background: "rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "var(--radius-lg)" }}>
                  <Award size={80} color="rgba(255,255,255,0.2)" />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="ad-container">
        <div className="ad-detail-body">
          {/* Left: info */}
          <div>
            {/* About the prize */}
            <div className="ad-verify-card">
              <h3 style={{ marginBottom: 12 }}>{t("campaign.aboutPrize")}</h3>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <Award size={40} color="var(--ad-gold)" />
                <div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 900, color: "var(--ad-navy)" }}>{campaign.prize}</div>
                  {campaign.prize_value && (
                    <div className="ad-text-soft ad-text-sm">
                      {t("campaign.declaredValue", { value: campaign.prize_value.toLocaleString() })}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="ad-divider" />

            {/* Progress */}
            <div className="ad-verify-card">
              <h3 style={{ marginBottom: 16 }}>{t("campaign.participation")}</h3>
              <ProgressBar current={campaign.entries} max={campaign.max_entries} />
              <div className="ad-divider" />
              <h4 style={{ marginBottom: 12, color: "var(--ad-navy)", fontSize: "0.95rem" }}>{t("campaign.drawIn")}</h4>
              <Countdown drawAt={campaign.draw_at} status={campaign.status} />
            </div>

            <div className="ad-divider" />

            {/* Rules */}
            <div className="ad-verify-card">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Info size={18} color="var(--ad-blue)" />
                <h3 style={{ margin: 0 }}>{t("campaign.rules")}</h3>
              </div>
              <ul style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  t("rules.oneEntry"),
                  t("rules.freeEntry", { mode: isFree ? t("entryMode.FREE") : isPromo ? t("entryMode.PROMOTIONAL") : "" }),
                  t("rules.cryptoDraw"),
                  t("rules.publicVerify"),
                  t("rules.prizeEscrow"),
                ].map((rule, i) => (
                  <li key={i} style={{ display: "flex", gap: 8, fontSize: "0.88rem", color: "var(--ad-text-mid)" }}>
                    <CheckCircle2 size={16} color="var(--ad-success)" style={{ flexShrink: 0, marginTop: 2 }} />
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Right: entry card */}
          <div>
            <div className="ad-entry-card">
              <h3>{t("campaign.enterDraw")}</h3>

              <div>
                <div className="ad-entry-price">
                  {isFree || isPromo ? (
                    <span style={{ fontSize: "1.6rem", color: "var(--ad-success)", fontWeight: 900 }}>{t("campaign.freeEntry")}</span>
                  ) : (
                    <>
                      {(campaign.entry_price ?? 0).toLocaleString()}
                      <span>&nbsp;{t("currency")}</span>
                    </>
                  )}
                </div>
                {needsPayment && (
                  <div className="ad-alert ad-alert-warning" style={{ marginTop: 12 }}>
                    <Info size={16} />
                    <span style={{ fontSize: "0.82rem" }}>{t("campaign.paidEntryGate")}</span>
                  </div>
                )}
              </div>

              {!isLoggedIn && (
                <div className="ad-alert ad-alert-info">
                  <Info size={16} />
                  {t("campaign.loginRequired")}
                </div>
              )}

              {isFull && (
                <div className="ad-alert ad-alert-warning">
                  <AlertCircle size={16} />
                  {t("campaign.full")}
                </div>
              )}

              {errorMsg && (
                <div className="ad-alert ad-alert-error">
                  <AlertCircle size={16} />
                  {errorMsg}
                </div>
              )}

              <button
                type="button"
                className={`ad-btn ad-btn-primary ad-btn-full ad-btn-lg ${(entryMutation.isPending || payMutation.isPending) ? "ad-btn-loading" : ""}`}
                onClick={handleParticipate}
                disabled={!isActive || isFull || entryMutation.isPending || payMutation.isPending}
              >
                {entryMutation.isPending || payMutation.isPending
                  ? t("common.loading")
                  : !isLoggedIn
                    ? t("campaign.loginToEnter")
                    : isFull
                      ? t("campaign.full")
                      : !isActive
                        ? t(`status.${campaign.status}`, { defaultValue: campaign.status })
                        : needsPayment
                          ? t("campaign.payAndEnter")
                          : t("campaign.getEntry")}
              </button>

              {!isLoggedIn && (
                <Link to={`/login?next=${encodeURIComponent(`/campaigns/${id}`)}`} className="ad-btn ad-btn-outline-navy ad-btn-full">
                  {t("nav.login")}
                </Link>
              )}

              <div className="ad-divider" />
              <p className="ad-text-soft ad-text-xs" style={{ textAlign: "center" }}>
                {t("campaign.verifyNote")}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Success modal */}
      <Modal
        open={!!successEntry}
        onClose={() => setSuccessEntry(null)}
        title={t("campaign.entrySuccess")}
      >
        <div style={{ textAlign: "center", padding: "12px 0" }}>
          <CheckCircle2 size={52} color="var(--ad-success)" style={{ margin: "0 auto 16px" }} />
          <h3 style={{ marginBottom: 8 }}>{t("campaign.youreIn")}</h3>
          <p className="ad-text-soft" style={{ marginBottom: 20 }}>{t("campaign.entrySuccessDesc")}</p>
          <div style={{ background: "var(--ad-surface)", borderRadius: "var(--radius-md)", padding: "16px", marginBottom: 20 }}>
            <div className="ad-text-soft ad-text-sm">{t("campaign.yourEntryNumber")}</div>
            <div style={{ fontSize: "2rem", fontWeight: 900, color: "var(--ad-navy)", fontVariantNumeric: "tabular-nums" }}>
              #{successEntry?.entry_number}
            </div>
          </div>
          <Link to="/my-entries" className="ad-btn ad-btn-primary ad-btn-full" onClick={() => setSuccessEntry(null)}>
            {t("nav.myEntries")}
          </Link>
        </div>
      </Modal>
    </div>
  );
}
