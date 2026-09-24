# Hugging Face, paso a paso

**Para qué sirve.** Hugging Face es donde busca conjuntos de datos quien construye algo con
modelos de lenguaje: investigadores, ONG que montan su propio asistente, gente que necesita
fuentes de salud infantil ya clasificadas. Publicar ahí el catálogo pone a PediBot delante de
ese público y deja un enlace desde un dominio con autoridad, que es lo que hoy le falta.

**Cuánto lleva:** unos diez minutos, y la página está viva el mismo día. No hace falta instalar
nada: se sube arrastrando ficheros.

> **Ojo con los dos ficheros que se llaman igual.** Éste es el guion de pasos.
> [`dataset/HUGGINGFACE.md`](../dataset/HUGGINGFACE.md) es **la tarjeta del dataset**: el texto
> que se sube y que la gente lee en Hugging Face. Ya está escrito, con su cabecera YAML.

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

| fichero local | cómo se llama al subirlo | qué es |
|---|---|---|
| `dataset/sources.csv` | `sources.csv` | el catálogo, 645 filas |
| `dataset/sources.json` | `sources.json` | el mismo, en JSON |
| `dataset/HUGGINGFACE.md` | **`README.md`** ← renómbralo | la tarjeta que se lee en la página |

> **El tercero es el importante y hay que renombrarlo.** Hugging Face lee la tarjeta del fichero
> `README.md` y de ningún otro: si lo subes con su nombre original, la página sale vacía y el
> dataset no aparece en las búsquedas por idioma ni por licencia, porque esos datos van en la
> cabecera de ese fichero.

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

El dataset no se actualiza solo. Cuando entren fuentes nuevas —como las catorce del 23-sep—, hay
que volver a subir `sources.csv` y `sources.json`: **Files and versions** → el fichero →
**Edit** → arrastrar el nuevo encima → commit. Hugging Face guarda el histórico, así que quien
lo hubiera descargado antes puede ver qué cambió.

Si algún día se hace a menudo, se automatiza con `huggingface_hub` desde el propio repositorio;
hoy, a mano y cuando cambie de verdad, sobra.
