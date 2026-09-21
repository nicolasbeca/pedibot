# Show HN — DESCARTADO el 20-sep-2026

> **Decisión del operador, y es suya: «olvídate de Hacker News, no es nuestro público».**
>
> Tiene razón en lo principal. El público de ahí es técnico y occidental, y este proyecto sirve
> a padres en Nairobi, Lagos, El Cairo y Patna. Un pico de un día de gente que mira el código y
> no vuelve no es tracción: es una gráfica bonita.
>
> El matiz, para que quede escrito y no se pierda: **yo no iba buscando usuarios, iba buscando
> enlaces.** La medición de Search Console del 20-sep dice que las páginas de dosis están bien
> hechas y en la posición 80 porque el dominio tiene tres semanas y **nadie lo enlaza**. Eso
> sigue siendo el cuello de botella con Hacker News o sin él, y hay que resolverlo en otro sitio.
> Lo que se busca es un enlace desde una página que Google respete, y eso puede venir del
> registro de bienes públicos digitales, de una sociedad de pediatría, de una ONG o de un blog
> médico, que además sí son nuestro público.
>
> El texto de abajo se conserva porque **sirve casi entero para cualquier otro sitio**: la
> explicación de las tres barreras entre la pregunta y la respuesta, lo de que nadie lo ha
> revisado y lo de cuánta gente lo usa se reaprovechan tal cual. Sólo hay que cambiar el tono
> del primer párrafo, que está escrito para programadores.


Guardado aquí porque la vez anterior se redactó en una conversación y se perdió con ella.
**Las cifras se releen antes de publicar.** Se recontaron el 20-sep-2026 contra `DATOS.md`:
decía 288 documentos cuando son 497, 18 organismos cuando son 21 y 7 calendarios cuando son 66,
porque el texto se escribió el 6 de septiembre y el candado de `scripts/check_docs.py` no lo
cogía por una palabra en medio («288 **published** documents»). Eso ya está arreglado, pero
vuelve a mirarlas igual.

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

It answers only from a corpus of 497 published documents from 21 bodies — NHS, WHO, CDC, RKI,
SEUP, MedlinePlus, AAP and others. Three things make it different from asking a general chatbot:

1. Retrieval first, and when nothing in the corpus covers the question it says so instead of
answering. That was the hardest part to get right and it is still the thing I check most often.

2. Doses are never generated. They are looked up in a fixed published table by weight, and a
guard blocks any answer containing a mg or ml quantity unless an authorised dosing source is
among its citations. A language model is not allowed near a milligram figure.

3. A rule-based check reads the question for red flags before any answer is produced and puts a
banner above it. It runs before retrieval, so it fires even when the corpus has nothing to say.
It does not diagnose: it says what the warning sign means and when a child needs to be seen.

There are also 507 guides in 8 languages built from the same corpus, where every statement
carries the number of the document it came from, listed at the foot with organisation, title and
page. Plus the national vaccination schedule for 66 countries and the emergency number for 90,
each citing its own national authority.

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
el 11% de las respuestas se regeneran** (lo dice `doctor` contra el servidor; reléelo antes de publicar).

**"¿Quién lo ha revisado?"** — Nadie. Dilo tal cual. Es lo que más credibilidad te va a dar ahí, y
mentir en eso sería la única mentira que de verdad podría hacer daño.

**"¿Y si el corpus se queda anticuado?"** — Cada documento guarda su hash de origen; la ingesta
detecta cambios y reprocesa. Los calendarios de vacunas llevan el año de la fuente a la vista.

**"¿Qué modelo usa?"** — DeepSeek. No lo escondas; en HN preguntarlo es rutina y ocultarlo queda
peor que la respuesta.

**"¿Cuánta gente lo usa?"** — Casi nadie, y **no lo maquilles**. Medido contra Search Console y
contra el registro del servidor el 20-sep-2026, o sea el día que se publicó:

- **341 personas** han entrado desde el 25 de agosto, en 558 visitas.
- **1.837 impresiones** en Google en 28 días y **3 clics**, con posición media 65,6. (Doce días
  antes eran 392 impresiones y posición 74,3: Google la está enseñando cada vez más, pero en la
  página siete, que es donde no pincha nadie.)
- **Nueve preguntas al chat en toda su vida.** Cuatro en la última semana.
- Lo que la gente sí busca son dosis por marca: «calculadora apiretal», «calpol dosage»,
  «doliprane posologie». Ni una sola consulta de chat.

En HN la humildad medida puntúa, y esas cifras cuentan además la historia de verdad: el producto
no tiene un problema de producto, tiene un problema de que nadie lo enlaza. Un número inflado se
detecta y hunde el hilo.

---

# El texto para CHIFA (20-sep-2026)

Esto es lo que sustituye al Show HN. Va a `chifa@hifaforums.org` después de apuntarse (gratis).
Escrito para personal sanitario y padres de países de renta baja, no para programadores: **se
reparte el hallazgo, no el enlace**, y el hallazgo aquí es concreto y de los suyos.

**Asunto:** Paracetamol drops: 100 mg/5 mL in Ethiopia, 100 mg/mL in Spain

```
Dear CHIFA colleagues,

I want to share something I got wrong, because I suspect it is not only my problem.

I run a free site that answers parents' questions about their sick child from published
paediatric guidelines, in eight languages, with the source shown beside every sentence. Part of
it is a dose calculator by weight for paracetamol and ibuprofen. Until this week it offered a
list of the bottle strengths I knew about, and the parent picked theirs.

Then I read the EFDA list of medicines allowed over the counter in Ethiopia, and found that
paracetamol drops there are 100 mg/5 mL. In Spain, Portugal and India, drops are 100 mg/mL —
five times stronger. My list only had the second one. A parent in Addis Ababa holding their
bottle would read "drops" on the label, find "drops 100 mg/mL" on my page, and give five times
the volume that bottle needs.

I fixed it, and then made it worse: the new, weaker strength sorted to the top of the list, so a
parent in Spain with the concentrated drops could have taken the first line and overdosed by
five. I found that by looking at the page the way a parent looks at it, not by reading my code.
All my tests were green.

What I have done since is stop trying to know every bottle. A 2025 study of national essential
medicines lists counts 28 different paracetamol formulations worldwide. So the calculator now
has a field where the parent types what their own bottle says, in mg per 5 mL or mg per mL, and
that line is shown first. The milligrams are still computed from the child's weight by a fixed
published table; the typed number only converts to millilitres, so a mistyped concentration
changes the volume and not the dose. Out of a plausible band it refuses to give a number and
asks them to check whether the bottle says per mL or per 5 mL.

Two questions for this forum, and they are the reason I am writing:

1. Is this confusion something you see in practice? I only found it because I went looking for
   Ethiopian brand names and found strengths instead.
2. I have since read the national essential medicines lists of Ethiopia, Rwanda, Mozambique
   and DR Congo myself. Madagascar's list gives paracetamol syrup as 125 mg/mL, which would be
   five times the usual strength, so I have not added it: I cannot tell whether it is a real
   product or a typo. If anyone here works in Madagascar, or in Angola or Malawi, whose lists I
   could not read, I would be grateful for a pointer. I will only add a country when I can read
   its own document; I am not willing to guess.

The site is pedibot.xyz, free, no account, no advertising, and it works on a phone with no
signal after the first visit. No clinician has reviewed any of it and I am not a doctor, which
is the main thing wrong with it and the reason I am asking here.

Thank you,
[nombre]
```

**Notas para ti, no para ellos:**

- **Abre con un error propio, y es deliberado.** En una lista de profesionales, llegar diciendo
  «he construido una cosa» es ruido; llegar diciendo «me equivoqué así y puede que os pase» es
  una conversación. Y además es verdad.
- **Las dos preguntas del final son de verdad**, no retóricas. Si alguien contesta con el
  registro de su país, eso vale más que cien visitas: son los países que faltan.
- **Lo de que nadie lo ha revisado va dentro.** Es lo que más credibilidad da ahí y ocultarlo en
  una lista de sanitarios sería el peor sitio posible para ocultarlo.
- El enlace va una sola vez y al final, detrás de todo lo que sí aporta.
