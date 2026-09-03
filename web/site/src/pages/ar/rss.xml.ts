import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

// One feed per language. Title, description and <language> come from the language it is for —
// every feed used to carry the Spanish ones, whatever guides it listed.
export async function GET(context: APIContext) {
  const guides = (await getCollection('guides', g => g.data.lang === 'ar' && !g.data.draft))
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
  return rss({
    title: 'PediBot — Ratgeber für Eltern',
    description: 'Kurze Antworten auf die Fragen, die Eltern am häufigsten stellen, geschrieben ausschließlich aus veröffentlichten kinderärztlichen Leitlinien, mit der Quelle an jedem Satz.',
    site: context.site!,
    items: guides.map(g => ({ title: g.data.title, description: g.data.description, pubDate: g.data.date, link: `/ar/guides/${g.id.replace(/^ar\//, '')}` })),
    customData: '<language>de</language>',
  });
}
