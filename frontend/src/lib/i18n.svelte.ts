export type Locale = 'en' | 'it';
export const language = $state<{ current: Locale }>({ current: 'en' });
const sections = import.meta.glob('./locales/*/ui/*.json', { eager: true, import: 'default' });
const messages: Record<Locale, Record<string, string>> = { en: {}, it: {} };
for (const [path, copy] of Object.entries(sections)) {
  const locale = path.split('/')[2] as Locale;
  Object.assign(messages[locale], copy);
}

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

export function tp(
  key: string,
  count: number,
  values: Record<string, string | number> = {}
): string {
  return t(count === 1 ? key : `${key} (plural)`, values);
}
