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

```
Working title: Five Times the Dose: Three Lessons From Building Offline Child-Health Information for Africa

I am an architect in Seville, Spain, and in my spare time I build PediBot (pedibot.xyz): a free site that answers parents' questions about a sick child from published paediatric guidelines, shows the source beside every sentence, and keeps working with no signal after the first visit. It carries the emergency number and vaccine schedule of all 54 African countries. I am not a doctor, and the post is not about the site. It is about three things I got wrong in the last month, which I think apply to anyone putting health information on a parent's phone.

1. Localisation is a safety feature, not a translation task. Reading Ethiopia's official list of over-the-counter medicines, I found that paracetamol drops there are 100 mg per 5 ml, while in Spain and India drops are 100 mg per ml. My dose calculator only knew the second. A 2025 study counts 28 paracetamol formulations across national essential medicines lists, so chasing every bottle is a race you lose. What works is letting the parent type what their own bottle says, while the milligrams stay in a fixed, published table.

2. Green tests are not a safe output. My first fix sorted the weaker drops to the top of the list, where a parent in Madrid could have given five times too much. Every test passed. I found it by using the page like a scared parent at three in the morning. Two rules came out of it: no default value on any input that changes a dose, and test the order of what a user sees, not only whether it is there.

3. Use the language model to read, never to answer. A parent in Italy got an English answer built from a Brazilian page about polio, because keyword search matched false friends across languages. I measured it on real-style questions: in languages the site does not support, letting a model restate the question for the search turned results from HIV and typhoid pages into the right fever guidance; in languages it does support, it made things slightly worse. So the model now only reads: the language, the intent, and a medical restatement. Answers still come only from cited guidelines, and the rule-based alarms run on the original text plus the translation, so the model can add an alarm but never remove one.

I would close with what I still cannot solve: many national medicines lists in WHO's new repository are scanned PDFs, and I will not use OCR on dose data.

About 750 words, informal and first person, with one screenshot of the dose calculator.
```
