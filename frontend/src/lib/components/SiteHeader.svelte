<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import { session, signOut } from '#lib/session.svelte.ts';
  import LanguageSwitch from './LanguageSwitch.svelte';
  let { gallery = false }: { gallery?: boolean } = $props();
  let scrolled = $state(false);
  let revealProgress = $state(0);
  let identityGrowth = $state(135);
  let identityBase = $state(76);
  let logoWidth = $state(40);
  let revealLocked = $state(false);
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
      // Match Opening.svelte: progress is controlled by scroll, not elapsed time.
      // Once fully revealed, keep the identity open when scrolling back upward.
      const scene = document.querySelector('.opening-scene');
      const distance = innerHeight * 0.65;
      const amount = scene
        ? Math.max(0, -scene.getBoundingClientRect().top / distance)
        : scrollY / distance;
      const position = Math.max(0, Math.min(1, amount));
      // Reverse with scroll until fully open; only then latch permanently.
      if (position >= 0.995) revealLocked = true;
      revealProgress = revealLocked ? 1 : position;
    };
    const measure = () => {
      // The expanded capsule fits the actual date, without trailing empty space.
      logoWidth = monogramElement.getBoundingClientRect().width;
      // Extra optical breathing room: the italic ampersand and final S otherwise look crowded.
      // As the capsule grows, its left inset stays at 14px and its right edge moves.
      identityBase = logoWidth + 40;
      // The date is inserted after a 16px gap with another 14px right inset.
      identityGrowth = dateElement.scrollWidth + 16;
      update();
    };
    measure();
    document.fonts.ready.then(measure);
    addEventListener('scroll', update, { passive: true });
    addEventListener('resize', measure);
    return () => {
      removeEventListener('scroll', update);
      removeEventListener('resize', measure);
    };
  });
</script>

<header
  class="site-header"
  class:gallery-header={gallery}
  class:scrolled={scrolled || gallery}
  class:identity-revealed={revealLocked || gallery}
>
  <div
    class="header-identity"
    style={`--identity-progress:${gallery ? 1 : revealProgress};--identity-growth:${identityGrowth}px;--identity-base:${identityBase}px;--logo-width:${logoWidth}px`}
  >
    <a
      bind:this={monogramElement}
      class="monogram"
      href={gallery ? resolve('/') : '#home'}
      aria-label={w.names.join(' & ')}>{w.names[0][0]}<em>&</em>{w.names[1][0]}</a
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
  }
  @media (prefers-reduced-motion: reduce) {
    .header-identity,
    .header-date,
    .monogram {
      transition: none !important;
    }
  }
</style>
