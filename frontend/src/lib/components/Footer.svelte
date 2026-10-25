<script lang="ts">
  import { onMount } from 'svelte';
  import Flourish from './Flourish.svelte';
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
  import { PUBLIC_CONTACT_EMAIL } from '$app/env/public';
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
</script>

<footer bind:this={footer} class:tied>
  <div class="footer-ribbon"><Flourish untied={tied ? 0 : 1} /></div>
  <p class="handwritten">{t('Tied together, always.')}</p>
  <p class="eyebrow">{t('THE BEST IS YET TO COME')}</p>
  <h2><span>{w.names[0]}</span> <em>&</em> <span>{w.names[1]}</span></h2>
  <p>{w.dateLabel} · {w.location}</p>
  <div class="footer-bottom">
    <span>{t('Made with love, for the people we love.')}</span><a
      href={`mailto:${PUBLIC_CONTACT_EMAIL}`}
      >{t('A question? Say hello ↗').replace('↗', '').trim()}
      <svg
        class="inline-arrow"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg
      ></a
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

<style>
  @media (max-width: 760px) {
    h2 {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      font-size: clamp(4rem, 16vw, 6.5rem);
      line-height: 0.95;
      font-weight: 300;
    }
    h2 em {
      margin: 0.1em 0;
      font-size: 0.58em;
      color: var(--gold);
    }
  }
</style>
