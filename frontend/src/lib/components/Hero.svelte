<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
</script>

<section class="hero" id="home" aria-labelledby="hero-title">
  <img
    class="hero-photo"
    src={w.heroImage}
    alt={w.heroAlt}
    fetchpriority="high"
    width="1920"
    height="1280"
  />
  <div class="hero-shade"></div>
  <div class="hero-corner hero-corner-left" aria-hidden="true">
    EST. <span>{new Date(w.date).getFullYear()}</span>
  </div>
  <div class="hero-corner hero-corner-right">{t('Forever starts here')}</div>
  <div class="hero-copy">
    <div class="hero-ornament" aria-hidden="true">✳</div>
    <p class="eyebrow">{t('WITH FULL HEARTS & OPEN ARMS')}</p>
    <h1 id="hero-title">{w.names[0]} <em>&</em> {w.names[1]}</h1>
    <p class="hero-sub">{t('We’re getting married. And you’re part of our story.')}</p>
    <p class="hero-kicker">{t('An Italian summer, a little magic, and you.')}</p>
    <div class="hero-date"><span>{w.dateLabel}</span><i></i><span>{w.location}</span></div>
    <a class="light-button" href="#rsvp">{t('Celebrate with us')}<span>↗</span></a>
  </div>
  <a class="scroll-cue" href="#story">{t('A DAY FOR LOVE, A LIFETIME OF MEMORIES')}<span>↓</span></a
  >
</section>

<div class="love-note">
  <span aria-hidden="true">✧</span>
  <p>{t('Together is our favourite place to be.')}</p>
  <span aria-hidden="true">✧</span>
</div>
