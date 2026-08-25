import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Guides are written by `pedibot publish` into web/content/<lang>/<slug>.md
const guides = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../content' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    lang: z.enum(['en', 'es']),
    topic: z.string(),
    date: z.coerce.date(),
    prompt_version: z.string().optional(),
    model: z.string().optional(),
    sources: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { guides };
