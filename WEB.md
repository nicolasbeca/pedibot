# WEB.md — la web de PediBot: decisiones, pendientes y mejoras

> **Las cifras de este documento no se escriben a mano.** `DATOS.md` lleva todas,
> contadas de los ficheros de datos, y `scripts/check_docs.py` avisa si aquí aparece
> una que ya no sea verdad. El 21-sep-2026 había 107 repartidas por los `.md`.

> Cuaderno vivo de **pedibot.xyz**: lo que se decidió y por qué, lo que está en marcha solo, y lo
> que queda. El estado general del proyecto vive en `STATE.md`; los fallos aprendidos en
> `LESSONS.md`; las ideas sin decidir en `IDEAS.md`. Aquí va lo que es de la web.
>
> Regla de este fichero: **cada cifra dice de cuándo es y de dónde sale.** Si una se queda vieja,
> se relee del sitio o del registro, no se estima.

---

## 1 · Qué hay, medido el 11-sep-2026

| | |
|---|---|
| Páginas | **792** en el sitemap, 8 idiomas (en, es, fr, de, ru, ar, pt, hi) |
| Corpus | **el corpus entero** (cuántos documentos y pasajes, en `DATOS.md`). Por idioma: en 166, es 93, fr 40, ar 38, ru 38, de 30, pt 14, **hi 0** |
| Capa de seguridad | **las reglas de alarma** (cuántas, en `DATOS.md`) en 8 lenguas, todas con documento que las respalda (auditado). Fuera de Europa: 25 de 25 |
| Alcance árabe / hindi | Diez preguntas por mercado: árabe **9 de 10** (era 2), hindi **10 de 10** (era 7) |
| Marcas reconocidas | **32** (eran 20): añadidas India, Golfo, Egipto y Levante. 18 de 20 preguntas por marca del mercado objetivo dan dosis |
| Páginas | **900** (eran 792 esta mañana) |
| Guías | 485 y subiendo: se publican solas, 2 al día |
| Indexadas en Google | **557 de 779**; 194 que no conoce, 28 rastreadas y descartadas |
| Bing | Verificado, sitemap entregado sin errores, IndexNow recibiendo — **y sin rastrear páginas** |
| Búsqueda (90 d) | 1.045 impresiones, 3 clics, **posición media 69**. El sitio tiene 14 días a ojos de Google |
| Visitas (7 d) | **94 con navegador**, 589 páginas vistas, 31 vieron dos o más |
| Consultas reales | **5 en toda la vida del proyecto** (web 1, Telegram 2, agente 2). Lo demás son pruebas |

La última fila es la que manda sobre todas las demás: **el cuello de botella no es el código.**

---

## 2 · Decisiones tomadas

| Fecha | Decisión | Por qué |
|---|---|---|
| 24-ago | Inglés primero, español después, resto más tarde | Mercado internacional desde el inicio (D-04) |
| 25-ago | **Costes e interioridades son privados** | La web dice que mantenerlo cuesta dinero; nunca las cifras |
| 25-ago | Respuestas **sin bloque de fuentes**: el organismo se nombra en la frase | Máximo ~110 palabras; sin enlaces ni marcadores |
| 25-ago | Tema **siempre claro**; la noche solo con el botón | El ajuste del navegador se ignora a propósito |
| 1-sep | La pestaña de apoyo va **fuera del `<nav>`**, en el grupo derecho | El `<nav>` se oculta en móvil y es justo la página que pide ayuda |
| 2-sep | **Sin `i18n` en el sitemap** | Calculaba hreflang por prefijo y el slug cambia con la lengua: contradecía al HTML |
| 2-sep | Insignia de LaunchLeague retirada | Medida: 20 visitantes en 7 días y **cero** consultas al bot |
| 9-sep | **Anillo de enlaces** entre guías, no «las más recientes» | 390 de las 483 guías de entonces colgaban de un solo enlace; el relleno por recencia concentra |
| 10-sep | `Substance`, nunca `Drug`, en los datos estructurados | `Drug` hereda de `Product`: Google pedía precio o valoración de un jarabe infantil |
| 10-sep | `lastmod` sale del **contenido**, no de la construcción | Declaraba 296 páginas cambiadas cada día y arrastraba a IndexNow |
| 11-sep | **Una visita exige la prueba del navegador** | El panel contaba 3.227 visitantes donde había 201 |
| 11-sep | **LaunchLeague: todo rastro fuera** | Sus SVG seguían sirviéndose con 200 sin que nada los enlazara |
| 11-sep | **La cuenta de Bluesky habla inglés** | Los mensajes del proyecto ya no alternan con castellano |
| 11-sep | El generador de guías **no sindica** | Escribe un día en hindi y otro en árabe; Bluesky lo deciden sus propios timers |
| 11-sep | **Atacar India y países árabes** es la baza principal | Y el token, si va a MetaDAO, se vende como altruismo, no como múltiplo |
| 11-sep | **Una frase de apoyo** al pie de las guías y de las páginas de marca | Son las dos familias de páginas con visitas reales. La portada ya tenía su bloque y repetirlo sería pesado |
| 11-sep | **La portada demuestra en vez de contar**: ocho alfabetos, dosis que se mueve, tarjetas que enseñan lo real, organismos con cifra y «tu país» | Un padre asustado a las 3 de la mañana no necesita un *landing* de startup: necesita ver que el sitio sabe lo que dice |
| 11-sep | **Ninguna cifra clínica se calcula en el navegador** | La tabla del deslizador la genera Python con el módulo real; JavaScript sólo consulta. Una segunda implementación de un cálculo clínico puede desviarse sin que nadie lo vea |
| 11-sep | **Los organismos se muestran por número de documentos, sin barajar** | Al hacer la cifra visible, el azar sacaba casillas de «1» junto a una de «74». Sólo siete organismos llegan a diez documentos |

---

## 3 · Lo que corre solo

| Cuándo | Qué | Unidad |
|---|---|---|
| Diario 06:30 | **2 guías nuevas**, en las dos lenguas más atrasadas, y reconstruye el sitio | `pedibot-publish` |
| Diario 07:15 | Avisa a Bing, Yandex, Seznam y Naver de lo que cambió | `pedibot-indexnow` |
| Cada 2 días 10:00 | Un mensaje del proyecto en Bluesky, en inglés | `pedibot-social-project` |
| Martes 09:00 | Una guía por idioma en Bluesky: 8 publicaciones | `pedibot-social-guides` |
| Cada 10 min | Vigila los servicios **y que una consulta funcione** | `pedibot-watchdog` |
| Diario 04:45 | Descarga los datos de Search Console al panel | `pedibot-gsc` |

**Si la cola de temas se vacía, `pedibot-publish` lo dice en voz alta** («NO QUEDA NADA QUE
PUBLICAR») y `test_topic_plan.py` falla. Es la avería que dejó el sitio seis días sin publicar
sin que nadie se enterara.

---

## 4 · Pendientes, en orden de consecuencia

### 4.1 · Bloqueantes de verdad

1. **India y países árabes: la baza principal, a medio hacer.**
   - ✅ **Licencia de India resuelta** (11-sep): la NHM permite reproducir citando la fuente de
     forma prominente (`FUENTES/INDIA.md`). El portal del ministerio da 403 desde España y una
     cáscara de JavaScript desde el VPS; la política se leyó en `nhm.gov.in`, mismo ministerio.
   - ✅ **Calendario vacunal de India publicado** en `/vaccines/in`, en los ocho idiomas,
     transcrito del PDF oficial, con candado para las siete diferencias que un europeo
     corregiría por instinto (MR y no MMR, pentavalente, OPV oral, fIPV, semanas en vez de
     meses, PCV y JE no nacionales, Td a los 10 y 16 años).
   - ✅ **Árabe: de 15 a 38 documentos** (11-sep). 23 fichas de la OMS en cinco idiomas —malaria,
     dengue, tifoidea, hepatitis A, anemia, sepsis, mordedura de serpiente, lombrices, sarna,
     agua potable, rabia, difteria, tétanos— porque el corpus era pediatría europea y no tenía
     nada de lo que mata fuera de ella.
   - ✅ **Y se pueden alcanzar**: 20 de 35 preguntas no llegaban a su documento (taxonomía y
     puentes de sinónimos). Ahora 35 de 35, con candado.
   - ⬜ **Hindi sigue con cero documentos propios.** No existe corpus pediátrico en hindi con
     licencia abierta y texto utilizable: el único candidato serio está en codificación Krutidev
     (L128). Las preguntas hindi se responden puenteando al inglés, que ya funciona.
   - ⬜ **EMRO y el ministerio saudí se pintan con JavaScript**: EMRO devuelve la misma página
     para cualquier URL (4.413 caracteres idénticos) y `moh.gov.sa` devuelve 170. Leerlos
     necesitaría un navegador de verdad; es una decisión aparte.
   - ⬜ **Ningún calendario vacunal de país árabe.** India ya está.
2. **Diez padres.** De 278 consultas en la base, 273 son pruebas. Sin lectores, nada de lo demás
   importa.
3. **Nadie enlaza al sitio.** Bluesky es el único enlace vivo, y LaunchLeague nunca llegó a
   publicar la ficha. Para Bing, que pesa mucho los enlaces, esto es el tapón.

### 4.2 · Mejoras identificadas y medidas (ver `IDEAS.md`, lote S-01…S-05)

| Id | Qué | Medida que lo justifica |
|---|---|---|
| S-02 | Página de «quién está detrás» + revisor médico | En salud (YMYL) es el techo de fondo. `reviewedBy` y `lastReviewed` **solo** cuando un pediatra revise de verdad |
| S-03 | Deshacer los pares de páginas de marca casi idénticas | 97 % de solapamiento entre apirofeno y junifen; 11 pares por encima del 70 % |
| S-04 | Acortar 157 títulos de más de 60 caracteres | Se cortan en el resultado; el CTR está en 0,29 % |
| S-05 | ¿Bloquear AhrefsBot y SemrushBot? | 1.715 peticiones en 7 días que no traen a nadie |

### 4.3 · Sin decidir

- **Las tres guías que solo existen en inglés** (asma, ibuprofeno, paracetamol): traducirlas a
  los siete idiomas o retirarlas. En ellas el selector de idioma no ofrece nada.
- **Fuentes nuevas** con licencia ya verificada y sin usar (`FUENTES/CANDIDATAS.md`): OPS/OPAS
  (abre el portugués), `gov.br/saude` y `gesund.bund.de` como `citar_solo`, y Canada.ca en
  inglés, que ya está aprobada y de la que solo se usan las 10 páginas francesas.
- **Volumen en Bluesky**: hoy son ~1 al día más una ráfaga de 8 los martes. Si resulta ruidoso,
  la ráfaga se reparte o se deja solo en inglés.

---

## 5 · Reglas de la web que no se tocan sin discutirlo

- **Ninguna página pide un recurso a otro dominio.** `/legal` lo promete y
  `test_no_third_party_assets.py` lo comprueba en las 779.
- **Ningún tipo de la familia `Product`** en los datos estructurados, y jamás `offers`, `review`
  ni `aggregateRating` sobre un medicamento.
- **Ninguna cifra pública sin medir.** El dossier de 2025 decía «100+ usuarios diarios» y
  «9,8 % CTR»; no se repiten hasta que la v2 los mida.
- **El aviso de urgencias no baja de posición por estética.**
- Nada de enlaces comprados, granjas de contenido ni directorios de pago.
