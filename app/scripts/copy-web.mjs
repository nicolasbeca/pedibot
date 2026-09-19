/**
 * Mete el sitio construido dentro de la app (19-sep-2026, F2 del plan de APP.md).
 *
 * Aquí está la mitad práctica de la regla que puso el operador —«cada vez que actualicemos la
 * web hay que actualizar la app»—: la app **no tiene su propio sitio**. Sale de `web/site/dist`,
 * así que un arreglo en un componente o una guía nueva llegan sin reescribir nada.
 *
 * **Qué va dentro y qué no**, que es la decisión de verdad de este fichero.
 *
 * El sitio entero son 81 MB: 2.607 páginas en ocho idiomas, y cada una pesa unos 25 kB porque
 * lleva su CSS y su navegación dentro. Meterlo todo daría una app que en Lagos o en Delhi nadie
 * se instala con datos móviles, que es justo el público al que va.
 *
 * Así que se elige por la pregunta que da sentido a la app: **¿qué hace falta a las tres de la
 * mañana sin cobertura?** El número al que llamar y los signos que significan ir ya. Eso son las
 * 88 fichas de emergencia por país, en los ocho idiomas, y pesan 17 MB. Con ellas van los datos
 * en bruto (`offline-data/`, 700 kB) y la carcasa del sitio.
 *
 * Lo que se queda fuera —las guías, las fichas de dosis por marca, los calendarios y las curvas
 * país por país— **sigue funcionando con red**, y el service worker guarda lo que cada uno abra.
 * No es que no quepa: es que no es lo que se busca a oscuras.
 *
 * Uso:  npm run copy      (o `npm run sync`, que además ejecuta `cap sync`)
 */
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const aqui = dirname(fileURLToPath(import.meta.url));
const raiz = join(aqui, '..', '..');
const dist = join(raiz, 'web', 'site', 'dist');
const www = join(aqui, '..', 'www');

const IDIOMAS = ['', 'es', 'fr', 'de', 'ru', 'ar', 'pt', 'hi'];

//: Carpetas que van enteras, sean del idioma que sean.
const CARPETAS_SUELTAS = ['_astro', 'fonts', 'offline-data', 'offline', '.well-known'];

//: Por idioma: la portada y las pantallas que tienen que abrir sin red.
const POR_IDIOMA = ['', 'emergency', 'legal', 'family', 'kit', 'diary'];

//: Ficheros sueltos de la raíz.
const RAIZ_FICHEROS = [
  'sw.js',
  'manifest.webmanifest',
  'favicon.ico',
  'logo.png',
  'logo-192.png',
  'logo-144.png',
  'logo-72.png',
  'apple-touch-icon.png',
  'og.png',
  'robots.txt',
];

//: Sin esto, la app no cumple lo que promete y hay que enterarse aquí y no en la tienda.
const OBLIGATORIOS = [
  'index.html',
  'sw.js',
  'manifest.webmanifest',
  'offline/index.html',
  'emergency/index.html',
  'offline-data/emergency.json',
  'offline-data/vaccines.json',
];

if (!existsSync(dist)) {
  console.error(`No hay sitio construido en ${dist}.\n  cd web/site && npm run build`);
  process.exit(1);
}
const faltan = OBLIGATORIOS.filter((f) => !existsSync(join(dist, f)));
if (faltan.length) {
  console.error(`El build está incompleto, falta: ${faltan.join(', ')}`);
  process.exit(1);
}

rmSync(www, { recursive: true, force: true });
mkdirSync(www, { recursive: true });

const copia = (rel) => {
  const de = join(dist, rel);
  if (!existsSync(de)) return false;
  const a = join(www, rel);
  mkdirSync(dirname(a), { recursive: true });
  cpSync(de, a, { recursive: true });
  return true;
};

for (const f of RAIZ_FICHEROS) copia(f);
for (const c of CARPETAS_SUELTAS) copia(c);
for (const lang of IDIOMAS) {
  for (const seccion of POR_IDIOMA) {
    const rel = [lang, seccion, 'index.html'].filter(Boolean).join('/');
    copia(rel);
    if (seccion === 'emergency') {
      // y las 88 fichas de país, que son el motivo de todo esto
      const dir = [lang, seccion].filter(Boolean).join('/');
      const origen = join(dist, dir);
      if (existsSync(origen)) {
        for (const e of readdirSync(origen, { withFileTypes: true })) {
          if (e.isDirectory()) copia(join(dir, e.name));
        }
      }
    }
  }
}

const cuenta = (dir) =>
  readdirSync(dir, { withFileTypes: true }).reduce(
    (acc, e) => {
      const p = join(dir, e.name);
      if (e.isDirectory()) {
        const sub = cuenta(p);
        return { n: acc.n + sub.n, bytes: acc.bytes + sub.bytes };
      }
      return { n: acc.n + 1, bytes: acc.bytes + statSync(p).size };
    },
    { n: 0, bytes: 0 }
  );
const { n, bytes } = cuenta(www);
const mb = bytes / 1024 / 1024;
console.log(`www: ${n} ficheros, ${mb.toFixed(1)} MB (de ${relative(raiz, dist)})`);
if (mb > 45) {
  // No es un límite de la tienda: es el umbral por encima del cual la gente no se instala cosas
  // con datos móviles donde este proyecto quiere estar.
  console.warn('  ojo: más de 45 MB. Mirar qué secciones se pueden dejar fuera del paquete.');
  process.exitCode = 0;
}
