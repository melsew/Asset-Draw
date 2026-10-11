import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlertCircle, ShieldCheck } from "lucide-react";
import { confirmStaffMfa, staffLogin, verifyStaffMfa } from "../services/api";
import { LanguageToggle } from "../components/LanguageToggle";

interface StaffAccessPageProps {
  setup?: boolean;
}

export function StaffAccessPage({ setup = false }: StaffAccessPageProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [challengeToken, setChallengeToken] = useState("");
  const [setupToken, setSetupToken] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStaffLogin(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await staffLogin(email.trim(), password);
      setChallengeToken(result.challenge_token);
      setPassword("");
      setStep("mfa");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("staffAccess.loginFailed"));
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaVerify(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await verifyStaffMfa(challengeToken, code);
      navigate("/admin", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("staffAccess.loginFailed"));
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaSetup(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await confirmStaffMfa(setupToken.trim(), code);
      setSetupToken("");
      setCode("");
      navigate("/staff/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("staffAccess.setupFailed"));
    } finally {
      setLoading(false);
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
          <ShieldCheck size={28} color="var(--ad-navy)" style={{ margin: "18px auto 0" }} />
          <h2>{setup ? t("staffAccess.setupTitle") : t("staffAccess.loginTitle")}</h2>
          <p className="subtitle">
            {setup
              ? t("staffAccess.setupSubtitle")
              : step === "mfa"
                ? t("staffAccess.mfaSubtitle")
                : t("staffAccess.loginSubtitle")}
          </p>
        </div>

        {error && (
          <div className="ad-alert ad-alert-error" role="alert" style={{ marginBottom: 18 }}>
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {setup ? (
          <form onSubmit={(event) => void handleMfaSetup(event)}>
            <p className="ad-text-soft ad-text-sm" style={{ marginBottom: 16 }}>
              {t("staffAccess.setupInstructions")}
            </p>
            <div className="ad-form-group">
              <label htmlFor="setup-token">{t("staffAccess.setupTokenLabel")}</label>
              <input
                id="setup-token"
                className="ad-input"
                value={setupToken}
                onChange={(event) => setSetupToken(event.target.value)}
                autoComplete="off"
                required
              />
            </div>
            <div className="ad-form-group">
              <label htmlFor="setup-code">{t("staffAccess.authenticatorCodeLabel")}</label>
              <input
                id="setup-code"
                className="ad-input"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                autoComplete="one-time-code"
                required
              />
            </div>
            <button type="submit" className="ad-btn ad-btn-primary ad-btn-full ad-btn-lg" disabled={loading}>
              {loading ? t("common.loading") : t("staffAccess.enableMfa")}
            </button>
          </form>
        ) : step === "credentials" ? (
          <form onSubmit={(event) => void handleStaffLogin(event)}>
            <div className="ad-form-group">
              <label htmlFor="staff-email">{t("staffAccess.emailLabel")}</label>
              <input
                id="staff-email"
                className="ad-input"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div className="ad-form-group">
              <label htmlFor="staff-password">{t("auth.passwordLabel")}</label>
              <input
                id="staff-password"
                className="ad-input"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button type="submit" className="ad-btn ad-btn-primary ad-btn-full ad-btn-lg" disabled={loading}>
              {loading ? t("common.loading") : t("staffAccess.continue")}
            </button>
          </form>
        ) : (
          <form onSubmit={(event) => void handleMfaVerify(event)}>
            <div className="ad-form-group">
              <label htmlFor="staff-mfa-code">{t("staffAccess.authenticatorCodeLabel")}</label>
              <input
                id="staff-mfa-code"
                className="ad-input"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                autoComplete="one-time-code"
                required
              />
            </div>
            <button type="submit" className="ad-btn ad-btn-primary ad-btn-full ad-btn-lg" disabled={loading}>
              {loading ? t("common.loading") : t("staffAccess.signIn")}
            </button>
            <button
              type="button"
              className="ad-btn ad-btn-ghost ad-btn-full"
              style={{ marginTop: 10 }}
              onClick={() => {
                setCode("");
                setChallengeToken("");
                setStep("credentials");
              }}
            >
              {t("staffAccess.back")}
            </button>
          </form>
        )}

        <div className="ad-auth-footer">
          <Link to="/login">{t("staffAccess.participantLogin")}</Link>
        </div>
        <div style={{ marginTop: 16, display: "flex", justifyContent: "center" }}>
          <LanguageToggle />
        </div>
      </div>
    </div>
  );
}
