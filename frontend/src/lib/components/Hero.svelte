<script lang="ts">
  import StaticPicture from './StaticPicture.svelte';
  import { language, t, tp } from '#lib/i18n.svelte.ts';
  import { session } from '#lib/session.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  const participants = $derived(session.guest?.participant_count ?? session.guest?.max_guests ?? 1);
  let { progress = 1 }: { progress?: number } = $props();
</script>

<section class="hero" id="home" aria-labelledby="hero-title">
  <div class="invitation-venue">
    <StaticPicture name="hero-picture" alt={t('Hero picture')} eager />
  </div>
  <p class="eyebrow hero-eyebrow">{t('Together with our families')}</p>
  <h1 id="hero-title">{w.names[0]} <em>&</em> {w.names[1]}</h1>
  <p class="hero-date">{w.dateLabel} <span>·</span> {w.location}</p>
  <span class="invitation-rule" aria-hidden="true"></span>
  <p class="hero-sub">{tp('We’re getting married. And you’re part of our story.', participants)}</p>
  <a inert={progress < 0.85} class="invitation-link" href="#rsvp"
    >{tp('Celebrate with us', participants)}<span aria-hidden="true">↗</span></a
  >
  <!-- eslint-disable svelte/no-navigation-without-resolve -- Download a static calendar file. -->
  <a
    class="save-date-link"
    inert={progress < 0.85}
    href={`/calendar/wedding-${language.current}.ics`}
    download="andrea-sara-wedding.ics"
    rel="external"
    data-sveltekit-reload
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"
      ><rect x="4" y="5" width="16" height="16" rx="3" /><path
        d="M8 2v6m8-6v6M4 11h16m-12 5h3"
      /></svg
    >
    {t('Save the date')}
  </a>
  <!-- eslint-enable svelte/no-navigation-without-resolve -->
</section>
