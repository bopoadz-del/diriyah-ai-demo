import React from "react";
import { useTranslation } from "react-i18next";

const LanguageSwitcher = () => {
  const { i18n, t } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === "ar" ? "en" : "ar";
    i18n.changeLanguage(newLang);
  };

  const isArabic = i18n.language === "ar";
  const label = isArabic ? t("sidebar.switchToEnglish") : t("sidebar.switchToArabic");

  return (
    <button
      onClick={toggleLanguage}
      className="language-switcher"
      type="button"
      aria-label={label}
      title={label}
    >
      {isArabic ? "English" : "العربية"}
    </button>
  );
};

export default LanguageSwitcher;
