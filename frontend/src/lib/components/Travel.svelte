<script lang="ts">
  import StaticPicture from './StaticPicture.svelte';
  import { wedding as w } from '#lib/wedding.ts';
  let showMap = $state(false);
</script>

<!-- eslint-disable svelte/no-navigation-without-resolve -- All configurable links below are external venue/map/train URLs. -->
<section class="section travel" id="travel">
  <div class="section-heading">
    <div>
      <p class="eyebrow">{w.travel.eyebrow}</p>
      <h2>{w.travel.title}</h2>
      <p>{w.address}</p>
    </div>
  </div>
  <div class="venue-intro">
    <div class="venue-photo"><StaticPicture name="venue-photo-1" alt={w.travel.imageAlt} /></div>
    <div class="venue-photo"><StaticPicture name="venue-photo-2" alt={w.travel.imageAlt} /></div>
    <div>
      <a href={w.travel.website} target="_blank" rel="noreferrer">{w.travel.venueLink}</a>
    </div>
  </div>
  <div class="travel-cards">
    <article>
      <h3>{w.travel.carTitle}</h3>
      <p>{w.travel.carText}</p>
      <a href={w.mapUrl} target="_blank" rel="noreferrer">{w.travel.directions}</a>
    </article>
    <article>
      <h3>{w.travel.trainTitle}</h3>
      <p>{w.travel.trainText}</p>
      <a href={w.travel.trainUrl} target="_blank" rel="noreferrer">{w.travel.trains}</a>
    </article>
  </div>
  <div class="venue-map">
    <h3>{w.travel.mapTitle}</h3>
    {#if showMap}<iframe
        src={w.travel.mapEmbed}
        title={w.travel.mapTitle}
        loading="lazy"
        referrerpolicy="no-referrer"
        allowfullscreen
      ></iframe>{:else}<p>{w.travel.mapNote}</p>
      <button class="button" onclick={() => (showMap = true)}>{w.travel.mapButton}</button>{/if}
  </div>
</section>

<style>
  .venue-photo {
    aspect-ratio: 3 / 2;
    overflow: hidden;
    border-radius: 48% 48% 0 0;
  }
</style>
