/**
 * i18n Configuration
 *
 * Multi-language support with English as default.
 * Supports: English (en), Chinese (zh)
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locales/en.json';
import zh from './locales/zh.json';

const STORAGE_KEY = 'remix-studio-language';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
    },
    fallbackLng: 'en',
    debug: false,
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: STORAGE_KEY,
      caches: ['localStorage'],
    },
  });

/**
 * Get current language
 * @returns {string} Current language code ('en' or 'zh')
 */
export function getCurrentLanguage() {
  return i18n.language?.startsWith('zh') ? 'zh' : 'en';
}

/**
 * Set language and persist to localStorage
 * @param {string} lang - Language code ('en' or 'zh')
 */
export function setLanguage(lang) {
  const normalizedLang = lang.startsWith('zh') ? 'zh' : 'en';
  i18n.changeLanguage(normalizedLang);
  localStorage.setItem(STORAGE_KEY, normalizedLang);

  // Dispatch custom event for components that need to react to language changes
  window.dispatchEvent(new CustomEvent('language-change', { detail: { language: normalizedLang } }));
}

/**
 * Toggle between English and Chinese
 */
export function toggleLanguage() {
  const current = getCurrentLanguage();
  setLanguage(current === 'en' ? 'zh' : 'en');
}

export default i18n;
