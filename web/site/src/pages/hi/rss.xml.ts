import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

// One feed per language. Title, description and <language> belong to the language the feed is
// for — cloning a language folder copied the German ones onto Russian and Arabic, because they
// are plain strings and the clone only rewrote the quoted language code.
export async function GET(context: APIContext) {
  const guides = (await getCollection('guides', g => g.data.lang === 'hi' && !g.data.draft))
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
  return rss({
    title: 'PediBot — माता-पिता के लिए गाइड',
    description: 'माता-पिता जो सवाल सबसे ज़्यादा पूछते हैं उनके छोटे जवाब, सिर्फ़ प्रकाशित बाल रोग दिशानिर्देशों से लिखे और हर वाक्य पर स्रोत के साथ।',
    site: context.site!,
    items: guides.map(g => ({ title: g.data.title, description: g.data.description, pubDate: g.data.date, link: `/hi/guides/${g.id.replace(/^hi\//, '')}` })),
    customData: '<language>hi-IN</language>',
  });
}
