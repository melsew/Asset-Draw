import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", padding: "40px 20px" }}>
        <div style={{ fontSize: "6rem", fontWeight: 900, color: "var(--ad-navy)", lineHeight: 1 }}>404</div>
        <h2 style={{ marginTop: 16 }}>{t("notFound.title")}</h2>
        <p className="ad-text-soft" style={{ margin: "12px 0 28px" }}>{t("notFound.desc")}</p>
        <Link to="/" className="ad-btn ad-btn-primary ad-btn-lg">{t("notFound.back")}</Link>
      </div>
    </div>
  );
}
