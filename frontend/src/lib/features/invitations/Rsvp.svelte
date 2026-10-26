<script lang="ts">
  import { tick } from 'svelte';
  import { t, tp } from '#lib/i18n.svelte.ts';
  import { api, type Rsvp } from '#lib/api.ts';
  import Celebration from '#lib/components/Celebration.svelte';
  import InvitationGate from '#lib/components/InvitationGate.svelte';
  import { session, signOut } from '#lib/session.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';

  let busy = $state(false);
  let submitted = $state(false);
  let editing = $state(true);
  let loadingRsvp = $state(false);
  let status = $state('');
  let celebrating = $state(false);
  let celebration = $state(0);

  let rsvpCard: HTMLDivElement;

  const empty = (): Rsvp => ({
    email: '',
    attending: true,
    guests: [{ name: '', dietary: '' }],
    message: '',
    consent: true,
    witness_acceptance: false
  });

  let form = $state<Rsvp>(empty());
  const participantCount = $derived(
    form.attending ? Math.max(1, form.guests.length) : (session.guest?.max_guests ?? 1)
  );

  $effect(() => {
    let cancelled = false;

    if (session.guest) {
      loadingRsvp = true;

      void api<{
        rsvp: Rsvp | null;
        prefill: { name: string; email: string };
      }>('/rsvp')
        .then((result) => {
          if (!cancelled) {
            editing = !result.rsvp || session.entry === 'code';
            session.entry = 'restore';
            submitted = false;

            form = result.rsvp ?? {
              ...empty(),
              email: result.prefill.email,
              guests: [{ name: result.prefill.name, dietary: '' }]
            };
          }
        })
        .catch((e) => {
          if (!cancelled) status = e.message;
        })
        .finally(() => {
          if (!cancelled) loadingRsvp = false;
        });
    } else {
      form = empty();
      loadingRsvp = false;
    }

    return () => {
      cancelled = true;
    };
  });

  async function scrollToRsvp() {
    await tick();

    rsvpCard?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }

  async function save() {
    if (busy || submitted || !session.guest) return;

    const invitationId = session.guest.id;

    busy = true;
    status = '';

    try {
      await api('/rsvp', 'PUT', {
        ...form,
        consent: true,
        guests: form.attending ? form.guests : [],
        witness_acceptance: !!(
          session.guest.is_witness &&
          form.attending &&
          form.witness_acceptance
        )
      });

      if (!session.submittedInvitationIds.includes(invitationId)) {
        session.submittedInvitationIds.push(invitationId);
      }

      session.guest.participant_count = participantCount;
      submitted = true;
      editing = false;

      status = form.attending
        ? tp('You’re on the list! We can’t wait to celebrate with you.', participantCount)
        : tp('Thank you for letting us know. We’ll miss you!', participantCount);

      celebrating = form.attending;
      celebration += 1;

      await scrollToRsvp();
    } catch (e) {
      status = (e as Error).message;
    } finally {
      busy = false;
    }
  }

  async function logout() {
    try {
      await signOut();
      status = '';
    } catch (e) {
      status = (e as Error).message;
    }
  }
</script>

<section class="rsvp-section" id="rsvp">
  <div class="section rsvp-grid">
    <div>
      <p class="eyebrow">{tp('SAVE YOUR SEAT', participantCount)}</p>

      <h2>
        {t('It wouldn’t be')}<br />
        {t('the same')}<br />
        <em>{tp('without you.', participantCount)}</em>
      </h2>

      <p>
        {tp('Please let us know by', participantCount)}
        {w.rsvpBy}.<br />
        <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- External video. -->
        <a
          class="rsvp-video-link"
          href="https://youtu.be/uxnbkagUzrU?t=3"
          target="_blank"
          rel="noreferrer"
        >
          {t("Oh, e dic sì, 'nda fess e sor't!")}
          <svg
            class="inline-arrow"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            aria-hidden="true"><path d="M6 18 18 6M6 6h12v12" /></svg
          >
        </a>
      </p>

      <span class="rsvp-flower" aria-hidden="true">✳</span>
    </div>

    <div class="rsvp-card" bind:this={rsvpCard}>
      {#if !session.ready || !session.guest}
        <InvitationGate />
      {:else}
        <div class="flex items-center justify-between gap-4">
          <h3>
            {session.guest.is_witness ? t('Our witness,') : tp('Welcome,', participantCount)}
            {session.guest.name}.
          </h3>

          <button type="button" class="text-button" disabled={busy} onclick={logout}>
            {t('Sign out')}
          </button>
        </div>

        <p>
          {t('We’ve reserved')}
          {session.guest.max_guests}
          {session.guest.max_guests === 1 ? t('place for you.') : t('places for your party.')}
        </p>

        {#if !editing && !loadingRsvp}
          <p>{tp('Your reply has been saved. Thank you!', participantCount)}</p>

          <button
            type="button"
            class="button"
            onclick={() => {
              editing = true;
              submitted = false;
              status = '';
            }}
          >
            {tp('Edit your preferences', participantCount)}
          </button>
        {:else}
          <form
            onsubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <fieldset class="rsvp-fields" disabled={loadingRsvp || busy || submitted}>
              <div class="witness-invitation">
                {#if session.guest.is_witness}
                  <h3>{t('Will you be our witness?')}</h3>

                  <p>
                    {t(
                      'We would love you by our side. Please confirm your role and attendance below.'
                    )}
                  </p>
                {/if}
              </div>

              <label for="attendance">
                {tp('Will you be joining us?', participantCount)}
              </label>

              <select
                id="attendance"
                bind:value={form.attending}
                onchange={() => {
                  if (!form.guests.length) {
                    form.guests = [{ name: '', dietary: '' }];
                  }
                }}
              >
                <option value={true}>{tp('Joyfully accepts', participantCount)}</option>
                <option value={false}>{tp('Regretfully declines', participantCount)}</option>
              </select>

              {#if session.guest.is_witness && form.attending}
                <label class="checkbox">
                  <input type="checkbox" required bind:checked={form.witness_acceptance} />
                  <span>
                    {t('Yes, I accept the role of wedding witness.')}
                  </span>
                </label>
              {/if}

              <label for="email">{t('Email address')}</label>

              <input
                id="email"
                type="email"
                bind:value={form.email}
                required
                maxlength="254"
                autocomplete="email"
              />

              {#if form.attending}
                {#each form.guests as person, i (i)}
                  <fieldset>
                    <legend>{t('Guest')} {i + 1}</legend>

                    {#if i > 0}
                      <label for={`guest-email-${i}`}>
                        {t('Additional guest email (optional)')}
                      </label>

                      <input
                        id={`guest-email-${i}`}
                        type="email"
                        bind:value={person.email}
                        maxlength="254"
                      />

                      <small>
                        {t(
                          'If provided, we will email this guest a personal invitation and photo upload access.'
                        )}
                      </small>
                    {/if}

                    <label for={`name-${i}`}>
                      {t('Full name')}
                    </label>

                    <input id={`name-${i}`} bind:value={person.name} required maxlength="100" />

                    <label for={`diet-${i}`}>
                      {t('Dietary needs or allergies')}
                      <span>{t('(optional)')}</span>
                    </label>

                    <input id={`diet-${i}`} bind:value={person.dietary} maxlength="500" />

                    {#if i > 0}
                      <button
                        type="button"
                        class="text-button"
                        onclick={() => {
                          form.guests = form.guests.filter((_, n) => n !== i);
                        }}
                      >
                        {t('Remove guest')}
                      </button>
                    {/if}
                  </fieldset>
                {/each}

                {#if form.guests.length < session.guest.max_guests}
                  <button
                    type="button"
                    class="text-button"
                    onclick={() => {
                      form.guests = [...form.guests, { name: '', dietary: '' }];
                    }}
                  >
                    {t('+ Add another guest')}
                  </button>
                {/if}
              {/if}

              <label for="message">
                {t('A little note for us')}
                <span>{t('(optional)')}</span>
              </label>

              <textarea id="message" bind:value={form.message} maxlength="1000" rows="3"></textarea>

              <button
                type="submit"
                class="button"
                class:working={busy}
                aria-busy={busy}
                disabled={busy || submitted}
              >
                {submitted
                  ? t('Reply saved')
                  : busy
                    ? tp('Saving your reply…', participantCount)
                    : tp('Send our reply ↗', participantCount)}
              </button>
            </fieldset>
          </form>
        {/if}
      {/if}

      {#if session.guest}
        <p role="status">{status}</p>
      {/if}

      {#if session.guest && session.error}
        <p role="alert">{session.error}</p>
      {/if}
    </div>
  </div>
</section>

{#if celebrating}
  {#key celebration}
    <Celebration onend={() => (celebrating = false)} />
  {/key}
{/if}

<style>
  .rsvp-video-link {
    text-decoration: underline;
    text-underline-offset: 0.2em;
  }
</style>
