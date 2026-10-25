<script lang="ts">
  import { PUBLIC_ASSET_URL } from '$app/env/public';
  import '../fonts.css';
  import '../app.css';
  import '../experience.css';
  import { onMount } from 'svelte';
  import { restoreLanguage } from '#lib/i18n.svelte.ts';
  let { children } = $props();
  onMount(restoreLanguage);
</script>

<svelte:head>
  {#if PUBLIC_ASSET_URL}<link
      rel="icon"
      type="image/svg+xml"
      sizes="any"
      href={`${PUBLIC_ASSET_URL}/favicon.svg`}
    />{/if}
</svelte:head>

{@render children()}
