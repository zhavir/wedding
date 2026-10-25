<script lang="ts">
  import { onMount } from 'svelte';
  import Hero from './Hero.svelte';
  import Monogram from './Monogram.svelte';
  import { t } from '#lib/i18n.svelte.ts';

  let scene: HTMLDivElement;
  let progress = $state(0);
  let viewport = $state({ width: 1200, height: 800 });
  let reduced = $state(false);
  const ease = (value: number) => {
    const x = Math.max(0, Math.min(1, value));
    return x * x * (3 - 2 * x);
  };
  const growth = $derived(ease(progress / 0.32));
  const opening = $derived(ease((progress - 0.32) / 0.3));
  const release = $derived(reduced ? 1 : ease((progress - 0.62) / 0.38));
  const width = $derived(
    Math.min(viewport.width * 0.82, 820, Math.max(140, viewport.height - 320) * 1.55)
  );
  const height = $derived(width / 1.55);
  const scale = $derived(
    1 + growth * (Math.max(viewport.width / width, viewport.height / height) * 1.04 - 1)
  );
  const renderWidth = $derived(width * scale);
  const renderHeight = $derived(height * scale);
  const flapTip = $derived(renderHeight * 0.5 * Math.cos(opening * Math.PI));
  const sealSize = $derived(Math.max(52, Math.min(76, viewport.width * 0.09)) * scale);
  const envelopeStyle = $derived(
    `width:${renderWidth}px;height:${renderHeight}px;transform:translate(-50%,calc(-50% + ${release * viewport.height * 1.8}px))`
  );
  const insetX = $derived(Math.max(0, (viewport.width - width * 0.88 * scale) / 2) * (1 - release));
  const insetY = $derived(
    Math.max(0, (viewport.height - height * 0.82 * scale) / 2) * (1 - release)
  );

  onMount(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    const update = () => {
      frame = 0;
      reduced = preference.matches;
      viewport = { width: innerWidth, height: innerHeight };
      progress = reduced
        ? 1
        : Math.max(
            0,
            Math.min(
              1,
              -scene.getBoundingClientRect().top / Math.max(1, scene.offsetHeight - innerHeight)
            )
          );
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    addEventListener('scroll', schedule, { passive: true });
    addEventListener('resize', schedule);
    preference.addEventListener('change', schedule);
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener('scroll', schedule);
      removeEventListener('resize', schedule);
      preference.removeEventListener('change', schedule);
    };
  });
  function skip() {
    window.scrollTo({
      top: scrollY + scene.getBoundingClientRect().top + scene.offsetHeight - innerHeight,
      behavior: reduced ? 'instant' : 'smooth'
    });
  }
</script>

<div
  class="envelope-scene"
  class:opened={release >= 0.995}
  bind:this={scene}
  style={`--page-reveal:${release}`}
>
  <div class="envelope-stage">
    <div class="envelope-back" style={envelopeStyle} aria-hidden="true"></div>
    <div class="letter-sheet" style={`clip-path:inset(${insetY}px ${insetX}px)`}>
      <Hero progress={release} />
    </div>
    <div class="envelope" style={envelopeStyle} aria-hidden="true">
      <svg class="envelope-paper" viewBox={`0 0 ${renderWidth} ${renderHeight}`}>
        <defs>
          <linearGradient id="pocket-paper" x2="0" y2="1">
            <stop stop-color="#E5D1A4" /><stop offset="1" stop-color="#C4A363" />
          </linearGradient>
        </defs>
        <path fill="#C9AA70" d={`M0 0L${renderWidth / 2} ${renderHeight / 2}L0 ${renderHeight}Z`} />
        <path
          fill="#D1B57F"
          d={`M${renderWidth} 0L${renderWidth / 2} ${renderHeight / 2}L${renderWidth} ${renderHeight}Z`}
        />
        <path
          fill="url(#pocket-paper)"
          d={`M0 ${renderHeight}L${renderWidth / 2} ${renderHeight / 2}L${renderWidth} ${renderHeight}Z`}
        />
        <path
          class="paper-edge"
          d={`M0 0V${renderHeight}H${renderWidth}V0 M0 0L${renderWidth / 2} ${renderHeight / 2}L${renderWidth} 0 M0 ${renderHeight}L${renderWidth / 2} ${renderHeight / 2}L${renderWidth} ${renderHeight}`}
        />
        <path
          class="paper-edge top-edge"
          opacity={Math.max(0, 1 - opening * 12)}
          d={`M0 0H${renderWidth}`}
        />
      </svg>
    </div>
    <div
      class="flap-layer"
      class:flap-front={opening < 0.5}
      style={envelopeStyle}
      data-opening={opening}
      aria-hidden="true"
    >
      <svg class="envelope-paper" viewBox={`0 0 ${renderWidth} ${renderHeight}`}>
        <path
          fill={opening < 0.5 ? '#D6B77A' : '#C4A363'}
          d={`M0 0H${renderWidth}L${renderWidth / 2} ${flapTip}Z`}
        />
        <path class="paper-edge" d={`M0 0L${renderWidth / 2} ${flapTip}L${renderWidth} 0`} />
      </svg>
      {#if opening < 0.5}
        <span
          class="wax-seal"
          style={`width:${sealSize}px;top:${flapTip}px;opacity:${Math.max(0, 1 - opening * 2)}`}
          ><Monogram /></span
        >
      {/if}
    </div>
    <button
      class="skip-opening"
      onclick={skip}
      inert={release >= 0.995}
      style={`opacity:${1 - release}`}
      >{t('Scroll to reveal')} <span class="scroll-line" aria-hidden="true"></span></button
    >
  </div>
</div>

<style>
  .envelope-scene {
    position: relative;
    height: 400svh;
    background: #f9f7f2;
  }
  .envelope-stage {
    position: sticky;
    top: 0;
    height: 100svh;
    overflow: hidden;
    isolation: isolate;
    background: radial-gradient(ellipse at center, #f9f7f2, #e9efe7);
  }
  .envelope,
  .envelope-back,
  .flap-layer {
    position: absolute;
    left: 50%;
    top: 50%;
    transform-origin: center;
  }
  .flap-layer {
    z-index: 0;
    pointer-events: none;
  }
  .flap-front {
    z-index: 3;
  }
  .envelope-back {
    z-index: 0;
    background: #b49356;
    box-shadow: 0 25px 65px #496a5535;
    border-radius: 5px;
  }
  .letter-sheet {
    position: absolute;
    inset: 0;
    z-index: 1;
    background: #f9f7f2;
    transform-origin: center;
  }
  .letter-sheet :global(.hero) {
    height: 100svh;
    min-height: 100svh;
    box-sizing: border-box;
  }
  .envelope {
    z-index: 2;
    pointer-events: none;
  }
  .envelope-paper {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
  }
  .paper-edge {
    fill: none;
    stroke: #977945;
    stroke-width: 1.2;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }
  .wax-seal {
    position: absolute;
    left: 50%;
    aspect-ratio: 1;
    transform: translate(-50%, -50%);
  }
  .skip-opening {
    position: absolute;
    z-index: 4;
    bottom: max(1.5rem, env(safe-area-inset-bottom));
    left: 50%;
    transform: translateX(-50%);
    display: grid;
    justify-items: center;
    gap: 0.85rem;
    padding: 0.6rem 1rem;
    border: 0;
    background: none;
    color: #496a55;
    font:
      400 0.6rem/1.5 'DM Sans',
      sans-serif;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  .scroll-line {
    display: block;
    position: relative;
    width: 1px;
    height: 48px;
    background: #496a5525;
    overflow: hidden;
  }
  .scroll-line::after {
    content: '';
    position: absolute;
    inset: 0;
    background: #496a55;
    animation: scroll-cue 2.2s ease-in-out infinite;
  }
  @keyframes scroll-cue {
    0% {
      transform: translateY(-105%);
    }
    55%,
    70% {
      transform: translateY(0);
    }
    100% {
      transform: translateY(105%);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .envelope-scene {
      height: 100svh;
    }
    .flap-layer,
    .envelope,
    .envelope-back,
    .skip-opening {
      display: none;
    }
    .letter-sheet {
      transform: none !important;
    }
  }
</style>
