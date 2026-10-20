<script lang="ts">
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import LanguageSwitch from '#lib/components/LanguageSwitch.svelte';
  import { reveal } from '#lib/reveal.ts';
  import { onMount } from 'svelte';
  import { wedding as w } from '#lib/wedding.ts';
  import { restoreSession, session } from '#lib/session.svelte.ts';
  import Travel from '#lib/components/Travel.svelte';
  import Akamaru from '#lib/components/Akamaru.svelte';
  import Hero from '#lib/components/Hero.svelte';
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
  /><meta name="theme-color" content="#f7f5ef" /><meta
    name="robots"
    content="noindex, nofollow"
  /><meta name="referrer" content="no-referrer" /></svelte:head
>
<a class="skip" href="#main">{t('Skip to content')}</a>
<header>
  <a class="monogram" href="#home">{w.names[0][0]}<span>&</span>{w.names[1][0]}</a>
  <nav aria-label={t('Main navigation')}>
    <a href="#story">{t('Our story')}</a><a href="#details">{t('The day')}</a><a href="#memories"
      >{t('Memories')}</a
    ><a class="nav-gallery" href={resolve('/gallery')}>{t('Gallery')}</a><a
      class="nav-rsvp"
      href="#rsvp">RSVP ↗</a
    >{#if session.guest?.is_admin}<a href={resolve('/admin')}>{t('Admin')}</a>{/if}
  </nav>
  <LanguageSwitch />
</header>
<main id="main" use:reveal>
  <Hero /><OurStory /><Countdown /><EventDetails /><Travel /><Akamaru /><Rsvp />
  <section class="section memory-link" id="memories">
    <p class="eyebrow">{t('04 / THROUGH YOUR EYES')}</p>
    <h2>{t('Share a little happiness.')}</h2>
    <p>{t('Your photos, our favourite memories. Upload them in our private gallery.')}</p>
    <a class="button" href={resolve('/gallery#upload')}>{t('Upload your photos ↗')}</a>
  </section>
</main>
<Footer />
