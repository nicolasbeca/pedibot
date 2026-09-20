# Emergent Ventures — el borrador, listo para pegar

> 21-sep-2026. La vía número 3 de `ops/FINANCIACION.md`, y la primera que cuesta cero y tiene a
> alguien leyendo: **Tyler Cowen lee personalmente todas las solicitudes**. De 1.000 a 50.000 $,
> sin participación, sin coste, y el formulario tiene un desplegable de región con **India,
> África, el Caribe y Ucrania**, que es literalmente donde está este proyecto.
>
> El formulario no publica sus preguntas, así que esto está escrito como el texto libre que
> siempre piden: quién eres, qué has hecho, qué harías con el dinero. Si el formulario pide algo
> más corto, se recorta desde abajo: los tres primeros párrafos aguantan solos.
>
> **Una cosa importante y es la razón de que no diga «triaje» en ningún sitio**: en Europa esa
> palabra tiene consecuencias regulatorias (L209). Aquí se dice lo que el sitio hace, que además
> es más concreto y se entiende mejor.
>
> Región del desplegable: **India** o **África**. Yo pondría África, porque es donde las cifras
> son más fuertes (los 54 países) y donde menos competencia de solicitudes hay.

---

## El texto, en inglés

I built and run [pedibot.xyz](https://pedibot.xyz), a free site that answers a parent's questions
about their sick child in eight languages, always with the guideline it came from shown next to
the answer. No account, no ads, no payment, nothing to install. I am one person, in Spain, and I
have paid for all of it myself.

The specific thing it does that general-purpose chatbots do not: **it knows where the child is.**
A parent in Lagos and a parent in Madrid asking the same question get the same medicine but a
different bottle, a different emergency number, and a different vaccine schedule, because those
things genuinely differ. Today it carries the emergency number for 90 countries, 66 national
vaccine schedules, 69 country growth charts, 83 red-flag rules and 507 guides, all cited. The
catalogue of 497 source documents behind it is published under CC0 and can be downloaded whole.
For Africa that means all 54 countries have their emergency number and their vaccine schedule,
49 have their growth charts, and 31 have the paracetamol and ibuprofen brands that are actually
sold there, at the concentration printed on that country's bottle, so a parent can recognise the
bottle in their hand rather than read a dose for a product they cannot buy.

It is built for the phone that a parent in Kano or Patna actually owns. The whole thing is a
static site of about five megabytes that keeps working with no signal after the first visit, and
the parts that matter most in an emergency — the warning signs, the dose, the arm tape for
malnutrition, the emergency number — are computed on the device without a round trip to a server
or a language model.

What it does **not** do is diagnose, and I am careful about this. It explains what a warning sign
means, what the guideline says, and when a child needs to be seen today rather than tomorrow, and
it shows the source so a parent can take it to a clinic and point at it.

**What the money would buy.** The single thing that separates this from being trustworthy is a
number I do not have: how its answers compare with what practising paediatricians would say about
the same cases. I want to hire a panel of paediatricians to grade a few hundred real questions
blind, publish the agreement rate whatever it turns out to be, and fix what the disagreements
expose. I would also pay native Arabic and Hindi speakers to review the safety-critical text,
which today is the weakest part of the project and the part where a translation error is most
expensive. That is roughly $25,000: about $18,000 for the clinical review, $5,000 for the
language review, and the rest for a year of hosting and the medical literature I have to buy.

**About me, and one thing I would rather you heard from me.** I am not a doctor and not a
funded founder. I have built this in evenings over the last year because the version of it I
wanted for my own use did not exist. In November 2025 I launched a token for the project on a
crypto platform, before there was a product worth funding. It raised nothing and I retired it;
it takes two minutes to find, so I would rather tell you first. What I learned from it is the
reason the site is now free, has no token in it anywhere, and is built so that the money, if it
ever arrives, comes from institutions and not from the parent.

---

## Notas para ti, no para ellos

- **La cifra de 25.000 $ es la que yo defendería**, y está pensada para que cada dólar tenga un
  entregable. Es alta para su mediana pero muy por debajo de su techo de 50.000, y lo que pides
  es exactamente lo que ellos llaman «de cero a uno»: un número que hoy no existe en ningún sitio.
- **Lo del token va dentro a propósito.** Se encuentra en dos minutos y encontrarlo por su cuenta
  vale mucho más que leerlo de ti. Contado así deja de ser un riesgo y pasa a ser la explicación
  de por qué el proyecto está construido como está.
- **No pone «motor de triaje» en ninguna parte** y no es por suavizarlo: es por L209. La frase
  «explica qué significa un signo de alarma y cuándo hay que ir hoy» describe lo mismo, se
  entiende mejor y no te mete en la clase IIa europea.
- **Las cifras salen de `DATOS.md`**, contadas el 20-sep-2026. Si pasan semanas antes de que lo
  mandes, regenera (`uv run python scripts/build_datos.py`) y cámbialas; son las únicas de este
  texto que envejecen.
- **Avisan de que no dan respuesta individual ni estado de la solicitud**, y de que sólo se puede
  mandar una por persona y proyecto. O sea que esto se manda una vez y bien.
