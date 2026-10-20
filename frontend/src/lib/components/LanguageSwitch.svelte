<script lang="ts">
  import { language, setLanguage } from '#lib/i18n.svelte.ts';
</script>

<div class="language-switch" role="group" aria-label="Language / Lingua">
  <button
    type="button"
    lang="it"
    aria-label="Italiano"
    aria-pressed={language.current === 'it'}
    onclick={() => setLanguage('it')}>IT</button
  >
  <span aria-hidden="true">/</span>
  <button
    type="button"
    lang="en"
    aria-label="English"
    aria-pressed={language.current === 'en'}
    onclick={() => setLanguage('en')}>EN</button
  >
</div>
