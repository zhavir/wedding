<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
</script>

<section class="intro section" id="story">
  <div class="intro-copy">
    <p class="eyebrow">{t('01 / OUR STORY')}</p>
    <h2>{t('Some things are')}<br />{t('just')} <em>{t('meant to be.')}</em></h2>
    <p class="lead">{w.intro}</p>
    <p>{w.story}</p>
    <div class="handwritten">{t('Here’s to our next chapter.')}</div>
  </div>
  <div class="story-image">
    <img src={w.storyImage} alt={w.storyAlt} width="800" height="1000" loading="lazy" /><span
      class="photo-note">{t('our favourite adventure yet')}</span
    ><span class="flower" aria-hidden="true">✳</span>
  </div>
</section>
