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
  let picker: HTMLDivElement;
  let trigger: HTMLButtonElement;
  const current = $derived(chapters.find((chapter) => chapter[0] === active) ?? chapters[0]);
  onMount(() => {
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
        <p class="eyebrow">{t('A day, a whole story')}</p>
        {#each chapters as [id, label], i (id)}
          <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- Same-page anchors. -->
          <a
            href={`#${id}`}
            aria-current={active === id ? 'location' : undefined}
            onclick={() => {
              expanded = false;
            }}
            ><span class="chapter-number">0{i + 1}</span><span>{t(label)}</span><span
              aria-hidden="true">↗</span
            ></a
          >
        {/each}
      </nav>
    </div>
  </div>
  <button
    class="chapter-trigger"
    type="button"
    bind:this={trigger}
    aria-label={t('Explore the chapters')}
    aria-expanded={expanded}
    aria-controls="chapter-links"
    onclick={() => {
      expanded = !expanded;
    }}
  >
    <span class="picker-star" aria-hidden="true">✳</span><span class="picker-label"
      ><small>{t('You are here')}</small>{t(current[1])}</span
    ><span class="picker-toggle" aria-hidden="true">{expanded ? '−' : '+'}</span>
  </button>
</div>
