import process from 'node:process';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
const proxy = {
  '/api': { target: process.env.API_PROXY_TARGET || 'http://localhost:8000', changeOrigin: false }
};
export default defineConfig({
  plugins: [tailwindcss(), sveltekit({ adapter: adapter() })],
  server: { proxy, allowedHosts: ['web'] },
  preview: { proxy, allowedHosts: ['web'] }
});
