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
 * 154 added since were invisible to it. A guide's date is the one in its own frontmatter.
 *
 * Every other page used to get THIS BUILD's date, and the site is rebuilt daily to publish the
 * guides — so every morning the sitemap announced 296 of 779 pages as modified without one of
 * them having changed (10-sep-2026). That is paid for twice: `lastmod` only works while it is
 * credible, and ops/indexnow.py picks what to send to Bing, Yandex, Seznam and Naver by reading
 * this same field, so it had been sending the very same 296 URLs every day.
 *
 * Now each page takes the date of what actually feeds it. Only files that TRAVEL in the deploy
 * tar are used: their mtime survives it (checked on both sides), while the generated
 * src/data/*.json are rebuilt on the server and carry the deploy time — which is the same lie in
 * another shape.
 */
const rutaDe = (rel) => fileURLToPath(new URL(rel, import.meta.url));
const cuando = (rel) => {
  try {
    return fs.statSync(rutaDe(rel)).mtime;
  } catch {
    return null;
  }
};
const masNueva = (...fechas) => new Date(Math.max(0, ...fechas.filter(Boolean).map((d) => +d)));
// El texto visible de cualquier página sale de estos dos, así que tocarlos sí es un cambio real.
const COMUN = [cuando('./src/i18n.ts'), cuando('./src/layouts/Base.astro')];
const LOCALES = new Set(['es', 'fr', 'de', 'ru', 'ar', 'pt', 'hi']);
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

const FECHA_DOSIS = masNueva(...COMUN, cuando('../../config/drugs.yaml'), cuando('./src/dosepages.ts'));
const FECHA_VACUNAS = masNueva(...COMUN, cuando('../../config/vaccines.yaml'));
// el índice de guías sí cambia cuando se publica una: es una lista de ellas
const FECHA_GUIAS = masNueva(...COMUN, ...guideDates.values());

// SITE_URL is read at build time (Makefile passes it); placeholder until the domain exists (D-01).
const site = process.env.SITE_URL || 'https://pedibot.xyz';

export default defineConfig({
  site,
  trailingSlash: 'never',
  build: { format: 'directory' },
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'es', 'fr', 'de', 'ru', 'ar', 'pt', 'hi'],
    routing: { prefixDefaultLocale: false },
  },
  integrations: [
    // Sin `i18n`, y a propósito (9-sep-2026). Esa opción hace que el sitemap calcule el hreflang
    // emparejando URLs por su prefijo de idioma, y en este sitio la rebanada cambia con la lengua:
    // /dose/ibuprofen, /es/dose/ibuprofeno, /fr/dose/ibuprofene. El resultado era un sitemap que
    // contradecía al HTML — al ibuprofeno le daba cinco alternativas de ocho, y a las 483 guías
    // ninguna, mientras que cada página declara en su `<head>` las ocho y la x-default, bien.
    //
    // Dos fuentes para la misma decisión y una equivocada. Google lee las dos, así que la de más
    // no suma: resta. Las etiquetas del HTML bastan y son las que aciertan.
    sitemap({
      serialize(item) {
        const p = new URL(item.url).pathname.replace(/\/$/, '');
        const guia = guideDates.get(p);
        const resto = p.split('/').filter((s) => s && !LOCALES.has(s));
        const tipo = resto[0] ?? '';
        const fecha =
          guia ??
          (tipo === 'dose'
            ? FECHA_DOSIS
            : tipo === 'vaccines'
              ? FECHA_VACUNAS
              : tipo === 'guides'
                ? FECHA_GUIAS
                : // una página suelta: su propio fichero de ruta, sea /legal.astro o /es/index.astro
                  masNueva(...COMUN, cuando(`./src/pages${p || '/index'}.astro`), cuando(`./src/pages${p}/index.astro`)));
        item.lastmod = fecha.toISOString();
        return item;
      },
    }),
  ],
  vite: { server: { proxy: { '/api': 'http://127.0.0.1:8601' } } }, // dev: API on the Python side
});
