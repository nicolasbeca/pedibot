/**
 * En qué lenguas se indexa la página de una marca (8-oct-2026).
 *
 * En las de los países donde se vende, y en inglés, que es la edición por defecto del sitio. Las
 * demás ediciones siguen existiendo para quien llegue por el selector de idioma, pero llevan
 * `noindex`, no van al sitemap y ningún hreflang las anuncia: /de/dose/apirofeno es una marca que
 * sólo se vende en España, en alemán, y Google la indexaba mientras dejaba fuera /dose/tylenol.
 * Medido y explicado en tests/test_brand_pages_index_where_sold.py.
 *
 * `.mjs` y no `.ts` porque lo leen dos sitios: las páginas y el filtro del sitemap en
 * astro.config.mjs, que no puede importar TypeScript.
 */
import drugs from './data/drugs.json' with { type: 'json' };

/** Las lenguas del sitio que lee un padre en cada país donde vendemos alguna marca. Sólo hacen
 *  falta los países de drugs.json; un país que no está aquí no añade ninguna lengua. EE. UU.
 *  lleva el castellano: «dosis de tylenol para niños» se busca allí. */
export const LANGS_OF_COUNTRY = {
  US: ['en', 'es'], CA: ['en', 'fr'], GB: ['en'], IE: ['en'], AU: ['en'], NZ: ['en'],
  IN: ['en', 'hi'],
  KE: ['en'], NG: ['en'], GH: ['en'], UG: ['en'], TZ: ['en'], ZA: ['en'], ZM: ['en'], ZW: ['en'],
  MW: ['en'], BW: ['en'], LS: ['en'], NA: ['en'], SZ: ['en'], MU: ['en', 'fr'],
  ES: ['es'], MX: ['es'], AR: ['es'], CL: ['es'], CO: ['es'],
  FR: ['fr'], BF: ['fr'], BJ: ['fr'], CG: ['fr'], CI: ['fr'], CM: ['fr'], GA: ['fr'], GN: ['fr'],
  ML: ['fr'], NE: ['fr'], SN: ['fr'], TD: ['fr'], TG: ['fr'],
  DZ: ['ar', 'fr'], MA: ['ar', 'fr'], TN: ['ar', 'fr'], MR: ['ar', 'fr'],
  AE: ['ar'], BH: ['ar'], KW: ['ar'], OM: ['ar'], QA: ['ar'], SA: ['ar'], EG: ['ar'], JO: ['ar'],
  LB: ['ar'],
  DE: ['de'], PT: ['pt'], BR: ['pt'],
};

/** slug de marca → países donde se vende (drugs.json repite una marca por país). */
const BRAND_COUNTRIES = new Map();
for (const d of Object.values(drugs)) {
  for (const b of d.brands) {
    if (!b.forms?.length) continue;
    const set = BRAND_COUNTRIES.get(b.slug) ?? new Set();
    for (const c of b.countries ?? []) set.add(c);
    BRAND_COUNTRIES.set(b.slug, set);
  }
}

/** ¿Se indexa la página de dosis `slug` en la lengua `lang`? Lo que no es marca (los
 *  genéricos), siempre. */
export function brandIndexedIn(slug, lang) {
  const countries = BRAND_COUNTRIES.get(slug);
  if (!countries) return true;
  if (lang === 'en') return true;
  for (const c of countries) if ((LANGS_OF_COUNTRY[c] ?? []).includes(lang)) return true;
  return false;
}
