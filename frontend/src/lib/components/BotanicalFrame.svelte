<script lang="ts">
  import { onMount } from 'svelte';

  // Repeatable randomness, so petals feel irregular without hydration differences.
  function random(seed: number): number {
    const value = Math.sin(seed * 127.1 + 78.233) * 43758.5453;
    return value - Math.floor(value);
  }

  const chapters =
    '.intro, .celebration-details, .countdown, .details, .visions, .travel, .rsvp-section, .dog-section, .travel-section';

  onMount(() => {
    const layers: HTMLElement[] = [];
    // Petals must keep falling even while a chapter is offscreen.
    // Pausing them made each chapter appear frozen on entry.

    document.querySelectorAll<HTMLElement>(chapters).forEach((chapter, chapterIndex) => {
      const layer = document.createElement('div');
      layer.className = 'chapter-petal-layer';
      layer.setAttribute('aria-hidden', 'true');
      for (let i = 0; i < 20; i++) {
        const seed = chapterIndex * 101 + i * 11;
        const duration = 6 + random(seed + 1) * 15;
        const petal = document.createElement('span');
        petal.className = 'chapter-petal';
        const values: Record<string, string> = {
          '--petal-x': `${4 + random(seed + 2) * 90}%`,
          '--petal-size': `${7 + random(seed + 3) * 10}px`,
          '--petal-duration': `${duration}s`,
          '--petal-delay': `${-random(seed + 4) * duration}s`,
          // Gentle, constant sideways drift; no alternating wind direction.
          '--petal-drift': `${(random(seed + 5) - 0.5) * 90}px`,
          '--petal-rotation': `${(random(seed + 7) > 0.5 ? 1 : -1) * (240 + random(seed + 8) * 700)}deg`,
          '--petal-opacity': `${0.78 + random(seed + 9) * 0.16}`,
          '--petal-distance': `${chapter.offsetHeight + 75}px`
        };
        for (const [name, value] of Object.entries(values)) petal.style.setProperty(name, value);
        petal.innerHTML =
          '<svg viewBox="0 0 24 32" aria-hidden="true"><path d="M12 30C4 23-2 12 3 5 6 1 10 2 12 6 14 2 18 1 21 5 26 12 20 23 12 30Z"/><path d="M12 27Q9 17 12 9"/></svg>';
        layer.appendChild(petal);
      }
      chapter.insertBefore(layer, chapter.firstChild);
      layers.push(layer);
    });
    // Track content that changes height after images/fonts finish loading.
    const resizeObserver = new ResizeObserver(() => {
      layers.forEach((layer) => {
        const height = layer.parentElement?.offsetHeight ?? 0;
        layer
          .querySelectorAll<HTMLElement>('.chapter-petal')
          .forEach((petal) => petal.style.setProperty('--petal-distance', `${height + 75}px`));
      });
    });
    layers.forEach((layer) => {
      if (layer.parentElement) resizeObserver.observe(layer.parentElement);
    });
    return () => {
      resizeObserver.disconnect();
      layers.forEach((layer) => layer.remove());
    };
  });
</script>

<!-- Decorative layers are mounted inside chapter sections, not above page content. -->
