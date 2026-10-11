import { useTranslation } from "react-i18next";
import { Languages } from "lucide-react";
import { setLanguage, type Language } from "../i18n";

export function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = (i18n.resolvedLanguage ?? "am") as Language;
  const next: Language = current === "am" ? "en" : "am";
  const label = current === "am" ? "EN" : "አማ";

  return (
    <button
      type="button"
      className="ad-lang-toggle"
      onClick={() => setLanguage(next)}
      aria-label={`Switch to ${next === "am" ? "Amharic" : "English"}`}
    >
      <Languages size={15} />
      {label}
    </button>
  );
}
