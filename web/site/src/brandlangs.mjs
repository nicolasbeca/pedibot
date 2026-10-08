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

import { LANGS_OF_COUNTRY } from './countrylangs.mjs';

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
