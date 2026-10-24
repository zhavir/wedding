import event from './locales/en/content/event.json';
import story from './locales/en/content/story.json';
import timeline from './locales/en/content/timeline.json';
import questions from './locales/en/content/questions.json';
import travel from './locales/en/content/travel.json';
import akamaru from './locales/en/content/akamaru.json';
import visions from './locales/en/content/ceremony-visions.json';
import footer from './locales/en/content/footer.json';
import { language } from './i18n.svelte.ts';
const content = {
  ...event,
  ...story,
  ...timeline,
  ...questions,
  ...travel,
  ...akamaru,
  ...visions,
  ...footer
};
const sections = import.meta.glob('./locales/it/content/*.json', {
  eager: true,
  import: 'default'
});
const italian = Object.assign({}, ...Object.values(sections)) as typeof content;
export const wedding = new Proxy(content, {
  get(target, property: keyof typeof content) {
    return language.current === 'it' ? italian[property] : target[property];
  }
});
