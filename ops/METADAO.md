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
> Estado: **las tres aprobadas por el operador.** Listas para pegar.
>
> Un arreglo del 19-sep que vale para las tres: «las tres de la mañana» aparecía cuatro
> veces —lo vio él— y una imagen repetida deja de ser una imagen. Queda **una sola vez**, en
> el cierre de P2, que es donde remata.

---

## P1 · Who are you, what is your background, and why are you the right person/team to build this?

*(8.000 caracteres · este texto: 5.509)*

My name is Nicolás Beca. I am an architect, I am not a doctor, and I do not have a team.

PediBot exists because my son had a difficult first few months and I could not find information I could trust. I will not tell you what was wrong with him, because that is his and not a pitch. What I will tell you is what those nights were actually like: a screen full of forums, of content farms, of sites that answered everything with total confidence and cited nothing, and none of it written by anyone who would put their name to it. Somewhere in there I stopped looking for an answer and started wanting the thing that did not exist: a place that tells you what the paediatric societies actually say, names the document, and admits when it does not know.

So I started building it, in January of this year, alone, in my own time and out of my own pocket. The site you can open today has been live since the end of August.

Since then: emergency numbers for 88 countries, vaccination schedules for 61, WHO growth charts for 69, 502 guides in eight languages, 496 paediatric documents catalogued with their licences read one by one, and 8,876 automated tests. I describe all of it in the next answer. I mention the test count here for one reason: in this project a bug is a wrong emergency number, and the only way to stop shipping one is to make every rule prove itself on every change.

It does not diagnose. It quotes, it names the source, it links the original, and when nothing in its sources supports an answer it says so instead of filling the gap. That last rule is the whole project. Anyone can build something that always has an answer.

Why me, then. Three reasons, and none of them is a credential.

First, I hunt my own mistakes in public and fix them the same day. Two from this week. The country selector had no empty option, so the first country alphabetically, the United Arab Emirates, came preselected: a parent in Madrid asking about a baby with blue lips was being told to call 998. Weeks of careful data undone by a default. I found it by testing against the live site instead of reading my own code, fixed it, and wrote a test so it cannot come back. The second: the safety layer treats "ni" as a Spanish negation, because it is. In Swahili, "ni" is the verb to be. So a Kenyan parent writing "midomo yake ni ya bluu", his lips are blue, had the alarm silenced by a word meaning "is". A silence, not a false alarm. That one frightened me more than anything I have written in my life.

Second, I know exactly what this is not. It is not a medical device. It is not a diagnosis. It is not a business that will make you money, and I am not going to pretend otherwise in a form where everyone else is promising you a multiple. No subscription, no advertising, no data sale, and there will not be: a project whose entire argument is that it sells nothing cannot start selling something without becoming the thing it was built against. I pay for the server myself. It is a small amount of money and it is the cheapest thing I do.

Third, the work is already given away. The catalogue of those 496 documents, the classification, the licences, the topic taxonomy, months of reading, is published as CC0, public domain, downloadable from the site. If I disappear tomorrow, someone else picks it up. That is not generosity. It is the only honest way to build something whose value is that it exists, not that I own it.

Now the part that matters, and I will be direct with you, because you are going to read a lot of applications this month.

You are here to make money, and you should be. Most of what you fund has to make money or the mechanism stops working and none of this is here next year. I am not asking you to pretend otherwise. I am asking for the other thing.

There are seven countries where PediBot cannot give an emergency number, because the government source says plainly that no national emergency service exists. Not "we could not find it": there isn't one. In an eighth, Zambia, we could not verify the number we found, so the page says that too. Every time I open that list I think about what it means to be the parent on the other side of it.

Those seven countries, and the fifty-odd others we added this month, are not a market. Nobody is going to monetise a mother in Kisumu with no credit left on her phone, and anyone who tells you otherwise is selling you something. She is not a user. She is someone who needs to know whether the way her daughter is breathing is normal, and who has nobody to ask. That is the same thing I needed, in a worse place, with less.

So that is what this is. Something that answers her, for free, in her language, with the source attached so she can check it, and that keeps working when her signal does not, because the emergency numbers for all 88 countries sit inside her phone.

You can fund a hundred things this year that will make you richer. You will fund very few that you would describe to your family over dinner. I think this is one of them. I think it costs you almost nothing to find out. And I think that in six months the honest measure of whether I was the right person to build it will not be my background, which is architecture, or my team, which is nobody. It will be whether those numbers are bigger, still cited, and still free.

Everything is at https://pedibot.xyz. The sources page lists every document. The legal page says exactly what is stored and what is not. Nothing on that site needs an account.

---

## P2 · What are you building, and who is it for?

*(8.000 caracteres · este texto: 5.070)*

PediBot is a free site that answers parents' questions about a sick child using only what paediatric societies, health ministries and the WHO already publish for families, and that shows where every answer comes from. It does not diagnose. It quotes, it names the document, it links the original, and it says when it does not know.

At the centre is a chat that answers in eight languages, with each claim followed by the organisation, the document and a link the reader can open. Behind it sit 496 catalogued paediatric documents, each with its licence read one by one. But the part that matters is what happens before the model is asked anything: a layer of fixed rules, 83 red flags, decides urgency first. If what the parent describes matches one, the first thing they see is the warning and their country's emergency number, not a paragraph. And drug doses never come from a model at all. They are looked up in published tables, by weight, with the brands actually sold in each country.

Around that there is a set of tools that are just data, carefully transcribed and always attributed. Emergency numbers for 88 countries, each with its government source; in seven of them the source says plainly that no national emergency service exists, and the page says so in those words instead of inventing a number. Childhood vaccination schedules for 61 countries, transcribed from the official documents, with the ministry that issues each one and the date it was checked. WHO growth charts for 69 countries, with the percentile worked out on the device. A dosing calculator for paracetamol and ibuprofen. And 502 guides in eight languages, every one citing documents a reader can open.

Since this week there is also an optional account. You save each child's date of birth, and then you ask "what vaccines are due for Laura?" and it answers for Laura's age. You can record her weight and height and see her own curve on the WHO bands, and send her next appointments to your phone's calendar. The account is optional, nothing else on the site needs one, and you can download everything or delete it from a button.

And all of it except the chat works with no signal. The emergency numbers for all 88 countries, the red flags, the schedules and the growth tables sit inside the phone. With no connection it still opens and tells you what it knows. Only the chat needs the network, because a model writes it.

Who is it for. First, the parent who in the middle of the night has nobody to ask. That happens everywhere, including in rich countries: the paediatrician does not answer the phone at night and the hospital is half an hour away.

But mostly it is for the places where there is no paediatrician to call at night, or at eleven in the morning either. That is why the eight languages are not English and Spanish with decoration: there is Arabic, Hindi, Russian and Portuguese, and the safety layer also reads Swahili. That is why 48 African countries have their emergency number and their schedule in it. And that is why each page weighs under twenty kilobytes and the data lives inside the phone: because the mother this is actually for runs out of credit halfway through the month.

It is also for families living where nobody speaks their language. A Moroccan family in Madrid needs the Spanish number and the explanation in Arabic, and that is written into the code: the country shown first is the reader's, not the language's.

And there is a second audience you will care about more. Millions of parents are already asking a language model whether their child needs a hospital, and that model answers with whatever it has. If it is going to answer anyway, let it cite something real. That is why the catalogue of 496 documents is published as CC0, public domain, downloadable from the site; why there is a machine-readable map of the project written for those assistants; and why PediBot offers its tools as an agent on an agent marketplace. Anyone can take all of that and build on it without asking me.

Who it is not for. It is not for someone looking for a diagnosis, because it does not give one. It is not a clinical tool and it is not aimed at professionals. It does not replace a paediatrician or an emergency department, and it says so on every page and in every answer. If your health service says something different, your health service is right.

Where this actually stands today, with no dressing up. I finished this week's work this week, and I have announced it nowhere. In the last seven days two real people used it. I am not going to sell you traction that does not exist. What exists is the thing itself, built and running, held up by 8,876 tests, and eighty-eight countries' worth of data that nobody had gathered in one free place in eight languages. What is missing is for anyone to know it is there.

And when they do, this is who is on the other side: a mother in Kisumu at three in the morning, with no credit on her phone, watching how her daughter is breathing and with nobody to ask. That is not a market. That is the person it is built for.

---

## P3 · Who are your main competitors. and why do you beat them?

*(8.000 caracteres · este texto: 5.498)*

My real competitors are not other apps. There are three of them, and two I am not going to beat.

The first and biggest is Google at four in the morning. That is where a frightened parent goes, and what they find is forums, sites built to place advertising, and pages that answer everything with total confidence and cite nothing. That is the real competitor, it is free, and right now it is winning. I do not beat it by being cleverer. I beat it on the only thing that matters at that hour: every sentence in my answer carries the body that says it, the document, and a link to check it. A parent who has already read four contradictory things does not need a fifth opinion. They need to see who signs it.

The second is ChatGPT and the other assistants, and that is the serious one. Millions of parents already ask them whether their child needs a hospital, and they often answer well. Where they fail is where it hurts most: they do not cite a source, so nothing can be checked; they do not know the emergency number for the country the parent is in, or the vaccination schedule that applies to that child, because none of that lives in a model, it lives in a ministry's PDF; and above all they always have an answer. A model does not know how to stay quiet. PediBot does: when nothing in its sources supports an answer, it says so instead of filling the gap.

There is also a difference that is not about quality but about architecture. In PediBot the urgency is not decided by the model. It is decided by a layer of 83 fixed rules that runs first, and drug doses are never generated: they are looked up in published tables, by weight, with the brands sold in each country. A general assistant cannot promise that, because its answer is always a generation.

But I am not kidding myself: I do not beat the assistants, I complement them. That is why the catalogue of 496 documents is public domain and downloadable, and why there is a machine-readable map of the project written for them. If ChatGPT answers these questions tomorrow citing my sources, I have won. The goal is not that people come to my site. The goal is that a parent does not get an invented answer.

The third group is the health services and the paediatric societies: the NHS, the CDC, the Spanish Paediatric Association, the ministries. They are better than me at what they do and I will not pretend otherwise. They are the source, and in fact they are my sources. Where they fall short is in form. Each covers one country and one or two languages, their material is scattered across dozens of PDFs, and nobody navigates an institutional site at night looking for the bronchiolitis leaflet. What I do is gather 88 countries in eight languages, read them, transcribe them with their source and their date, and answer in the language of the person asking. Nobody was doing that for free.

Then there are the symptom checkers, such as Ada, K Health, Infermedica or Mediktor. They are serious and some of them are good, but they play a different game: they give a diagnostic orientation, they ask for an account, and they have to monetise, through subscriptions, insurers, or licensing the technology. I do not give a diagnosis and I have nothing to monetise, which removes the conflict of interest they carry. It is also worth looking at how Babylon Health ended, after raising hundreds of millions: in this field it is usually the business model that kills the product, not the medicine.

And the baby tracking apps, the ones with the growth curves and the feeds, used by millions of parents. Those I do watch closely, because I have just built the same thing. They do one thing well: recording. What they do not do is answer. You note the weight and you get a dot on a curve, but when at night you type "his ribs are pulling in when he breathes", there is nobody on the other side. PediBot does both: your child's curve on the WHO bands, and an answer with its source when you need one. And with no advertising inside, which is the first thing you see when you open any of them.

There are two more things none of the above has. It works with no signal: the emergency numbers for all 88 countries, the red flags, the schedules and the growth tables sit inside the phone, and with no connection it still opens. And it asks for no account, charges nothing, carries no advertising and sells no data, and it never will, because a project whose entire argument is that it sells nothing cannot start selling something without becoming the thing it was built against.

Where I lose, which is worth saying too. I lose on conversational speed against a general model. I lose on brand: nobody knows me, I am not in the app stores, and I have been findable for three weeks. I lose to the NHS on authority about England, and I lose to a real paediatrician every single time, which is what the site repeats on every page. And my answer is never better than the documents I hold: where there is no openly licensed paediatric source, and in Swahili there is none, I say so and answer in English.

So the honest answer to "why do you beat them" is that I do not beat most of them, and the ones that matter I do not want to beat: I want them to use my catalogue. The one I do beat, because it is the one answering those parents today and should not be, is the sourceless forum and the page built to place advertising. That is the competitor. Bringing a single parent back to what their own health service actually says already justifies this.

---

## Antes de enviar

1. **Releer las cifras**: `uv run python scratchpad/comprueba_cifras_metadao.py` (o pedírmelo).
   Cambian cada semana y el texto las afirma como hechos comprobables.
2. **Nada de formato**: el cuadro es texto plano. Si se pega algo con `-` o `**`, se ve literal.
3. **Las dos decisiones que el operador confirmó**: no se cuenta qué le pasó al niño, y no se
   finge tracción. Las dos suman en esa sala más de lo que restan.
