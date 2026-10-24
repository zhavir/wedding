import { api, ApiError } from '#lib/api.ts';
export type Guest = {
  id: string;
  name: string;
  max_guests: number;
  is_admin: boolean;
  is_witness: boolean;
};
export const session = $state<{
  guest: Guest | null;
  ready: boolean;
  revision: number;
  error: string;
  submittedInvitationIds: string[];
  entry: 'restore' | 'link' | 'code';
}>({
  guest: null,
  ready: false,
  revision: 0,
  error: '',
  entry: 'restore',
  submittedInvitationIds: []
});

export async function signIn(code: string, entry: 'link' | 'code' = 'code') {
  session.entry = entry;
  session.guest = await api<Guest>('/session', 'POST', { code });
  session.error = '';
  session.ready = true;
  session.revision++;
}
export async function signOut() {
  await api('/session', 'DELETE');
  session.guest = null;
}
export async function restoreSession() {
  session.ready = false;
  session.error = '';
  let openingLink = false;
  try {
    // eslint-disable-next-line svelte/prefer-svelte-reactivity -- One-time parsing, never mutated.
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const code = fragment.get('invite');
    if (code) {
      openingLink = true;
      history.replaceState(
        null,
        '',
        window.location.pathname +
          (window.location.pathname.startsWith('/gallery') ? '#upload' : '')
      );
      if (!window.location.pathname.startsWith('/gallery')) window.scrollTo(0, 0);
      await signIn(code, 'link');
    } else {
      session.guest = await api<Guest>('/session');
    }
  } catch (error) {
    session.guest = null;
    if (!(error instanceof ApiError && error.status === 401 && !openingLink))
      session.error = (error as Error).message;
  } finally {
    session.ready = true;
    if (openingLink && window.location.pathname.startsWith('/gallery'))
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          document.getElementById('upload')?.scrollIntoView({ block: 'start' });
        })
      );
  }
}
