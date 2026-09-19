# MetaDAO — los textos definitivos

> 19-sep-2026. Las tres preguntas del formulario, con el texto aprobado por el operador y listo
> para pegar. **El formulario es texto plano**: nada de viñetas, nada de asteriscos, nada de
> encabezados. Lo pidió él después de ver cómo se veía el primero, y tiene razón: en ese cuadro
> un `- ` se queda en un guion suelto y un `**` se ve literal.
>
> **Todas las cifras están releídas de los ficheros publicados** el día que se escribieron. Si
> pasan días hasta el envío, se vuelven a contar: `scratchpad/comprueba_cifras_metadao.py` lo
> hace en un minuto. Regla de la casa, y ya salvó un error: yo había escrito «ocho países sin
> número de emergencias» y son siete, más uno donde no pudimos verificarlo.
>
> Estado: **las siete aprobadas por el operador.** Listas para pegar, de arriba abajo.
>
> Un arreglo del 19-sep que vale para las tres: «las tres de la mañana» aparecía cuatro
> veces —lo vio él— y una imagen repetida deja de ser una imagen. Queda **una sola vez**, en
> el cierre de P2, que es donde remata.

---

## P1 · Who are you, what is your background, and why are you the right person/team to build this?

*(8.000 caracteres · este texto: 5.412)*

My name is Nicolás Beca. I am an architect, I am not a doctor, and I do not have a team.

PediBot exists because my son had a difficult first few months and I could not find information I could trust. I will not tell you what was wrong with him, because that is his and not a pitch. What I will tell you is what those nights were actually like: a screen full of forums, of content farms, of sites that answered everything with total confidence and cited nothing, and none of it written by anyone who would put their name to it. Somewhere in there I stopped looking for an answer and started wanting the thing that did not exist: a place that tells you what the paediatric societies actually say, names the document, and admits when it does not know.

So I started building it, in January of this year, alone, in my own time and out of my own pocket. The site you can open today has been live since the end of August.

Since then: emergency numbers for 88 countries, vaccination schedules for 61, WHO growth charts for 69, 502 guides in eight languages, 496 paediatric documents catalogued with their licences read one by one, and 8,876 automated tests. I describe all of it in the next answer. I mention the test count here for one reason: in this project a bug is a wrong emergency number, and the only way to stop shipping one is to make every rule prove itself on every change.

It does not diagnose. It quotes, it names the source, it links the original, and when nothing in its sources supports an answer it says so instead of filling the gap. That last rule is the whole project. Anyone can build something that always has an answer.

Why me, then. Three reasons, and none of them is a credential.

First, I hunt my own mistakes in public and fix them the same day. Two from this week. The country selector had no empty option, so the first country alphabetically, the United Arab Emirates, came preselected: a parent in Madrid asking about a baby with blue lips was being told to call 998. Weeks of careful data undone by a default. I found it by testing against the live site instead of reading my own code, fixed it, and wrote a test so it cannot come back. The second: the safety layer treats "ni" as a Spanish negation, because it is. In Swahili, "ni" is the verb to be. So a Kenyan parent writing "midomo yake ni ya bluu", his lips are blue, had the alarm silenced by a word meaning "is". A silence, not a false alarm. That one frightened me more than anything I have written in my life.

Second, I know exactly what this is not. It is not a medical device. It is not a diagnosis. And for the parent it is free and it stays free: no subscription, no advertising, no sale of anyone's data, ever. I pay for the server myself. It is a small amount of money and it is the cheapest thing I do.

That does not mean it can never pay for itself. It can, from the other side: the engine underneath is deterministic on purpose, which makes it the kind of thing an institution can audit and stand behind, and that is what I would licence. The details are in the funding answer. What will not happen is charging the parent.

Third, the work is already given away. The catalogue of those 496 documents, the classification, the licences, the topic taxonomy, months of reading, belongs to nobody: I put it in the public domain and anyone can download it from the site. If I disappear tomorrow, someone else picks it up. That is not generosity. It is the only honest way to build something whose value is that it exists, not that I own it.

Now the part that matters, and I will be direct with you, because you are going to read a lot of applications this month.

You are here to make money, and you should be. Most of what you fund has to make money or the mechanism stops working and none of this is here next year. I am not asking you to pretend otherwise. I am asking for the other thing.

There are seven countries where PediBot cannot give an emergency number, because the government source says plainly that no national emergency service exists. Not "we could not find it": there isn't one. In an eighth, Zambia, we could not verify the number we found, so the page says that too. Every time I open that list I think about what it means to be the parent on the other side of it.

Those seven countries, and the fifty-odd others added this month, are not a market. Nobody is going to make money out of a parent whose phone has run out of credit, and anyone who tells you otherwise is selling you something. What that parent needs is to know whether the way their child is breathing is normal, and somebody to ask. It is what I needed, in a far better place, with far more.

So that is what this is. An answer, free, in their language, with the document attached so they can go and check me.

You can fund a hundred things this year that will make you richer. You will fund very few that you would describe to your family over dinner. I think this is one of them. I think it costs you almost nothing to find out. And I think that in six months the honest measure of whether I was the right person to build it will not be my background, which is architecture, or my team, which is nobody. It will be whether those numbers are bigger, still cited, and still free.

Everything is at https://pedibot.xyz. The sources page lists every document. The legal page says exactly what is stored and what is not. Nothing on that site needs an account.

---

## P2 · What are you building, and who is it for?

*(8.000 caracteres · este texto: 4.972)*

PediBot is a free site that answers parents' questions about a sick child using only what paediatric societies, health ministries and the WHO already publish for families. Every answer carries the document it came from and a link to it, and there is no diagnosis anywhere in it.

At the centre is a chat that answers in eight languages, with each claim followed by the organisation, the document and a link the reader can open. Behind it sit 496 catalogued paediatric documents, each with its licence read one by one. But the part that matters is what happens before the model is asked anything: a layer of fixed rules, 83 red flags, decides urgency first. If what the parent describes matches one, the first thing they see is the warning and their country's emergency number, not a paragraph. And drug doses never come from a model at all. They are looked up in published tables, by weight, with the brands actually sold in each country.

Around that there is a set of tools that are just data, carefully transcribed and always attributed. Emergency numbers for 88 countries, each with the government source it came from, including the handful where the honest answer is that there is no number to give. Childhood vaccination schedules for 61 countries, transcribed from the official documents, with the ministry that issues each one and the date it was checked. WHO growth charts for 69 countries, with the percentile worked out on the device. A dosing calculator for paracetamol and ibuprofen. And 502 guides in eight languages, every one citing documents a reader can open.

Since this week there is also an optional account. You save each child's date of birth, and then you ask "what vaccines are due for Laura?" and it answers for Laura's age. You can record her weight and height and see her own curve on the WHO bands, and send her next appointments to your phone's calendar. The account is optional, nothing else on the site needs one, and you can download everything or delete it from a button.

And all of it except the chat works with no signal. The emergency numbers for all 88 countries, the red flags, the schedules and the growth tables sit inside the phone. With no connection it still opens and tells you what it knows. Only the chat needs the network, because a model writes it.

Who is it for. First, the parent who in the middle of the night has nobody to ask. That happens everywhere, including in rich countries: the paediatrician does not answer the phone at night and the hospital is half an hour away.

But mostly it is for the places where there is no paediatrician to call at night, or at eleven in the morning either. That is why the eight languages are not English and Spanish with decoration: there is Arabic, Hindi, Russian and Portuguese, and the safety layer also reads Swahili. That is why 48 African countries have their emergency number and their schedule in it. And that is why each page weighs under twenty kilobytes and the data lives inside the phone: because the mother this is actually for runs out of credit halfway through the month.

It is also for families living where nobody speaks their language. A Moroccan family in Madrid needs the Spanish number and the explanation in Arabic, and that is written into the code: the country shown first is the reader's, not the language's.

And there is a second audience you will care about more. Millions of parents are already putting these questions to a language model, and it answers with whatever it happens to hold. If it is going to answer anyway, let it cite something real. That is why the catalogue of 496 documents is published as CC0, public domain, downloadable from the site; why there is a machine-readable map of the project written for those assistants; and why PediBot offers its tools as an agent on an agent marketplace. Anyone can take all of that and build on it without asking me.

Who it is not for. It is not for someone looking for a diagnosis, because it does not give one. It is not a clinical tool and it is not aimed at professionals. It does not replace a paediatrician or an emergency department, and it says so on every page and in every answer. If your health service says something different, your health service is right.

Where this actually stands today, with no dressing up. I finished this week's work this week, and I have announced it nowhere. In the last seven days two real people used it. I am not going to sell you traction that does not exist. What exists is the thing itself, built, running and tested to the point of obsession, and eighty-eight countries' worth of data that nobody had gathered in one free place in eight languages. What is missing is for anyone to know it is there.

And when they do, this is who is on the other side: a mother in Kisumu at three in the morning, with no credit on her phone, watching how her daughter is breathing and with nobody to ask. That is not a market. That is the person it is built for.

---

## P3 · Who are your main competitors. and why do you beat them?

*(8.000 caracteres · este texto: 5.402)*

My real competitors are not other apps. There are three of them, and two I am not going to beat.

The first and biggest is Google at four in the morning. That is where a frightened parent goes, and what they find is forums, sites built to place advertising, and pages that answer everything with total confidence and cite nothing. That is the real competitor, it is free, and right now it is winning. I do not beat it by being cleverer. I beat it on the only thing that matters at that hour: every sentence in my answer carries the body that says it, the document, and a link to check it. A parent who has already read four contradictory things does not need a fifth opinion. They need to see who signs it.

The second is ChatGPT and the other assistants, and that is the serious one. Millions of parents already ask them whether their child needs a hospital, and they often answer well. Where they fail is where it hurts most: they do not cite a source, so nothing can be checked; they do not know the emergency number for the country the parent is in, or the vaccination schedule that applies to that child, because none of that lives in a model, it lives in a ministry's PDF; and above all they always have an answer. A model does not know how to stay quiet. PediBot does, and that silence is the feature I am proudest of.

There is also a difference that is not about quality but about architecture. In PediBot the urgency is not decided by the model. It is decided by fixed rules that run first, and a dose is never something the system writes: it is something it looks up. A general assistant cannot promise either of those, because everything it says is generated.

But I am not kidding myself: I do not beat the assistants, I complement them. That is why I gave the catalogue away under a public domain licence and left them a map of the site, as I described in the previous answer. If ChatGPT answers these questions tomorrow citing my sources, I have won. The goal is not that people come to my site. The goal is that a parent does not get an invented answer.

The third group is the health services and the paediatric societies: the NHS, the CDC, the Spanish Paediatric Association, the ministries. They are better than me at what they do and I will not pretend otherwise. They are the source, and in fact they are my sources. Where they fall short is in form. Each covers one country and one or two languages, their material is scattered across dozens of PDFs, and nobody navigates an institutional site at night looking for the bronchiolitis leaflet. What I do is gather 88 countries in eight languages, read them, transcribe them with their source and their date, and answer in the language of the person asking. Nobody was doing that for free.

Then there are the symptom checkers, such as Ada, K Health, Infermedica or Mediktor. They are serious and some of them are good, but they play a different game: they give a diagnostic orientation, they ask for an account, and they have to monetise, through subscriptions, insurers, or licensing the technology. I do not give a diagnosis, and nothing on the parent's side is monetised or ever will be, which removes the conflict of interest they carry. If this ever pays for itself it will be by licensing the engine to institutions, not by charging the mother. It is also worth looking at how Babylon Health ended, after raising hundreds of millions: in this field it is usually the business model that kills the product, not the medicine.

And the baby tracking apps, the ones with the growth curves and the feeds, used by millions of parents. Those I do watch closely, because I have just built the same thing. They do one thing well: recording. What they do not do is answer. You note the weight and you get a dot on a curve, but when at night you type "his ribs are pulling in when he breathes", there is nobody on the other side. PediBot does both: the measurements plotted where a paediatrician would plot them, and an answer with its source on the night you need one. And no advertising in the middle of it, which is the first thing you meet when you open most of them.

Two more things that none of them has. The first is that it keeps working with the phone offline, which I described above and which no app on this list does. The second is that it asks for no account, charges nothing, carries no advertising and sells no data, and it never will on the parent's side.

Where I lose, which is worth saying too. I lose on conversational speed against a general model. I lose on brand: nobody knows me, I am not in the app stores, and I have been findable for three weeks. I lose to the NHS on authority about England, and I lose to a real paediatrician every single time, which is what the site repeats on every page. And my answer is never better than the documents I hold: where there is no openly licensed paediatric source, and in Swahili there is none, I say so and answer in English.

So the honest answer to "why do you beat them" is that I do not beat most of them, and the ones that matter I do not want to beat: I want them to use my catalogue. The one I do beat, because it is the one answering those parents today and should not be, is the sourceless forum and the page built to place advertising. That is the competitor. Bringing a single parent back to what their own health service actually says already justifies this.

---

## P4 · What stage are you at?

Se marca «Live», que es la única casilla verdadera: está construido entero, en producción y
funcionando, y no hay ingresos. No es MVP —no es un esqueleto para probar una idea— y no es
post-revenue, porque no ha entrado un euro.

(Esta pregunta es un botón, no un cuadro de texto: aquí no hay nada que pegar.)

---

## P5 · How many users do you have? Include revenue, volume, waitlist, or other traction if relevant.

*(8.000 caracteres · este texto: 3.514)*

Since it went live on 25 August, 337 people have visited with a real browser, in 531 visits and 1,943 page views. I say "real browser" because the counter only counts someone who asked for the page and then for its stylesheet or its font, which is what a browser does and a crawler does not; the other 8,727 requests I do not count as people. I would rather have a small number that is true.

A third of them looked at more than one page: 104 of 337. The median time on the site is 93 seconds, and of the 150 sessions that could be timed, 82 stayed over a minute. For a three-week-old site that nobody has announced, that means the people who arrive do not bounce. They stay and read.

And what they read is not only the chat. After the home page, the most visited pages are the vaccination schedules, the emergency numbers, the dosing calculator, the guides and the symptom diary. The third and fourth are the legal page and the sources page. That tells me something I did not expect and that I think is the best signal I have: people go and check who is behind it and where the data comes from before they use it. That is exactly the behaviour this site is built for.

The chat, which is one tool out of seven, has answered ten questions from real people, across nine distinct sessions, in English, Spanish and Arabic; two of them came through the Telegram bot. Three of the ten triggered a red flag. I am not hiding that number, but it is not the measure either: most of what this site does is answered without asking anything. Someone who wants to know which vaccines are due at 12 months in Kenya, or the emergency number in Morocco, or what percentile their daughter is on, opens the page and sees it. There is nothing to type.

Where they come from: X, and a couple of places where I have mentioned it. No launch, not one paid advert, and I have not posted it in a single parenting community yet.

In search, the demand is measured and it is the right demand. Over the last 28 days Google has shown the site 1,827 times for queries like "calendario de vacunación infantil", "dosis ibuprofeno niños" and "calculadora apiretal", and given 3 clicks at an average position of 65. So people search for exactly what the site answers, the site already appears, and it appears on page seven because it is three weeks old and almost nobody links to it. That is not fixed with money. It is fixed with time and with somebody citing it.

Revenue: zero today. The path I have in mind is not charging parents, because that would break the only thing that makes the project credible. It is licensing the triage engine, which is deterministic and auditable, to health insurers, hospitals and private practices for first-line patient sorting. The institutions pay so that the side that matters stays free. I have not spoken to any of them yet, because first the triage has to be measured against how a real clinician classifies the same cases, and that is what I am doing next.

On the other side of the ledger: I have spent 0.22 dollars on model calls since August, and the server costs a few euros a month. Everything else is deterministic. The triage is rules, the doses are tables, the percentiles are worked out on the reader's device and the schedules are transcriptions. This does not need funding to keep existing. What it needs is for anyone to know that it is there.

All of this can be checked. The usage figures are published at https://pedibot.xyz/api/stats, and that counter deliberately excludes my own tests.

---

## P6 · Have you raised before? If yes, how much, from who, and on what terms?

*(8.000 caracteres · este texto: 3.119)*

In the normal sense of the question, no: I have never raised money. There are no investors, no previous round, no debt, no side agreements, no options, and nobody holds any rights over the project. I have paid for all of it myself.

But there is something you would find in two minutes, so I will tell you myself, with the numbers in front of me.

In November 2025 I launched a token, $PDBT, on Virtuals, on Base. It was the only place I knew where somebody working alone could try to get some money to keep working on the idea. I got nothing. The token exists, it graduated to Uniswap and it is still there, with about 3,900 holders, a fully diluted valuation of roughly 25,000 dollars and a daily volume in the double digits. What is left of it is speculators.

The allocation is the Virtuals standard, not something I designed: 38.7 per cent in the liquidity pool, 25 per cent as a team allocation on vesting that has not unlocked yet, with the first unlock on 27 October 2026, almost 25 per cent in the protocol's own automated capital formation vault, programmed to sell in tranches between 2 and 160 million of fully diluted valuation, and the rest in ecosystem airdrops. If you look at the concentration you will see ten addresses holding 97 per cent of the supply: nine of those ten are protocol contracts. That is what a Virtuals launch looks like, and that vault has never sold a single token, because its first order sits eighty times above where the token trades.

What is mine, exactly: I put 1,000 dollars of my own money into the initial buy at launch, and that is the only money that has ever moved between that token and me. I have sold part of it trying to get those 1,000 dollars back, and I have not got them back. My wallet holds 0.6 per cent of the supply today. All of it is on chain, and I would rather you saw it from me.

In terms of what that token is and is not: it gives no ownership of the project. It gives no right to revenue. It gives no vote. It buys access to nothing and it never has, which is a red line written into the repository's own rules from the first day, because a health service you can unlock by paying stops being the thing I wanted to build. In September I removed every mention of the token from the site, zero appearances across the whole thing, and left an automated test that fails if one comes back.

The team allocation starts unlocking on 27 October. If that is a problem for what you propose, tell me what you need and I will do it: lock it, burn it, or hand it over. I am not going to defend a position that was created before the product existed.

And what I learned from all that is exactly why I am here in this way. Asking for money before you have something is not fundraising, it is noise, and nothing gets built on top of noise. I did it too early, with the product half made, and it went the way it had to go. Afterwards I went quiet, paid for it myself, and I come to you now with the thing working, eighty-eight countries of data inside it and 8,876 tests holding it up. This time I am not showing you an idea. I am showing you what is already built.

---

## P7 · How much are you looking to raise, and why do you need the capital?

En el campo pequeño de la cantidad va, sin puntos ni comas: 210000

*(8.000 caracteres · este texto: 3.959)*

210,000 dollars, with a monthly budget of about 17,500, and I will not accept more than that even if more is committed. I know your average is well above this. I am asking for what I can spend well in a year and can justify line by line, and I would rather come up short and come back with results than take too much and have to invent something to spend it on.

Where it goes.

Clinical review by paediatricians, 40,000. This is the most important item on the list. Paying practising paediatricians to go through the 83 red flags one by one, to review a sample of the guides, and above all to measure how closely my triage agrees with the classification they would make of the same cases. Today the triage is tested against itself, with 8,876 automated tests, and that proves it does what it says, not that what it says is right. Only a clinician closes that gap.

Native-speaker review of the eight languages, 15,000. Arabic, Hindi and Swahili above all, which are the ones I cannot judge myself. The Swahili bug I described earlier, the one that silenced a warning about a child with blue lips, I found by accident. I do not want to find the next one by accident.

My own time for a year, 90,000. Until now this has been built in the hours I steal from my job, and it has got this far. With a full year it gets to where it should be.

A second person, half time, 40,000. Someone to take on the transcription and verification of schedules and emergency numbers, country by country, which is slow, boring and absolutely critical work: every number copied wrong is a call to a phone that does not exist.

Legal and regulatory work, 15,000. Before the triage engine can be offered to hospitals and insurers, somebody has to settle which category it falls into in the European Union, and draft the contracts and the data processing terms. It is unexciting money and it is what separates an idea about sustainability from an actual source of revenue.

Infrastructure and model calls for a year, 8,000, with room for a hundred times today's traffic. And 2,000 for the e-mail provider, the app stores and loose ends.

Why the capital is needed, precisely: it is not so that this keeps existing. This keeps existing without you. The server is a few euros a month and the entire model bill since August is twenty-two cents, because almost nothing here is generated. If you give me nothing tomorrow, the site stays up and I keep working on it in my spare hours.

The money buys two things that spare hours do not. The first is clinical credibility: that a paediatrician has reviewed every rule, and that there is a published number for how closely the triage agrees with their judgement. Without that, this will always be a well meaning amateur's project, however well it is built. The second is reach: more languages, more countries, the app on Android, and the first pilot with an institution.

And there is a third, which is the one that pays the rest of you back: the clinical review is also the requirement for licensing the engine to insurers and hospitals. Without that work, the only revenue path this project has cannot even be offered. With it, this stops depending on somebody paying for it and can stay free for the people who need it.

What it will not be spent on: not one dollar on advertising, on token incentives, on offices or on growth agencies. If this grows it will be because somebody cites it, not because I bought it.

And what you should hold me to in twelve months, which is how I think this ought to be judged: the triage measured against paediatricians' classifications and the number published, good or bad; the data in all eight languages reviewed by native speakers; the app working on Android; one pilot signed with an institution; and the usage figures still public at the same address where they are today, updated and unpolished. If those five things are not there in a year, I will have failed, and I want that to be easy to check.

---

## Antes de enviar

1. **Releer las cifras**: `uv run python scratchpad/comprueba_cifras_metadao.py` (o pedírmelo).
   Cambian cada semana y el texto las afirma como hechos comprobables.
2. **Nada de formato**: el cuadro es texto plano. Si se pega algo con `-` o `**`, se ve literal.
3. **Las dos decisiones que el operador confirmó**: no se cuenta qué le pasó al niño, y no se
   finge tracción. Las dos suman en esa sala más de lo que restan.
