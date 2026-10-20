<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { api } from '#lib/api.ts';
  import { session, signIn } from '#lib/session.svelte.ts';
  let code = $state('');
  let email = $state('');
  let busy = $state(false);
  let recovering = $state(false);
  let status = $state('');
  async function login() {
    busy = true;
    status = '';
    session.error = '';
    try {
      await signIn(code);
      code = '';
    } catch (error) {
      status = (error as Error).message;
    } finally {
      busy = false;
    }
  }
  async function recover() {
    busy = true;
    status = '';
    session.error = '';
    try {
      const result = await api<{ message: string }>('/session/recover', 'POST', { email });
      status = t(result.message);
    } catch (error) {
      status = (error as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

{#if !session.ready}<p role="status">{t('Opening your invitation…')}</p>
{:else}
  <h3>{t('Open your invitation')}</h3>
  <p>
    {t(
      'Use your personal email link or paste the short code from your email. We’ll remember you on this device.'
    )}
  </p>
  <form
    onsubmit={(event) => {
      event.preventDefault();
      void login();
    }}
  >
    <label for="invitation-code">{t('Your invitation code')}</label>
    <input
      id="invitation-code"
      bind:value={code}
      required
      minlength="8"
      maxlength="100"
      autocomplete="one-time-code"
      autocapitalize="characters"
      spellcheck="false"
      placeholder="ABCDE-FG234"
      disabled={busy}
    />
    <button class="button" disabled={busy}
      >{busy ? t('Finding your invitation…') : t('Open my invitation ↗')}</button
    >
  </form>
  <button
    class="text-button"
    type="button"
    aria-expanded={recovering}
    onclick={() => {
      recovering = !recovering;
      status = '';
    }}>{t('Lost your code?')}</button
  >
  {#if recovering}<form
      class="recovery-form"
      onsubmit={(event) => {
        event.preventDefault();
        void recover();
      }}
    >
      <p>
        {t(
          'Enter the email address on your invitation. We’ll send a replacement link and short code there.'
        )}
      </p>
      <label for="recovery-email">{t('Invitation email address')}</label><input
        id="recovery-email"
        type="email"
        autocomplete="email"
        bind:value={email}
        maxlength="254"
        required
        disabled={busy}
      />
      <button class="button" disabled={busy}>{t('Email me a replacement code')}</button>
    </form>{/if}
  <p role="status">{status || session.error}</p>
{/if}
