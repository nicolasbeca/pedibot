# ICTworks — la propuesta de artículo (21-sep-2026)

> Comprobado antes de preparar nada (L206): el blog sigue activo en 2026, llega a unos 30.000
> profesionales de tecnología para el desarrollo, y sus normas piden primera persona, lecciones y
> sorpresas, nada de promocionar la organización, **750 palabras como máximo** con subtítulos y
> listas, y una imagen de al menos 640 píxeles de ancho.
>
> **El formulario no es para mandar el artículo: es para proponerlo.** Se manda el resumen; si
> les interesa, piden el texto entero (en un Google Doc, que es lo que prefieren).

## Las casillas

| casilla | qué poner |
|---|---|
| First Name | Nicolás |
| Last Name | Beca |
| Email | pedibot.ai@gmail.com |
| Organizational Affiliation | PediBot (independent, self-funded) |
| Primary Topic Area | Digital Health |
| Primary Technology Focus | Artificial Intelligence / Machine Learning |
| Primary Geographic Focus | Africa |
| Guest Post Synopsis | el texto de abajo |
| Publication Deadline | nada |

## El resumen

> Reescrito el 21-sep-2026 a petición del operador: contaba tres errores míos; ahora cuenta
> tres decisiones de diseño y lo que consiguen para un padre (ver la memoria «hacia fuera, lo
> que hace la web»).

```
Working title: Offline, Local and Cited: Child-Health Answers for Parents in Africa

I am an architect in Seville, Spain, and in my spare time I build PediBot (pedibot.xyz): a free site that answers parents' questions about a sick child using only published paediatric guidelines, with the source beside every sentence. It covers the emergency number and vaccine schedule of all 54 African countries and keeps working with no signal after the first visit. The post would walk through three design decisions behind it, for anyone putting health information on a parent's phone.

1. Local is a safety feature. The same medicine comes in very different strengths from one country to the next: paracetamol drops are 100 mg per 5 ml in Ethiopia and 100 mg per ml in Spain, five times stronger. A 2025 study counts 28 paracetamol formulations across national essential medicines lists. So the dose calculator shows first the strengths that each country's regulator lists, and lets the parent type exactly what their own bottle says, while the milligrams always come from a fixed, published table.

2. The language model reads the question and never writes the answer. Parents write in the language they speak, often not one of the site's eight. A model reads the message for its language and meaning and restates it in medical English for the search; in languages the site does not cover, this turned poor matches into the right guidance. The answer still comes only from cited guidelines, it is written back in the parent's own language, and when the guidelines do not cover the question it says so. The rule-based alarms read both the original and the translation, so a child with blue lips triggers the red emergency banner, with the country's number, whatever language the parent writes in.

3. Built for the phone parents actually have. The whole site is about five megabytes and works offline after the first visit, and the parts that matter most in an emergency, the warning signs, the doses, the arm tape for malnutrition and the emergency numbers, are computed on the device without a server or a model.

I would close with an open question to readers: many national medicines lists in WHO's new repository are scanned PDFs, and I will not use OCR on dose data, so I am looking for programmes that can share them as text.

About 750 words, informal and first person, with one screenshot of the dose calculator.
```
