import content from '../../../content/locales/en/wedding.json';
import italian from '../../../content/locales/it/wedding.json';
import { language } from './i18n.svelte.ts';

const localized: typeof content = { ...content, ...italian };
/** Shared event settings and images, with reactive Italian editorial overrides. */
export const wedding = new Proxy(content, {
  get(target, property: keyof typeof content) {
    return language.current === 'it' ? localized[property] : target[property];
  }
});
