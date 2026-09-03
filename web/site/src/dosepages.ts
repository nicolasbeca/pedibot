/**
 * One page per medicine, with the whole weight table on it.
 *
 * It used to be one page per brand AND weight: 1,442 pages of ~216 words each, differing only in
 * a number. Measured over seven days (2-sep-2026): Googlebot crawled 13 of them and they brought
 * zero visits, while the guides — 38 pages — took every single one. Near-duplicate pages at that
 * scale are not free: they eat the crawl budget of the pages that do work.
 *
 * So the same content now lives on ~21 pages per language, each answering "how much X for my
 * child" for every weight at once, which is also the page a parent actually wants. The old URLs
 * are redirected in Caddy with a single pattern.
 */
import drugs from './data/drugs.json';
import { LANGS, type Lang } from './i18n';

export interface Form {
  label: string;
  mg_per_ml: number;
}

export interface Medicine {
  key: string;
  slug: string;
  /** Slug and name per language: the generic is spelled differently in each (/es/dose/
   *  ibuprofeno, /fr/dose/ibuprofene), a brand is spelled the same everywhere. One field per
   *  language meant adding a field for every new language. */
  slug_by: Record<Lang, string>;
  name_by: Record<Lang, string>;
  isBrand: boolean;
  forms: Form[];
  d: any;
}

/** The dosage form, translated for display only.
 *
 * "jarabe 120 mg/5 ml" is a catalogue key — it identifies a presentation and must not change.
 * What a parent reads is the word, so only the word is swapped, and only when the language has
 * one; the numbers are the same everywhere.
 */
const FORM_WORD: Partial<Record<Lang, Record<string, string>>> = {
  en: { jarabe: 'syrup', gotas: 'drops', 'suspensión': 'suspension', sobres: 'sachets', comprimidos: 'tablets', supositorios: 'suppositories' },
  fr: { jarabe: 'sirop', gotas: 'gouttes', 'suspensión': 'suspension', sobres: 'sachets', comprimidos: 'comprimés', supositorios: 'suppositoires' },
  de: { jarabe: 'Sirup', gotas: 'Tropfen', 'suspensión': 'Suspension', sobres: 'Beutel', comprimidos: 'Tabletten', supositorios: 'Zäpfchen' },
  ru: { jarabe: 'сироп', gotas: 'капли', 'suspensión': 'суспензия', sobres: 'пакетики', comprimidos: 'таблетки', supositorios: 'свечи' },
  ar: { jarabe: 'شراب', gotas: 'نقط', 'suspensión': 'معلّق', sobres: 'أكياس', comprimidos: 'أقراص', supositorios: 'تحاميل' },
};

/** The label of a presentation, with its form word in the reader's language. */
export function formLabel(label: string, lang: Lang): string {
  const words = FORM_WORD[lang];
  if (!words) return label;
  const first = label.split(' ')[0];
  const word = words[first.toLowerCase()];
  return word ? word + label.slice(first.length) : label;
}

/** How each language spells the two generics in a URL. Anything unlisted keeps the key. */
const GENERIC_SLUG: Partial<Record<Lang, Record<string, string>>> = {
  es: { ibuprofen: 'ibuprofeno' },
  fr: { ibuprofen: 'ibuprofene', paracetamol: 'paracetamol' },
  de: { ibuprofen: 'ibuprofen', paracetamol: 'paracetamol' },
};

/** Every generic and every brand that has at least one presentation, deduplicated by slug. */
export function medicines(): Medicine[] {
  const out: Medicine[] = [];
  const seen = new Set<string>();
  for (const [key, d] of Object.entries(drugs as any)) {
    const drug = d as any;
    const rows: Medicine[] = [
      {
        key,
        slug: key,
        slug_by: Object.fromEntries(
          LANGS.map((l) => [l, GENERIC_SLUG[l]?.[key] ?? key])
        ) as Record<Lang, string>,
        name_by: Object.fromEntries(
          LANGS.map((l) => [l, drug.generic[l] ?? drug.generic.en])
        ) as Record<Lang, string>,
        isBrand: false,
        forms: drug.presentations.map((p: any) => ({ label: p.name, mg_per_ml: p.mg_per_ml })),
        d: drug,
      },
      ...drug.brands
        .filter((b: any) => b.forms.length)
        .map((b: any) => ({
          key,
          slug: b.slug,
          slug_by: Object.fromEntries(LANGS.map((l) => [l, b.slug])) as Record<Lang, string>,
          name_by: Object.fromEntries(LANGS.map((l) => [l, b.name])) as Record<Lang, string>,
          isBrand: true,
          forms: b.forms,
          d: drug,
        })),
    ];
    for (const r of rows) {
      // drugs.json lists a brand once per country, so the same slug can appear twice
      if (seen.has(r.slug)) continue;
      seen.add(r.slug);
      out.push(r);
    }
  }
  return out;
}

export interface Row {
  kg: number;
  mgMin: number;
  mgMax: number;
  ml: string[];
  belowMin: boolean;
}

const r1 = (x: number) => Math.round(x * 10) / 10;

/** The dose for every weight from 5 to 40 kg, the same arithmetic the calculator uses. */
export function weightTable(m: Medicine): Row[] {
  const [lo, hi] = m.d.per_dose_mg_per_kg;
  const rows: Row[] = [];
  for (let kg = 5; kg <= 40; kg++) {
    const mgMax = Math.min(hi * kg, m.d.max_single_mg);
    const mgMin = Math.min(lo * kg, mgMax);
    rows.push({
      kg,
      mgMin: Math.round(mgMin),
      mgMax: Math.round(mgMax),
      ml: m.forms.map((f) => `${r1(mgMin / f.mg_per_ml)}–${r1(mgMax / f.mg_per_ml)}`),
      belowMin: kg < m.d.min_weight_kg,
    });
  }
  return rows;
}

/** Doses allowed in 24 h at the top of the range, for a child of that weight. */
export function maxDoses(m: Medicine, kg: number): number {
  const [, hi] = m.d.per_dose_mg_per_kg;
  const mgMax = Math.min(hi * kg, m.d.max_single_mg);
  const dailyCap = Math.min(m.d.max_mg_per_kg_day * kg, m.d.max_daily_mg);
  return Math.max(1, Math.min(Math.floor(dailyCap / mgMax), Math.floor(24 / m.d.interval_hours[0])));
}
