<script lang="ts">
  import { api, type Photo } from '#lib/api.ts';
  import { session } from '#lib/session.svelte.ts';
  import { t } from '#lib/i18n.svelte.ts';
  let photos = $state<Pick<Photo, 'id' | 'caption' | 'preview'>[]>([]);
  // Fetch once per authenticated session and discard stale responses on sign-out.
  $effect(() => {
    const guest = session.guest?.id;
    void session.revision;
    photos = [];
    if (!guest) return;
    let mounted = true;
    void api<{ items: Pick<Photo, 'id' | 'caption' | 'preview'>[] }>('/photos/carousel')
      .then(({ items }) => {
        if (mounted) photos = items;
      })
      .catch(() => {
        /* The gallery link remains available if the preview cannot load. */
      });
    return () => {
      mounted = false;
    };
  });
</script>

{#if session.guest && photos.length}
  <div class="carousel" aria-label={t('Memories from our guests')}>
    <div class="track" style={`--duration: ${Math.max(30, photos.length * 5)}s`}>
      {#each [0, 1] as copy (copy)}
        <div class="group" aria-hidden={copy === 1}>
          {#each photos as photo (photo.id)}
            <figure>
              <img
                src={photo.preview}
                alt={copy === 0 ? photo.caption || t('A little moment of joy') : ''}
                width="360"
                height="450"
                decoding="async"
                onerror={(event) => {
                  (event.currentTarget as HTMLImageElement).style.visibility = 'hidden';
                }}
              />
            </figure>
          {/each}
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .carousel {
    overflow: hidden;
    margin: 2rem 0 1rem;
    mask-image: linear-gradient(90deg, transparent, #000 5%, #000 95%, transparent);
  }
  .track {
    display: flex;
    width: max-content;
    animation: drift var(--duration) linear infinite;
  }
  .group {
    display: flex;
    gap: 1.2rem;
    padding: 1rem 0.6rem;
  }
  figure {
    width: clamp(150px, 24vw, 260px);
    margin: 0;
    padding: 0.5rem 0.5rem 1.8rem;
    background: #fffdf7;
    box-shadow: 0 5px 15px #25352b18;
    transform: rotate(-2deg);
  }
  figure:nth-child(even) {
    transform: rotate(2deg);
  }
  img {
    width: 100%;
    height: auto;
    aspect-ratio: 4 / 5;
    object-fit: cover;
    display: block;
  }
  .carousel:hover .track {
    animation-play-state: paused;
  }
  @keyframes drift {
    to {
      transform: translateX(-50%);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .track {
      animation: none;
    }
    .carousel {
      overflow-x: auto;
      mask-image: none;
    }
    .group[aria-hidden='true'] {
      display: none;
    }
  }
</style>
