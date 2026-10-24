<script lang="ts">
  import { wedding as w } from '#lib/wedding.ts';
  import StaticPicture from './StaticPicture.svelte';
</script>

<section class="section visions" id="ceremony-visions" aria-labelledby="visions-title">
  <p class="eyebrow">{w.visions.eyebrow}</p>
  <h2 id="visions-title">{w.visions.title}</h2>
  <div class="dreams">
    <figure>
      <div class="dream bride">
        <StaticPicture name="ceremony-bride" alt={w.visions.brideAlt} />
      </div>
      <figcaption>{w.visions.bride}</figcaption>
    </figure>
    <figure>
      <div class="dream groom">
        <StaticPicture name="ceremony-groom" alt={w.visions.groomAlt} />
      </div>
      <figcaption>{w.visions.groom}</figcaption>
    </figure>
  </div>
</section>

<style>
  .visions {
    text-align: center;
  }
  .dreams {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: center;
    gap: clamp(2rem, 5vw, 5rem);
    margin-top: 3rem;
  }
  figure {
    margin: 0;
    min-width: 0;
  }
  .dream {
    overflow: hidden;
    box-shadow: 0 12px 32px #25352b18;
    aspect-ratio: 3 / 4;
    border: 0.6rem solid #fffdf7;
  }
  .bride {
    border-radius: 48% 48% 3% 3%;
    transform: rotate(-3deg);
  }
  .groom {
    border-radius: 3% 3% 45% 45%;
    transform: rotate(3deg);
  }
  figcaption {
    font:
      italic clamp(1.2rem, 3vw, 1.8rem) Georgia,
      serif;
    margin-top: 1.5rem;
  }
  @media (max-width: 600px) {
    .dreams {
      grid-template-columns: minmax(0, 1fr);
      gap: 3rem;
      max-width: 360px;
      margin-inline: auto;
      padding-inline: 0.75rem;
    }
    .dream {
      border-width: 0.3rem;
    }
  }
</style>
