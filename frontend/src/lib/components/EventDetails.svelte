<script lang="ts">
  import Timeline from './Timeline.svelte';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
</script>

<section class="section details" id="details">
  <div class="section-heading">
    <div>
      <p class="eyebrow">{t('THE CELEBRATION')}</p>
      <h2>{t('A beautiful day.')}<br /><em>{t('Even better company.')}</em></h2>
    </div>
    <p>
      {w.dateLabel}<br />{w.venue}<br />{w.location}<br
      /><!-- eslint-disable-next-line svelte/no-navigation-without-resolve --><!-- External map URL from editable content. --><a
        href={w.mapUrl}
        target="_blank"
        rel="noreferrer">{t('Find your way ↗')}</a
      >
    </p>
  </div>
  <Timeline />
  <div class="good-to-know">
    <h3>{t('A few little details')}</h3>
    <div>
      {#each w.faqs as faq (faq.question)}<details>
          <summary>{faq.question}<span aria-hidden="true">+</span></summary>
          <p>
            {#if 'link' in faq && faq.link}
              {faq.answer.split(
                faq.link.placeholder
              )[0]}<!-- eslint-disable-next-line svelte/no-navigation-without-resolve --><!-- External hotel URL from editable content. --><a
                href={faq.link.url}
                target="_blank"
                rel="noreferrer">{faq.link.label}</a
              >{faq.answer.split(faq.link.placeholder)[1]}
            {:else}
              {faq.answer}
            {/if}
          </p>
        </details>{/each}
    </div>
  </div>
</section>
