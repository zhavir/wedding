<script lang="ts">
  import { onMount } from 'svelte';
  import Flourish from './Flourish.svelte';
  import BotanicalFrame from './BotanicalFrame.svelte';
  let footer: HTMLElement;
  let tied = $state(false);
  onMount(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        tied = entry.isIntersecting;
      },
      { threshold: 0.2 }
    );
    observer.observe(footer);
    return () => observer.disconnect();
  });
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
</script>

<footer bind:this={footer} class:tied>
  <BotanicalFrame footer />
  <div class="footer-ribbon"><Flourish untied={tied ? 0 : 1} /></div>
  <p class="handwritten">{t('Tied together, always.')}</p>
  <p class="eyebrow">{t('THE BEST IS YET TO COME')}</p>
  <h2>{w.names[0]} <em>&</em> {w.names[1]}</h2>
  <p>{w.dateLabel} · {w.location}</p>
  <div class="footer-bottom">
    <span>{t('Made with love, for the people we love.')}</span><a href={`mailto:${w.contactEmail}`}
      >{t('A question? Say hello ↗')}</a
    ><a href={resolve('/#home')}>{t('Back to the beginning ↑')}</a>
  </div>
  <div class="marquee" aria-hidden="true">
    <div class="marquee-track">
      {#each [0, 1] as group (group)}<div class="marquee-group">
          {#each w.footerPhrases as phrase (phrase)}<span>{phrase}<i>✧</i></span>{/each}
        </div>{/each}
    </div>
  </div>
</footer>
