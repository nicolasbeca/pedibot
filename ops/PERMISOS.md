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

## Concedidos — las condiciones que nos han puesto, al pie de la letra

Lo que una fuente nos pide al dar permiso no se cumple de memoria: está aquí, citado del correo,
y cada condición dice dónde se cumple en el código. Si se toca ese sitio, se relee esto.

### BIÖG (kindergesundheit-info.de) — 8-oct-2026

Claudia Thienel (`su dirección, en el hilo «Kooperation»`, «i.A.», Ref. Q5 – Kinder und Heranwachsende; contesta
por encargo del Bundesinstitut für Öffentliche Gesundheit), hilo «Kooperation», respuesta a la
petición del 5-oct a poststelle@bioeg.de. Condiciones, citadas:

- «Gerne dürfen Sie unsere Seite https://www.kindergesundheit-info.de/ als Quelle nutzen.»
- «Sobald Sie die Texte unserer Seite jedoch in irgendeiner Weise bearbeiten/stark kürzen,
  bitten wir Sie, uns vorab ein Beispiel zukommen zu lassen.» → **antes de indexar, mandarles un
  ejemplo de respuesta resumida y esperar su visto bueno.**
- «…dass unsere Seite sowie unsere Inhalte absolut werbefrei sind und bleiben.» → PediBot no
  lleva publicidad; si eso cambiara algún día, sus páginas salen del índice.

**Estado:** nada suyo en el índice todavía; falta el ejemplo.

### Immunize.org — 30-sep-2026

Kayla Ohlde, Operations Administrator (`admin@immunize.org`, kayla.ohlde@immunize.org), en el
hilo «Permission request: Swahili VIS translations…». Agradecido el 1-oct.

> Our printable immunization materials at https://www.immunize.org/clinical/a-z/ are
> copyright-free and we encourage people to use them. If you change a piece, please provide an
> adapted credit on the document consistent with our guidelines on our web page "Citing
> Immunize.org," located at https://www.immunize.org/content-review/.
>
> Please do not co-brand your organization's name on our educational piece without our express
> permission to do so in writing. […]
>
> As we update our materials frequently, it is best always to check the website to make sure you
> have the most recent version of a piece.
>
> Please credit/attribute it to us and include a link to our website to the full PDF document.

Vale para todas sus traducciones de las VIS, no sólo el suajili (el permiso es de «our printable
immunization materials»). Condiciones:

1. **Atribuir a Immunize.org y enlazar el PDF completo.** En `config/fuentes.yaml` las 40 hojas
   (árabe, hindi y suajili) llevan `org: Immunize.org` —hasta el 1-oct decían «CDC», que
   incumplía esto— y como `url` el PDF de `immunize.org/wp-content/uploads/vis/…`. Además, el
   encabezado «Immunize.org» de /sources enlaza a https://www.immunize.org/
   (`web/site/src/components/SourcesTable.astro`, `ORG_HOME`).
2. **No modificar las hojas; si algún día se adapta una, crédito «adaptado de»** según
   https://www.immunize.org/content-review/. Hoy no se adapta ninguna: se indexa el texto tal cual.
   Al pasar a `publico`, las guías de la web pueden apoyarse en ellas citándolas con su enlace,
   como en cualquier fuente; eso es citar, no publicar una versión cambiada de su hoja. Si algún
   día se maquetara una hoja suya, aplica el crédito «adaptado de».
3. **No poner la marca PediBot sobre sus hojas** sin permiso escrito. No se republican sus PDF
   con nuestro logo; se citan y se enlazan.
4. **Versión más reciente.** Las actualizan a menudo: al volver a bajar las fuentes, se bajan de
   su web, nunca de una copia guardada; `notes` del catálogo lleva la fecha del permiso.
   Comprobado el 1-oct: el texto de las 19 que ya teníamos es idéntico al que publican hoy (los
   bytes cambian en cada descarga; el texto no). Repetir la comprobación cada pocos meses.

### Vikaspedia (C-DAC) — 1-oct-2026

Equipo de Vikaspedia (`vikaspedia@cdac.in`, con copia a vijayab@cdac.in), en el hilo «Permission
request: Vikaspedia health content…». Agradecido el 1-oct; en el agradecimiento nos comprometimos
a las tres cosas y, además, a enlazar Vikaspedia desde la página de fuentes.

> We would be happy to permit the non-commercial use of the health content with proper citation
> of the source of the content contirbutor and the Vikaspedia page link. It would be preferred if
> you can also provide a backlink to Vikaspedia at appropriate places. It is also best to include
> a disclaimer that the information provided is for informational purposes only and does not
> substitute for professional medical advice, diagnosis or treatment.

Condiciones:

1. **Uso no comercial.** PediBot es gratis, sin anuncios y no vende nada. Si eso cambiara, este
   permiso no cubre el contenido de Vikaspedia.
2. **Citar al autor del contenido («content contributor») y enlazar la página de Vikaspedia.**
   Cada página firma al pie quién la aporta («स्रोत: स्वास्थ्य विभाग, झारखण्ड सरकार»). Ese
   nombre va en el TÍTULO del documento —«… — स्रोत: <quién>»—, porque el título acompaña a la
   cita en el chat, en /sources y en el catálogo descargable; `org` es «Vikaspedia» y la `url`
   es la de la página concreta. Lo hace `vikaspedia_page` en `scripts/fetch_web_sources.py`
   (`tests/test_vikaspedia_cites_its_contributor.py`). Sin firma al pie, «स्रोत: Vikaspedia».
3. **Enlace a Vikaspedia «en los sitios apropiados»** (lo prefieren, no lo exigen; en el
   agradecimiento nos comprometimos a la página de fuentes): el encabezado de Vikaspedia en
   /sources, en las ocho lenguas, enlaza https://vikaspedia.in/ (`SourcesTable.astro`,
   `ORG_HOME`; `tests/test_sources_page_links_who_asked.py`).
4. **Aviso de que la información no sustituye al consejo médico.** Está en el pie de todas las
   páginas (`footer_legal`) y en la línea legal bajo el chat (`legal_line`, en `i18n.ts`); NO
   en cada mensaje, por decisión del 25-ago. No se quita mientras haya contenido de
   Vikaspedia.

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
