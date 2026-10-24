<script lang="ts">
  import { onMount } from 'svelte';
  import { wedding as w } from '#lib/wedding.ts';
  let container: HTMLDivElement;
  let path: SVGPathElement;
  let thread: SVGSVGElement;
  let width = $state(100);
  let height = $state(1000);
  let progress = $state(0);
  let x = $state(50);
  let y = $state(0);
  let activeIndex = $state(0);
  let centers = $state<number[]>([]);
  const curve = $derived.by(() => {
    const stops = w.schedule.map((_, i) => ({
      x: width * (i % 2 ? (width < 600 ? 0.53 : 0.57) : width < 600 ? 0.47 : 0.43),
      y: centers[i] ?? (height * (i + 0.5)) / w.schedule.length
    }));
    let d = `M${width / 2} 0`;
    let previous = { x: width / 2, y: 0 };
    for (const stop of [...stops, { x: width / 2, y: height }]) {
      const middle = (previous.y + stop.y) / 2;
      d += ` C${previous.x} ${middle} ${stop.x} ${middle} ${stop.x} ${stop.y}`;
      previous = stop;
    }
    return d;
  });
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
      x = point.x;
      const entries = [...container.querySelectorAll<HTMLElement>('.timeline-event')];
      const markerY = innerHeight * 0.65;
      activeIndex = entries.reduce((closest, entry, index) => {
        const bounds = entry.getBoundingClientRect();
        const current = entries[closest].getBoundingClientRect();
        return Math.abs(bounds.top + bounds.height / 2 - markerY) <
          Math.abs(current.top + current.height / 2 - markerY)
          ? index
          : closest;
      }, 0);
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
      centers = [...container.querySelectorAll<HTMLElement>('.timeline-event')].map((entry) => {
        const rect = entry.getBoundingClientRect();
        return rect.top - bounds.top + rect.height / 2;
      });
      schedule();
    };
    const resize = new ResizeObserver(measure);
    resize.observe(container);
    resize.observe(thread);
    container.querySelectorAll('.timeline-event').forEach((entry) => resize.observe(entry));
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
  <span class="timeline-bead" style={`left:${x}px;top:${y}%`} aria-hidden="true">✦</span>
  {#each w.schedule as event, i (event.time)}
    <article
      class="timeline-event"
      class:arrived={i <= activeIndex}
      class:active={i === activeIndex}
      aria-current={i === activeIndex ? 'step' : undefined}
    >
      <div class="event-copy">
        <p class="eyebrow">{event.time}</p>
        <h3>{event.title}</h3>
        <p>{event.text}</p>
      </div>
    </article>
  {/each}
</div>

<style>
  .ribbon-timeline {
    position: relative;
    margin: 2.5rem auto 3rem;
    max-width: 1000px;
  }
  .timeline-thread {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    overflow: visible;
  }
  .timeline-bead {
    position: absolute;
    width: 22px;
    height: 22px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    color: var(--paper);
    background: var(--gold);
    box-shadow: 0 0 0 5px #b99c651a;
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 2;
    font-size: 0.7rem;
  }
  .timeline-event {
    position: relative;
    display: grid;
    grid-template-columns: 39% 22% 39%;
    padding: 0.3rem 0;
  }
  .timeline-event + .timeline-event {
    margin-top: -3rem;
  }
  .event-copy {
    grid-column: 1;
    padding: 1rem 1.3rem;
    border-left: 2px solid transparent;
    border-radius: 0 0.6rem 0.6rem 0;
    transition:
      background-color 0.3s,
      border-color 0.3s;
  }
  .timeline-event:nth-of-type(even) .event-copy {
    grid-column: 3;
  }
  .timeline-event:nth-of-type(odd) .event-copy {
    text-align: right;
    border-left: 0;
    border-right: 2px solid transparent;
    border-radius: 0.6rem 0 0 0.6rem;
  }
  .timeline-event:nth-of-type(odd).active .event-copy {
    border-right-color: #b89a6155;
  }
  .event-copy .eyebrow {
    margin: 0 0 0.4rem;
    color: var(--gold);
  }
  .event-copy h3 {
    font-size: clamp(1.7rem, 3vw, 2.3rem);
    margin: 0 0 0.5rem;
    line-height: 1.1;
  }
  .event-copy p:last-child {
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.7;
    color: #5f6a59;
  }
  .active .event-copy {
    background: #5a6e5d06;
    border-left-color: #b89a6155;
  }
  @media (max-width: 640px) {
    .timeline-event + .timeline-event {
      margin-top: -1.25rem;
    }
    .timeline-event {
      grid-template-columns: 42% 16% 42%;
      padding-block: 0.35rem;
    }
    .event-copy h3 {
      font-size: 1.5rem;
    }
    .event-copy p:last-child {
      font-size: 0.8rem;
      line-height: 1.55;
    }
    .event-copy {
      padding: 0.65rem 0.4rem;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .event-copy {
      transition: none;
    }
    .timeline-bead {
      display: none;
    }
  }
</style>
