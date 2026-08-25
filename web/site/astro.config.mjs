// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// SITE_URL is read at build time (Makefile passes it); placeholder until the domain exists (D-01).
const site = process.env.SITE_URL || 'https://pedibot.xyz';

export default defineConfig({
  site,
  trailingSlash: 'never',
  build: { format: 'directory' },
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'es'],
    routing: { prefixDefaultLocale: false },
  },
  integrations: [sitemap({ i18n: { defaultLocale: 'en', locales: { en: 'en', es: 'es' } } })],
  vite: { server: { proxy: { '/api': 'http://127.0.0.1:8601' } } }, // dev: API on the Python side
});
