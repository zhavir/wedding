import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
  PUBLIC_ASSET_URL: {
    public: true,
    static: true,
    schema: (value) => {
      if (!value) return '';
      const url = new URL(value);
      if (!['https:', 'http:'].includes(url.protocol))
        throw new Error('PUBLIC_ASSET_URL must be an HTTP(S) URL');
      return url.toString().replace(/\/$/, '');
    }
  },
  PUBLIC_API_URL: {
    public: true,
    static: true,
    schema: (value) => {
      if (!value || value === '/api') return '/api';
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol))
        throw new Error('PUBLIC_API_URL must be an HTTP(S) URL');
      return url.toString().replace(/\/$/, '');
    }
  }
});
