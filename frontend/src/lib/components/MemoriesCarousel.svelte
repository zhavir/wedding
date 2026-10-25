<script lang="ts">
  import { api, type Photo } from '#lib/api.ts';
  import { session } from '#lib/session.svelte.ts';
  import { t } from '#lib/i18n.svelte.ts';
  let photos = $state<
    Pick<Photo, 'id' | 'caption' | 'preview' | 'width' | 'height' | 'orientation'>[]
  >([]);
  // Fetch once per authenticated session and discard stale responses on sign-out.
  $effect(() => {
    const guest = session.guest?.id;
    void session.revision;
    photos = [];
    if (!guest) return;
    let mounted = true;
    void api<{
      items: Pick<Photo, 'id' | 'caption' | 'preview' | 'width' | 'height' | 'orientation'>[];
    }>('/photos/carousel')
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
  <div class="carousel mt-8 mb-4 overflow-hidden" aria-label={t('Memories from our guests')}>
    <div class="track flex w-max" style={`--duration: ${Math.max(30, photos.length * 5)}s`}>
      {#each [0, 1] as copy (copy)}
        <div class="group flex items-center gap-[1.2rem] px-[0.6rem] py-4" aria-hidden={copy === 1}>
          {#each photos as photo (photo.id)}
            <figure
              class={photo.orientation}
              class:portrait={photo.width > 0 && photo.height > photo.width}
              style={`--photo-ratio: ${photo.width > 0 && photo.height > 0 ? photo.width / photo.height : 1}`}
            >
              <img
                src={photo.preview}
                alt={copy === 0 ? photo.caption || t('A little moment of joy') : ''}
                width={photo.width || undefined}
                height={photo.height || undefined}
                decoding="async"
                onerror={(event) => {
                  (event.currentTarget as HTMLImageElement).style.visibility = 'hidden';
                }}
              />
              <figcaption>{photo.caption || ''}</figcaption>
            </figure>
          {/each}
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .carousel {
    mask-image: linear-gradient(90deg, transparent, #000 5%, #000 95%, transparent);
  }
  .track {
    animation: drift var(--duration) linear infinite;
  }
  figure {
    width: calc(clamp(150px, 24vw, 260px) * var(--photo-ratio));
    flex: none;
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: 0.5rem 0.5rem 1.8rem;
    background: #fffdf7;
    box-shadow: 0 5px 15px #25352b18;
    transform: rotate(-2deg);
  }
  /* Enlarge portrait photos only; landscape and square photos keep their original sizing. */
  figure.portrait {
    width: clamp(190px, calc(clamp(300px, 40vw, 440px) * var(--photo-ratio)), 300px);
  }
  figure:nth-child(even) {
    transform: rotate(2deg);
  }
  img {
    width: 100%;
    height: auto;
    aspect-ratio: var(--photo-ratio);
    object-fit: contain;
    display: block;
  }
  figcaption {
    box-sizing: border-box;
    height: 3.6rem;
    flex: none;
    padding-top: 0.6rem;
    overflow: hidden;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    font:
      italic 0.85rem Georgia,
      serif;
    overflow-wrap: anywhere;
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
