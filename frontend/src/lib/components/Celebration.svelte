<script lang="ts">
  import { onMount } from 'svelte';
  let { onend }: { onend: () => void } = $props();
  let canvas: HTMLCanvasElement;
  onMount(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      onend();
      return;
    }
    const context = canvas.getContext('2d');
    if (!context) {
      onend();
      return;
    }
    const width = window.innerWidth;
    const height = window.innerHeight;
    const scale = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * scale;
    canvas.height = height * scale;
    context.scale(scale, scale);
    const colours = ['#d6ad60', '#ecb6bb', '#7d9c80', '#f3d5a0', '#bca4cc'];
    const confetti = Array.from({ length: 100 }, (_, i) => ({
      x: i % 2 ? width * 0.14 : width * 0.86,
      y: height + 10,
      vx: (i % 2 ? 1 : -1) * (30 + Math.random() * 180),
      vy: -(350 + Math.random() * 430),
      spin: Math.random() * 6,
      colour: colours[i % colours.length]
    }));
    const bursts = [0.25, 0.5, 0.75].map((x, index) => ({
      x: x * width,
      y: height * (0.25 + index * 0.09),
      delay: 0.45 + index * 0.22
    }));
    let frame = 0;
    const started = performance.now();
    function draw(now: number) {
      if (!context) return;
      const elapsed = (now - started) / 1000;
      if (elapsed > 4) {
        onend();
        return;
      }
      context.clearRect(0, 0, width, height);
      context.globalAlpha = Math.min(1, 4 - elapsed);
      for (const particle of confetti) {
        context.save();
        context.translate(
          particle.x + particle.vx * elapsed,
          particle.y + particle.vy * elapsed + 190 * elapsed ** 2
        );
        context.rotate(particle.spin + elapsed * 5);
        context.fillStyle = particle.colour;
        context.fillRect(-3, -5, 6, 10);
        context.restore();
      }
      for (const [index, burst] of bursts.entries()) {
        const age = elapsed - burst.delay;
        context.fillStyle = colours[index];
        if (age < 0) {
          context.fillRect(burst.x, height - ((height - burst.y) * elapsed) / burst.delay, 3, 14);
        } else if (age < 1.6) {
          context.globalAlpha = (1 - age / 1.6) * 0.85;
          for (let ray = 0; ray < 24; ray++) {
            const angle = (ray * Math.PI) / 12;
            const radius = 95 * age;
            context.beginPath();
            context.arc(
              burst.x + Math.cos(angle) * radius,
              burst.y + Math.sin(angle) * radius + age * age * 45,
              2.5,
              0,
              Math.PI * 2
            );
            context.fill();
          }
          context.globalAlpha = Math.min(1, 4 - elapsed);
        }
      }
      frame = requestAnimationFrame(draw);
    }
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  });
</script>

<canvas bind:this={canvas} aria-hidden="true" class="celebration"></canvas>

<style>
  .celebration {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 100;
  }
</style>
