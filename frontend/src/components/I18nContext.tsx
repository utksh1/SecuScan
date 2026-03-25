import React, { createContext, useContext, useState, ReactNode } from 'react';

type Translations = {
  [key: string]: string | Translations;
};

const translations: Translations = {
  en: {
    common: {
      dashboard: 'Dashboard',
      assets: 'Assets',
      scanners: 'Scanners',
      history: 'History',
      findings: 'Findings',
      reports: 'Reports',
      settings: 'Settings',
      search: 'Search...',
      loading: 'Loading system...',
      error: 'System Error',
      success: 'Operation Successful',
    },
    nav: {
      monitor: 'Monitor',
      analyze: 'Analyze',
      execute: 'Execute',
    }
  }
};

interface I18nContextType {
  t: (path: string) => string;
  locale: string;
  setLocale: (locale: string) => void;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState('en');

  const t = (path: string): string => {
    const keys = path.split('.');
    let result: any = translations[locale];
    
    for (const key of keys) {
      if (result && typeof result === 'object' && key in result) {
        result = result[key];
      } else {
        return path;
      }
    }
    
    return typeof result === 'string' ? result : path;
  };

  return (
    <I18nContext.Provider value={{ t, locale, setLocale }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useTranslation must be used within an I18nProvider');
  }
  return context;
}
