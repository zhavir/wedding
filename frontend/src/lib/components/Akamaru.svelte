<script lang="ts">
  import { wedding as w } from '#lib/wedding.ts';
</script>

<section class="section dog-section" id="akamaru">
  <div class="dog-picture">
    <img src={w.dog.image} alt={w.dog.imageAlt} width="800" height="650" loading="lazy" />
    <p>{w.dog.placeholder}</p>
  </div>
  <div>
    <p class="eyebrow">{w.dog.eyebrow} · {w.dog.name}</p>
    <h2>{w.dog.title}</h2>
    <p>{w.dog.text}</p>
    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- External Instagram profile from editable content. --><a
      href={w.dog.instagram}
      target="_blank"
      rel="noreferrer">{w.dog.linkLabel}</a
    >
  </div>
</section>
