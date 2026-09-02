# Fuentes alemanas — resultado del rastreo de licencias (3-sep-2026)

> Paso 1 de la fase alemana, mismo método que el francés: cada licencia se leyó en la página
> legal del sitio, no se supuso. El rastreo se hace desde el VPS porque el antivirus local rompe
> el TLS de Python (L65).

## Lo que se verificó

| Fuente | Quién es | Licencia leída | Veredicto |
|---|---|---|---|
| **RKI** (rki.de) | El instituto federal de salud pública; publica la STIKO y los *RKI-Ratgeber*, una ficha por enfermedad | «Soweit eine unveränderte Wiedergabe und korrekte Quellenangabe sichergestellt sind, ist es erlaubt…»; prohibido el uso comercial y la modificación sin permiso | ✅ usable, clase no comercial como la OMS y Canadá |
| **gesund.bund.de** (Ministerio de Sanidad) | Portal federal de salud para ciudadanos | Da permiso expreso de reproducción **como cita**, sin cambios y con la fuente, pero «die Wiedergabe ist auf einzelne Zitate beschränkt» | ⚠️ solo como referencia citable, no para construir corpus |
| **BZgA / kindergesundheit-info.de** | El portal alemán de salud infantil para padres — el equivalente exacto de lo que buscábamos | «Alle Rechte bleiben vorbehalten… Für die Wiedergabe von Text- und Multimedia-Daten ist eine vorherige schriftliche Genehmigung einzuholen» | ❌ cerrada sin permiso escrito |
| **kinderaerzte-im-netz.de** (BVKJ) | El portal de los pediatras alemanes | Todos los derechos de Monks – Ärzte im Netz GmbH; RSS solo para webs no comerciales de suscriptores | ❌ cerrada |
| **AWMF** (awmf.org) | El registro alemán de guías clínicas | «dürfen nicht ohne Genehmigung der AWMF… übernommen» | ❌ cerrada sin permiso |
| **gesundheit.gv.at** (Austria) | El portal público austríaco | «Alle Rechte… vorbehalten» (la única mención de licencia abierta es sobre fotos de stock) | ❌ cerrada |
| **OMS en alemán** | — | **No existe**: `who.int/de` devuelve 404 | ❌ no hay |
| IQWiG (gesundheitsinformation.de) | Instituto de calidad; contenido excelente para pacientes | No se localizó una cláusula de licencia clara en el impressum | ❓ segunda ronda |

## La foto honesta

**El alemán está peor servido que el francés.** En Francia había dos pilares abiertos (OMS en
francés y Canadá en francés); en alemán no hay ninguno de los dos: la OMS no publica en alemán y
no existe un «Canadá alemán». Lo único abierto es el **RKI**, que es excelente pero está escrito
para profesionales y cubre sobre todo enfermedades infecciosas y vacunación — justo donde un
padre alemán más quiere una respuesta local, pero no cubre crianza, alimentación, sueño ni
accidentes.

**Lo que eso significa en la práctica**: las respuestas y las guías en alemán se apoyarán en el
corpus que ya existe (SEUP, AEP, NHS, CDC, MedlinePlus, OMS) traducido al alemán en el momento de
escribir, con el organismo nombrado en cada frase. Eso ya funciona — es exactamente lo que hace
el francés — pero conviene decirlo sin adornos: **una parte del consejo en alemán viene de guías
británicas, españolas y estadounidenses**. La regla nueva del generador (nunca remitir al
servicio sanitario de otro país) evita el error grave; la limitación de fondo sigue ahí.

## Decisión aplicada

Se sigue la **opción A** que el operador eligió para el francés: corpus abierto, sin pedir
permisos. Añadidos **30 RKI-Ratgeber** (sarampión, varicela, tos ferina, escarlatina, VRS, gripe,
noro/rotavirus, boca-mano-pie, meningococo, neumococo, piojos, sarna, salmonela, campylobacter,
EHEC, hepatitis A, Lyme, FSME, conjuntivitis, tuberculosis, COVID, polio, tétanos, difteria,
Hib, toxoplasmosis, CMV). Índice: 258 documentos, 6.294 fragmentos.

**Sin hacer, y es la vía si algún día importa**: escribir a la BZgA. Es el mismo caso que Santé
publique France — PediBot es gratis, sin anuncios y nombra la fuente en cada frase, así que un
permiso no es imposible. No se ha pedido.

## Nota sobre el calendario de vacunación

El **Impfkalender de la STIKO 2026 ya está transcrito y publicado** en `/vaccines/de` desde el
2-sep (se hizo con el francés). Eso es una tabla de datos oficiales citada con su fuente, no una
reproducción de contenido protegido.
