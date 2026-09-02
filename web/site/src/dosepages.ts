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

export interface Form {
  label: string;
  mg_per_ml: number;
}

export interface Medicine {
  key: string;
  slug: string;
  /** The Spanish page keeps its own slug for the generics (/es/dose/ibuprofeno), as it always did. */
  slug_es: string;
  name_en: string;
  name_es: string;
  isBrand: boolean;
  forms: Form[];
  d: any;
}

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
        slug_es: key === 'ibuprofen' ? 'ibuprofeno' : key,
        name_en: drug.generic.en,
        name_es: drug.generic.es,
        isBrand: false,
        forms: drug.presentations.map((p: any) => ({ label: p.name, mg_per_ml: p.mg_per_ml })),
        d: drug,
      },
      ...drug.brands
        .filter((b: any) => b.forms.length)
        .map((b: any) => ({
          key,
          slug: b.slug,
          slug_es: b.slug,
          name_en: b.name,
          name_es: b.name,
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
