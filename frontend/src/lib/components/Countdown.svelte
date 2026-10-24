<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { onMount } from 'svelte';
  import { wedding as w } from '#lib/wedding.ts';
  let remaining = $state(0);
  let rings: HTMLDivElement;
  let ringProgress = $state(0);
  const countdown = $derived([
    { value: Math.floor(remaining / 86400), label: t('days') },
    { value: Math.floor(remaining / 3600) % 24, label: t('hours') },
    { value: Math.floor(remaining / 60) % 60, label: t('minutes') },
    { value: remaining % 60, label: t('seconds') }
  ]);
  onMount(() => {
    const tick = () =>
      (remaining = Math.max(0, Math.floor((new Date(w.date).getTime() - Date.now()) / 1000)));
    tick();
    const timer = setInterval(tick, 1000);
    let frame = 0;
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');

    const updateRings = () => {
      frame = 0;
      if (!rings) return;
      if (motionPreference.matches) {
        ringProgress = 1;
        return;
      }
      const rect = rings.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      // The rings start moving near the bottom of the viewport and
      // finish as they approach the center. This value decreases again
      // when scrolling upward, giving a fully reversible movement.
      const start = viewportHeight * 0.95;
      const end = viewportHeight * 0.4;
      ringProgress = Math.max(0, Math.min(1, (start - rect.top) / (start - end)));
    };
    const scheduleRings = () => {
      if (!frame) frame = requestAnimationFrame(updateRings);
    };

    updateRings();
    window.addEventListener('scroll', scheduleRings, { passive: true });
    window.addEventListener('resize', scheduleRings);
    motionPreference.addEventListener('change', scheduleRings);

    return () => {
      clearInterval(timer);
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', scheduleRings);
      window.removeEventListener('resize', scheduleRings);
      motionPreference.removeEventListener('change', scheduleRings);
    };
  });
</script>

<section class="countdown" aria-label={t('Wedding countdown')}>
  <div
    class="joined-rings"
    bind:this={rings}
    style={`--ring-progress: ${ringProgress}`}
    aria-hidden="true"
  >
    <span><i class="diamond"></i></span><span></span>
  </div>
  <p class="eyebrow">{t('EVERY DAY, A LITTLE CLOSER')}</p>
  <h2>{t('Until we say')} <em>{t('“I do”.')}</em></h2>

  <div class="clock">
    {#each countdown as unit (unit.label)}<div>
        <span>{String(unit.value).padStart(2, '0')}</span><small>{unit.label}</small>
      </div>{/each}
  </div>
  {#if remaining === 0}<p>{t('Our next chapter is here.')}</p>{/if}
</section>
