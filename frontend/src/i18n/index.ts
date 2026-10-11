import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import am from "./am.json";
import en from "./en.json";

export const SUPPORTED_LANGUAGES = ["am", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];
const STORAGE_KEY = "asset-draw.lang";

function initialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "am" || saved === "en") return saved;
  } catch {
    /* storage unavailable */
  }
  return "am"; // Amharic-first (spec section 17)
}

const language = initialLanguage();
document.documentElement.lang = language;

void i18n.use(initReactI18next).init({
  resources: { am: { translation: am }, en: { translation: en } },
  lng: language,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export function setLanguage(lang: Language): void {
  void i18n.changeLanguage(lang);
  document.documentElement.lang = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* storage unavailable */
  }
}

export default i18n;
