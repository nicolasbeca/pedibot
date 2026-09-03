// @ts-check
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

/**
 * Last-modified date per URL, so the sitemap says what changed.
 *
 * Without it Google has no reason to re-read: it looked on 30-ago, counted 223 pages, and the
 * 154 added since were invisible to it. A guide's date is the one in its own frontmatter; every
 * other page gets this build's date, which is when it was last generated.
 */
const BUILD_DATE = new Date();
const guideDates = new Map();
// fileURLToPath, not .pathname: on Windows the latter yields '/D:/…' and readdirSync fails,
// which silently left every page on the build date instead of its own
const contentRoot = fileURLToPath(new URL('../content/', import.meta.url));
for (const lang of fs.existsSync(contentRoot) ? fs.readdirSync(contentRoot) : []) {
  const dir = path.join(contentRoot, lang);
  if (!fs.statSync(dir).isDirectory()) continue;
  for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.md'))) {
    const front = fs.readFileSync(path.join(dir, file), 'utf-8').slice(0, 800);
    const m = front.match(/^date:\s*(\d{4}-\d{2}-\d{2})/m);
    const slug = file.replace(/\.md$/, '');
    const prefix = lang === 'en' ? '' : `/${lang}`;
    if (m) guideDates.set(`${prefix}/guides/${slug}`, new Date(m[1]));
  }
}

// SITE_URL is read at build time (Makefile passes it); placeholder until the domain exists (D-01).
const site = process.env.SITE_URL || 'https://pedibot.xyz';

export default defineConfig({
  site,
  trailingSlash: 'never',
  build: { format: 'directory' },
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'es', 'fr', 'de'],
    routing: { prefixDefaultLocale: false },
  },
  integrations: [
    sitemap({
      i18n: { defaultLocale: 'en', locales: { en: 'en', es: 'es', fr: 'fr', de: 'de' } },
      serialize(item) {
        const p = new URL(item.url).pathname.replace(/\/$/, '');
        item.lastmod = (guideDates.get(p) ?? BUILD_DATE).toISOString();
        return item;
      },
    }),
  ],
  vite: { server: { proxy: { '/api': 'http://127.0.0.1:8601' } } }, // dev: API on the Python side
});
