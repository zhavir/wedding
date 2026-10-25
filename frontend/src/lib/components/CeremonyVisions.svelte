<script lang="ts">
  import { wedding as w } from '#lib/wedding.ts';
  import StaticPicture from './StaticPicture.svelte';
</script>

<section class="section visions" id="ceremony-visions" aria-labelledby="visions-title">
  <p class="eyebrow">{w.visions.eyebrow}</p>
  <h2 id="visions-title">{w.visions.title}</h2>
  <div
    class="dreams mx-auto mt-12 grid max-w-[360px] grid-cols-1 items-center gap-12 px-3 min-[601px]:max-w-none min-[601px]:grid-cols-2 min-[601px]:gap-[clamp(2rem,5vw,5rem)] min-[601px]:px-0"
  >
    <figure class="m-0 min-w-0">
      <div class="dream bride aspect-[3/4] overflow-hidden">
        <StaticPicture name="ceremony-bride" alt={w.visions.brideAlt} />
      </div>
      <figcaption>{w.visions.bride}</figcaption>
    </figure>
    <figure class="m-0 min-w-0">
      <div class="dream groom aspect-[3/4] overflow-hidden">
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
  .dream {
    box-shadow: 0 12px 32px #25352b18;
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
    .dream {
      border-width: 0.3rem;
    }
  }
</style>
