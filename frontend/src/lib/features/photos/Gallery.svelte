<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { onMount, untrack } from 'svelte';
  import { api, type Photo } from '#lib/api.ts';
  import InvitationGate from '#lib/components/InvitationGate.svelte';
  import PhotoViewer from './PhotoViewer.svelte';
  import { session } from '#lib/session.svelte.ts';
  // Center the active upload/invitation card on arrival, including on iOS Safari.
  // The same #upload anchor is used for both the signed-in form and invitation gate.
  function centerUploadCard() {
    const card = document.getElementById('upload');
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
    const viewportTop = window.visualViewport?.offsetTop ?? 0;
    // Tall cards cannot fit in the viewport; show their beginning in that case.
    const offset =
      rect.height <= viewportHeight
        ? (viewportHeight - rect.height) / 2
        : Math.min(96, viewportHeight * 0.12);
    const top = Math.max(0, window.scrollY + rect.top - viewportTop - offset);
    window.scrollTo({ top, left: 0, behavior: 'instant' });
  }

  let centerFrame1 = 0;
  let centerFrame2 = 0;
  function scheduleCenterUpload() {
    cancelAnimationFrame(centerFrame1);
    cancelAnimationFrame(centerFrame2);
    centerFrame1 = requestAnimationFrame(() => {
      centerFrame2 = requestAnimationFrame(centerUploadCard);
    });
  }

  onMount(() => {
    // Ordinary Gallery navigation opens at the top. Only #upload targets the form.
    if (window.location.hash === '#upload') scheduleCenterUpload();
    else window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
    const handleHashChange = () => {
      if (window.location.hash === '#upload') scheduleCenterUpload();
      else if (!window.location.hash) window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => {
      cancelAnimationFrame(centerFrame1);
      cancelAnimationFrame(centerFrame2);
      window.removeEventListener('hashchange', handleHashChange);
    };
  });

  // The invitation gate can be replaced with the upload form after session hydration.
  // Recenter on that replacement, but not on photo updates or user typing.
  $effect(() => {
    const ready = session.ready;
    const guest = Boolean(session.guest);
    if (typeof window === 'undefined') return;
    void ready;
    void guest;
    if (window.location.hash === '#upload') scheduleCenterUpload();
  });
  let photos = $state<Photo[]>([]);
  let cursor = $state<string | null>(null);
  let busy = $state(false);
  let hasMore = $state(false);
  let loadingAll = $state(false);
  let error = $state('');
  let status = $state('');
  let uploading = $state(false);
  let files = $state<FileList>();
  let dragging = $state(false);
  let dragDepth = 0;
  const canDrop = () => Boolean(session.guest && session.ready && !uploading);
  const hasFiles = (event: DragEvent) =>
    Array.from(event.dataTransfer?.types || []).includes('Files');
  function resetDrag() {
    dragDepth = 0;
    dragging = false;
  }
  function enterDrag(event: DragEvent) {
    if (!canDrop() || !hasFiles(event)) return;
    event.preventDefault();
    dragDepth++;
    dragging = true;
  }
  function overDrag(event: DragEvent) {
    if (!hasFiles(event)) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = canDrop() ? 'copy' : 'none';
  }
  function leaveDrag() {
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) dragging = false;
  }
  function dropMedia(event: DragEvent) {
    if (hasFiles(event)) event.preventDefault();
    resetDrag();
    if (canDrop() && event.dataTransfer?.files.length) files = event.dataTransfer.files;
  }
  function removeFile(file: File) {
    if (uploading) return;
    const remaining = new DataTransfer();
    Array.from(files || [])
      .filter((selected) => selected !== file)
      .forEach((selected) => remaining.items.add(selected));
    files = remaining.files;
  }
  let caption = $state('');
  let previews = $state<{ file: File; url: string; failed: boolean }[]>([]);
  $effect(() => {
    const next = Array.from(files || []).map((file) => ({
      file,
      url: URL.createObjectURL(file),
      failed: false
    }));
    previews = next;
    return () => next.forEach((item) => URL.revokeObjectURL(item.url));
  });
  let input = $state<HTMLInputElement>();
  let viewIndex = $state<number | null>(null);
  const viewed = $derived(viewIndex === null ? undefined : photos[viewIndex]);
  let generation = 0;
  $effect(() => {
    void session.revision;
    if (session.guest && session.ready) untrack(() => void load(true));
    else {
      generation++;
      photos = [];
      files = undefined;
      busy = false;
      loadingAll = false;
      viewIndex = null;
    }
  });
  async function load(reset = false): Promise<boolean> {
    if (!session.guest || (!reset && busy)) return false;
    if (reset) {
      generation++;
      viewIndex = null;
    }
    const current = generation;
    busy = true;
    error = '';
    const previousCursor = reset ? null : cursor;
    try {
      const result = await api<{ items: Photo[]; cursor: string | null }>(
        `/photos${previousCursor ? '?cursor=' + encodeURIComponent(previousCursor) : ''}`
      );
      if (current !== generation || !session.guest) return false;
      if (result.cursor && result.cursor === previousCursor)
        throw new Error(t('The gallery could not load the next page. Please try again.'));
      photos = reset
        ? result.items
        : [
            ...photos,
            ...result.items.filter((photo) => !photos.some((existing) => existing.id === photo.id))
          ];
      cursor = result.cursor;
      hasMore = !!cursor;
      return true;
    } catch (e) {
      if (current === generation) error = (e as Error).message;
      return false;
    } finally {
      if (current === generation) busy = false;
    }
  }
  async function loadAll() {
    loadingAll = true;
    const current = generation;
    while (loadingAll && hasMore && current === generation && session.guest) {
      if (!(await load())) break;
    }
    loadingAll = false;
  }
  async function nextPhoto() {
    if (viewIndex === null || busy) return;
    const current = viewIndex;
    if (current + 1 >= photos.length && hasMore) await load();
    if (viewIndex === current && current + 1 < photos.length) viewIndex = current + 1;
  }
  function mediaType(file: File): string {
    const extensions: Record<string, string> = {
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      png: 'image/png',
      webp: 'image/webp',
      heic: 'image/heic',
      heif: 'image/heif',
      mov: 'video/quicktime',
      mp4: 'video/mp4',
      webm: 'video/webm'
    };
    return file.type || extensions[file.name.split('.').pop()?.toLowerCase() || ''] || '';
  }
  async function upload() {
    if (!files?.length || uploading) return;
    uploading = true;
    status = '';
    try {
      const selected = Array.from(files);
      const used: File[] = [];
      const stem = (file: File) => file.name.replace(/\.[^.]+$/, '').toLowerCase();
      const jobs = selected
        .filter((file) => mediaType(file).startsWith('image/'))
        .map((file) => {
          const motion = selected.find(
            (candidate) =>
              candidate.name.toLowerCase().endsWith('.mov') &&
              stem(candidate) === stem(file) &&
              !used.includes(candidate)
          );
          used.push(file);
          if (motion) used.push(motion);
          return { file, motion };
        });
      jobs.push(
        ...selected
          .filter((file) => !used.includes(file))
          .map((file) => ({ file, motion: undefined }))
      );
      const allowed = [
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/heic',
        'image/heif',
        'video/mp4',
        'video/quicktime',
        'video/webm'
      ];
      for (const file of selected) {
        const type = mediaType(file);
        if (
          !allowed.includes(type) ||
          !file.size ||
          (type.startsWith('image/') && file.size > 25 * 1024 * 1024)
        )
          throw new Error(t('Choose supported images up to 25 MB or videos.'));
      }
      type UploadTarget = {
        url?: string;
        fields?: Record<string, string>;
        multipart?: boolean;
        part_size?: number;
      };
      type Part = { number: number; etag: string };
      for (let index = 0; index < jobs.length; index++) {
        const { file, motion } = jobs[index];
        status = t('Uploading {current} of {total}…', { current: index + 1, total: jobs.length });
        const result = await api<{
          id: string;
          upload: UploadTarget;
          motion_upload: UploadTarget | null;
        }>('/photos/upload', 'POST', {
          filename: file.name,
          content_type: mediaType(file),
          size: file.size,
          caption,
          motion_size: motion?.size || 0,
          motion_content_type: motion ? mediaType(motion) : ''
        });
        async function send(target: UploadTarget, value: File, isMotion = false): Promise<Part[]> {
          if (target.multipart && target.part_size) {
            const parts: Part[] = [];
            for (
              let offset = 0, number = 1;
              offset < value.size;
              offset += target.part_size, number++
            ) {
              const { url } = await api<{ url: string }>(
                `/photos/${result.id}/parts/${number}?motion=${isMotion}`
              );
              const response = await fetch(url, {
                method: 'PUT',
                body: value.slice(offset, offset + target.part_size)
              });
              const etag = response.headers.get('ETag');
              if (!response.ok || !etag) throw new Error(t('Upload failed. Please try again.'));
              parts.push({ number, etag });
            }
            return parts;
          }
          const data = new FormData();
          Object.entries(target.fields || {}).forEach(([key, entry]) => data.append(key, entry));
          data.append('file', value);
          if (!(await fetch(target.url!, { method: 'POST', body: data })).ok)
            throw new Error(t('Upload failed. Please try again.'));
          return [];
        }
        const parts = await send(result.upload, file);
        const motion_parts =
          motion && result.motion_upload ? await send(result.motion_upload, motion, true) : [];
        await api(`/photos/${result.id}/complete`, 'POST', { parts, motion_parts });
      }
      status = t('{count} memories received. They will appear after the couple approves them.', {
        count: jobs.length
      });
      files = undefined;
      if (input) input.value = '';
      caption = '';
      await load(true);
    } catch (error) {
      status = (error as Error).message;
    } finally {
      uploading = false;
    }
  }
</script>

<svelte:window
  ondragenter={enterDrag}
  ondragover={overDrag}
  ondragleave={leaveDrag}
  ondrop={dropMedia}
  ondragend={resetDrag}
  onblur={resetDrag}
/>

{#if dragging && canDrop()}
  <div class="media-drop-overlay" role="status">
    <div class="media-drop-message">
      <span class="drop-icon" aria-hidden="true">↓</span>
      <h2>{t('Drop photos and videos')}</h2>
      <p>{t('Add your memories to the selection, ready to share.')}</p>
    </div>
  </div>
{/if}

<section class="section memories" id="memories">
  <div class="section-heading">
    <div>
      <p class="eyebrow">{t('04 / THROUGH YOUR EYES')}</p>
      <h2>{t('The moments')}<br /><em>{t('we’ll keep forever.')}</em></h2>
    </div>
    <p>{t('Share the happy tears, the dancing,')}<br />{t('and the little moments in between.')}</p>
  </div>
  {#if session.guest && session.ready}<form
      id="upload"
      class:dragging
      class="upload-box"
      onsubmit={(e) => {
        e.preventDefault();
        void upload();
      }}
    >
      <h3>{t('A memory worth sharing')}</h3>
      <p>{t('Drag photos and videos here, or choose multiple files from your device.')}</p>
      <p>{t('Original quality. Photos and videos are published after approval.')}</p>
      <label class="file-picker" for="photos">{t('Choose photos and videos')}</label>
      <input
        class="media-file-input"
        bind:this={input}
        id="photos"
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic,image/heif,video/mp4,video/quicktime,video/webm,.heic,.heif,.mov"
        multiple
        required
        bind:files
        disabled={uploading}
      />
      {#if previews.length}<div class="selected-previews" aria-live="polite">
          {#each previews as preview (preview.url)}<figure class="selected-preview">
              {#if preview.failed}<div class="preview-fallback">{t('Preview unavailable')}</div>
              {:else if mediaType(preview.file).startsWith('video/')}<video
                  src={preview.url}
                  controls
                  muted
                  playsinline
                  preload="metadata"
                  onerror={() => (preview.failed = true)}><track kind="captions" /></video
                >
              {:else}<img
                  src={preview.url}
                  alt={preview.file.name}
                  onerror={() => (preview.failed = true)}
                />{/if}
              <button
                type="button"
                class="remove-preview"
                aria-label={t('Remove {name}', { name: preview.file.name })}
                title={t('Remove {name}', { name: preview.file.name })}
                disabled={uploading}
                onclick={() => removeFile(preview.file)}><span aria-hidden="true">×</span></button
              >
              <figcaption>{preview.file.name}</figcaption>
            </figure>{/each}
        </div>{/if}
      <label for="caption">{t('A little caption')} <span>{t('(optional)')}</span></label><input
        id="caption"
        bind:value={caption}
        maxlength="200"
      /><button
        class="button"
        class:working={uploading}
        aria-busy={uploading}
        disabled={uploading || !files?.length}
        >{uploading ? t('Sharing your memories…') : t('Share the love ↗')}</button
      >
      <p role="status">{status}</p>
    </form>
    <div class="gallery">
      {#each photos as photo, index (photo.id)}<button
          class="photo-card"
          onclick={() => (viewIndex = index)}
          aria-label={`${t('Open photo:')} ${photo.caption || t('Wedding memory')}`}
        >
          <img
            src={photo.preview}
            alt={photo.caption || t('A memory shared by a guest')}
            loading="lazy"
            decoding="async"
            width="600"
            height="600"
          />
          <span>{photo.caption || t('A little moment of joy')}<small>{t('View photo')}</small></span
          >
        </button>{/each}
    </div>
    {#if !busy && !photos.length}<p class="empty-gallery">
        {t('Our memory book is waiting for its first photograph.')}
      </p>{/if}
    <p role="alert">{error}</p>
    <div class="gallery-controls">
      {#if hasMore || error}<button
          class="text-button"
          disabled={busy || loadingAll}
          onclick={() => load()}>{busy ? t('Loading…') : t('Load more memories ↓')}</button
        >{/if}
      {#if hasMore}{#if loadingAll}<button class="text-button" onclick={() => (loadingAll = false)}
            >{t('Stop loading')}</button
          >{:else}<button class="text-button" disabled={busy} onclick={loadAll}
            >{t('Load all photos')}</button
          >{/if}{/if}
      <button class="text-button refresh" disabled={busy || loadingAll} onclick={() => load(true)}
        >{t('Refresh gallery ↻')}</button
      >
      <p aria-live="polite">{t('{count} photos loaded', { count: photos.length })}</p>
    </div>
  {:else}<div class="rsvp-card gallery-gate" id="upload"><InvitationGate /></div>{/if}
</section>

{#if viewed && viewIndex !== null}<PhotoViewer
    photo={viewed}
    index={viewIndex}
    canPrevious={viewIndex > 0}
    canNext={viewIndex + 1 < photos.length || hasMore}
    {busy}
    {error}
    onprevious={() => {
      if (viewIndex !== null && viewIndex > 0) viewIndex--;
    }}
    onnext={() => {
      void nextPhoto();
    }}
    onclose={() => (viewIndex = null)}
  />{/if}

<style>
  .media-drop-overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: grid;
    place-items: center;
    padding: 1.5rem;
    background: rgb(32 44 36 / 70%);
    backdrop-filter: blur(5px);
    pointer-events: none;
  }
  .media-drop-message {
    width: min(100%, 38rem);
    padding: clamp(1.5rem, 5vw, 4rem);
    border: 2px dashed currentColor;
    border-radius: 1rem;
    background: #faf7f0;
    color: #30483b;
    text-align: center;
  }
  .drop-icon {
    font-size: 3rem;
  }
  .media-drop-message h2 {
    font-size: clamp(2rem, 6vw, 3rem);
  }
  .remove-preview {
    position: absolute;
    top: 0.4rem;
    right: 0.4rem;
    display: grid;
    place-items: center;
    width: 2.75rem;
    height: 2.75rem;
    border: 1px solid #fff;
    border-radius: 50%;
    background: rgb(28 35 30 / 85%);
    color: #fff;
    font-size: 1.6rem;
    line-height: 1;
    cursor: pointer;
    transition: background-color 150ms ease;
  }
  .remove-preview:hover:not(:disabled),
  .remove-preview:focus-visible {
    background: #b42318;
  }
  .remove-preview:focus-visible {
    outline: 3px solid #b42318;
    outline-offset: 3px;
  }
  .remove-preview:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  @media (prefers-reduced-motion: reduce) {
    .remove-preview {
      transition: none;
    }
  }

  .media-file-input {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
  .file-picker {
    display: inline-block;
    cursor: pointer;
    padding: 0.8rem 1.2rem;
    border: 1px solid currentColor;
    border-radius: 0.3rem;
  }
  .file-picker:has(+ input:focus-visible) {
    outline: 2px solid currentColor;
    outline-offset: 3px;
  }
  .selected-previews {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 1rem;
    margin-block: 1rem;
  }
  .selected-preview {
    position: relative;
    margin: 0;
    min-width: 0;
  }
  .selected-preview img,
  .selected-preview video,
  .preview-fallback {
    width: 100%;
    height: 130px;
    object-fit: cover;
    border-radius: 0.4rem;
    background: #e9e4d9;
  }
  .selected-preview figcaption {
    font-size: 0.85rem;
    overflow-wrap: anywhere;
    padding-top: 0.4rem;
  }
  .preview-fallback {
    display: grid;
    place-items: center;
    padding: 0.5rem;
  }
</style>
