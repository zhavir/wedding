<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  let container: HTMLDivElement;
  let path: SVGPathElement;
  let thread: SVGSVGElement;
  let width = $state(100);
  let height = $state(1000);
  let progress = $state(0);
  let x = $state(50);
  let y = $state(0);
  const icons = ['♡', '♧', '✧', '♫'];
  const curve = $derived(
    `M${width / 2} 0 ` +
      w.schedule
        .map((_, i) => {
          const step = height / w.schedule.length;
          const side = width * (i % 2 ? 0.85 : 0.15);
          return `C${width / 2} ${step * (i + 0.15)} ${side} ${step * (i + 0.15)} ${side} ${step * (i + 0.5)} S${width / 2} ${step * (i + 0.85)} ${width / 2} ${step * (i + 1)}`;
        })
        .join(' ')
  );
  onMount(() => {
    let frame = 0;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    function update() {
      frame = 0;
      const rect = container.getBoundingClientRect();
      const vertical = Math.max(
        0,
        Math.min(height, ((innerHeight * 0.65 - rect.top) / rect.height) * height)
      );
      const length = path.getTotalLength();
      // Invert the curve's Y coordinate so the bead stays at the reader's scroll position.
      let low = 0,
        high = length;
      for (let i = 0; i < 16; i++) {
        const middle = (low + high) / 2;
        if (path.getPointAtLength(middle).y < vertical) low = middle;
        else high = middle;
      }
      const distance = vertical <= 0 ? 0 : vertical >= height ? length : (low + high) / 2;
      const point = path.getPointAtLength(distance);
      progress = preference.matches ? 1 : distance / length;
      x = (point.x / width) * 100;
      y = (point.y / height) * 100;
    }
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    // Match SVG units to rendered pixels so dash length and the marker use the
    // same geometry, including the narrower mobile thread.
    const measure = () => {
      const bounds = thread.getBoundingClientRect();
      width = Math.max(1, bounds.width);
      height = Math.max(1, bounds.height);
      schedule();
    };
    const resize = new ResizeObserver(measure);
    resize.observe(container);
    resize.observe(thread);
    measure();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    preference.addEventListener('change', schedule);
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      preference.removeEventListener('change', schedule);
    };
  });
</script>

<div class="ribbon-timeline" bind:this={container}>
  <svg
    class="timeline-thread"
    bind:this={thread}
    viewBox={`0 0 ${width} ${height}`}
    preserveAspectRatio="none"
    fill="none"
    aria-hidden="true"
  >
    <path d={curve} class="thread-base" vector-effect="non-scaling-stroke" />
    <path
      bind:this={path}
      d={curve}
      class="thread-progress"
      pathLength="1"
      stroke-dasharray="1"
      stroke-dashoffset={1 - progress}
      vector-effect="non-scaling-stroke"
    />
  </svg>
  <span class="timeline-bead" style={`--cursor-x:${x};top:${y}%`} aria-hidden="true">✦</span>
  {#each w.schedule as event, i (event.time)}
    <article class="timeline-event" class:arrived={progress >= (i + 0.3) / w.schedule.length}>
      <div class="event-copy">
        <span class="event-number">0{i + 1}</span>
        <p class="eyebrow">{w.scheduleUnconfirmed ? t('Time to be confirmed') : event.time}</p>
        <h3>{event.title}</h3>
        <p>{event.text}</p>
      </div>
      <span class="event-keepsake" aria-hidden="true"
        >{icons[i % icons.length]}<span>0{i + 1}</span></span
      >
    </article>
  {/each}
</div>
