<script lang="ts">
  import { onMount } from 'svelte';
  import Hero from './Hero.svelte';
  import { t } from '#lib/i18n.svelte.ts';
  let scene: HTMLElement;
  let progress = $state(0);
  let opened = $state(false);
  const foldPath = (i: number) => {
    const top = 1 - Math.pow(progress, 1.35);
    const hem = 1 - Math.pow(progress, 0.65);
    const a = (i * 100) / 12,
      b = ((i + 1) * 100) / 12 + 0.025;
    return `M${a * top} 0 H${b * top} C${b * top} 320 ${b * hem} 670 ${b * hem} 1000 H${a * hem} C${a * hem} 670 ${a * top} 320 ${a * top} 0Z`;
  };
  let stage: HTMLElement;
  let stageHeight = $state(0);
  let reduced = $state(false);
  onMount(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    const update = () => {
      frame = 0;
      reduced = preference.matches;
      const position = Math.min(
        1,
        Math.max(0, -scene.getBoundingClientRect().top / (innerHeight * 0.65))
      );
      if (reduced || position >= 0.995) opened = true;
      progress = opened ? 1 : position;
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    const observer = new ResizeObserver(() => {
      stageHeight = stage.offsetHeight;
      schedule();
    });
    observer.observe(stage);
    update();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    preference.addEventListener('change', schedule);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      preference.removeEventListener('change', schedule);
    };
  });
  function open() {
    if (progress >= 0.9) {
      document
        .getElementById('story')
        ?.scrollIntoView({ behavior: reduced ? 'instant' : 'smooth' });
      return;
    }
    window.scrollTo({
      top: scrollY + scene.getBoundingClientRect().top + innerHeight * 0.65,
      behavior: reduced ? 'instant' : 'smooth'
    });
  }
</script>

<div
  class="opening-scene"
  class:reduced
  class:opened
  bind:this={scene}
  style={`--opening:${progress}; --stage-height:${stageHeight}px`}
>
  <div class="opening-stage" bind:this={stage}>
    {#each ['left', 'right'] as side (side)}
      <svg
        class={`curtain curtain-${side}`}
        viewBox="0 0 100 1000"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={`linen-${side}`}>
            <stop offset="0" stop-color="#b4a68e" />
            <stop offset=".12" stop-color="#d7cbb6" />
            <stop offset=".38" stop-color="#f6efe1" />
            <stop offset=".55" stop-color="#eee4d2" />
            <stop offset=".82" stop-color="#c9baa1" />
            <stop offset="1" stop-color="#a99a81" />
          </linearGradient>
        </defs>
        {#each Array.from({ length: 12 }, (_, i) => i) as fold (fold)}
          <path class="fabric-pleat" d={foldPath(fold)} fill={`url(#linen-${side})`} />
        {/each}
      </svg>
    {/each}
    <Hero {progress} />
    <button
      type="button"
      class="scroll-cue curtain-cue"
      class:departed={progress > 0.01 || reduced}
      tabindex={progress > 0.01 || reduced ? -1 : 0}
      onclick={open}
      aria-label={t('Open our invitation')}
    >
      <span>{t('Scroll to reveal')}</span><i aria-hidden="true"></i>
    </button>
  </div>
</div>
