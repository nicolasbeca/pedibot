import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

// One feed per language. Title, description and <language> come from the language it is for —
// every feed used to carry the Spanish ones, whatever guides it listed.
export async function GET(context: APIContext) {
  const guides = (await getCollection('guides', g => g.data.lang === 'fr' && !g.data.draft))
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
  return rss({
    title: 'PediBot — guides pour les parents',
    description: 'Des réponses courtes aux questions que les parents posent le plus, écrites uniquement à partir de recommandations pédiatriques publiées, avec la source à chaque phrase.',
    site: context.site!,
    items: guides.map(g => ({ title: g.data.title, description: g.data.description, pubDate: g.data.date, link: `/fr/guides/${g.id.replace(/^fr\//, '')}` })),
    customData: '<language>fr</language>',
  });
}
