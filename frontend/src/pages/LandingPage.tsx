import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Car, Laptop, Package, Plane, Refrigerator,
  Smartphone, Tablet, Tv, WashingMachine,
  Shield, TrendingUp, Users, Award,
  ChevronLeft, ChevronRight, CheckCircle2
} from "lucide-react";
import { useCampaigns } from "../hooks/useCampaigns";
import { Countdown } from "../components/Countdown";
import { ProgressBar } from "../components/ProgressBar";
import { PrizeCategoryCard } from "../components/PrizeCategoryCard";
import { Badge, entryModeBadge, statusBadge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import type { Campaign } from "../types/campaign";

const HERO_SLIDES = [
  {
    id: "1",
    bg: "linear-gradient(135deg, #001f5b 0%, #0d3a8e 60%, #0f5598 100%)",
    eyebrowKey: "hero.slide1.eyebrow",
    titleKey:   "hero.slide1.title",
    subKey:     "hero.slide1.sub",
  },
  {
    id: "2",
    bg: "linear-gradient(135deg, #0a2a1a 0%, #0d5a3a 60%, #107545 100%)",
    eyebrowKey: "hero.slide2.eyebrow",
    titleKey:   "hero.slide2.title",
    subKey:     "hero.slide2.sub",
  },
  {
    id: "3",
    bg: "linear-gradient(135deg, #3b1e00 0%, #7a4b00 60%, #da9100 100%)",
    eyebrowKey: "hero.slide3.eyebrow",
    titleKey:   "hero.slide3.title",
    subKey:     "hero.slide3.sub",
  },
];

const PRIZE_CATEGORIES = [
  { id: "car",            icon: Car, art: buildCategoryArt("car") },
  { id: "smartphone",     icon: Smartphone, art: buildCategoryArt("smartphone") },
  { id: "laptop",         icon: Laptop, art: buildCategoryArt("laptop") },
  { id: "tablet",         icon: Tablet, art: buildCategoryArt("tablet") },
  { id: "tv",             icon: Tv, art: buildCategoryArt("tv") },
  { id: "refrigerator",   icon: Refrigerator, art: buildCategoryArt("refrigerator") },
  { id: "washingMachine", icon: WashingMachine, art: buildCategoryArt("washingMachine") },
  { id: "travel",         icon: Plane, art: buildCategoryArt("travel") },
  { id: "other",          icon: Package, art: buildCategoryArt("other") },
] as const;

function buildCategoryArt(category: string) {
  const svgMap: Record<string, string> = {
    car: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Car prize illustration">
        <defs>
          <linearGradient id="car-bg" x1="0" x2="1">
            <stop offset="0%" stop-color="#edf6ff"/>
            <stop offset="100%" stop-color="#dceaf8"/>
          </linearGradient>
        </defs>
        <rect width="240" height="160" rx="18" fill="url(#car-bg)"/>
        <path d="M30 94 L60 66 H150 L177 94 H188 C201 94 212 105 212 118 V122 H28 V118 C28 105 39 94 52 94 Z" fill="#0d3b8c"/>
        <path d="M67 70 L95 52 H153 L176 70" stroke="#e7b74e" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <circle cx="76" cy="124" r="18" fill="#102d5d"/>
        <circle cx="76" cy="124" r="8" fill="#e8f4ff"/>
        <circle cx="169" cy="124" r="18" fill="#102d5d"/>
        <circle cx="169" cy="124" r="8" fill="#e8f4ff"/>
        <rect x="90" y="82" width="52" height="20" rx="5" fill="#f5d77a"/>
        <path d="M102 82 V64 H150" stroke="#f5d77a" stroke-width="6" stroke-linecap="round" fill="none"/>
      </svg>
    `,
    smartphone: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Smartphone prize illustration">
        <rect width="240" height="160" rx="18" fill="#edf2ff"/>
        <rect x="82" y="20" width="76" height="118" rx="14" fill="#102d5d"/>
        <rect x="92" y="34" width="56" height="88" rx="8" fill="#1d4ea3"/>
        <rect x="102" y="44" width="36" height="54" rx="8" fill="#dbe7ff"/>
        <circle cx="120" cy="112" r="5" fill="#e7b74e"/>
        <path d="M96 82 H144" stroke="#f5d77a" stroke-width="4" stroke-linecap="round"/>
      </svg>
    `,
    laptop: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Laptop prize illustration">
        <rect width="240" height="160" rx="18" fill="#eaf7ff"/>
        <rect x="38" y="48" width="164" height="86" rx="10" fill="#102d5d"/>
        <rect x="52" y="60" width="136" height="62" rx="8" fill="#dfefff"/>
        <path d="M20 130 H220 L198 148 H42 Z" fill="#0d3b8c"/>
        <circle cx="123" cy="92" r="18" fill="#e7b74e" opacity="0.9"/>
      </svg>
    `,
    tablet: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Tablet prize illustration">
        <rect width="240" height="160" rx="18" fill="#eef6ff"/>
        <rect x="60" y="26" width="120" height="108" rx="16" fill="#102d5d"/>
        <rect x="72" y="38" width="96" height="84" rx="10" fill="#dfefff"/>
        <circle cx="120" cy="112" r="5" fill="#e7b74e"/>
      </svg>
    `,
    tv: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="TV prize illustration">
        <rect width="240" height="160" rx="18" fill="#edf4ff"/>
        <rect x="42" y="32" width="156" height="90" rx="12" fill="#0d3b8c"/>
        <rect x="58" y="46" width="124" height="62" rx="8" fill="#dfefff"/>
        <path d="M82 126 H158" stroke="#102d5d" stroke-width="8" stroke-linecap="round"/>
        <path d="M120 126 V146" stroke="#102d5d" stroke-width="8" stroke-linecap="round"/>
        <circle cx="120" cy="78" r="18" fill="#f5d77a"/>
      </svg>
    `,
    refrigerator: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Refrigerator prize illustration">
        <rect width="240" height="160" rx="18" fill="#edf7ff"/>
        <rect x="72" y="18" width="96" height="122" rx="14" fill="#102d5d"/>
        <rect x="82" y="30" width="76" height="22" rx="6" fill="#e7b74e"/>
        <rect x="82" y="66" width="76" height="52" rx="8" fill="#dfefff"/>
        <path d="M100 66 V118" stroke="#102d5d" stroke-width="3" opacity="0.35"/>
        <path d="M138 66 V118" stroke="#102d5d" stroke-width="3" opacity="0.35"/>
      </svg>
    `,
    washingMachine: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Washing machine prize illustration">
        <rect width="240" height="160" rx="18" fill="#edf6ff"/>
        <rect x="62" y="22" width="116" height="116" rx="18" fill="#0d3b8c"/>
        <circle cx="120" cy="80" r="30" fill="#dfefff"/>
        <circle cx="120" cy="80" r="18" fill="#e7b74e"/>
        <path d="M92 52 H148" stroke="#e7b74e" stroke-width="6" stroke-linecap="round"/>
        <path d="M98 110 H142" stroke="#e7b74e" stroke-width="6" stroke-linecap="round"/>
      </svg>
    `,
    travel: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Travel prize illustration">
        <rect width="240" height="160" rx="18" fill="#ebf9f4"/>
        <path d="M52 92 L104 50 L140 58 L188 46 L188 110 L148 118 L104 112 L52 92 Z" fill="#0d5a3a"/>
        <path d="M76 92 L122 66 L136 74 L172 60" stroke="#d4f2e5" stroke-width="8" stroke-linecap="round" fill="none"/>
        <circle cx="92" cy="120" r="10" fill="#102d5d"/>
        <circle cx="164" cy="118" r="10" fill="#102d5d"/>
      </svg>
    `,
    other: `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160" role="img" aria-label="Other prize illustration">
        <rect width="240" height="160" rx="18" fill="#f7f3ff"/>
        <path d="M110 28 L162 48 L162 102 L110 124 L58 102 L58 48 Z" fill="#102d5d"/>
        <path d="M110 28 V124" stroke="#e7b74e" stroke-width="6"/>
        <path d="M58 48 L110 68 L162 48" stroke="#e7b74e" stroke-width="6" fill="none"/>
        <path d="M82 80 H138" stroke="#dfefff" stroke-width="6" stroke-linecap="round"/>
      </svg>
    `,
  };

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svgMap[category] ?? svgMap.other)}`;
}

const STATS = [
  { key: "stats.campaigns", value: "50+" },
  { key: "stats.vendors",   value: "20+" },
  { key: "stats.entries",   value: "10K+" },
  { key: "stats.winners",   value: "100+" },
];

const HOW_STEPS = [
  { icon: Users,        key: "how.step1" },
  { icon: Shield,       key: "how.step2" },
  { icon: TrendingUp,   key: "how.step3" },
  { icon: CheckCircle2, key: "how.step4" },
];

function formatDate(value: string, lang: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(lang === "am" ? "am-ET" : "en-ET", {
    dateStyle: "medium",
    timeZone: "Africa/Addis_Ababa",
  }).format(date);
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "am";
  const navigate = useNavigate();

  return (
    <article className="ad-campaign-card">
      <div className="ad-campaign-card-img">
        {campaign.prize_image_url ? (
          <img src={campaign.prize_image_url} alt={campaign.prize} loading="lazy" />
        ) : (
          <div style={{ height: "100%", background: "linear-gradient(135deg, #001f5b 0%, #0484c0 100%)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Award size={64} color="rgba(255,255,255,0.25)" />
          </div>
        )}
        <div className="ad-campaign-card-badge">
          <Badge variant={entryModeBadge(campaign.entry_mode)}>
            {t(`entryMode.${campaign.entry_mode}`, { defaultValue: campaign.entry_mode })}
          </Badge>
          <Badge variant={statusBadge(campaign.status)}>
            {t(`status.${campaign.status}`, { defaultValue: campaign.status })}
          </Badge>
        </div>
        <button
          type="button"
          className="ad-campaign-card-action-btn"
          onClick={() => navigate(`/campaigns/${campaign.id}`)}
        >
          {t("campaign.participate")}
        </button>
        <div className="ad-campaign-card-prize-overlay">
          <span>{campaign.vendor}</span>
          <strong>{campaign.prize}</strong>
        </div>
      </div>

      <div className="ad-campaign-card-body">
        <h3 className="ad-campaign-card-title">{campaign.title}</h3>
        <ProgressBar current={campaign.entries} max={campaign.max_entries} />
        <Countdown drawAt={campaign.draw_at} status={campaign.status} />
        <div className="ad-campaign-card-footer">
          <span className="ad-text-soft ad-text-sm">
            {t("campaign.closes", { date: formatDate(campaign.ends_at, lang) })}
          </span>
          <Link to={`/campaigns/${campaign.id}`} className="ad-section-link">
            {t("campaign.details")} →
          </Link>
        </div>
      </div>
    </article>
  );
}

export function LandingPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "am";
  const { data: campaigns, isLoading, isError } = useCampaigns({ status: "ACTIVE" });
  const safeCampaigns = Array.isArray(campaigns) ? campaigns : [];

  const [slide, setSlide] = useState(0);
  const navigate = useNavigate();

  // Auto-advance hero
  useEffect(() => {
    const id = setInterval(() => setSlide((s) => (s + 1) % HERO_SLIDES.length), 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      {/* ── Hero Carousel ─────────────────────────────── */}
      <section className="ad-hero" aria-label={t("hero.ariaLabel")}>
        <div
          className="ad-hero-slides"
          style={{ transform: `translateX(-${slide * 100}%)` }}
          aria-live="polite"
        >
          {HERO_SLIDES.map((s) => (
            <div key={s.id} className="ad-hero-slide" style={{ background: s.bg }} />
          ))}
        </div>

        <div className="ad-hero-content">
          <span className="ad-hero-eyebrow">
            {t(HERO_SLIDES[slide].eyebrowKey)}
          </span>
          <h1>{t(HERO_SLIDES[slide].titleKey)}</h1>
          <p className="ad-hero-sub">{t(HERO_SLIDES[slide].subKey)}</p>
          <div className="ad-hero-actions">
            <Link to="/campaigns" className="ad-btn ad-btn-primary ad-btn-xl">
              {t("hero.browseCampaigns")}
            </Link>
            <Link to="/verify" className="ad-btn ad-btn-outline ad-btn-xl">
              {t("hero.verifyDraw")}
            </Link>
          </div>
        </div>

        {/* Prev/Next */}
        <button
          type="button"
          className="ad-hero-nav ad-hero-nav-prev"
          onClick={() => setSlide((s) => (s - 1 + HERO_SLIDES.length) % HERO_SLIDES.length)}
          aria-label={t("hero.prev")}
        >
          <ChevronLeft size={22} />
        </button>
        <button
          type="button"
          className="ad-hero-nav ad-hero-nav-next"
          onClick={() => setSlide((s) => (s + 1) % HERO_SLIDES.length)}
          aria-label={t("hero.next")}
        >
          <ChevronRight size={22} />
        </button>

        {/* Dots */}
        <div className="ad-hero-dots">
          {HERO_SLIDES.map((s, i) => (
            <button
              key={s.id}
              type="button"
              className={`ad-hero-dot ${i === slide ? "active" : ""}`}
              onClick={() => setSlide(i)}
              aria-label={`Slide ${i + 1}`}
            />
          ))}
        </div>
      </section>

      {/* ── Stats ─────────────────────────────────────── */}
      <section className="ad-stats" aria-label={t("stats.ariaLabel")}>
        <div className="ad-container">
          <div className="ad-stats-grid">
            {STATS.map(({ key, value }) => (
              <div key={key} className="ad-stat-item">
                <h3>{value}</h3>
                <p>{t(key)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Active Campaigns ──────────────────────────── */}
      <section className="ad-campaigns-section ad-section" id="campaigns" aria-labelledby="campaigns-heading">
        <div className="ad-container">
          <div className="ad-section-header">
            <div className="ad-section-header-left">
              <span className="ad-eyebrow">{t("campaigns.eyebrow")}</span>
              <h2 id="campaigns-heading">{t("campaigns.title")}</h2>
            </div>
            <Link to="/campaigns" className="ad-section-link">{t("campaigns.viewAll")} ↗</Link>
          </div>

          {isLoading ? (
            <Spinner center />
          ) : isError ? (
            <div className="ad-alert ad-alert-error">{t("campaigns.loadError")}</div>
          ) : safeCampaigns.length === 0 ? (
            <div className="ad-empty">
              <span className="ad-empty-icon">🎁</span>
              <h3>{t("campaigns.empty")}</h3>
              <p>{t("campaigns.emptyDesc")}</p>
            </div>
          ) : (
            <div className="ad-campaign-grid">
              {safeCampaigns.slice(0, 6).map((c) => (
                <CampaignCard key={c.id} campaign={c} />
              ))}
            </div>
          )}

          {safeCampaigns.length > 0 && (
            <div style={{ textAlign: "center", marginTop: 36 }}>
              <Link to="/campaigns" className="ad-btn ad-btn-outline-navy ad-btn-lg">
                {t("campaigns.viewAll")} →
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* ── Prize Categories ──────────────────────────── */}
      <section className="ad-prize-categories ad-section-sm" aria-labelledby="categories-heading">
        <div className="ad-container">
          <div className="ad-section-header">
            <div className="ad-section-header-left">
              <span className="ad-eyebrow">{t("categories.eyebrow")}</span>
              <h2 id="categories-heading">{t("categories.title")}</h2>
            </div>
          </div>
          <div className="ad-prize-grid">
            {PRIZE_CATEGORIES.map(({ id, icon }) => (
              <PrizeCategoryCard
                key={id}
                icon={icon}
                title={t(`categories.items.${id}`)}
                onClick={() => navigate(`/campaigns?category=${id}`)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ──────────────────────────────── */}
      <section className="ad-how-section ad-section" aria-labelledby="how-heading">
        <div className="ad-container">
          <div className="ad-section-header">
            <div className="ad-section-header-left">
              <span className="ad-eyebrow">{t("how.eyebrow")}</span>
              <h2 id="how-heading">{t("how.title")}</h2>
            </div>
            <Link to="/verify" className="ad-section-link">{t("how.verifyLink")} ↗</Link>
          </div>
          <div className="ad-steps-grid">
            {HOW_STEPS.map(({ icon: Icon, key }, i) => (
              <div key={key} className="ad-step">
                <div className="ad-step-num">{String(i + 1).padStart(2, "0")}</div>
                <Icon size={28} color="var(--ad-gold)" />
                <h3>{t(`${key}.title`)}</h3>
                <p>{t(`${key}.desc`)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Vendor CTA ────────────────────────────────── */}
      <section className="ad-vendor-strip" aria-labelledby="vendor-heading">
        <div className="ad-container">
          <div className="ad-vendor-strip-inner">
            <div>
              <h2 id="vendor-heading">{t("vendor.ctaTitle")}</h2>
              <p>{t("vendor.ctaDesc")}</p>
            </div>
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <Link to="/vendor/register" className="ad-btn ad-btn-primary ad-btn-lg">
                {t("vendor.ctaBtn")}
              </Link>
              <Link to="/vendor" className="ad-btn ad-btn-outline ad-btn-lg">
                {t("vendor.learnMore")}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Verification Strip ────────────────────────── */}
      <section className="ad-section" style={{ background: "var(--ad-surface)" }} aria-labelledby="verify-strip-heading">
        <div className="ad-container" style={{ textAlign: "center", maxWidth: 680 }}>
          <span className="ad-eyebrow">{t("verifyStrip.eyebrow")}</span>
          <h2 id="verify-strip-heading" style={{ margin: "12px 0 16px" }}>{t("verifyStrip.title")}</h2>
          <p style={{ marginBottom: 28 }}>{t("verifyStrip.desc")}</p>
          <Link to="/verify" className="ad-btn ad-btn-primary ad-btn-lg">
            {t("verifyStrip.btn")}
          </Link>
        </div>
      </section>
    </div>
  );
}
