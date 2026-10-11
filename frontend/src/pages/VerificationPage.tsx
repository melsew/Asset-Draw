import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Shield, CheckCircle2, XCircle, Search, Copy, AlertCircle } from "lucide-react";
import { fetchDrawVerification } from "../services/api";
import { Spinner } from "../components/Spinner";

function HashBox({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    void navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--ad-text-soft)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <div className="ad-verify-hash" style={{ flex: 1 }}>{value}</div>
        <button type="button" className="ad-btn ad-btn-ghost ad-btn-sm" onClick={copy} title="Copy">
          <Copy size={14} />
          {copied ? "✓" : ""}
        </button>
      </div>
    </div>
  );
}

function VerificationResult({ drawId }: { drawId: string }) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["verify", drawId],
    queryFn: () => fetchDrawVerification(drawId),
    enabled: !!drawId,
    retry: 1,
  });

  if (isLoading) return <Spinner center />;
  if (isError) return (
    <div className="ad-alert ad-alert-error">
      <AlertCircle size={16} />
      {t("verify.notFound")}
    </div>
  );
  if (!data) return null;

  return (
    <div>
      {/* Pass/Fail */}
      <div className={`ad-verify-result ${data.verified ? "pass" : "fail"}`} style={{ marginBottom: 24 }}>
        {data.verified
          ? <><CheckCircle2 size={24} /> {t("verify.pass")}</>
          : <><XCircle size={24} />      {t("verify.fail")}</>}
      </div>

      {/* Summary */}
      <div className="ad-verify-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 14 }}>{t("verify.summary")}</h3>
        <div className="ad-grid-2" style={{ gap: 12 }}>
          {[
            { k: t("verify.campaign"),     v: data.campaign_title },
            { k: t("verify.drawId"),       v: data.draw_id },
            { k: t("verify.algorithm"),    v: data.algorithm },
            { k: t("verify.totalEntries"), v: String(data.total_entries) },
            { k: t("verify.winnerIndex"),  v: String(data.winner_index) },
            { k: t("verify.winnerEntry"),  v: `#${data.winning_entry_number}` },
            { k: t("verify.lockedAt"),     v: new Date(data.locked_at).toLocaleString() },
            { k: t("verify.completedAt"),  v: new Date(data.completed_at).toLocaleString() },
          ].map(({ k, v }) => (
            <div key={k}>
              <div className="ad-text-soft ad-text-xs" style={{ marginBottom: 2 }}>{k}</div>
              <div style={{ fontWeight: 600, color: "var(--ad-navy)", fontSize: "0.88rem", wordBreak: "break-all" }}>{v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Cryptographic evidence */}
      <div className="ad-verify-card">
        <h3 style={{ marginBottom: 16 }}>{t("verify.evidence")}</h3>
        <HashBox label={t("verify.poolHash")}       value={data.pool_hash} />
        <HashBox label={t("verify.seedCommitment")} value={data.seed_commitment} />
        {data.seed && <HashBox label={t("verify.revealedSeed")} value={data.seed} />}
        <HashBox label={t("verify.canonicalMsg")}   value={data.canonical_message} />
      </div>

      {/* How to verify independently */}
      <div className="ad-alert ad-alert-info" style={{ marginTop: 20 }}>
        <Shield size={16} />
        <span style={{ fontSize: "0.82rem" }}>{t("verify.independentNote")}</span>
      </div>
    </div>
  );
}

export function VerificationPage() {
  const { t } = useTranslation();
  const { drawId: paramDrawId } = useParams();
  const navigate = useNavigate();

  const [inputId, setInputId] = useState(paramDrawId ?? "");
  const [activeId, setActiveId] = useState(paramDrawId ?? "");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = inputId.trim();
    if (!trimmed) return;
    setActiveId(trimmed);
    navigate(`/verify/${trimmed}`, { replace: true });
  }

  return (
    <div className="ad-verify-page">
      <div className="ad-container">
        {/* Hero */}
        <div className="ad-verify-hero">
          <span className="ad-eyebrow">{t("verify.eyebrow")}</span>
          <h1 style={{ marginTop: 10 }}>{t("verify.title")}</h1>
          <p style={{ marginTop: 12 }}>{t("verify.desc")}</p>
        </div>

        {/* Search */}
        <div className="ad-verify-card" style={{ marginBottom: 32 }}>
          <h3 style={{ marginBottom: 14 }}>{t("verify.lookupTitle")}</h3>
          <form onSubmit={handleSearch} style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <div className="ad-search-wrap" style={{ flex: 1 }}>
              <Search size={16} />
              <input
                type="text"
                className="ad-input"
                placeholder={t("verify.drawIdPlaceholder")}
                value={inputId}
                onChange={(e) => setInputId(e.target.value)}
              />
            </div>
            <button type="submit" className="ad-btn ad-btn-primary">
              <Shield size={16} />
              {t("verify.btn")}
            </button>
          </form>
        </div>

        {/* Result */}
        {activeId ? (
          <VerificationResult key={activeId} drawId={activeId} />
        ) : (
          <div className="ad-empty">
            <Shield size={52} color="var(--ad-text-soft)" style={{ margin: "0 auto" }} />
            <h3>{t("verify.empty")}</h3>
            <p>{t("verify.emptyDesc")}</p>
          </div>
        )}

        {/* Protocol explainer */}
        <div className="ad-verify-card" style={{ marginTop: 40 }}>
          <h3 style={{ marginBottom: 16 }}>{t("verify.howTitle")}</h3>
          <ol style={{ display: "flex", flexDirection: "column", gap: 14, paddingLeft: 20 }}>
            {["verify.step1", "verify.step2", "verify.step3", "verify.step4", "verify.step5"].map((key) => (
              <li key={key} style={{ fontSize: "0.88rem", color: "var(--ad-text-mid)", lineHeight: 1.6 }}>
                {t(key)}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
