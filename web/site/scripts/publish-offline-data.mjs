/**
 * Los datos que la web guarda dentro para funcionar sin cobertura (19-sep-2026, F1b de APP.md).
 *
 * Los JSON de `src/data/` los usa Astro al construir: acaban dentro del HTML de cada página, no
 * como ficheros. Eso vale con red y no vale sin ella: un padre que instaló el sitio el martes y
 * el viernes, sin saldo, busca por primera vez el número de su país, necesita que ese dato esté
 * **antes** de haber visitado la página.
 *
 * Así que se copian tal cual a `public/offline-data/`, el service worker se los guarda al
 * instalarse y quedan disponibles para la app cuando llegue.
 *
 * Se genera en cada build y no se guarda en el repositorio: un fichero copiado a mano se queda
 * viejo, y aquí quedarse viejo significa un calendario de vacunas de hace ocho meses.
 */
import { copyFileSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const aqui = dirname(fileURLToPath(import.meta.url));
const origen = join(aqui, '..', 'src', 'data');
const destino = join(aqui, '..', 'public', 'offline-data');

//: Lo que sirve sin red, y sólo eso. `sources.json` (211 kB) es el catálogo de documentos y no
//: se usa sin conexión; `countries.json` y los demás pequeños van dentro del HTML igualmente.
const QUE_SE_COPIA = [
  'emergency.json',
  'vaccines.json',
  'growth_charts.json',
  'checklist.json',
  'drugs.json',
  'dose_table.json',
];

mkdirSync(destino, { recursive: true });
let total = 0;
for (const nombre of QUE_SE_COPIA) {
  const de = join(origen, nombre);
  try {
    copyFileSync(de, join(destino, nombre));
    total += statSync(de).size;
  } catch (e) {
    console.error(`  falta ${nombre}: ${e.message}`);
    process.exit(1);
  }
}
const sobra = readdirSync(destino).filter((f) => !QUE_SE_COPIA.includes(f));
console.log(
  `offline-data: ${QUE_SE_COPIA.length} ficheros, ${(total / 1024).toFixed(0)} kB` +
    (sobra.length ? ` (sobran: ${sobra.join(', ')})` : '')
);
