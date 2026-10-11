import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Globe, Send, BriefcaseBusiness, MessageCircle, Play } from "lucide-react";

export function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="ad-footer">
      <div className="ad-container">
        <div className="ad-footer-grid">
          {/* Brand */}
          <div className="ad-footer-brand">
            <Link to="/" className="ad-navbar-brand" aria-label={t("app.name")}>
              <span className="ad-navbar-brand-mark">A</span>
              <span>Asset<strong>Draw</strong></span>
            </Link>
            <p>{t("footer.about")}</p>
            <div className="ad-social-links">
              <a href="https://facebook.com" target="_blank" rel="noreferrer" className="ad-social-link" aria-label="Facebook"><Globe size={16} /></a>
              <a href="https://t.me"         target="_blank" rel="noreferrer" className="ad-social-link" aria-label="Telegram"><Send size={16} /></a>
              <a href="https://linkedin.com" target="_blank" rel="noreferrer" className="ad-social-link" aria-label="LinkedIn"><BriefcaseBusiness size={16} /></a>
              <a href="https://twitter.com"  target="_blank" rel="noreferrer" className="ad-social-link" aria-label="Twitter/X"><MessageCircle size={16} /></a>
              <a href="https://youtube.com"  target="_blank" rel="noreferrer" className="ad-social-link" aria-label="YouTube"><Play size={16} /></a>
            </div>
          </div>

          {/* Explore */}
          <div className="ad-footer-col">
            <h4>{t("footer.explore")}</h4>
            <Link to="/campaigns">{t("nav.campaigns")}</Link>
            <Link to="/results">{t("nav.results")}</Link>
            <Link to="/verify">{t("nav.verify")}</Link>
          </div>

          {/* For Business */}
          <div className="ad-footer-col">
            <h4>{t("footer.forBusiness")}</h4>
            <Link to="/vendor/register">{t("footer.becomeVendor")}</Link>
            <Link to="/vendor">{t("footer.vendorPortal")}</Link>
          </div>

          {/* Legal */}
          <div className="ad-footer-col">
            <h4>{t("footer.legal")}</h4>
            <Link to="/terms">{t("footer.terms")}</Link>
            <Link to="/privacy">{t("footer.privacy")}</Link>
          </div>
        </div>

        <div className="ad-footer-bottom">
          <p>{t("footer.copyright", { year: new Date().getFullYear() })}</p>
          <p>{t("footer.tagline")}</p>
        </div>
      </div>
    </footer>
  );
}
