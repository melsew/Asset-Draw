import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Phone, AlertCircle } from "lucide-react";
import { requestOtp, verifyOtp } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { LanguageToggle } from "../components/LanguageToggle";

export function LoginPage() {
  const { t } = useTranslation();
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = searchParams.get("next") ?? "/";

  const [phone,    setPhone]    = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [developmentCode, setDevelopmentCode] = useState<string | null>(null);
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  async function handleRequestOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await requestOtp(phone);
      setChallengeId(result.challenge_id);
      setDevelopmentCode(result.development_code ?? null);
      setStep("otp");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await verifyOtp(challengeId, otp.join(""));
      await refresh();
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.loginError"));
    } finally {
      setLoading(false);
    }
  }

  function handleOtpChange(index: number, value: string) {
    const digit = value.replace(/\D/g, "").slice(-1);
    const nextOtp = [...otp];
    nextOtp[index] = digit;
    setOtp(nextOtp);
    if (digit && index < 5) {
      (document.getElementById(`login-otp-${index + 1}`) as HTMLInputElement | null)?.focus();
    }
  }

  function handleOtpKey(index: number, event: React.KeyboardEvent) {
    if (event.key === "Backspace" && !otp[index] && index > 0) {
      (document.getElementById(`login-otp-${index - 1}`) as HTMLInputElement | null)?.focus();
    }
  }

  return (
    <div className="ad-auth-page">
      <div className="ad-auth-card">
        {/* Header */}
        <div className="ad-auth-card-header">
          <Link to="/" className="ad-auth-brand">
            <span className="ad-auth-brand-mark">A</span>
            <span>Asset<strong>Draw</strong></span>
          </Link>
          <h2>{step === "phone" ? t("auth.loginTitle") : t("auth.verifyTitle")}</h2>
          <p className="subtitle">{step === "phone" ? t("auth.loginSubtitle") : t("auth.verifySubtitle", { phone })}</p>
        </div>

        {error && (
          <div className="ad-alert ad-alert-error" style={{ marginBottom: 18 }}>
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {step === "phone" ? (
          <form onSubmit={(event) => void handleRequestOtp(event)}>
            <div className="ad-form-group">
              <label htmlFor="phone">{t("auth.phoneLabel")}</label>
              <div className="ad-input-group">
                <Phone size={16} className="ad-input-prefix" style={{ left: 14 }} />
                <input
                  id="phone"
                  type="tel"
                  className="ad-input"
                  placeholder={t("auth.phonePlaceholder")}
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  autoComplete="tel"
                  required
                />
              </div>
            </div>
            <button type="submit" className={`ad-btn ad-btn-primary ad-btn-full ad-btn-lg ${loading ? "ad-btn-loading" : ""}`} disabled={loading}>
              {loading ? t("common.loading") : t("auth.loginBtn")}
            </button>
          </form>
        ) : (
          <form onSubmit={(event) => void handleVerifyOtp(event)}>
            <div className="ad-form-group">
              <label>{t("auth.otpLabel")}</label>
              <div className="ad-otp-grid">
                {otp.map((value, index) => (
                  <input
                    key={index}
                    id={`login-otp-${index}`}
                    type="text"
                    inputMode="numeric"
                    className="ad-otp-input"
                    maxLength={1}
                    value={value}
                    onChange={(event) => handleOtpChange(index, event.target.value)}
                    onKeyDown={(event) => handleOtpKey(index, event)}
                    required
                  />
                ))}
              </div>
            </div>
            {developmentCode && (
              <div className="ad-alert ad-alert-info" role="status" style={{ marginBottom: 18 }}>
                {t("auth.developmentOtpCode", { code: developmentCode })}
              </div>
            )}
            <button type="submit" className={`ad-btn ad-btn-primary ad-btn-full ad-btn-lg ${loading ? "ad-btn-loading" : ""}`} disabled={loading || otp.join("").length !== 6}>
              {loading ? t("common.loading") : t("auth.verifyBtn")}
            </button>
            <button type="button" className="ad-btn ad-btn-ghost ad-btn-full" style={{ marginTop: 10 }} onClick={() => setStep("phone")}>
              ← {t("auth.backToRegister")}
            </button>
          </form>
        )}

        <div className="ad-auth-footer">
          {t("auth.noAccount")}&nbsp;
          <Link to="/register">{t("auth.registerLink")}</Link>
          <span aria-hidden="true"> · </span>
          <Link to="/staff/login">{t("auth.staffLoginLink")}</Link>
        </div>
        <div style={{ marginTop: 16, display: "flex", justifyContent: "center" }}>
          <LanguageToggle />
        </div>
      </div>
    </div>
  );
}
