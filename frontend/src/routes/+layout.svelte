<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { restoreLanguage } from '#lib/i18n.svelte.ts';
  let { children } = $props();
  onMount(restoreLanguage);
</script>

{@render children()}
