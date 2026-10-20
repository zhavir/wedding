import { t } from './i18n.svelte.ts';
import { PUBLIC_API_URL } from '$app/env/public';
export type Person = { name: string; dietary: string; email?: string };
export type Rsvp = {
  email: string;
  attending: boolean;
  guests: Person[];
  message: string;
  consent: boolean;
  witness_acceptance?: boolean;
};
export type Photo = {
  kind: 'photo' | 'video' | 'live';
  motion: string;
  id: string;
  caption: string;
  preview: string;
  original: string;
};
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}
export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${PUBLIC_API_URL}${path}`, {
    method,
    credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      typeof error.detail === 'string'
        ? t(error.detail)
        : t('Please check your details and try again.'),
      response.status
    );
  }
  return response.json() as Promise<T>;
}
