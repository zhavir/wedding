<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  let photoActivated = $state(false);
</script>

<section class="intro section" id="story">
  <div class="intro-copy">
    <p class="eyebrow">{t('01 / OUR STORY')}</p>
    <h2>{t('Some things are')}<br />{t('just')} <em>{t('meant to be.')}</em></h2>
    <p class="lead">{w.intro}</p>
    <p>{w.story}</p>
    <div class="handwritten">{t('Here’s to our next chapter.')}</div>
  </div>
  <div class="story-image" class:touch-activated={photoActivated}
    role="button" tabindex="0" aria-pressed={photoActivated}
    aria-label="Animate our story photo"
    onclick={() => { if (window.matchMedia('(hover: none)').matches) photoActivated = !photoActivated; }}
    onkeydown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); photoActivated = !photoActivated; } }}>
    <img src={w.storyImage} alt={w.storyAlt} width="800" height="1000" loading="lazy" /><span
      class="photo-note">{t('our favourite adventure yet')}</span
    ><span class="flower" aria-hidden="true">✳</span>
  </div>
</section>
