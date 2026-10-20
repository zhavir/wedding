<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '#lib/i18n.svelte.ts';
  import type { Photo } from '#lib/api.ts';
  let {
    photo,
    index,
    canPrevious,
    canNext,
    busy,
    error,
    onprevious,
    onnext,
    onclose
  }: {
    photo: Photo;
    index: number;
    canPrevious: boolean;
    canNext: boolean;
    busy: boolean;
    error: string;
    onprevious: () => void;
    onnext: () => void;
    onclose: () => void;
  } = $props();
  let dialog: HTMLDialogElement;
  let touchStart: { x: number; y: number } | null = null;
  onMount(() => {
    const focused = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.showModal();
    return () => {
      dialog.close();
      document.body.style.overflow = overflow;
      if (focused instanceof HTMLElement) focused.focus();
    };
  });
  function keydown(event: KeyboardEvent) {
    if (event.altKey || event.ctrlKey || event.metaKey || busy) return;
    if (event.key === 'ArrowRight' && canNext) {
      event.preventDefault();
      onnext();
    }
    if (event.key === 'ArrowLeft' && canPrevious) {
      event.preventDefault();
      onprevious();
    }
  }
</script>

<svelte:window onkeydown={keydown} />
<dialog
  bind:this={dialog}
  class="photo-viewer"
  aria-label={t('Wedding photo viewer')}
  oncancel={(event) => {
    event.preventDefault();
    onclose();
  }}
>
  <button class="viewer-close" onclick={onclose} aria-label={t('Close photo viewer')}>×</button>
  <div
    class="viewer-stage"
    role="group"
    aria-label={t('Photo navigation')}
    onpointerdown={(event) => {
      if (event.pointerType === 'touch') touchStart = { x: event.clientX, y: event.clientY };
    }}
    onpointercancel={() => {
      touchStart = null;
    }}
    onpointerup={(event) => {
      if (!touchStart || busy) return;
      const dx = event.clientX - touchStart.x;
      const dy = event.clientY - touchStart.y;
      touchStart = null;
      if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.4) return;
      if (dx < 0 && canNext) onnext();
      if (dx > 0 && canPrevious) onprevious();
    }}
  >
    <button
      class="viewer-arrow previous"
      disabled={busy || !canPrevious}
      aria-label={t('Previous photo')}
      onclick={onprevious}>‹</button
    >
    {#key photo.id}
      {#if photo.kind === 'video' || photo.kind === 'live'}
        <!-- svelte-ignore a11y_media_has_caption -->
        <video
          controls
          playsinline
          preload="none"
          poster={photo.preview}
          src={photo.motion || photo.original}
          aria-label={photo.caption || t('Wedding memory')}
        >
          {t('Your browser cannot play this video. Download the original to watch it.')}
        </video>
        <p class="playback-help">
          {t('If playback is unavailable, download the original to watch it.')}
        </p>
      {:else}
        <img
          src={photo.preview}
          alt={photo.caption || t('A memory shared by a guest')}
          decoding="async"
          draggable="false"
        />
      {/if}
    {/key}
    <button
      class="viewer-arrow next"
      disabled={busy || !canNext}
      aria-label={t('Next photo')}
      onclick={onnext}>›</button
    >
  </div>
  <div class="viewer-caption">
    {#if error}<p role="alert">{error}</p>{/if}
    <p aria-live="polite">
      {t('Photo {number}', { number: index + 1 })} · {photo.caption ||
        t('A little moment of joy')}{#if busy}
        · {t('Loading…')}{/if}
    </p>
    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- Private presigned S3 URL. -->
    <a href={photo.original} target="_blank" rel="noreferrer">{t('Download original ↗')}</a>
    {#if photo.motion}
      <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- Private presigned original. -->
      <a href={photo.motion} target="_blank" rel="noreferrer">{t('Download Live Photo video ↗')}</a>
    {/if}
    <p class="viewer-help">{t('Swipe or use the arrows to browse. Escape closes the viewer.')}</p>
  </div>
</dialog>

<style>
  .photo-viewer {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100dvh;
    max-width: none;
    max-height: none;
    margin: 0;
    padding: 60px 16px 20px;
    border: 0;
    color: #f7f5ef;
    background: #17231af5;
    overflow: auto;
    overscroll-behavior: contain;
  }
  .photo-viewer::backdrop {
    background: #17231a;
  }
  .viewer-stage {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    height: calc(100dvh - 210px);
    min-height: 180px;
    touch-action: pan-y pinch-zoom;
  }
  .playback-help {
    position: absolute;
    bottom: 0;
    font-size: 0.8rem;
  }
  img,
  video {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    user-select: none;
  }
  button {
    min-width: 48px;
    min-height: 48px;
    color: #fff;
    background: #17231acc;
    border: 1px solid #ffffff70;
    border-radius: 50%;
    font:
      36px Arial,
      sans-serif;
  }
  button:disabled {
    cursor: default;
  }
  .viewer-close {
    position: absolute;
    top: 8px;
    right: 16px;
    z-index: 2;
  }
  .viewer-arrow {
    position: absolute;
    z-index: 1;
  }
  .previous {
    left: 0;
  }
  .next {
    right: 0;
  }
  .viewer-caption {
    text-align: center;
    padding-top: 12px;
    overflow-wrap: anywhere;
  }
  .viewer-help {
    font-size: 0.8rem;
    opacity: 0.85;
  }
</style>
