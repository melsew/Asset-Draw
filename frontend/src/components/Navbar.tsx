import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Menu, X, Trophy, ShieldCheck } from "lucide-react";
import { LanguageToggle } from "./LanguageToggle";
import { useAuth } from "../hooks/useAuth";
import { logout } from "../services/api";

export function Navbar() {
  const { t } = useTranslation();
  const { user, isLoggedIn, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    signOut();
    navigate("/");
    setMenuOpen(false);
  }

  const navLinks = [
    { to: "/campaigns", label: t("nav.campaigns") },
    { to: "/results",   label: t("nav.results") },
    { to: "/verify",    label: t("nav.verify") },
  ];

  const isVendor = user?.role === "VENDOR";
  const isAdmin  = user?.role === "ADMIN" || user?.role === "SUPER_ADMIN";

  return (
    <header>
      <nav className="ad-navbar" aria-label={t("nav.ariaLabel")}>
        <div className="ad-navbar-inner">
          {/* Brand */}
          <Link to="/" className="ad-navbar-brand" aria-label={t("app.name")}>
            <span className="ad-navbar-brand-mark">A</span>
            <span>Asset<strong>Draw</strong></span>
          </Link>

          {/* Desktop links */}
          <div className="ad-navbar-links">
            {navLinks.map(({ to, label }) => (
              <NavLink key={to} to={to} className={({ isActive }) => isActive ? "active" : ""}>
                {label}
              </NavLink>
            ))}
            {isVendor && (
              <NavLink to="/vendor" className={({ isActive }) => isActive ? "active" : ""}>
                {t("nav.vendorDashboard")}
              </NavLink>
            )}
            {isAdmin && (
              <NavLink to="/admin" className={({ isActive }) => isActive ? "active" : ""}>
                <ShieldCheck size={15} style={{ marginRight: 4, verticalAlign: "middle" }} />
                {t("nav.admin")}
              </NavLink>
            )}
          </div>

          {/* Desktop actions */}
          <div className="ad-navbar-actions">
            <LanguageToggle />
            {isLoggedIn ? (
              <>
                <Link to="/my-entries" className="ad-btn ad-btn-outline ad-btn-sm">
                  <Trophy size={14} />
                  {t("nav.myEntries")}
                </Link>
                <button type="button" className="ad-btn ad-btn-primary ad-btn-sm" onClick={() => void handleLogout()}>
                  {t("nav.logout")}
                </button>
              </>
            ) : (
              <>
                <Link to="/login"    className="ad-btn ad-btn-outline ad-btn-sm">{t("nav.login")}</Link>
                <Link to="/register" className="ad-btn ad-btn-primary ad-btn-sm">{t("nav.register")}</Link>
              </>
            )}

            {/* Hamburger */}
            <button
              type="button"
              className="ad-navbar-hamburger"
              aria-label={menuOpen ? t("nav.closeMenu") : t("nav.openMenu")}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu */}
      <div className={`ad-mobile-menu ${menuOpen ? "open" : ""}`} role="navigation" aria-label={t("nav.mobileMenu")}>
        {navLinks.map(({ to, label }) => (
          <Link key={to} to={to} onClick={() => setMenuOpen(false)}>{label}</Link>
        ))}
        {isVendor && <Link to="/vendor" onClick={() => setMenuOpen(false)}>{t("nav.vendorDashboard")}</Link>}
        {isAdmin  && <Link to="/admin"  onClick={() => setMenuOpen(false)}>{t("nav.admin")}</Link>}
        {isLoggedIn && <Link to="/my-entries" onClick={() => setMenuOpen(false)}>{t("nav.myEntries")}</Link>}
        <div className="ad-mobile-menu-actions">
          {isLoggedIn ? (
            <button type="button" className="ad-btn ad-btn-primary ad-btn-sm" onClick={() => void handleLogout()}>
              {t("nav.logout")}
            </button>
          ) : (
            <>
              <Link to="/login"    className="ad-btn ad-btn-outline ad-btn-sm" onClick={() => setMenuOpen(false)}>{t("nav.login")}</Link>
              <Link to="/register" className="ad-btn ad-btn-primary ad-btn-sm" onClick={() => setMenuOpen(false)}>{t("nav.register")}</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
