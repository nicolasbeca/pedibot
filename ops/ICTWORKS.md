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
> hilo «ICTworks Guest Post»). Borrador escrito y **ENVIADO el 29-oct** con su sí, en el hilo: va
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

## 3-nov-2026: reescrito con su historia (primera versión, PARADA por él)

> Wayan (1-nov): «This reads as if it was written by AI… Please add your own color to the words.
> You can also add a link to your Hugging Face data sets.» El operador mandó su historia por audio
> el 3-nov (el hijo con bronquitis y laringitis, casi neumonía; los documentos de la AEP metidos en
> un LLM; acceso fácil al pediatra que otros no tienen; empezó en inglés y luego idiomas de países en
> desarrollo; las gotas de Etiopía y lo anglosajón de internet; la mente ordenada del arquitecto; las
> herramientas de automatización del principio, que dependían de la IA de un tercero). Nada inventado.
>
> Comprobado en lo publicado el 3-nov: 8 idiomas en la web (SUPPORTED_LANGS) y el suajili en los
> avisos (TRIAGE_LANGS); 54 de 54 africanos con número y calendario en offline-data; 92 calendarios;
> los seis ficheros sin conexión suman 1.017.729 bytes; Etiopía «gotas 100 mg/5 ml» (config/drugs.yaml,
> EFDA); la ingesta (src/pedibot/ingest) no llama a ningún modelo. Hugging Face tiene UN dataset,
> pedibot-sources, CC0, todavía con los 632 documentos de entonces (subido el 28-sep; el local ya tiene más): por eso dice «a
> catalogue of the documents behind PediBot» y no «every document». voz.py --palabras 800: limpio, 743
> palabras. El título es el que Wayan aceptó.

```
Offline, Local and Cited: Child-Health Answers for Parents in Africa

My son had a bad run of bronchitis and laryngitis, and at one point he was close to pneumonia. I wanted information I could trust. I had a few books at home, so I was looking things up on paper, and I didn't trust much of what I found on the internet.

Then I found the documents of the Spanish Paediatrics Association. I downloaded them and gave them to a language model, with one rule: answer only from these. Honestly, it worked quite well.

That made me think. In Spain I can see a paediatrician easily, in the public system or in a private one. A lot of parents can't. They don't have those documents either, and most of them wouldn't know how to set up a language model to read them. So I started PediBot (pedibot.xyz) as a personal project, free and with nothing to sell. It wasn't an idea I had one day. It grew step by step.

I'm an architect, not a doctor. What I bring from architecture is an ordered way of thinking, and that helps a lot when you want to get real work out of AI tools.

English first, then the languages that need it

I started in English, because it's the international language. Then I thought it made more sense to go where good information is harder to find. Today the site works in eight languages, Hindi and Arabic among them, and the emergency alarms also read and answer in Swahili. It has the emergency number and the vaccine schedule of all 54 African countries.

The same drops, five times stronger

Going through each country's information, two things surprised me. Some countries have very little published. And medicines change from one place to another, while almost everything you find online is written for the English-speaking world.

Paracetamol drops are the clearest example. In Spain they are 100 mg per ml. In Ethiopia, the regulator's list has drops of 100 mg per 5 ml. Same word on the bottle, and the Spanish ones are five times stronger. My calculator only had the Spanish drops, so a parent in Addis Ababa choosing "drops" would have given a fifth of the dose.

Now the calculator shows first what the parent's own country lists, and the parent can type what their bottle says. The milligrams always come from the child's weight and a fixed, published dose table. What the parent types only turns them into millilitres.

What I got wrong at the start

My first versions used other automation tools. They were clumsier, and almost every step needed an answer generated by someone else's AI model. So I depended on a third party, and I had to trust how that model read the official documents.

Now the documents go in by rules. The text is extracted and classified by code I can check, with no model in between. The emergency alarms are rules too. They read the parent's message and its English translation, so a child with blue lips gets the red banner with the country's number, whatever language the parent writes in.

The model still has a job. It reads the question and writes the answer, but only from the passages the search gives it, and every answer cites its sources. Code checks the answer before it goes out, and when the guidelines don't cover something, PediBot says so.

Built for the phone parents actually have

After the first visit, the parts that matter most in an emergency work with no signal: the warning signs, the dose calculator, the arm tape for malnutrition and the emergency numbers. They run on the phone, with no server and no model. All the data the phone keeps for that, including 92 vaccine schedules, is about one megabyte. The chat still needs a connection.

What I'm missing

A catalogue of the documents behind PediBot is public on Hugging Face, with the publisher, the topic, the language, what may be done with each one and the link to the original. It's CC0, so anyone building something similar can start there: https://huggingface.co/datasets/PediBot/pedibot-sources

What I still don't have is text. Many national medicines lists in WHO's repository are scanned PDFs. I won't use OCR on dose data, because a misread digit is exactly the mistake all this is built to avoid. If your programme has your country's list as text, I'd like to hear from you.
```

Nota en el hilo:

```
Hi Wayan,

Here it is again, rewritten with my own story behind it. The Hugging Face link is in the last part. If you want a screenshot of the dose calculator for the post, I can send one.

Nicolas
```

## 3-nov-2026: segunda versión, ESPERA SU SÍ

> La primera la paró al leerla: «Ninguna persona escribe datos muy concretos ni muy específicos…
> Quita frases tuyas tipo la de soy arquitecto no doctor» (L267). Ésta, sin una sola cifra, con
> las frases encadenadas como en su audio y sin frases que él no dijo. Lo que afirma sigue
> comprobado en lo publicado (arriba). voz.py --palabras 800, con las reglas nuevas: limpio.

```
Offline, Local and Cited: Child-Health Answers for Parents in Africa

My son went through a very bad stretch of bronchitis and laryngitis, and at one point he was close to pneumonia. I was looking for information I could trust. I had some books at home, but that meant searching through a physical book every time, and I didn't really trust what I was finding on the internet.

Then I found the documents of the Spanish Paediatrics Association. In the end I decided to download them and put them into a language model, so that the answers would come only from those documents. The truth is that it worked quite well for me.

Here in Spain I have easy access to a paediatrician, because I can use both public and private healthcare. But I kept thinking about the people who don't have that access, or the documents I had, and who wouldn't know how to use a language model either. So I decided to turn it into an altruistic project of my own, to bring reliable paediatric information to people who don't have it close at hand. All of this came little by little, over time.

By profession I'm an architect, and what I've brought from that is an ordered mind, which helps me get the most out of some AI engines to build tools like this.

From English to the languages that need it

I started PediBot (pedibot.xyz) in English, as the international language, but later I thought it was more interesting to adapt it to languages spoken in developing countries. Today it also works in Hindi and Arabic, among others, and the emergency warnings come out in Swahili as well.

Every country is different

When you research what information each country has, you realise that some countries are very short of it, and that the same medicine changes from one place to another. It isn't easy to find this online either, because almost everything is written with the English-speaking world in mind.

Paracetamol drops are a good example. In Ethiopia they are much less concentrated than the ones we use in Spain, so a dose calculator built only with the Spanish drops would have told a parent there to give far too little. Now the calculator first shows the bottles listed in each country, the parent can also type what their own bottle says, and the dose itself always comes from the child's weight and a published table.

What went wrong at the beginning

At first I tried to build it with other automation tools, but they were clumsier, and they needed a lot of answers generated by AI engines, so I depended on a third party. I also had to trust whatever that AI understood from the official documents.

Now it works with rules and direct automation. The documents go in without any AI interpreting them, and the warning signs that mean a child has to be seen urgently are rules as well, so they work in whatever language the parent writes. A language model still reads the question and writes the answer, but it can only use the passages of the guidelines that the search finds. The answer shows where each part comes from, and if the guidelines don't cover the question, PediBot says so. For me this is much safer than what I had at the start.

For the phones people really have

Where signal or data is short, the parts that matter most keep working without a connection after the first visit. I mean the warning signs, the emergency number of each country, the dose calculator and the arm tape for malnutrition. All of that weighs very little on the phone, although the chat does need a connection.

Where I could use some help

A list of the documents behind PediBot is open on Hugging Face, with the organisation, the topic, the language and the link to each original. In case it is useful to anyone working on something similar, it's here: https://huggingface.co/datasets/PediBot/pedibot-sources

What I'm missing now are the national medicines lists of many countries in a form I can read. In the WHO repository a lot of them are scanned PDFs, and I prefer not to use OCR on doses, because a wrong digit there is exactly the kind of mistake I'm trying to avoid. If your programme has your country's list as text, I would be happy to hear from you.
```

Nota en el hilo: la misma de arriba.
