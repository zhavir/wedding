<script lang="ts">
  import { wedding as w } from '#lib/wedding.ts';
  import Flourish from './Flourish.svelte';
</script>

<section class="menu-section section" id="menu" aria-labelledby="menu-title">
  <div class="menu-intro">
    <p class="eyebrow">{w.menu.eyebrow}</p>
    <h2 id="menu-title">{w.menu.title}</h2>
    <Flourish />
    <p>{w.menu.intro}</p>
    <svg
      class="menu-place-setting"
      viewBox="0 0 260 210"
      fill="none"
      stroke="currentColor"
      aria-hidden="true"
      ><circle cx="130" cy="105" r="76" /><circle cx="130" cy="105" r="65" /><circle
        cx="130"
        cy="105"
        r="48"
        stroke-dasharray="1 5"
      /><path
        d="M25 20V75Q25 88 35 88Q45 88 45 75V20M35 20V188M226 20Q207 62 225 90V188M225 90V20"
      /><path
        class="menu-sprig"
        d="M108 125Q120 90 149 78M116 107Q92 89 119 96M128 90Q122 69 137 85M135 87Q158 100 143 80"
      /></svg
    >
  </div>
  <div class="menu-paper">
    <p class="menu-word">Menu</p>
    {#each w.menu.courses as course, i (course.title)}<article>
        <span class="eyebrow">0{i + 1}</span>
        <h3>{course.title}</h3>
        <p>{course.description}</p>
      </article>{/each}
    <p class="menu-note">{w.menu.note}</p>
  </div>
</section>
