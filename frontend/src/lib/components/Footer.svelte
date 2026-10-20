<script lang="ts">
  import { resolve } from '$app/paths';
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
</script>

<footer>
  <p class="eyebrow">{t('THE BEST IS YET TO COME')}</p>
  <h2>{w.names[0]} <em>&</em> {w.names[1]}</h2>
  <p>{w.dateLabel} · {w.location}</p>
  <div class="footer-bottom">
    <span>{t('Made with love, for the people we love.')}</span><a href={`mailto:${w.contactEmail}`}
      >{t('A question? Say hello ↗')}</a
    ><a href={resolve('/#home')}>{t('Back to the beginning ↑')}</a>
  </div>
</footer>
