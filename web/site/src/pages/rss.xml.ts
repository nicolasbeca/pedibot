import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const guides = (await getCollection('guides', g => g.data.lang === 'en' && !g.data.draft)).sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
  return rss({
    title: 'PediBot — guides for parents',
    description: 'Short answers to the questions parents ask most, written only from published paediatric guidelines, with the source on every sentence.',
    site: context.site!,
    items: guides.map(g => ({ title: g.data.title, description: g.data.description, pubDate: g.data.date, link: `/guides/${g.id.replace(/^en\//, '')}` })),
    customData: '<language>en</language>',
  });
}
