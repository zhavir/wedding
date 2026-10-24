<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
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
  const empty = (): Rsvp => ({
    email: '',
    attending: true,
    guests: [{ name: '', dietary: '' }],
    message: '',
    consent: true,
    witness_acceptance: false
  });
  let form = $state<Rsvp>(empty());
  $effect(() => {
    let cancelled = false;
    if (session.guest) {
      loadingRsvp = true;
      void api<{ rsvp: Rsvp | null; prefill: { name: string; email: string } }>('/rsvp')
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
      session.submittedInvitationIds.push(invitationId);
      submitted = true;
      editing = false;
      celebrating = form.attending;
      celebration += 1;
      status = form.attending
        ? t('You’re on the list! We can’t wait to celebrate with you.')
        : t('Thank you for letting us know. We’ll miss you!');
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
      <p class="eyebrow">{t('03 / SAVE YOUR SEAT')}</p>
      <h2>{t('It wouldn’t be')}<br />{t('the same')}<br /> <em>{t('without you.')}</em></h2>
      <p>
        {t('Please let us know by')}
        {w.rsvpBy}.<br
        /><!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- External video. -->
        <a href="https://youtu.be/uxnbkagUzrU?t=3" target="_blank" rel="noreferrer"
          >{t('E dic sì, nda fess i sort!')}</a
        >
      </p>
      <span class="rsvp-flower" aria-hidden="true">✳</span>
    </div>
    <div class="rsvp-card">
      {#if !session.ready || !session.guest}<InvitationGate />
      {:else}<div class="flex items-center justify-between gap-4">
          <h3>
            {session.guest.is_witness ? t('Our witness,') : t('Welcome,')}
            {session.guest.name}.
          </h3>
          <button class="text-button" disabled={busy} onclick={logout}>{t('Sign out')}</button>
        </div>
        <p>
          {t('We’ve reserved')}
          {session.guest.max_guests}
          {t('places for your party.')}
        </p>
        {#if !editing && !loadingRsvp}
          <p>{t('Your reply has been saved. Thank you!')}</p>
          <button
            class="button"
            onclick={() => {
              editing = true;
              submitted = false;
              status = '';
            }}>{t('Edit your preferences')}</button
          >
        {:else}
          <form
            onsubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <fieldset class="rsvp-fields" disabled={loadingRsvp || busy || submitted}>
              <div class="witness-invitation">
                {#if session.guest.is_witness}<h3>{t('Will you be our witness?')}</h3>
                  <p>
                    {t(
                      'We would love you by our side. Please confirm your role and attendance below.'
                    )}
                  </p>{/if}
              </div>
              <label for="attendance">{t('Will you be joining us?')}</label><select
                id="attendance"
                bind:value={form.attending}
                onchange={() => {
                  if (!form.guests.length) form.guests = [{ name: '', dietary: '' }];
                }}
                ><option value={true}>{t('Joyfully accepts')}</option><option value={false}
                  >{t('Regretfully declines')}</option
                ></select
              >{#if session.guest.is_witness && form.attending}<label class="checkbox"
                  ><input type="checkbox" required bind:checked={form.witness_acceptance} /><span
                    >{t('Yes, I accept the role of wedding witness.')}</span
                  ></label
                >{/if}<label for="email">{t('Email address')}</label><input
                id="email"
                type="email"
                bind:value={form.email}
                required
                maxlength="254"
                autocomplete="email"
              />
              {#if form.attending}{#each form.guests as person, i (i)}<fieldset>
                    <legend>{t('Guest')} {i + 1}</legend>{#if i > 0}<label for={`guest-email-${i}`}
                        >{t('Additional guest email')}</label
                      ><input
                        id={`guest-email-${i}`}
                        type="email"
                        bind:value={person.email}
                        required
                        maxlength="254"
                      /><small
                        >{t(
                          'We will email this guest a personal invitation and photo upload access.'
                        )}</small
                      >{/if}<label for={`name-${i}`}>{t('Full name')}</label><input
                      id={`name-${i}`}
                      bind:value={person.name}
                      required
                      maxlength="100"
                    /><label for={`diet-${i}`}
                      >{t('Dietary needs or allergies')} <span>{t('(optional)')}</span></label
                    ><input
                      id={`diet-${i}`}
                      bind:value={person.dietary}
                      maxlength="500"
                    />{#if i > 0}<button
                        type="button"
                        class="text-button"
                        onclick={() => (form.guests = form.guests.filter((_, n) => n !== i))}
                        >{t('Remove guest')}</button
                      >{/if}
                  </fieldset>{/each}{#if form.guests.length < session.guest.max_guests}<button
                    type="button"
                    class="text-button"
                    onclick={() => (form.guests = [...form.guests, { name: '', dietary: '' }])}
                    >{t('+ Add another guest')}</button
                  >{/if}{/if}
              <label for="message">{t('A little note for us')} <span>{t('(optional)')}</span></label
              ><textarea id="message" bind:value={form.message} maxlength="1000" rows="3"
              ></textarea>
              <p class="privacy-note">
                {t(
                  'By sending your reply, you agree that your details are stored to organise the wedding. Dietary information is shared only with the hosts and caterer as needed.'
                )}
              </p>
              <button
                class="button"
                class:working={busy}
                aria-busy={busy}
                disabled={busy || submitted}
                >{submitted
                  ? t('Reply saved')
                  : busy
                    ? t('Saving your reply…')
                    : t('Send our reply ↗')}</button
              >
            </fieldset>
          </form>{/if}{/if}
      {#if session.guest}<p role="status">{status}</p>
        {#if submitted}<p>
            {t('You can update your reply using Edit your preferences.')}
          </p>{/if}{/if}
      {#if session.guest && session.error}<p role="alert">{session.error}</p>{/if}
    </div>
  </div>
</section>

{#if celebrating}{#key celebration}<Celebration onend={() => (celebrating = false)} />{/key}{/if}
