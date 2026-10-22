<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '#lib/i18n.svelte.ts';
  const chapters = [
    ['home', 'The beginning'],
    ['story', 'Our story'],
    ['details', 'The day'],
    ['menu', 'At the table'],
    ['travel', 'Getting there'],
    ['rsvp', 'RSVP'],
    ['memories', 'Gallery']
  ];
  let active = $state('home');
  let expanded = $state(false);
  let ready = $state(false);
  let picker: HTMLDivElement;
  let trigger: HTMLButtonElement;
  onMount(() => {
    ready = true;
    let frame = 0;
    function update() {
      frame = 0;
      active =
        chapters
          .filter(
            ([id]) =>
              (document.getElementById(id)?.getBoundingClientRect().top ?? Infinity) <
              innerHeight * 0.5
          )
          .at(-1)?.[0] ?? 'home';
    }
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    const outside = (event: PointerEvent) => {
      if (!picker.contains(event.target as Node)) expanded = false;
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && expanded) {
        expanded = false;
        trigger.focus();
      }
    };
    update();
    addEventListener('scroll', schedule, { passive: true });
    addEventListener('pointerdown', outside);
    addEventListener('keydown', escape);
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener('scroll', schedule);
      removeEventListener('pointerdown', outside);
      removeEventListener('keydown', escape);
    };
  });
</script>

<div class="chapter-picker" class:expanded bind:this={picker}>
  <div class="chapter-panel" aria-hidden={!expanded} inert={!expanded}>
    <div class="chapter-panel-clip">
      <nav class="chapter-nav" id="chapter-links" aria-label={t('Jump to a chapter')}>
        {#each chapters as [id, label], i (id)}
          <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- Same-page anchors. -->
          <a
            href={`#${id}`}
            style={`--item-index:${i}`}
            aria-current={active === id ? 'location' : undefined}
            onclick={() => {
              expanded = false;
            }}
            ><span class="chapter-number">0{i + 1}</span><span class="chapter-copy"
              ><span class="chapter-title">{t(label)}</span></span
            ><svg
              class="chapter-arrow"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg
            ></a
          >
        {/each}
      </nav>
    </div>
  </div>
  <button
    class="chapter-trigger"
    disabled={!ready}
    type="button"
    bind:this={trigger}
    aria-label={t('Explore the chapters')}
    aria-expanded={expanded}
    aria-controls="chapter-links"
    onclick={() => {
      expanded = !expanded;
    }}
  >
    <svg
      class="menu-toggle-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      aria-hidden="true"
    >
      <path class="toggle-top" d="M4 7h16" />
      <path class="toggle-middle" d="M4 12h16" />
      <path class="toggle-bottom" d="M4 17h16" />
    </svg>
  </button>
</div>

<style>
  /* Keep the animated panel in its own clipped layer: no transient scrollbars. */
  .chapter-panel {
    overflow: clip;
    scrollbar-width: none;
    contain: paint;
  }

  .chapter-panel-clip {
    overflow: clip;
    scrollbar-width: none;
  }

  .chapter-panel::-webkit-scrollbar,
  .chapter-panel-clip::-webkit-scrollbar,
  .chapter-nav::-webkit-scrollbar {
    display: none;
  }

  .chapter-nav {
    overflow-x: clip;
    scrollbar-width: none;
  }

  .chapter-nav a {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }

  .chapter-copy {
    display: flex;
    flex: 1;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
  }

  .chapter-title {
    display: block;
  }

  .chapter-preview {
    display: block;
    font-size: 0.72rem;
    line-height: 1.35;
    letter-spacing: 0.065em;
    opacity: 0.62;
    transform: translateY(3px);
    transition:
      opacity 220ms ease,
      transform 220ms ease;
  }

  .expanded .chapter-preview,
  .chapter-nav a:hover .chapter-preview,
  .chapter-nav a:focus-visible .chapter-preview {
    opacity: 0.8;
    transform: translateY(0);
  }

  .chapter-arrow {
    flex-shrink: 0;
  }

  @media (max-width: 640px) {
    .chapter-nav a {
      gap: 10px;
    }
    .chapter-preview {
      font-size: 0.65rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .chapter-preview {
      transition: none;
      transform: none;
    }
  }
</style>
