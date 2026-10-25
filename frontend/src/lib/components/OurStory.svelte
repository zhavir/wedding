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
  <div class="story-chapters mx-auto grid max-w-[1100px] gap-[clamp(3rem,7vw,6rem)]">
    {#each w.chapters as chapter, index (chapter.title)}
      <article
        class="story-chapter grid grid-cols-1 items-center gap-6 min-[701px]:grid-cols-2 min-[701px]:gap-[clamp(2rem,5vw,5rem)]"
      >
        <div class={index % 2 ? 'chapter-copy min-[701px]:order-2' : 'chapter-copy'}>
          <span class="chapter-number">0{index + 1}</span>
          <h3>{chapter.title}</h3>
          <p>{chapter.text}</p>
        </div>
        <div
          class="story-keepsakes grid min-w-0 grid-cols-2 gap-4 px-3 pt-4 pb-8"
          aria-label={t('Our photographs')}
        >
          {#each chapter.photos as photo, photoIndex (photo.name)}
            <figure class="polaroid">
              <div class="photograph aspect-[3/4] overflow-hidden">
                <StaticPicture
                  name={photo.name}
                  alt={t('Our story, photograph {number}', { number: index * 2 + photoIndex + 1 })}
                />
              </div>
              <figcaption>{photo.caption}</figcaption>
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
  figcaption {
    padding-top: 0.8rem;
    font:
      italic 0.85rem Georgia,
      serif;
  }
  @media (prefers-reduced-motion: reduce) {
    .polaroid {
      transition: none;
    }
  }
</style>
