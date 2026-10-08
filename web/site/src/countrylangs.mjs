/**
 * Qué lenguas del sitio lee un padre en cada país, y en cuáles se indexa la página de ese país
 * (8-oct-2026).
 *
 * Las tablas por país —urgencias, calendario, curvas— existían en las ocho lenguas: 2.216 de las
 * 2.965 URLs del sitemap. Google indexaba /es/vaccines/gb y dejaba fuera /es/vaccines/es. Ahora un
 * país se indexa en inglés (la edición por defecto) y en las lenguas de aquí; las demás ediciones
 * siguen abiertas para quien llegue por el selector, con `noindex`, fuera del sitemap y del
 * hreflang. Las marcas usan el mismo mapa (src/brandlangs.mjs).
 *
 * Sólo cuentan las ocho lenguas del sitio, oficiales o de uso general en el país. Un país sin
 * ninguna (Italia, Turquía, Afganistán…) se queda con el inglés. `.mjs` porque lo lee también el
 * filtro del sitemap en astro.config.mjs. Medido y fijado en
 * tests/test_country_pages_index_where_spoken.py, que además falla si entra un país sin estar aquí.
 */

export const LANGS_OF_COUNTRY = {
  // América
  US: ['en', 'es'], CA: ['en', 'fr'], MX: ['es'], GT: ['es'], HN: ['es'], SV: ['es'], NI: ['es'],
  CR: ['es'], PA: ['es'], CU: ['es'], DO: ['es'], HT: ['fr'], CO: ['es'], VE: ['es'], EC: ['es'],
  PE: ['es'], BO: ['es'], PY: ['es'], UY: ['es'], AR: ['es'], CL: ['es'], BR: ['pt'],
  // Europa
  GB: ['en'], IE: ['en'], ES: ['es'], PT: ['pt'], FR: ['fr'], BE: ['fr', 'de'], LU: ['fr', 'de'],
  CH: ['de', 'fr'], DE: ['de'], AT: ['de'], LI: ['de'], IT: ['en'], RU: ['ru'], BY: ['ru'],
  UA: ['ru'], TR: ['en'],
  // Asia y Oceanía
  IN: ['en', 'hi'], PK: ['en'], AF: ['en'], KZ: ['ru'], AU: ['en'], NZ: ['en'],
  // Oriente Medio y norte de África
  SA: ['ar'], AE: ['ar'], BH: ['ar'], KW: ['ar'], QA: ['ar'], OM: ['ar'], YE: ['ar'], IQ: ['ar'],
  SY: ['ar'], JO: ['ar'], LB: ['ar', 'fr'], PS: ['ar'], EG: ['ar'], LY: ['ar'], SD: ['ar', 'en'],
  TN: ['ar', 'fr'], DZ: ['ar', 'fr'], MA: ['ar', 'fr'], MR: ['ar', 'fr'],
  // África subsahariana
  SN: ['fr'], ML: ['fr'], BF: ['fr'], NE: ['fr'], GN: ['fr'], CI: ['fr'], TG: ['fr'], BJ: ['fr'],
  CM: ['fr', 'en'], GA: ['fr'], CG: ['fr'], CD: ['fr'], CF: ['fr'], TD: ['fr', 'ar'],
  BI: ['fr'], RW: ['en', 'fr'], DJ: ['fr', 'ar'], KM: ['fr', 'ar'], MG: ['fr'], SC: ['en', 'fr'],
  MU: ['en', 'fr'], GQ: ['es', 'fr', 'pt'], AO: ['pt'], MZ: ['pt'], GW: ['pt'], CV: ['pt'],
  ST: ['pt'], NG: ['en'], GH: ['en'], GM: ['en'], SL: ['en'], LR: ['en'], KE: ['en'], UG: ['en'],
  TZ: ['en'], ET: ['en'], ER: ['ar', 'en'], SO: ['ar'], SS: ['en', 'ar'], ZA: ['en'], ZM: ['en'],
  ZW: ['en'], MW: ['en'], BW: ['en'], NA: ['en'], LS: ['en'], SZ: ['en'],
};

/** ¿Se indexa la página del país `code` en la lengua `lang`? El inglés, siempre. */
export function countryIndexedIn(code, lang) {
  if (lang === 'en') return true;
  return (LANGS_OF_COUNTRY[String(code).toUpperCase()] ?? []).includes(lang);
}

const ALL = ['en', 'es', 'fr', 'de', 'ru', 'ar', 'pt', 'hi'];

/** Las ediciones que se indexan de la página de un país: lo que anuncia el hreflang. */
export function countryIndexedLangs(code) {
  return ALL.filter((l) => countryIndexedIn(code, l));
}
