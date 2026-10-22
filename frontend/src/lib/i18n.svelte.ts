import en from './locales/en/ui.json';
import it from './locales/it/ui.json';

export type Locale = 'en' | 'it';
export const language = $state<{ current: Locale }>({ current: 'en' });
const messages: Record<Locale, Record<string, string>> = { en, it };

export function t(key: string, values: Record<string, string | number> = {}): string {
  const message = messages[language.current][key] ?? key;
  return message.replace(/\{(\w+)\}/g, (match, name: string) => String(values[name] ?? match));
}

export function setLanguage(locale: Locale) {
  language.current = locale;
  if (typeof document !== 'undefined') document.documentElement.lang = locale;
  try {
    localStorage.setItem('wedding-language', locale);
  } catch {
    /* Storage can be disabled. */
  }
}

export function restoreLanguage() {
  let saved: string | null = null;
  try {
    saved = localStorage.getItem('wedding-language');
  } catch {
    /* Use browser language. */
  }
  setLanguage(
    saved === 'it' || saved === 'en'
      ? saved
      : navigator.language.toLowerCase().startsWith('it')
        ? 'it'
        : 'en'
  );
}
