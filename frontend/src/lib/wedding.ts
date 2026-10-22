import content from './locales/en/content.json';
import italian from './locales/it/content.json';
import { language } from './i18n.svelte.ts';
const localized: typeof content = { ...content, ...italian };
/** Frontend-owned event details and reactive editorial translations. */
export const wedding = new Proxy(content, {
  get(target, property: keyof typeof content) {
    return language.current === 'it' ? localized[property] : target[property];
  }
});
