<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import { session, restoreSession, signOut } from '#lib/session.svelte.ts';
  import LanguageSwitch from '#lib/components/LanguageSwitch.svelte';
  import Gallery from '#lib/features/photos/Gallery.svelte';
  import Footer from '#lib/components/Footer.svelte';
  onMount(() => {
    void restoreSession();
  });
</script>

<svelte:head
  ><title>{t('Our wedding gallery')} · {w.names.join(' & ')}</title><meta
    name="robots"
    content="noindex,nofollow"
  /><meta name="referrer" content="no-referrer" /></svelte:head
>
<header>
  <a href={resolve('/')}>{t('← Back to our wedding')}</a>
  <div class="gallery-nav">
    {#if session.guest}<button
        class="text-button"
        onclick={async () => {
          try {
            await signOut();
          } catch (error) {
            session.error = (error as Error).message;
          }
        }}>{t('Sign out')}</button
      >{/if}<LanguageSwitch />
  </div>
</header>
<main>
  <h1 class="gallery-title">{t('Our wedding gallery')}</h1>
  <Gallery />
</main>
<Footer />
