# Hugging Face, paso a paso

> **Hecho el 28-sep-2026:** <https://huggingface.co/datasets/PediBot/pedibot-sources>
> Queda como guion para la próxima vez que haya que actualizar el catálogo.

**Para qué sirve.** Hugging Face es donde busca conjuntos de datos quien construye algo con
modelos de lenguaje: investigadores, ONG que montan su propio asistente, gente que necesita
fuentes de salud infantil ya clasificadas. Publicar ahí el catálogo pone a PediBot delante de
ese público y deja un enlace desde un dominio con autoridad, que es lo que hoy le falta.

**Cuánto lleva:** unos diez minutos, y la página está viva el mismo día. No hace falta instalar
nada: se sube arrastrando ficheros.

> Éste es el guion de pasos. Lo que se sube son los **tres ficheros de `dataset/`** tal y como
> están: los genera `scripts/export_dataset.py` desde el catálogo, cabecera de Hugging Face
> incluida, así que no hay nada que escribir ni que renombrar.

---

## 1 · Crear la cuenta

<https://huggingface.co/join> con `pedibot.ai@gmail.com`. Verifica el correo: sin eso no deja
crear nada.

## 2 · Crear el dataset

<https://huggingface.co/new-dataset>

- **Owner:** tu usuario.
- **Dataset name:** `pedibot-sources` — corto y pegado a la marca, que ya tiene web y DOI. Si
  prefieres que se encuentre por lo que es antes que por cómo se llama,
  `pediatric-guidance-catalog` también vale. Lo que no conviene es cambiarlo después: la
  dirección se queda fija y los enlaces se rompen.
- **License:** `cc0-1.0` (Creative Commons Zero). Está comprobado contra la lista de licencias
  que Hugging Face acepta; si pones otra cosa, el campo se queda en blanco sin avisar.
- **Public**, obviamente.
- **Create dataset**.

## 3 · Subir los tres ficheros

En el dataset recién creado → pestaña **Files and versions** → **Add file** → **Upload files**.
Arrastra estos tres, de la carpeta `dataset/` del repositorio:

| fichero local | qué es |
|---|---|
| `dataset/sources.csv` | el catálogo, 632 filas |
| `dataset/sources.json` | el mismo, en JSON |
| `dataset/README.md` | la tarjeta que se lee en la página |

> Los tres van con su propio nombre: no hay que renombrar nada. Hugging Face lee la tarjeta del
> fichero `README.md` y de ningún otro, y su cabecera —licencia, idiomas, etiquetas— es lo que
> pone las etiquetas de la página y la tabla navegable del CSV. Hasta el 28-sep-2026 esa tarjeta
> era un fichero aparte que había que renombrar al subirlo, y mantenerla a mano ya había dejado
> una cifra vieja dentro; ahora la escribe el generador.

Pesan 170 KB y 280 KB, así que van por el navegador sin problema. Escribe un mensaje de commit
—«first upload» vale— y **Commit changes to main**.

## 4 · Comprobar que se ve

Vuelve a la pestaña principal del dataset. En un minuto deberías ver:

- la **tabla navegable** del CSV (Hugging Face la genera sola para los datasets públicos);
- en la cabecera, las etiquetas de **licencia CC0**, los **ocho idiomas** y las palabras clave;
- el texto de la tarjeta, con los enlaces a pedibot.xyz, al repositorio y al DOI.

Si la tabla no aparece, casi siempre es que el `README.md` no está o que su cabecera se rompió
al copiar: el bloque entre las dos líneas de `---` tiene que quedar intacto, con sus sangrías.

## 5 · Avisarme

Mándame la dirección (`https://huggingface.co/datasets/<usuario>/<nombre>`) y la enlazo desde la
web, desde el README del repositorio y desde el indicador 6 de la solicitud de bien público
digital, que es justo el que pide un mecanismo de extracción de datos sin información personal.

---

## Cuando el catálogo cambie

El dataset no se actualiza solo. Cuando entren fuentes nuevas —como las catorce del 23-sep—, se
regenera con `uv run python scripts/export_dataset.py` y se vuelven a subir **los tres**:
**Files and versions** → el fichero → **Edit** → arrastrar el nuevo encima → commit. El README
también, porque sus cifras y sus tablas cambian con el catálogo. Hugging Face guarda el
histórico, así que quien lo hubiera descargado antes puede ver qué cambió.

Si algún día se hace a menudo, se automatiza con `huggingface_hub` desde el propio repositorio;
hoy, a mano y cuando cambie de verdad, sobra.
