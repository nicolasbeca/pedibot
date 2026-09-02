import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const guides = (await getCollection('guides', g => g.data.lang === 'fr' && !g.data.draft)).sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
  return rss({
    title: 'PediBot — guías para padres',
    description: 'Respuestas cortas a las preguntas más frecuentes, escritas solo a partir de guías pediátricas publicadas, con la fuente en cada frase.',
    site: context.site!,
    items: guides.map(g => ({ title: g.data.title, description: g.data.description, pubDate: g.data.date, link: `/fr/guides/${g.id.replace(/^fr\//, '')}` })),
    customData: '<language>es</language>',
  });
}
