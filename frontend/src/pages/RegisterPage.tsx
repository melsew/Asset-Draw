import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Phone, AlertCircle, CheckCircle2 } from "lucide-react";
import { requestOtp, verifyOtp } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { LanguageToggle } from "../components/LanguageToggle";

type Step = "phone" | "otp" | "done";

export function RegisterPage() {
  const { t } = useTranslation();
  const { refresh } = useAuth();
  const navigate = useNavigate();

  const [step,        setStep]        = useState<Step>("phone");
  const [phone,       setPhone]       = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [developmentCode, setDevelopmentCode] = useState<string | null>(null);
  const [otp,         setOtp]         = useState(["", "", "", "", "", ""]);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState<string | null>(null);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await requestOtp(phone);
      setChallengeId(result.challenge_id);
      setDevelopmentCode(result.development_code ?? null);
      setStep("otp");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.registerError"));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    const code = otp.join("");
    if (code.length < 6) { setError(t("auth.otpRequired")); return; }
    setError(null);
    setLoading(true);
    try {
      await verifyOtp(challengeId, code);
      await refresh();
      setStep("done");
      setTimeout(() => navigate("/"), 1800);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.otpError"));
    } finally {
      setLoading(false);
    }
  }

  function handleOtpChange(index: number, val: string) {
    const digit = val.replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[index] = digit;
    setOtp(next);
    if (digit && index < 5) {
      (document.getElementById(`otp-${index + 1}`) as HTMLInputElement | null)?.focus();
    }
  }

  function handleOtpKey(index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      (document.getElementById(`otp-${index - 1}`) as HTMLInputElement | null)?.focus();
    }
  }

  return (
    <div className="ad-auth-page">
      <div className="ad-auth-card">
        <div className="ad-auth-card-header">
          <Link to="/" className="ad-auth-brand">
            <span className="ad-auth-brand-mark">A</span>
            <span>Asset<strong>Draw</strong></span>
          </Link>
          {step === "phone"    && <><h2>{t("auth.registerTitle")}</h2><p className="subtitle">{t("auth.registerSubtitle")}</p></>}
          {step === "otp"      && <><h2>{t("auth.verifyTitle")}</h2><p className="subtitle">{t("auth.verifySubtitle", { phone })}</p></>}
          {step === "done"     && <><h2>{t("auth.successTitle")}</h2><p className="subtitle">{t("auth.successSubtitle")}</p></>}
        </div>

        {step === "done" ? (
          <div style={{ textAlign: "center", padding: "24px 0" }}>
            <CheckCircle2 size={60} color="var(--ad-success)" style={{ margin: "0 auto 16px" }} />
            <p>{t("auth.redirecting")}</p>
          </div>
        ) : (
          <>
            {error && (
              <div className="ad-alert ad-alert-error" style={{ marginBottom: 18 }}>
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            {step === "phone" && (
              <form onSubmit={(e) => void handleRegister(e)}>
                <div className="ad-form-group">
                  <label htmlFor="reg-phone">{t("auth.phoneLabel")}</label>
                  <div className="ad-input-group">
                    <Phone size={16} className="ad-input-prefix" style={{ left: 14 }} />
                    <input id="reg-phone" type="tel" className="ad-input" placeholder={t("auth.phonePlaceholder")} value={phone} onChange={(e) => setPhone(e.target.value)} autoComplete="tel" required />
                  </div>
                </div>
                <button type="submit" className={`ad-btn ad-btn-primary ad-btn-full ad-btn-lg ${loading ? "ad-btn-loading" : ""}`} disabled={loading}>
                  {loading ? t("common.loading") : t("auth.registerBtn")}
                </button>
              </form>
            )}

            {step === "otp" && (
              <form onSubmit={(e) => void handleVerifyOtp(e)}>
                <div className="ad-form-group">
                  <label>{t("auth.otpLabel")}</label>
                  <div className="ad-otp-grid">
                    {otp.map((val, i) => (
                      <input
                        key={i}
                        id={`otp-${i}`}
                        type="text"
                        inputMode="numeric"
                        className="ad-otp-input"
                        maxLength={1}
                        value={val}
                        onChange={(e) => handleOtpChange(i, e.target.value)}
                        onKeyDown={(e) => handleOtpKey(i, e)}
                      />
                    ))}
                  </div>
                </div>
                {developmentCode && (
                  <div className="ad-alert ad-alert-info" role="status" style={{ marginBottom: 18 }}>
                    {t("auth.developmentOtpCode", { code: developmentCode })}
                  </div>
                )}
                <button type="submit" className={`ad-btn ad-btn-primary ad-btn-full ad-btn-lg ${loading ? "ad-btn-loading" : ""}`} disabled={loading}>
                  {loading ? t("common.loading") : t("auth.verifyBtn")}
                </button>
                  <button type="button" className="ad-btn ad-btn-ghost ad-btn-full" style={{ marginTop: 10 }} onClick={() => setStep("phone")}>
                  ← {t("auth.backToRegister")}
                </button>
              </form>
            )}

            <div className="ad-auth-footer">
              {t("auth.hasAccount")}&nbsp;<Link to="/login">{t("auth.loginLink")}</Link>
            </div>
          </>
        )}

        <div style={{ marginTop: 16, display: "flex", justifyContent: "center" }}>
          <LanguageToggle />
        </div>
      </div>
    </div>
  );
}
