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

## 28-oct-2026: Wayan Vota la acepta

> «I love this post idea. Please share a draft of your post.» (wayan@wayan.com, 28-oct 17:20 UTC,
> hilo «ICTworks Guest Post»). Borrador escrito el 29-oct, **pendiente del sí del operador**: va
> con su nombre y es de fondo. Prefieren un Google Doc.
>
> Un cambio respecto al resumen, a propósito: el punto 2 decía «the language model never writes
> the answer», y no es verdad: el modelo redacta, a partir de los pasajes. Ahora dice lo que pasa.
> Cifras releídas el 29-oct: 54 de 54 países africanos con número de urgencias y calendario
> (offline-data), 92 calendarios, ~1 MB de datos guardados en el móvil, Etiopía 100 mg/5 ml, 28
> formulaciones (estudio de 2025, tests/test_the_parent_can_type_their_own_bottle.py), /muac
> precargada en sw.js. Unas 760 palabras.

```
Offline, Local and Cited: Child-Health Answers for Parents in Africa

I'm an architect in Seville, Spain. In my spare time I build PediBot (pedibot.xyz), a free website that answers parents' questions about a sick child using only published paediatric guidelines, with the source beside every sentence. It covers the emergency number and vaccine schedule of all 54 African countries, and it keeps working without signal after the first visit.

I'm not a doctor, and I didn't start from a theory of digital health. What I have is a list of things that went wrong while I was building it, and three design decisions that came out of them. If you're putting health information on a parent's phone, I think they travel.

1. Local is a safety feature

The word "drops" on a bottle of children's paracetamol means very different things depending on where you buy it. In Spain, Portugal and India the drops are usually 100 mg per ml. In Ethiopia, according to the national regulator's list, they are 100 mg per 5 ml. Same word, same dropper, five times the strength.

I found this by accident, looking for local brand names. Ethiopia's register doesn't list brands; it lists strengths. My calculator only had the Spanish drops, so a parent in Addis Ababa reading "drops" on their bottle would have picked them and given a fifth of the dose.

Adding Ethiopia wasn't the real fix. A 2025 study of national essential medicines lists counts 28 different paracetamol formulations around the world. Chasing them country by country is a race you lose. So the calculator now does two things. It shows first the strengths that the parent's own country lists, and it lets the parent type exactly what their bottle says.

The milligrams never come from what they type. They come from the child's weight and a fixed, published dose table, so a typo changes the volume, not the dose. And anything outside a plausible range gets no number at all, just a question: does your bottle say mg per ml, or mg per 5 ml?

2. The model reads and writes; the guidelines decide

A language model helps in two places: reading the parent's message, and turning guideline passages into plain sentences. It doesn't add medical content of its own. Every sentence points to the passage it came from, and when the guidelines don't cover the question, PediBot says so instead of filling the gap.

Parents write in the language they speak, which is often not one of the site's eight. Before searching, a model reads the message for its language and meaning and restates it in medical English. In languages the site doesn't cover, that step alone turned poor matches into the right guidance. The answer then goes back in the parent's own language.

The alarms are not left to the model at all. Rule-based checks read both the original message and the translation, so a child with blue lips gets the red emergency banner, with the country's number, whatever language the parent writes in. A baby under three months with a fever gets the same banner, in Swahili as in German.

3. Built for the phone parents actually have

After the first visit, the parts that matter most in an emergency keep working with no signal: the warning signs, the dose calculator, the arm tape for malnutrition and the emergency numbers. They run on the device, with no server and no model. Everything the phone keeps for that, including 92 national vaccine schedules, is about one megabyte.

The chat itself still needs a connection. I'd rather say that plainly than let anyone find out at the wrong moment.

What I'm still missing

Many national essential medicines lists in WHO's new repository are scanned PDFs. I won't use OCR on dose data: a misread digit there is exactly the mistake all of this is designed to avoid. So if your programme has your country's list as text, or knows who does, I'd love to hear from you.

And if you try PediBot with the questions parents bring you and it gets something wrong, I'd like to hear that even more.
```
