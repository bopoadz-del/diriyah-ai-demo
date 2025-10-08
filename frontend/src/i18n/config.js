import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "../locales/en.json";
import ar from "../locales/ar.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ar: { translation: ar },
    },
    fallbackLng: "en",
    supportedLngs: ["en", "ar"],
    debug: import.meta.env.MODE === "development",
    interpolation: {
      escapeValue: false,
    },
  });

const updateDocumentDirection = (language) => {
  const isArabic = language === "ar";
  document.documentElement.setAttribute("dir", isArabic ? "rtl" : "ltr");
  document.documentElement.setAttribute("lang", language);
};

updateDocumentDirection(i18n.language || "en");
i18n.on("languageChanged", updateDocumentDirection);

export default i18n;
