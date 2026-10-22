<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { onMount } from 'svelte';
  import { wedding as w } from '#lib/wedding.ts';
  let remaining = $state(0);
  let section: HTMLElement;
  let joined = $state(false);
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
    const observer = new IntersectionObserver(
      ([entry]) => {
        joined = entry.isIntersecting;
      },
      { threshold: 0.3 }
    );
    observer.observe(section);
    return () => {
      clearInterval(timer);
      observer.disconnect();
    };
  });
</script>

<section
  class="countdown"
  bind:this={section}
  class:rings-joined={joined}
  aria-label={t('Wedding countdown')}
>
  <div class="joined-rings" aria-hidden="true">
    <span><i class="diamond"></i></span><span></span>
  </div>
  <p class="eyebrow">{t('EVERY DAY, A LITTLE CLOSER')}</p>
  <h2>{t('Until we say')} <em>{t('“I do”.')}</em></h2>

  <div class="clock">
    {#each countdown as unit (unit.label)}<div>
        <span>{String(unit.value).padStart(2, '0')}</span><small>{unit.label}</small>
      </div>{/each}
  </div>
  <p>
    {remaining === 0
      ? t('Our next chapter is here.')
      : t('We’re counting the moments until we’re all together.')}
  </p>
</section>
