# Show HN — borrador para publicar

Guardado aquí porque la vez anterior se redactó en una conversación y se perdió con ella.
Cifras comprobadas el 6-sep-2026 contra el índice y el contenido; si pasan meses, vuelve a
contarlas antes de publicar (`ops/weekly_tweets.py` usa `facts()`, que las cuenta solas).

**Cuándo publicar:** martes a jueves, entre las 8:00 y las 10:00 hora de la costa este de EE. UU.
(14:00-16:00 en España). Y quédate una hora disponible para responder comentarios: en Show HN,
un autor que contesta sube el hilo mucho más que el propio texto.

---

## Título (76 caracteres, el límite son 80)

```
Show HN: PediBot – paediatric answers only from published clinical guidelines
```

## URL

```
https://pedibot.xyz
```

## Primer comentario — publícalo tú mismo justo después de enviar el enlace

La primera frase es suya, del 6-sep: «lo construí porque acababa de ser padre primerizo y me di
cuenta de que la información es contradictoria y poco fiable, necesitaba algún sitio donde
acudir». Traducida y sin adornar — la queja *contradictoria* es exactamente el problema que
resuelve la web, así que el resto del texto ya no tiene que argumentar: solo cuenta cómo.

```
I built this when I became a father for the first time. What I found when I went looking for
answers was contradictory and hard to trust, and I wanted one place I could go.

It answers only from a corpus of 288 published documents from 18 bodies — NHS, WHO, CDC, RKI,
SEUP, MedlinePlus, AAP and others. Three things make it different from asking a general chatbot:

1. Retrieval first, and when nothing in the corpus covers the question it says so instead of
answering. That was the hardest part to get right and it is still the thing I check most often.

2. Doses are never generated. They are looked up in a fixed published table by weight, and a
guard blocks any answer containing a mg or ml quantity unless an authorised dosing source is
among its citations. A language model is not allowed near a milligram figure.

3. A rule-based triage reads the question for red flags before any answer is produced and puts a
banner above it. It runs before retrieval, so it fires even when the corpus has nothing to say.

There are also 483 guides in 8 languages built from the same corpus, where every statement
carries the number of the document it came from, listed at the foot with organisation, title and
page. Plus vaccination schedules for 7 countries, each citing its own national authority.

What it is not: no clinician has reviewed any of this, and I am not a doctor. It is a reading aid
pointed at primary sources, not medical advice, and it says so on every page. If that disqualifies
it for you, that is fair.

A few things I learned that might interest people here:

- Python's \w excludes Devanagari combining vowel signs, so \b silently stopped matching in three
separate places the day I added Hindi. Three bugs, one property, no errors anywhere.

- Arabic proclitics (و ف ب ك ل ال) glue to the following word, and a final ة becomes ت under
suffixation, so BM25 misses most matches unless you strip them first.

- A sitemap is a hint; a link is an instruction. I crossed 45 days of Googlebot against my own
link graph: 100% of pages one click from the homepage had been crawled, ~50% at two or three
clicks, and 0% of orphan pages — which had been sitting in the sitemap for months.

Free, no ads, no account, no third-party trackers, and no plan to change that. Happy to answer
anything.
```

---

## Lo que te van a preguntar, y lo que puedes contestar sin quedarte pillado

**"¿Cómo evitas que alucine?"** — Recuperación primero; el modelo solo redacta con los pasajes
recuperados delante. Un verificador relee la respuesta y la rechaza si cita una fuente que no
usó, si nombra un organismo que no está entre las citadas, o si suelta una cifra de dosis sin una
fuente de dosis autorizada. Lo rechazado se vuelve a pedir una vez. **Dato honesto y medido:
alrededor del 10% de las respuestas se regeneran.**

**"¿Quién lo ha revisado?"** — Nadie. Dilo tal cual. Es lo que más credibilidad te va a dar ahí, y
mentir en eso sería la única mentira que de verdad podría hacer daño.

**"¿Y si el corpus se queda anticuado?"** — Cada documento guarda su hash de origen; la ingesta
detecta cambios y reprocesa. Los calendarios de vacunas llevan el año de la fuente a la vista.

**"¿Qué modelo usa?"** — DeepSeek. No lo escondas; en HN preguntarlo es rutina y ocultarlo queda
peor que la respuesta.

**"¿Cuánta gente lo usa?"** — Casi nadie, y **no lo maquilles**: 235 impresiones en Google en 30
días, 3 clics, posición media 75. En HN la humildad medida puntúa; un número inflado se detecta y
hunde el hilo.
