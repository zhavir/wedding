<script lang="ts">
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import SiteHeader from '#lib/components/SiteHeader.svelte';
  import BotanicalFrame from '#lib/components/BotanicalFrame.svelte';
  import CelebrationDetails from '#lib/components/CelebrationDetails.svelte';
  import CeremonyVisions from '#lib/components/CeremonyVisions.svelte';
  import MemoriesCarousel from '#lib/components/MemoriesCarousel.svelte';
  import { reveal } from '#lib/reveal.ts';
  import { onMount } from 'svelte';
  import { wedding as w } from '#lib/wedding.ts';
  import { restoreSession } from '#lib/session.svelte.ts';
  import Travel from '#lib/components/Travel.svelte';
  import Akamaru from '#lib/components/Akamaru.svelte';
  import EnvelopeOpening from '#lib/components/EnvelopeOpening.svelte';
  import ChapterNav from '#lib/components/ChapterNav.svelte';
  import OurStory from '#lib/components/OurStory.svelte';
  import Countdown from '#lib/components/Countdown.svelte';
  import EventDetails from '#lib/components/EventDetails.svelte';
  import Footer from '#lib/components/Footer.svelte';
  import Rsvp from '#lib/features/invitations/Rsvp.svelte';

  onMount(() => {
    void restoreSession();
  });
</script>

<svelte:head
  ><title>{w.names.join(' & ')} — {t('We’re getting married')}</title><meta
    name="description"
    content={`${w.names.join(' & ')} · ${w.dateLabel} · ${w.location}`}
  /><meta name="theme-color" content="#fbf8f2" /><meta
    name="robots"
    content="noindex, nofollow"
  /><meta name="referrer" content="no-referrer" /></svelte:head
>
<BotanicalFrame /><SiteHeader />
<ChapterNav />
<main id="main" use:reveal>
  <EnvelopeOpening /><OurStory /><CelebrationDetails /><Countdown /><EventDetails /><CeremonyVisions
  /><Travel /><Akamaru /><Rsvp />
  <section class="section memory-link" id="memories">
    <p class="eyebrow">{t('04 / THROUGH YOUR EYES')}</p>
    <h2>{t('Share a little happiness.')}</h2>
    <p>{t('Your photos, our favourite memories. Upload them in our private gallery.')}</p>
    <MemoriesCarousel />
    <a class="button" href={resolve('/gallery#upload')}>{t('Upload your photos ↗')}</a>
  </section>
</main>
<Footer />
