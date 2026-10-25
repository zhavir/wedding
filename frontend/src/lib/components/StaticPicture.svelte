<script lang="ts">
  import { PUBLIC_ASSET_URL } from '$app/env/public';
  let { name, alt, eager = false }: { name: string; alt: string; eager?: boolean } = $props();
  const source = $derived(PUBLIC_ASSET_URL ? `${PUBLIC_ASSET_URL}/${name}.webp` : '');
  let failed = $state(false);
</script>

{#if source && !failed}
  <img
    class="block h-full w-full object-cover"
    src={source}
    {alt}
    width="1200"
    height="1600"
    loading={eager ? 'eager' : 'lazy'}
    decoding="async"
    fetchpriority={eager ? 'high' : 'auto'}
    onerror={() => (failed = true)}
  />
{:else}
  <div
    class="picture-placeholder grid h-full min-h-72 w-full place-items-center"
    role="img"
    aria-label={alt}
  >
    <span aria-hidden="true">♡</span>
  </div>
{/if}

<style>
  .picture-placeholder {
    background: linear-gradient(145deg, #ece9dc, #d8dfce);
    color: #7e896e;
  }
  span {
    font:
      italic 4rem Georgia,
      serif;
    opacity: 0.5;
  }
</style>
