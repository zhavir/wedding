<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import { session, signOut } from '#lib/session.svelte.ts';
  import LanguageSwitch from './LanguageSwitch.svelte';
  import Monogram from './Monogram.svelte';
  let { gallery = false }: { gallery?: boolean } = $props();
  let scrolled = $state(false);
  let revealProgress = $state(0);
  let identityGrowth = $state(135);
  let identityBase = $state(76);
  let logoWidth = $state(40);
  let monogramElement: HTMLAnchorElement;
  let dateElement: HTMLSpanElement;
  let signingOut = $state(false);
  async function logout() {
    if (signingOut) return;
    signingOut = true;
    try {
      await signOut();
    } catch (error) {
      session.error = (error as Error).message;
    } finally {
      signingOut = false;
    }
  }
  onMount(() => {
    const update = () => {
      scrolled = scrollY > 50;
      const scene = document.querySelector<HTMLElement>('.envelope-scene');
      const distance = scene ? Math.max(1, scene.offsetHeight - innerHeight) : innerHeight;
      const amount = scene ? -scene.getBoundingClientRect().top / distance : 1;
      const value = Math.max(0, Math.min(1, (amount - 0.62) / 0.38));
      revealProgress = matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 1
        : value * value * (3 - 2 * value);
    };
    const measure = () => {
      // Fit the date with extra trailing space for optical balance.
      logoWidth = monogramElement.getBoundingClientRect().width;
      // Extra optical breathing room: the italic ampersand and final S otherwise look crowded.
      // As the capsule grows, its left inset stays at 14px and its right edge moves.
      identityBase = logoWidth + 40;
      // Match the logo's 14px inset, 1px border, and 6px of optical spacing.
      const identity = monogramElement.parentElement!.getBoundingClientRect();
      const date = dateElement.getBoundingClientRect();
      identityGrowth = date.right - identity.left + 21 - identityBase;
      update();
    };
    measure();
    document.fonts.ready.then(measure);
    const observer = new ResizeObserver(measure);
    observer.observe(dateElement);
    addEventListener('scroll', update, { passive: true });
    addEventListener('resize', measure);
    return () => {
      observer.disconnect();
      removeEventListener('scroll', update);
      removeEventListener('resize', measure);
    };
  });
</script>

<header
  class="site-header"
  class:gallery-header={gallery}
  class:scrolled={scrolled || gallery}
  class:identity-revealed={gallery || revealProgress >= 0.995}
>
  <div
    class="header-identity"
    style={`--identity-progress:${gallery ? 1 : revealProgress};--identity-growth:${identityGrowth}px;--identity-base:${identityBase}px;--logo-width:${logoWidth}px`}
  >
    <a
      bind:this={monogramElement}
      class="monogram"
      href={gallery ? resolve('/') : '#home'}
      aria-label={w.names.join(' & ')}><Monogram /></a
    >
    <span bind:this={dateElement} class="header-date">{w.dateLabel}</span>
  </div>
  <div class="header-actions">
    <nav aria-label={t('Main navigation')}>
      {#if gallery}
        <a class="gallery-back" href={resolve('/')} aria-label={t('← Back to our wedding')}
          ><span class="desktop-label">{t('← Back to our wedding')}</span><span
            class="mobile-label"
            aria-hidden="true">← {t('The wedding')}</span
          ></a
        >
      {:else}<a class="nav-gallery" href={resolve('/gallery')}>{t('Gallery')}</a>{/if}
      <a class="nav-rsvp" href={gallery ? resolve('/#rsvp') : '#rsvp'}
        >RSVP <span aria-hidden="true">↗</span></a
      >
      {#if gallery && session.guest}<button
          class="text-button header-signout"
          disabled={signingOut}
          aria-busy={signingOut}
          onclick={logout}>{t('Sign out')}</button
        >{/if}
      {#if session.guest?.is_admin}<a class="nav-admin" href={resolve('/admin')}>{t('Admin')}</a
        >{/if}
    </nav>
    <LanguageSwitch />
  </div>
</header>

<style>
  .monogram {
    flex-shrink: 0;
    width: 44px;
    height: 44px;
  }
  @media (prefers-reduced-motion: reduce) {
    .header-identity,
    .header-date,
    .monogram {
      transition: none !important;
    }
  }
</style>
