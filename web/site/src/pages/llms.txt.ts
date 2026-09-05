import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';
import { LANGS, LANG_NAMES, type Lang } from '../i18n';
import sources from '../data/sources.json';

/**
 * A map of the site for the crawlers that read it to answer questions (4-sep-2026).
 *
 * Measured over the 30 days to 4-sep, the second-largest group of legitimate crawlers after
 * Google was the answer engines: Anthropic 83 fetches, OpenAI 55 across GPTBot and its search
 * bot, Perplexity 26, ChatGPT-User 25. They are already reading the site, and what they need is
 * not persuasion but structure — which pages exist, what each one answers, and where the claim
 * came from. That last part is the only thing this site has that a content farm does not.
 *
 * Honest about its own footing: llms.txt is a proposed convention, not a standard, and there is
 * no public evidence that any of these crawlers weighs it. It costs one generated file. What
 * makes it worth having anyway is that it is built from the collections at build time, so it
 * cannot drift into describing a site that no longer exists — the failure mode of every
 * hand-written index this project has had.
 */
export async function GET(context: APIContext) {
  const site = context.site!.origin;
  const docs = (sources as { usage?: string; org?: string }[]).filter(d => d.usage !== 'excluido');
  // Ranked by how much of the corpus each one actually supplies, not by the order they happen to
  // sit in the file — which put a teaching textbook ahead of the NHS and the CDC.
  const perOrg = new Map<string, number>();
  for (const d of docs) if (d.org) perOrg.set(d.org, (perOrg.get(d.org) ?? 0) + 1);
  const orgs = [...perOrg.entries()].sort((a, b) => b[1] - a[1]).map(([org]) => org);
  const all = await getCollection('guides', g => !g.data.draft);

  const path = (lang: string, id: string) => {
    const slug = id.replace(new RegExp(`^${lang}/`), '');
    return lang === 'en' ? `${site}/guides/${slug}` : `${site}/${lang}/guides/${slug}`;
  };
  const pre = (lang: string) => (lang === 'en' ? '' : `/${lang}`);

  const lines: string[] = [
    '# PediBot',
    '',
    '> Answers for parents about a sick child, written only from published paediatric guidelines.',
    '',
    'Three rules decide everything on this site, and they are the reason it is worth quoting:',
    '',
    '1. **Nothing is stated that is not in one of those documents.** The answer names the bodies',
    '   it comes from, and every guide lists them with the organisation, the title and the page.',
    '   A reader who wants to check us can open the source and check us.',
    '2. **Doses come from fixed published tables, never from a language model.** They are looked',
    '   up, not generated.',
    '3. **When nothing in the corpus supports an answer, it says so.** It does not fill the gap.',
    '',
    `The corpus is ${docs.length} documents from ${orgs.length} organisations — ${orgs.slice(0, 8).join(', ')} and others.`,
    // languages that actually HAVE guides, not the languages the site is built in: the two
    // differ for as long as a new edition exists before its guides are generated, and this
    // line is read by machines that quote it.
    `There are ${all.length} guides across ${new Set(all.map((g) => g.data.lang)).size} languages.`,
    'Everything is free, with no account, no ads and no third-party trackers.',
    '',
    'This is reference material for parents. It is not a diagnosis and it does not replace a',
    'doctor. Warning signs are checked by fixed rules before any answer is produced.',
    '',
    '## Machine-readable',
    '',
    `- [Every source document](${site}/sources.json): the full list as JSON — organisation, title, language and the link to the original.`,
    `- [Sitemap](${site}/sitemap-index.xml): all pages, with the alternates for each language.`,
    ...LANGS.map(l => `- [RSS, ${LANG_NAMES[l as Lang]}](${site}${pre(l)}/rss.xml)`),
    '',
    '## Tools',
    '',
    `- [Dose calculator](${site}/dose): paracetamol and ibuprofen by weight, read from the published table. Also oral rehydration.`,
    `- [What the guidelines say to keep at home](${site}/kit): each item with the guideline that says it, including what not to keep.`,
    `- [Should I go to the emergency department?](${site}/emergency): a checklist of warning signs, rule-based, not a model.`,
    `- [Vaccines](${site}/vaccines): the published schedule by country.`,
    `- [Symptom diary](${site}/diary): kept in the browser, nothing is sent anywhere.`,
    `- [Sources](${site}/sources): every document behind the answers.`,
    '',
  ];

  for (const lang of LANGS) {
    const guides = all
      .filter(g => g.data.lang === lang)
      .sort((a, b) => a.data.title.localeCompare(b.data.title, lang));
    if (!guides.length) continue;
    lines.push(`## Guides — ${LANG_NAMES[lang]} (${guides.length})`, '');
    for (const g of guides) {
      const desc = (g.data.description || '').replace(/\s+/g, ' ').trim();
      lines.push(`- [${g.data.title}](${path(lang, g.id)})${desc ? `: ${desc}` : ''}`);
    }
    lines.push('');
  }

  return new Response(lines.join('\n'), {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
