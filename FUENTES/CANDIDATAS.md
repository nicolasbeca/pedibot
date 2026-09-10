# Webs candidatas para indexar — rastreo de licencias (10-sep-2026)

> Misma criba que en agosto dejó entrar al NHS (OGL), MedlinePlus/CDC (dominio público) y la OMS
> (CC BY-NC-SA), y que en septiembre descartó a Santé publique France y ameli. **Cada licencia se
> leyó en la página del propio sitio**, no se supuso. Lo que no se pudo leer se marca como
> pendiente, no se estima.

## El agujero, medido

Índice actual: **288 documentos, 6.548 pasajes**. Por idioma:

| Idioma | Documentos | Pasajes | De quién |
|---|---|---|---|
| en | 141 | 1.798 | NHS, OMS, AAP, MedlinePlus, CDC, College of the Canyons |
| es | 70 | 3.707 | Ecimed, PUC Chile, Junta de Andalucía, SEUP, AEPap, AEP… |
| de | 30 | 657 | **RKI y nadie más** |
| fr | 17 | 132 | OMS-FR, Canada.ca |
| ar | 15 | 126 | **solo OMS** |
| ru | 15 | 128 | **solo OMS** |
| **pt** | **0** | **0** | — |
| **hi** | **0** | **0** | — |

El bot responde en ocho idiomas (`SUPPORTED_LANGS`) y **dos no tienen ni un documento**. Un padre
en São Paulo o en Delhi recibe hoy una respuesta construida entera con pasajes en inglés y
castellano, traducida al redactar.

Y el atajo que resolvió el ruso, el árabe y el francés —«si la OMS publica en ese idioma, hay
corpus abierto garantizado»— **no existe para el portugués ni para el hindi**: no son lenguas
oficiales de la OMS. Para esos dos hay que abrir camino nuevo.

## Verificado hoy: abiertas ✅

| Fuente | Quién es | Licencia leída | Qué aporta |
|---|---|---|---|
| **OPS/OPAS** (paho.org/pt, iris.paho.org) | La oficina regional de la OMS para las Américas | **CC BY-NC-SA 3.0 IGO desde el 6-dic-2019**, leído en su página de permisos: «any non-commercial use, without the need to obtain permission from PAHO»; adaptaciones y traducciones permitidas con la misma licencia y su descargo | **Es el desbloqueo del portugués.** Publica en portugués y castellano, y es exactamente la licencia que el proyecto ya aceptó para la OMS en agosto |
| **Ministério da Saúde de Brasil** (gov.br/saude) | El ministerio; contenido «Saúde de A a Z» para ciudadanos | Pie de página, leído en la ficha de dengue: «Todo o conteúdo deste site está publicado sob a licença **Creative Commons Atribuição-SemDerivações 3.0 Não Adaptada**» (CC BY-ND) | Portugués con el sistema sanitario brasileño (SUS, calendario del PNI). ND = citar sí, reelaborar no → entra como **`citar_solo`** |
| **gesund.bund.de** (Portal Nacional de Salud, BMG) | El portal oficial alemán de información sanitaria | «Die Wiedergabe von textlichen Informationen … als Zitat in anderen Medien ist … zulässig, dass die Informationen **unverändert und vollständig mit Quellenangabe** wiedergegeben werden» | Tapa el hueco alemán: los 30 documentos `de` son **todos del RKI**, o sea vacunas. Aquí hay fiebre, diarrea, otitis… → **`citar_solo`** |
| **Canada.ca en inglés** | Ya aprobada el 2-sep para el francés | Uso no comercial libre sin permiso, con exactitud + título + autor + URL | Tenemos las **10 páginas francesas y ninguna inglesa**. Las gemelas ya están licenciadas: es coger lo que ya se pagó |
| **NHS, MedlinePlus, CDC, OMS** | Ya aprobadas en agosto | Sin cambios | **La ampliación más barata que existe**: 56 páginas del NHS, 74 de MedlinePlus, 19 de los CDC. Cero riesgo legal, cero decisión nueva, y `scripts/fetch_web_sources.py` ya está escrito |

## Verificado hoy: cerradas ❌

| Fuente | Licencia leída | Por qué duele |
|---|---|---|
| **BZgA / kindergesundheit-info.de** | «Für die Wiedergabe von Text- und Multimedia-Daten … ist eine **vorherige schriftliche Genehmigung** einzuholen» | Es *el* sitio alemán para padres, el equivalente del SEUP. Mismo patrón que Francia: el corazón del contenido para padres, cerrado sin permiso escrito |
| **healthdirect Australia** | «All intellectual property rights … owned by Healthdirect»; prohíbe «modify, publish, transmit, distribute … create derivative works … without the prior written permission» | Habría dado inglés no británico ni estadounidense |
| **HSE Irlanda** (hse.ie) | «© Health Service Executive», sin cláusula de reutilización | — |
| **DGS Portugal** (dgs.pt) | «All rights reserved» | El portugués europeo queda dependiendo de la OPS (que es brasileño/americano) |

## Pendientes de verificar ❓ (no se pudieron leer desde este PC)

| Fuente | Qué falta | Cómo cerrarlo |
|---|---|---|
| **MoHFW India** (mohfw.gov.in) | La política estándar de las webs del Gobierno de India —«may be reproduced free of charge … provided the source is prominently acknowledged»— aparece en las webs satélite del ministerio (NCDC, NHSRC, Safdarjung, Farmacopea). **La del ministerio no la he leído**: `main.mohfw.gov.in` no resuelve desde aquí y `mohfw.gov.in` devuelve 403 | Es **la vía del hindi**. Reintentar desde el VPS, que sale por otra IP |
| **BVS / bvsms.saude.gov.br** (Cadernos de Atenção Básica, incluidos los de salud infantil) | Los propios cadernos declaran CC BY-NC-SA 4.0, pero el servidor **corta la conexión** desde este PC | Reintentar desde el VPS y leer la página de créditos del PDF, no el resumen de un buscador |
| **SNS24 / sns24.gov.pt** | La página de términos vino vacía (se pinta con JS) | Navegador o lectura del JSON de la API |
| **Better Health Channel** (Victoria) | Devuelve 500 en su propia página de copyright | Reintentar |

## Una trampa que conviene mirar antes de tocarla

MedlinePlus tiene sección **«Health Information in Multiple Languages»** con hindi, y sería el
camino corto. Pero esas páginas **enlazan traducciones de terceros** (fundaciones, hospitales,
Healthinfotranslations…), cada una con su copyright: el dominio público cubre lo que escribe
MedlinePlus, no lo que aloja. Hay que verificar documento a documento, no la portada.

## Recomendación, por relación valor/riesgo

1. **Ampliar dentro de lo ya aprobado** (NHS, MedlinePlus, CDC, OMS) y traer **Canada.ca en
   inglés**. Ninguna licencia nueva, ninguna decisión nueva.
2. **OPS/OPAS en portugués y castellano** — abre el portugués con la licencia que el proyecto ya
   aceptó hace un mes.
3. **gov.br/saude** como `citar_solo` — el sistema sanitario brasileño, que la OPS no da.
4. **gesund.bund.de** como `citar_solo` — el alemán deja de ser solo vacunas.
5. **India**: verificar desde el VPS. Si la política estándar aplica al ministerio, hay hindi
   abierto; si no, el hindi se queda como el árabe y hay que decirlo.

## La foto honesta

El portugués se puede abrir hoy y con licencias ya conocidas. **El hindi no**: depende de una
página que no he podido leer, y sin ella no hay ni un documento en hindi ni forma legal evidente
de conseguirlo. Y en alemán se repite lo de Francia: lo bueno para padres (BZgA) está cerrado, y
lo abierto (gesund.bund.de) es más institucional.
