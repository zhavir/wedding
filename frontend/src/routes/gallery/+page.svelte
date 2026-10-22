<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import { restoreSession } from '#lib/session.svelte.ts';
  import SiteHeader from '#lib/components/SiteHeader.svelte';
  import BotanicalFrame from '#lib/components/BotanicalFrame.svelte';
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
<BotanicalFrame /><SiteHeader gallery />
<main class="gallery-page">
  <h1 class="gallery-title">{t('Our wedding gallery')}</h1>
  <Gallery />
</main>
<Footer />
