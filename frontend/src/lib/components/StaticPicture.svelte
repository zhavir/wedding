<script lang="ts">
  import { PUBLIC_ASSET_URL } from '$app/env/public';
  let { name, alt, eager = false }: { name: string; alt: string; eager?: boolean } = $props();
  const bundled: Record<string, string> = {
    'venue-garden': '/images/villa-valentina.webp',
    'ceremony-bride': '/images/ceremony-bride.webp',
    'ceremony-groom': '/images/ceremony-groom.webp',
    akamaru: '/images/akamaru.webp',
    'akamaru-naruto': '/images/akamaru-naruto.webp'
  };
  const source = $derived(
    bundled[name] ?? (PUBLIC_ASSET_URL ? `${PUBLIC_ASSET_URL}/${name}.webp` : '')
  );
  let failed = $state(false);
</script>

{#if source && !failed}
  <img
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
  <div class="picture-placeholder" role="img" aria-label={alt}>
    <span aria-hidden="true">♡</span>
  </div>
{/if}

<style>
  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .picture-placeholder {
    width: 100%;
    height: 100%;
    min-height: 18rem;
    display: grid;
    place-items: center;
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
