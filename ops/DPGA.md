# Bien público digital (DPGA) — la solicitud, respuesta por respuesta

> **Lo que tiene que hacer el operador:** entrar en <https://app.digitalpublicgoods.net>, crear
> la cuenta con `pedibot.ai@gmail.com`, verificar el correo y pegar las respuestas de abajo.
> Sólo puede enviarla «un representante autorizado de la solución digital», o sea él.
> Después: **de 4 a 8 semanas** de revisión, y el resultado es binario — reconocido o no
> elegible. Si piden una aclaración y no se contesta en plazo, la solicitud se declara no
> elegible sola, así que conviene mirar el correo mientras dure.

Escrito el 23-sep-2026 contra el [DPG Standard](https://github.com/DPGAlliance/DPG-Standard),
que son nueve indicadores y once casillas. **Ninguna respuesta de aquí afirma nada que no esté
en el repositorio o vivo en pedibot.xyz**; cada una dice dónde mirarlo.

---

## 1 · Relevancia para los ODS

**ODS 3 — Salud y bienestar**, metas 3.2 (acabar con las muertes evitables de menores de cinco
años) y 3.8 (cobertura sanitaria universal, incluida la información).

PediBot contesta lo que una familia pregunta cuando un niño está enfermo, usando sólo lo que
las sociedades de pediatría, los ministerios de sanidad y la OMS ya publican para padres, y
citando el documento del que sale cada frase. Es gratis, no pide cuenta y funciona en ocho
idiomas.

Lo que lo ata a la meta 3.2 no es la intención, son los datos que lleva dentro:

- **54 países africanos con su número de emergencia** y **54 con su calendario de vacunación**,
  que son todos los del continente.
- **MUAC** (perímetro braquial) para desnutrición aguda, que es la herramienta de cribado que
  usan los programas comunitarios donde no hay báscula.
- Las **curvas de crecimiento de la OMS**, que son las que usan los sistemas de salud que no
  tienen tablas propias.
- Los **96 avisos de alarma** están escritos para que un padre reconozca un niño grave y acuda,
  no para que se quede en casa: cuando saltan, lo primero que aparece es el número de
  emergencias de su país.

## 2 · Licencia abierta

| Qué | Licencia | Dónde |
|---|---|---|
| El código | **AGPL-3.0-or-later** (aprobada por la OSI) | [`LICENSE`](../LICENSE) |
| El catálogo de fuentes | **CC0 1.0** (dominio público) | [`dataset/LICENSE`](../dataset/LICENSE) |
| Los documentos citados | de sus organismos; no se relicencian | cada ficha dice de quién es y si es reproducible |

La tercera fila es deliberada y conviene explicarla en la solicitud: el corpus **apunta** a
documentos que son del NHS, del CDC, de la OMS o de un ministerio, y guarda la licencia de cada
uno. Tres documentos del corpus no se pueden redistribuir, y el catálogo público lo dice.

## 3 · Propiedad claramente definida

Copyright © 2026 Nicolás Beca, declarado en el [README](../README.md#ownership). El nombre
PediBot y el logotipo son del autor y no van con la licencia: el código se puede bifurcar, la
marca no. Contacto público: `pedibot.ai@gmail.com`, que aparece en la web y firma el dominio.

## 4 · Independencia de plataforma

Nada de lo que hace PediBot depende de un servicio cerrado:

- El chat habla con **cualquier punto final compatible con OpenAI** (`OpenAICompatibleProvider`
  recibe una `base_url`), así que un servidor local —Ollama, vLLM, llama.cpp— lo sustituye.
- **Triaje, dosis, calendarios de vacunación, números de emergencia, curvas de crecimiento y
  MUAC funcionan sin ningún modelo**: son reglas y tablas, y se ejecutan en local.
- El índice es **SQLite**, el catálogo es **JSON y CSV**, la web son **ficheros estáticos**, el
  servidor es **Python con FastAPI**. Todo instalable con `uv sync`.

## 5 · Documentación

- [`README.md`](../README.md) — qué es, cómo se construye una respuesta, cómo se ejecuta.
- [`PRD.md`](../PRD.md) — el plan completo, con la arquitectura por capas.
- [`LESSONS.md`](../LESSONS.md) — 236 fallos documentados con lo que costaron y lo que
  cambiaron. No es habitual enseñarlo, y es lo que mejor explica cómo funciona esto de verdad.
- [`DATOS.md`](../DATOS.md) — todas las cifras del proyecto, **generadas** de los ficheros de
  datos, con un comprobador que hace fallar la suite si un documento repite una mal.
- **10.336 pruebas automáticas** y un conjunto dorado que se mide de punta a punta antes de
  cada despliegue.

## 6 · Extracción de datos sin información personal

El catálogo entero se publica en formatos no propietarios y sin nada personal dentro:

- <https://pedibot.xyz/dataset/sources.json> — JSON, CC0, 645 documentos.
- `dataset/sources.csv` — el mismo, en CSV.
- <https://pedibot.xyz/sources> — la misma lista, legible, con el organismo de cada documento.

Se regeneran con `uv run python scripts/export_dataset.py`. No hay ningún dato de usuario en
ellos, ni ninguna forma de que lo haya: salen del catálogo de fuentes, no del registro de uso.

## 7 · Privacidad y leyes aplicables

Política pública en <https://pedibot.xyz/es/legal>, en los ocho idiomas. Sujeta al RGPD
(el responsable y el servidor están en la Unión Europea). En resumen de lo que hace el sistema:

- **Sin cuenta no se pide ni un dato personal**, y la web lo dice con esas palabras.
- Con cuenta —opcional— se guardan correo, contraseña con hash, y de los hijos: nombre, fecha
  de nacimiento, sexo, país y las medidas que se apunten. **Se puede descargar todo y borrar la
  cuenta desde la propia página, sin pedírselo a nadie.**
- Las preguntas se guardan **de forma anónima** (sesión aleatoria, **sin IP**) para evaluar la
  calidad. La memoria de conversación dura 24 horas y se borra sola.
- La IP se usa **sólo como hash con sal** para limitar peticiones; no se guarda en claro.
- **Sin rastreadores publicitarios**, sin anuncios y sin cesión a terceros.

## 8 · Estándares abiertos y buenas prácticas

HTTP/JSON con esquema abierto (FastAPI publica su OpenAPI), HTML estático con `hreflang` y
`sitemap.xml`, SQLite con FTS5, CSV y JSON para los datos, CC0 para el catálogo, ocho idiomas
con sus ficheros de traducción en el repositorio. Las fuentes clínicas son las que publican los
propios organismos, y cada respuesta enlaza el documento original en lugar de reescribirlo.

## 9 · No hacer daño por diseño

Este es el indicador que ordena todo el sistema, así que conviene decirlo entero.

**El diseño de la respuesta.** Un modelo de lenguaje sólo redacta, y sólo con los pasajes que se
le entregan. Antes hay un triaje **por reglas y sin modelo** que pone el aviso y el número de
emergencias delante de todo; después hay una verificación que rechaza el borrador si no cita, si
cita algo que no existe o si da una dosis que no sale de la tabla autorizada. Un borrador
rechazado se regenera una vez; si vuelve a fallar, **la respuesta es una negativa**. Medido en
el servicio vivo: alrededor del **3 % de las respuestas terminan en «no tengo una fuente fiable
para esto»**, y eso es el producto funcionando, no fallando.

### 9a · Privacidad y seguridad de los datos

Lo del indicador 7, más: la base de datos de cuentas está separada de la anónima; las
contraseñas se guardan con hash; el servidor sirve sólo por HTTPS; las páginas de respuesta
compartida llevan `noindex` y un identificador aleatorio que no se adivina, **y desde el
23-sep-2026 quien comparte puede retirarlas desde la propia página**.

### 9b · Contenido inapropiado o ilegal

PediBot **no publica contenido de usuarios**: no tiene foro, ni comentarios, ni perfiles. Lo
único que un usuario puede hacer público es **su propia respuesta**, con el botón de compartir,
y esa página:

1. sólo la puede crear quien hizo la pregunta, desde su propia sesión;
2. no se indexa (`noindex`) y su dirección no se puede adivinar;
3. **la puede retirar quien la creó**, en un clic, desde la propia página;
4. y cualquiera que vea una que no debería existir puede escribir a `pedibot.ai@gmail.com`,
   que está publicado en todas las páginas del sitio.

### 9c · Protección frente al acoso

No hay interacción entre usuarios: nadie puede escribir a nadie dentro de PediBot, no hay
nombres públicos, ni mensajes, ni comentarios. Por construcción no hay superficie de acoso.

Sobre menores: PediBot está escrito **para el adulto que cuida a un niño**, y los datos de los
hijos —cuando hay cuenta— los introduce ese adulto y puede borrarlos cuando quiera. El chat no
pide nunca el nombre del niño ni ningún dato identificable, y la web dice expresamente que no
hacen falta.

---

## Lo que faltaba y se hizo para esto (23-sep-2026)

No se envía una solicitud declarando cosas que no están hechas. Al repasar el estándar
aparecieron tres huecos y los tres se taparon antes de escribir esto:

1. **No había licencia de código.** Un repositorio público sin licencia es «todos los derechos
   reservados»: el indicador 2 lo rechaza de entrada. Ahora es AGPL-3.0.
2. **No había declaración de propiedad** (indicador 3). Ahora está en el README.
3. **Un enlace compartido no se podía retirar** (indicador 9b, y sentido común). Ahora sí, en
   los ocho idiomas, y la política legal lo cuenta.

---

## Y lo que va con esto: repositorio, dataset y DOI

Tres sitios más donde el proyecto tiene que estar para que los enlaces existan. La razón es la
medida del 23-sep-2026: **1.848 impresiones en Google, 3 clics, posición media 65,5**. Las
páginas están bien escritas —«calculadora dalsy» nos muestra en el puesto 51 con una página que
lleva ese título exacto y 1.200 palabras—, así que lo que falta no es contenido: es que ningún
sitio con autoridad nos enlaza todavía.

### 1 · GitHub (hace falta él: crear el repositorio)

El repositorio local está listo: licencia AGPL-3.0, README escrito para quien llega de fuera,
`CITATION.cff` para que sea citable, y **el historial ya revisado** — 515 commits sin una sola
clave, sin datos de padres, y con la autoría reescrita a `pedibot.ai@gmail.com` para que los
correos personales no queden públicos.

    # en github.com: New repository → nicolasbeca/pedibot → Public → sin README ni licencia
    git push -u origin master

### 2 · Hugging Face (hace falta él: la cuenta)

El catálogo como dataset, que es donde lo busca quien construye algo parecido.
[`dataset/HUGGINGFACE.md`](../dataset/HUGGINGFACE.md) es la tarjeta, ya con su cabecera YAML:
se sube tal cual como `README.md` del dataset, junto a `sources.csv` y `sources.json`.

### 3 · Zenodo (hace falta él: conectar la cuenta)

Zenodo se conecta a GitHub una vez y, a partir de ahí, **cada versión publicada recibe un DOI
automáticamente**. Un DOI hace el proyecto citable en literatura académica y lo mete en los
buscadores científicos, que es otro sitio donde las ONG miran. Con el repositorio ya público:
Zenodo → GitHub → activar `nicolasbeca/pedibot` → en GitHub, publicar la versión `v2.0.0`.

### Lo que NO hay que hacer

Publicar el repositorio y ya. Un repositorio sin enlaces entrantes no mueve la posición en
Google ni un puesto. Lo que la mueve es estar en el registro de la DPGA, en Hugging Face y con
DOI, porque esos tres sí tienen autoridad y sí enlazan de vuelta.
