<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import StaticPicture from './StaticPicture.svelte';
</script>

<section class="section intro" id="story">
  <div class="intro-copy">
    <p class="eyebrow">{t('01 OUR STORY')}</p>
    <h2><span>{t('Some things are')} {t('just')}</span><em>{t('meant to be.')}</em></h2>
  </div>
  <div class="story-chapters">
    {#each w.chapters as chapter, index (chapter.title)}
      <article class="story-chapter">
        <div class="chapter-copy">
          <span class="chapter-number">0{index + 1}</span>
          <h3>{chapter.title}</h3>
          <p>{chapter.text}</p>
        </div>
        <div class="story-keepsakes" aria-label={t('Our photographs')}>
          {#each [index * 2 + 1, index * 2 + 2] as number (number)}
            <figure class="polaroid">
              <div class="photograph">
                <StaticPicture
                  name={`story-0${number}`}
                  alt={t('Our story, photograph {number}', { number })}
                />
              </div>
              <figcaption>Andrea &amp; Sara <span>0{number}</span></figcaption>
            </figure>
          {/each}
        </div>
      </article>
    {/each}
  </div>
</section>

<style>
  .intro {
    display: block;
  }
  .intro-copy {
    max-width: 42rem;
    margin: 0 auto clamp(2.5rem, 5vw, 4rem);
    text-align: center;
  }
  .story-chapters {
    display: grid;
    gap: clamp(3rem, 7vw, 6rem);
    max-width: 1100px;
    margin-inline: auto;
  }
  .story-chapter {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: center;
    gap: clamp(2rem, 5vw, 5rem);
  }
  .story-chapter:nth-child(even) .chapter-copy {
    order: 2;
  }
  .chapter-number {
    font:
      italic 2.5rem Georgia,
      serif;
    color: #9b745e;
  }
  h3 {
    font:
      300 var(--chapter-subtitle)/1.2 'Cormorant Garamond',
      serif;
    margin: 1rem 0;
  }
  .chapter-copy p {
    max-width: 42ch;
    font-size: var(--chapter-body);
    line-height: 1.8;
  }
  @media (max-width: 700px) {
    .story-chapter {
      grid-template-columns: minmax(0, 1fr);
      gap: 1.5rem;
    }
    .story-chapter:nth-child(even) .chapter-copy {
      order: 0;
    }
  }

  .intro-copy h2 {
    font-size: var(--chapter-title);
    line-height: 1.14;
    letter-spacing: -0.025em;
  }
  .intro-copy h2 > * {
    display: block;
  }
  .intro-copy h2 em {
    margin-top: 0.12em;
    line-height: 1.2;
  }

  .story-keepsakes {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 1rem;
    padding: 1rem 0.75rem 2rem;
    min-width: 0;
  }
  .polaroid {
    min-width: 0;
    margin: 0;
    padding: 0.7rem 0.7rem 1rem;
    background: #fffdf7;
    box-shadow: 0 8px 22px #25352b20;
    transform: rotate(-3deg);
    transition: transform 0.4s;
  }
  .polaroid:nth-child(even) {
    transform: rotate(3deg) translateY(0.8rem);
  }
  .polaroid:nth-child(3) {
    transform: rotate(-3deg);
  }
  .polaroid:hover {
    transform: rotate(0) translateY(-0.4rem);
  }
  .photograph {
    aspect-ratio: 3 / 4;
    overflow: hidden;
  }
  figcaption {
    padding-top: 0.8rem;
    font:
      italic 0.85rem Georgia,
      serif;
  }
  figcaption span {
    opacity: 0.5;
    margin-left: 0.5rem;
  }
  @media (prefers-reduced-motion: reduce) {
    .polaroid {
      transition: none;
    }
  }
</style>
