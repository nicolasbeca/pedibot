/**
 * Two things every guide page needs and did not have (2-sep-2026), both measured rather than
 * assumed:
 *
 *  - **Related guides.** There were ZERO links between guides: each one was an island, so a
 *    reader who arrived from a search had nowhere to go and a crawler had no path onwards.
 *    Guides are also the only pages actually earning traffic (in fourteen days every single
 *    visit from Google landed on one), so linking them to each other is where the leverage is.
 *  - **FAQ structured data.** Every guide already ends in a "Common questions" section written
 *    as bold question / paragraph answer. Declaring it as an FAQPage is the same content, in the
 *    form a search engine can show directly.
 */

/** One question and its answer, pulled out of the guide's markdown. */
export interface Faq {
  q: string;
  a: string;
}

/**
 * Reads the "Common questions" / "Preguntas frecuentes" block. The shape is fixed by the article
 * prompt (**question** on its own line, answer underneath), so a guide that does not follow it
 * simply yields nothing instead of guessing.
 */
import samePairs from './data/same_subject.json';
import topicCategory from './data/topic_category.json';

/** Every topic key naming the same subject as this one, itself included.
 *
 *  The same subject carries two keys when the English guide was anchored on English sources
 *  (`constipation` / `estrenimiento`). Matching `topic` exactly therefore found no twins and the
 *  language switcher showed nothing on those guides, in both directions. The pairs come from
 *  SAME_SUBJECT in the generator, exported by scripts/export_catalog.py.
 */
export function topicKeys(topic: string): string[] {
  const out = new Set<string>([topic]);
  for (const pair of samePairs as string[][]) {
    if (pair.includes(topic)) pair.forEach((t) => out.add(t));
  }
  return [...out];
}

/** The "common questions" heading in every language the site publishes, exactly as
 *  src/pedibot/publish/prompts/article_v1.md asks the model to write it. Adding a language
 *  without adding its heading here costs that language its FAQ structured data, silently. */
export const FAQ_HEADINGS = [
  'Common questions',
  'Preguntas (?:frecuentes|habituales)',
  'Questions fr[ée]quentes',
  'Häufige Fragen',
  'Частые вопросы',
  'أسئلة شائعة',
  'Perguntas frequentes',
  'आम सवाल',
];

export function faqsFrom(markdown: string): Faq[] {
  // One alternative per language, and it must stay in step with the canonical headings the
  // article prompt asks for. A heading missing here silently costs that language its FAQ
  // structured data — it cost French that in July, and German, Russian and Arabic until 3-sep.
  const heading = new RegExp('^##\\s+(' + FAQ_HEADINGS.join('|') + ')\\s*$', 'im');
  const start = markdown.search(heading);
  if (start < 0) return [];
  const after = markdown.slice(start);
  const end = after.slice(1).search(/^##\s/m);
  const block = end < 0 ? after : after.slice(0, end + 1);

  // Split on the bold questions rather than looking ahead to the end of the string: `\Z` is
  // Python, not JavaScript. As a literal "Z" it silently dropped the last question of every
  // guide — two of three on the vomiting one (found 2-sep-2026 by counting both sides).
  // The bold question is at the start of a line, but the answer may sit on the same line or on
  // the next one — the model writes both shapes and neither is wrong. Requiring end-of-line lost
  // every question of the guides written the first way (2-sep-2026).
  const parts = block.split(/^\*\*(.+?)\*\*:?[ \t]*/m);
  const out: Faq[] = [];
  for (let i = 1; i < parts.length; i += 2) {
    const q = (parts[i] ?? '').trim();
    // strip citation markers: [3] means nothing to a reader arriving from a search result
    const a = (parts[i + 1] ?? '')
      .replace(/\[\d+\]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    if (q && a) out.push({ q, a });
  }
  return out;
}

/**
 * Hasta `n` guías a las que enlazar, del mismo idioma: primero las de su misma categoría, y
 * SIEMPRE dos vecinas del anillo. Nunca ella misma.
 *
 * Lo que había agrupaba por `topic` exacto, y cada tema tiene UNA sola guía por idioma: el grupo
 * salía siempre vacío y el sustituto eran «las tres más recientes», que son las mismas para las
 * sesenta guías de la lengua. Medido el 9-sep-2026 sobre el build: **390 de las 483 guías
 * recibían un único enlace interno** —el índice de su idioma— y 24 recibían más de sesenta.
 * Search Console lo decía de la guía portuguesa de la meningitis: «Página de referencia: no se
 * ha detectado ninguna». Para un dominio nuevo, una página que cuelga de un solo enlace en un
 * índice de sesenta es una página que el rastreador no llega a visitar.
 *
 * Las dos mitades hacen falta y hacen cosas distintas:
 *
 *  - **la categoría** da relevancia: quien acaba de leer sobre fiebre quiere la convulsión
 *    febril, no la última guía que se publicó;
 *  - **el anillo** da el suelo: cada guía es sucesora de exactamente dos, así que ninguna puede
 *    quedarse otra vez con un solo enlace, ni siquiera si su categoría tiene un único miembro o
 *    la taxonomía no la clasifica. El orden es por `topic`, que no cambia entre compilaciones —
 *    con la fecha, publicar una guía barajaría los enlaces de todas.
 *
 * El anillo va al final de la lista porque para el lector es lo menos relevante; para el
 * rastreador vale igual, que es de lo que se trata.
 */
export function relatedTo<T extends { id: string; data: { topic: string; date: Date } }>(
  current: T,
  all: T[],
  n = 6,
): T[] {
  const cats = topicCategory as Record<string, string>;
  const orden = [...all].sort((a, b) => a.data.topic.localeCompare(b.data.topic));
  const i = orden.findIndex((g) => g.id === current.id);
  const anillo =
    i < 0 || orden.length < 2
      ? []
      : [orden[(i + 1) % orden.length], orden[(i + 2) % orden.length]];

  const mia = cats[current.data.topic];
  const afines = mia
    ? all
        .filter((g) => g.id !== current.id && cats[g.data.topic] === mia)
        .sort((a, b) => a.data.topic.localeCompare(b.data.topic))
    : [];

  const salida: T[] = [];
  const visto = new Set<string>([current.id]);
  for (const g of afines) {
    if (salida.length >= Math.max(0, n - anillo.length)) break;
    if (visto.has(g.id)) continue;
    visto.add(g.id);
    salida.push(g);
  }
  // Lo que falte se completa dando la vuelta al anillo, no con «las más recientes». Para el
  // lector una y otra son igual de arbitrarias; para el reparto no se parecen en nada: rellenar
  // con las recientes se lo daba todo a las mismas veinte guías —de ahí los 60 enlaces de unas y
  // el 1 de las otras—, y el anillo lo reparte por construcción.
  for (let k = 1; k <= orden.length && salida.length < n; k++) {
    const g = orden[(i + k) % orden.length];
    if (!g || visto.has(g.id)) continue;
    visto.add(g.id);
    salida.push(g);
  }
  return salida.slice(0, n);
}
