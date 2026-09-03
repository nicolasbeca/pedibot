import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

// One feed per language. Title, description and <language> belong to the language the feed is
// for — cloning a language folder copied the German ones onto Russian and Arabic, because they
// are plain strings and the clone only rewrote the quoted language code.
export async function GET(context: APIContext) {
  const guides = (await getCollection('guides', g => g.data.lang === 'de' && !g.data.draft))
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
  return rss({
    title: 'PediBot — Ratgeber für Eltern',
    description: 'Kurze Antworten auf die Fragen, die Eltern am häufigsten stellen, geschrieben ausschließlich aus veröffentlichten kinderärztlichen Leitlinien, mit der Quelle an jedem Satz.',
    site: context.site!,
    items: guides.map(g => ({ title: g.data.title, description: g.data.description, pubDate: g.data.date, link: `/de/guides/${g.id.replace(/^de\//, '')}` })),
    customData: '<language>de</language>',
  });
}
