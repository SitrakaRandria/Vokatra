import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-lidetector';

// Import des traductions (on utilisera des fichiers JSON)
import frCommon from './locales/fr/common.json';
import mgCommon from './locales/mg/common.json';

const resources = {
  fr: { common: frCommon },
  mg: { common: mgCommon }
};

i18next
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'fr',
    ns: ['common'],
    defaultNS: 'common',
    interpolation: {
      escapeValue: false
    },
    detection: {
      order: ['path', 'cookie', 'localStorage', 'navigator'],
      caches: ['cookie']
    }
  });

export default i18next;
