import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Guides are written by `pedibot publish` into web/content/<lang>/<slug>.md
const guides = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../content' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    // keep in step with LANGS in src/i18n.ts: a guide in a language missing here fails
    // the whole build, not just its own page
    lang: z.enum(['en', 'es', 'fr', 'de', 'ru', 'ar']),
    topic: z.string(),
    date: z.coerce.date(),
    prompt_version: z.string().optional(),
    model: z.string().optional(),
    sources: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { guides };
