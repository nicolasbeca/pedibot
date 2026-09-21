# Permisos por escribir — dos puertas cerradas que un correo puede abrir (18-sep-2026)

> Puestos al día el 21-sep-2026: las cifras de entonces se habían quedado viejas (496
> documentos, 48 países africanos) y ahora los firma él con su nombre, que desde MetaDAO ya no
> es un problema y en una petición de permiso da más confianza que una marca.

Los dos rastreos de licencias que acabaron en «hay material bueno y está cerrado» terminan en lo
mismo: un correo. Están redactados abajo, listos para copiar y enviar. **Los manda el operador**,
no el proyecto: nada sale hacia fuera sin su visto bueno.

Qué se pide en los dos casos, y qué NO:

- Se pide **incluir el material en el corpus indexado** y citarlo con su nombre y su enlace, sin
  modificarlo, sin uso comercial. Es exactamente lo que ya se hace con el NHS (OGL), la OMS
  (CC BY-NC-SA) y los CDC (dominio público).
- **No** se pide exclusividad, ni ceder derechos, ni reproducir el PDF entero en la web. Si
  prefieren que sólo enlacemos, eso también vale y se dice en el correo.

---

## 1. Immunize.org — las 36 hojas de vacunas en suajili

**A:** `admin@immunize.org` (de su página de contacto, 18-sep-2026)
**Asunto:** Permission request: Swahili VIS translations for a free paediatric information service

> Dear Immunize.org team,
>
> I write on behalf of PediBot (https://pedibot.xyz), a free, non-commercial information service
> for parents of young children. It answers questions in eight languages using a corpus of 497
> documents — the NHS, the CDC, MedlinePlus, the WHO and several national paediatric societies —
> and every answer cites the document it came from, with a link, so a parent can check it. The
> licence of every source is recorded in the catalogue before it is indexed; nothing goes in
> without one.
>
> We have just extended the service to Africa: all 54 African countries now have their childhood
> vaccination schedule and their emergency number on the site, 52 have their growth charts, and
> the safety layer — the part that tells a parent when to go to hospital now — understands Swahili.
> Since this week the service also answers in the language the parent writes in, Swahili included,
> but the sources behind those answers are still in English and Spanish.
>
> What we could not find is a paediatric corpus in Swahili with an open licence. We checked
> MedlinePlus, the WHO, WHO AFRO, Hesperian and others. The best Swahili material for parents
> that exists is yours: the 36 translated Vaccine Information Statements listed on MedlinePlus.
>
> We would like to ask your permission to include those Swahili translations (and, if you are
> willing, your translations in other languages) in our indexed corpus, under these conditions:
>
> · the text is never altered, and never presented as ours;
> · every passage we quote is attributed as "Immunize.org — translation of the CDC Vaccine
>   Information Statement", with a link to your PDF;
> · no commercial use: the service is free, has no advertising and sells nothing;
> · if you prefer, we can link to your PDFs instead of indexing their text, and we will do that
>   rather than nothing.
>
> We are aware that the underlying VIS are public-domain CDC documents and that the translation
> work is yours. That work is the reason we are writing: for a parent in Kisumu or Dar es Salaam,
> a vaccine sheet in Swahili is the difference between an answer and a shrug.
>
> Happy to sign whatever attribution or usage terms you need, and to show you the site and the
> source catalogue first.
>
> With thanks for the work you do,
>
> Nicolás Beca
> PediBot · https://pedibot.xyz · pedibot.ai@gmail.com

**Si contestan que sí:** el material entra por `scripts/fetch_web_sources.py` como cualquier otra
fuente, con `notes: "licence: permission granted by Immunize.org, <fecha>"`, y el suajili pasa de
lengua de triaje a lengua completa (`SUPPORTED_LANGS` en `src/pedibot/bot/answer.py`, ver L183).

---

## 2. Vikaspedia (C-DAC) — el hindi

Pendiente desde el 11-sep. Su política exige permiso por correo. El 11-sep su página de
contacto era sólo un formulario; **el 21-sep ya publica dirección: `vikaspedia@cdac.in`**
(escrita como «vikaspedia[at]cdac[dot]in»). Va por correo, que admite el texto entero —el
formulario corta a 300 caracteres— y deja copia. No por las dos vías a la vez.

**Asunto:** Permission request: Vikaspedia health content for a free paediatric information service

> Dear Vikaspedia team,
>
> I write on behalf of PediBot (https://pedibot.xyz), a free, non-commercial information service
> for parents of young children, available in eight languages including Hindi. Every answer cites
> the document it came from, with a link, and the licence of every source is recorded before it
> is indexed.
>
> Hindi is one of our languages and it is the one worst served by our corpus. The National Health
> Mission's own copyright policy allows reuse with prominent attribution, and we follow it, but
> its parent-facing material in Hindi is published as PDFs whose text layer does not survive
> extraction: of four documents we tested, the best one corrupted words. We do not use OCR for
> health content — a misread digit in a dose is exactly the error this project exists to avoid.
>
> Vikaspedia has what we need: parent-facing health content, written in Hindi, in HTML, with
> correct Unicode. Your terms require written permission, so we are asking for it rather than
> assuming.
>
> We would use it under these conditions:
>
> · the text is never altered, and never presented as ours;
> · every passage is attributed to Vikaspedia (C-DAC) with a link to the original page;
> · no commercial use: the service is free, has no advertising and sells nothing;
> · we remove anything you ask us to remove, at any time.
>
> Happy to show you the site and the full source catalogue first, and to accept any attribution
> wording you prefer.
>
> With thanks,
>
> Nicolás Beca
> PediBot · https://pedibot.xyz · pedibot.ai@gmail.com

**Si contestan que sí:** mismo camino, y además se puede cerrar la deuda de que el hindi es la
única de las ocho lenguas sin documentos propios (L154).

---

## Dónde queda apuntado

- El rastreo del suajili, con las siete licencias leídas: `FUENTES/SUAJILI.md`.
- El de la India, con la cita literal de la política del ministerio: `FUENTES/INDIA.md`.
- La decisión de partir el suajili en lengua de aviso y lengua de respuesta: `LESSONS.md`, L183.
