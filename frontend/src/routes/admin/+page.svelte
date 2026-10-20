<script lang="ts">
  import { onMount } from 'svelte';
  onMount(() => window.location.replace('/api/admin/'));
</script>

<svelte:head
  ><title>Wedding administration</title><meta
    name="robots"
    content="noindex,nofollow"
  /></svelte:head
>
<main class="section">
  <h1>Wedding administration</h1>
  <p>
    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- Backend-owned SQLAdmin route. --><a
      href="/api/admin/"
      rel="external"
      data-sveltekit-reload>Open administration / Apri amministrazione →</a
    >
  </p>
</main>
