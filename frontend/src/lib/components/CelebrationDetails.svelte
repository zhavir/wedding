<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import Flourish from './Flourish.svelte';
</script>

<section class="celebration-details" aria-labelledby="save-date-title">
  <p class="eyebrow">{t('The celebration')}</p>
  <h2 id="save-date-title">{t('Save the date')}</h2>
  <Flourish />
  <div class="celebration-grid">
    <article>
      <span class="eyebrow">{t('When')}</span>
      <h3>{w.dateLabel}</h3>
      <p>{w.schedule[0].time}</p>
    </article>
    <span class="details-seal" aria-hidden="true">{w.names[0][0]}<i>&</i>{w.names[1][0]}</span>
    <article>
      <span class="eyebrow">{t('Where')}</span>
      <h3>{w.venue}</h3>
      <p>{w.location}</p>
    </article>
  </div>
</section>
