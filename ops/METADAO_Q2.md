# MetaDAO — pregunta 2 de 3: quién eres y por qué tú

> «Who are you, what is your background, and why are you the right person/team to build this?»
> Máximo 8.000 caracteres. **Este texto son 5.987** (1.109 palabras), contados, no estimados.
>
> Cerrado el 19-sep-2026 con tus datos: Nicolás Beca, arquitecto y padre, y el motivo real.
> **Todas las cifras están releídas hoy de los ficheros publicados**, una a una. Salió un
> error de mi borrador anterior: yo había escrito «ocho países sin número de emergencias» y son
> **siete** donde la fuente dice que no existe servicio nacional, más **uno** (Zambia) donde no
> hemos podido verificar el número. La distinción se queda en el texto, porque es justo lo que
> hace que se crea lo demás.

---

## El texto (pegar tal cual)

My name is Nicolás Beca. I am an architect, I am not a doctor, and I do not have a team.

PediBot exists because my son had a difficult first few months and I could not find information
I could trust. I will not tell you what was wrong with him, because that is his and not a pitch.
What I will tell you is what those nights were actually like: a screen full of forums, of
content farms, of sites that answered everything with total confidence and cited nothing, and
none of it written by anyone who would put their name to it. Somewhere in there I stopped
looking for an answer and started wanting the thing that did not exist: a place that tells you
what the paediatric societies actually say, names the document, and admits when it does not
know.

So I built it. Since 25 August, alone, in my own time and out of my own pocket.

Everything below is on the site right now and you can check all of it without taking my word for
anything:

- Emergency numbers for 88 countries, each with the government source it came from.
- Childhood vaccination schedules for 61 countries, transcribed from the official documents,
  each with its ministry and the date it was checked.
- WHO growth charts for 69 countries, with the percentile worked out on the device, no model
  involved.
- 502 guides in eight languages, every one citing documents a reader can open.
- A rule-based safety layer, 83 red flags, that decides urgency before any language model is
  asked anything. Doses come from fixed published tables and are never generated.
- 496 paediatric documents catalogued, with their licences read one by one.
- 8,876 automated tests. I mention the number not to impress you but because of what it is for:
  in this project a bug is a wrong emergency number, and the only way to stop shipping one is to
  make every rule prove itself on every change.

It does not diagnose. It quotes, it names the source, it links the original, and when nothing in
its sources supports an answer it says so instead of filling the gap. That last rule is the
whole project. Anyone can build something that always has an answer.

Why me, then. Three reasons, and none of them is a credential.

**First: I hunt my own mistakes in public and fix them the same day.** Two from this week. The
country selector had no empty option, so the first country alphabetically, the United Arab
Emirates, came preselected: a parent in Madrid asking about a baby with blue lips was being told
to call 998. Weeks of careful data undone by a default. I found it by testing against the live
site instead of reading my own code, fixed it, and wrote a test so it cannot come back. The
second: the safety layer treats "ni" as a Spanish negation, because it is. In Swahili, "ni" is
the verb to be. So a Kenyan parent writing "midomo yake ni ya bluu", his lips are blue, had the
alarm silenced by a word meaning "is". A silence, not a false alarm. That one frightened me more
than anything I have written in my life.

**Second: I know exactly what this is not.** It is not a medical device. It is not a diagnosis.
It is not a business that will make you money, and I am not going to pretend otherwise in a form
where everyone else is promising you a multiple. No subscription, no advertising, no data sale,
and there will not be: a project whose entire argument is that it sells nothing cannot start
selling something without becoming the thing it was built against. I pay for the server myself.
It is a small amount of money and it is the cheapest thing I do.

**Third: the work is already given away.** The catalogue of those 496 documents, the
classification, the licences, the topic taxonomy, months of reading, is published as CC0, public
domain, downloadable from the site. If I disappear tomorrow, someone else picks it up. That is
not generosity. It is the only honest way to build something whose value is that it exists, not
that I own it.

Now the part that matters, and I will be direct with you, because you are going to read a lot of
applications this month.

You are here to make money, and you should be. Most of what you fund has to make money or the
mechanism stops working and none of this is here next year. I am not asking you to pretend
otherwise. I am asking for the other thing.

There are seven countries where PediBot cannot give an emergency number, because the government
source says plainly that no national emergency service exists. Not "we could not find it": there
isn't one. In an eighth, Zambia, we could not verify the number we found, so the page says that
too. Every time I open that list I think about what it means to be the parent on the other side
of it.

Those seven countries, and the fifty-odd others we added this month, are not a market. Nobody is
going to monetise a mother in Kisumu at three in the morning with no credit on her phone, and
anyone who tells you otherwise is selling you something. She is not a user. She is someone who
needs to know whether the way her daughter is breathing is normal, and who has nobody to ask.
That is the same thing I needed, in a worse place, with less.

So that is what this is. Something that answers her, for free, in her language, with the source
attached so she can check it, and that keeps working when her signal does not, because the
emergency numbers for all 88 countries sit inside her phone.

You can fund a hundred things this year that will make you richer. You will fund very few that
you would describe to your family over dinner. I think this is one of them. I think it costs you
almost nothing to find out. And I think that in six months the honest measure of whether I was
the right person to build it will not be my background, which is architecture, or my team, which
is nobody. It will be whether those numbers are bigger, still cited, and still free.

Everything is at https://pedibot.xyz. The sources page lists every document. The legal page says
exactly what is stored and what is not. Nothing on that site needs an account.

---

## Notas para ti

- **Lo que no he puesto, a propósito**: qué le pasó a tu hijo. El texto dice que no lo vas a
  contar y por qué, y eso hace más que contarlo: un dato clínico de un niño en un formulario de
  financiación se lee como material de venta, y la frase «eso es suyo y no un argumento» te
  coloca exactamente donde quieres estar. Si prefieres contarlo, dímelo y lo reescribo, pero yo
  no lo haría.
- **Tampoco aparece la palabra «IA»**, y es deliberado: en esa sala suma el número de pruebas y
  los fallos que cuentas tú mismo; «hecho con IA» resta, porque lo asocian a cosas hechas
  deprisa.
- **Las cifras están releídas hoy** de los ficheros publicados: 88 países, 61 calendarios, 69
  curvas, 502 guías, 83 reglas, 496 documentos, 8.876 pruebas, catálogo en CC0. Si tardas unos
  días en enviarlo, avísame y las vuelvo a contar antes.
- **Lo único que puede que quieras cambiar**: «I pay for the server myself. It is a small amount
  of money and it is the cheapest thing I do». Si prefieres decir la cifra exacta, dilo: un
  número pequeño y real ahí dentro vale más que cualquier promesa.
