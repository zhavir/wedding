<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import { session, signOut } from '#lib/session.svelte.ts';
  import LanguageSwitch from './LanguageSwitch.svelte';
  let { gallery = false }: { gallery?: boolean } = $props();
  let scrolled = $state(false);
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
    };
    update();
    addEventListener('scroll', update, { passive: true });
    return () => removeEventListener('scroll', update);
  });
</script>

<header class="site-header" class:gallery-header={gallery} class:scrolled={scrolled || gallery}>
  <div class="header-identity">
    <a class="monogram" href={gallery ? resolve('/') : '#home'} aria-label={w.names.join(' & ')}
      >{w.names[0][0]}<em>&</em>{w.names[1][0]}</a
    >
    <span class="header-date">{w.dateLabel}</span>
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
