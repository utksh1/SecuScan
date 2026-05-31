import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { I18nProvider, useTranslation } from '../../../src/components/I18nContext';

const LocaleDisplay: React.FC = () => {
  const { locale } = useTranslation();
  return <div data-testid="locale">{locale}</div>;
};

const TranslationDisplay: React.FC<{ path: string }> = ({ path }) => {
  const { t } = useTranslation();
  return <div data-testid="translation">{t(path)}</div>;
};

const LocaleSwitcher: React.FC<{ targetLocale: string }> = ({ targetLocale }) => {
  const { locale, setLocale } = useTranslation();
  return (
    <>
      <div data-testid="locale">{locale}</div>
      <button onClick={() => setLocale(targetLocale)}>Switch</button>
    </>
  );
};

describe('I18nContext', () => {

  it('should default locale to "en"', () => {
    render(
      <I18nProvider>
        <LocaleDisplay />
      </I18nProvider>
    );
    expect(screen.getByTestId('locale').textContent).toBe('en');
  });

  it('should return correct translation for a valid nested key', () => {
    render(
      <I18nProvider>
        <TranslationDisplay path="common.dashboard" />
      </I18nProvider>
    );
    expect(screen.getByTestId('translation').textContent).toBe('Dashboard');
  });

  it('should return the key itself when translation path is not found', () => {
    render(
      <I18nProvider>
        <TranslationDisplay path="common.nonexistent" />
      </I18nProvider>
    );
    expect(screen.getByTestId('translation').textContent).toBe('common.nonexistent');
  });

  it('should expose setLocale function in context', () => {
    render(
      <I18nProvider>
        <LocaleSwitcher targetLocale="fr" />
      </I18nProvider>
    );
    expect(screen.getByRole('button', { name: 'Switch' })).toBeDefined();
  });

  it('should update locale when setLocale is called', async () => {
    render(
      <I18nProvider>
        <LocaleSwitcher targetLocale="fr" />
      </I18nProvider>
    );
    expect(screen.getByTestId('locale').textContent).toBe('en');
    await act(async () => {
      screen.getByRole('button', { name: 'Switch' }).click();
    });
    expect(screen.getByTestId('locale').textContent).toBe('fr');
  });

  it('should update locale correctly when switching to Hindi', async () => {
    render(
      <I18nProvider>
        <LocaleSwitcher targetLocale="hi" />
      </I18nProvider>
    );
    await act(async () => {
      screen.getByRole('button', { name: 'Switch' }).click();
    });
    expect(screen.getByTestId('locale').textContent).toBe('hi');
  });

  it('should fail if provider stops exposing locale as a string', () => {
    render(
      <I18nProvider>
        <LocaleDisplay />
      </I18nProvider>
    );
    const localeEl = screen.getByTestId('locale');
    expect(typeof localeEl.textContent).toBe('string');
    expect(localeEl.textContent).toBeTruthy();
  });

  it('should fail if provider stops exposing t as a function', () => {
    let capturedT: ((path: string) => string) | undefined;
    const Inspector: React.FC = () => {
      const { t } = useTranslation();
      capturedT = t;
      return null;
    };
    render(
      <I18nProvider>
        <Inspector />
      </I18nProvider>
    );
    expect(typeof capturedT).toBe('function');
  });

  it('should throw error when useTranslation is used outside I18nProvider', () => {
    const BadComponent: React.FC = () => {
      useTranslation();
      return null;
    };
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<BadComponent />)).toThrow(
      'useTranslation must be used within an I18nProvider'
    );
    spy.mockRestore();
  });
});
