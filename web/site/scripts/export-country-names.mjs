/**
 * Los nombres de cada país, en las lenguas del sitio → config/country_names.json (20-sep-2026).
 *
 * El chat necesita decir «En Marruecos, el número de urgencias es el 150 / 141», y Python no
 * tiene de dónde sacar «Marruecos»: `locale` depende de lo que el servidor tenga instalado y
 * `pycountry` es una dependencia más para algo que el navegador ya sabe. Node sí lo sabe, con
 * `Intl.DisplayNames`, que es exactamente la misma fuente que ya usa `web/site/src/countries.ts`
 * para pintar los desplegables. Así los dos lados dicen el mismo nombre por construcción.
 *
 * Se genera, no se escribe a mano: noventa países por nueve lenguas son ochocientas diez
 * cadenas, y escribirlas a mano es garantizar una docena de errores que nadie va a revisar.
 *
 *   node scripts/export-country-names.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const raiz = path.resolve(aqui, '../../..');

// El suajili va con los ocho del sitio: la capa de seguridad ya lo lee, y el día que conteste
// un número tiene que decir el país como lo dice esa lengua.
const LENGUAS = ['en', 'es', 'fr', 'de', 'ru', 'ar', 'pt', 'hi', 'sw'];

// Se leen los JSON que ya exporta `scripts/export_catalog.py`, y no los YAML de `config/`,
// por una razón práctica: así este script no necesita un lector de YAML. `js-yaml` estaba
// disponible sólo como dependencia de otra cosa, y apoyarse en eso es apoyarse en algo que
// puede desaparecer en un `npm ci` sin que nadie lo toque.
const leer = (rel) => JSON.parse(fs.readFileSync(path.join(raiz, rel), 'utf8'));
const codigos = [
  ...new Set([
    ...Object.keys(leer('web/site/src/data/emergency.json')),
    ...Object.keys(leer('web/site/src/data/vaccines.json')),
  ]),
].sort();

const salida = {};
for (const lang of LENGUAS) {
  const nombres = new Intl.DisplayNames([lang], { type: 'region' });
  salida[lang] = {};
  for (const cc of codigos) {
    let nombre;
    try {
      nombre = nombres.of(cc);
    } catch {
      nombre = cc;
    }
    // `Intl` devuelve el propio código cuando no conoce la región; guardarlo sería guardar
    // «En NG, el número es…», así que se deja que el lector vea el código sólo si no hay más.
    salida[lang][cc] = nombre || cc;
  }
}

const destino = path.join(raiz, 'config/country_names.json');
fs.writeFileSync(destino, JSON.stringify(salida, null, 1) + '\n', 'utf8');
console.log(
  `country_names.json: ${codigos.length} países en ${LENGUAS.length} lenguas → ${destino}`,
);
