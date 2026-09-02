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
export function faqsFrom(markdown: string): Faq[] {
  // one alternative per language: a heading missing here silently costs that language its
  // FAQ structured data, which is what happened to every French guide
  const heading = /^##\s+(Common questions|Preguntas (?:frecuentes|habituales)|Questions fr[ée]quentes)\s*$/im;
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
 * Up to `n` other guides to link to, same language, nearest first: the ones sharing this guide's
 * topic, then the most recent. Never the guide itself.
 */
export function relatedTo<T extends { id: string; data: { topic: string; date: Date } }>(
  current: T,
  all: T[],
  n = 3,
): T[] {
  const others = all.filter((g) => g.id !== current.id);
  const sameTopic = others.filter((g) => g.data.topic === current.data.topic);
  const rest = others
    .filter((g) => g.data.topic !== current.data.topic)
    .sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
  return [...sameTopic, ...rest].slice(0, n);
}
