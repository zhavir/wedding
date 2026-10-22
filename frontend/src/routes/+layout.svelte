<script lang="ts">
  import '../fonts.css';
  import '../app.css';
  import '../experience.css';
  import { onMount } from 'svelte';
  import { restoreLanguage } from '#lib/i18n.svelte.ts';
  let { children } = $props();
  onMount(restoreLanguage);
</script>

{@render children()}
