import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

// One feed per language. Title, description and <language> belong to the language the feed is
// for — cloning a language folder copied the German ones onto Russian and Arabic, because they
// are plain strings and the clone only rewrote the quoted language code.
export async function GET(context: APIContext) {
  const guides = (await getCollection('guides', g => g.data.lang === 'pt' && !g.data.draft))
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
  return rss({
    title: 'PediBot — guias para pais',
    description: 'Respostas curtas às perguntas que os pais mais fazem, escritas apenas a partir de diretrizes pediátricas publicadas, com a fonte em cada frase.',
    site: context.site!,
    items: guides.map(g => ({ title: g.data.title, description: g.data.description, pubDate: g.data.date, link: `/pt/guides/${g.id.replace(/^pt\//, '')}` })),
    customData: '<language>pt-BR</language>',
  });
}
