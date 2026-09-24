# Zenodo, paso a paso

> **Hecho el 24-sep-2026.** DOI de concepto `10.5281/zenodo.22932517`,
> registro en <https://zenodo.org/records/22932518>. Esto queda como guion para la próxima
> versión: a partir de ahora basta con publicar la release en GitHub, Zenodo la archiva sola.

**Para qué sirve.** Zenodo es el archivo abierto del CERN. Conectado a GitHub, cada versión que
publiques queda archivada y recibe un **DOI**: un identificador permanente que hace el proyecto
citable en literatura académica y lo mete en los buscadores científicos. Es gratis, no pide ser
empresa y no caduca. Para lo que buscamos —que sitios con autoridad enlacen a PediBot— es de lo
más barato que hay.

**El orden importa.** Zenodo archiva las versiones que se publican **después** de activar el
repositorio. Su documentación no dice qué pasa con las anteriores, así que no se prueba con una
versión de verdad: se activa primero y se publica después. Ahora mismo el repositorio no tiene
ninguna versión publicada, o sea que vamos bien.

---

## 1 · Crear la cuenta

<https://zenodo.org> → **Sign up**. Se puede entrar directamente con GitHub, que ahorra el paso
siguiente. Si prefieres correo, usa `pedibot.ai@gmail.com`.

## 2 · Conectar GitHub

Menú de tu perfil (arriba a la derecha) → **Linked accounts** → junto a GitHub, **Connect** →
autorizas en GitHub y vuelves a Zenodo. Cuando esté hecho aparece una marca verde.

> Zenodo pide permiso de escritura sobre webhooks del repositorio. Es lo que necesita para
> enterarse de que has publicado una versión; no toca el código.

## 3 · Activar el repositorio

Menú de tu perfil → **GitHub**. Sale la lista de tus repositorios. Busca **pedibot** y pon el
interruptor en **ON**.

> Si no aparece: pulsa **Sync now** (Zenodo cachea la lista de repositorios) y recarga. Tiene que
> ser público, y ya lo es.

## 4 · Publicar la versión en GitHub

En <https://github.com/nicolasbeca/pedibot> → **Releases** (columna derecha) → **Create a new
release**:

- **Choose a tag** → escribe `v2.0.0` → *Create new tag on publish*
- **Release title:** `PediBot 2.0.0`
- **Describe this release:** vale con dos líneas. Por ejemplo:

      First public release. Answers parents' questions from 632 published paediatric
      documents, citing the source of every clinical sentence. Emergency numbers for 90
      countries, vaccination schedules for 66, WHO growth standards and MUAC, in eight
      languages.

- **Publish release**.

> **Sobre el número:** el proyecto se declara hoy como `2.0.0a0` (alfa) en `pyproject.toml` y en
> `CITATION.cff`. Publicar `v2.0.0` a secas es decir que ya no es alfa. Es tu decisión: si
> prefieres mantener el alfa, la etiqueta es `v2.0.0a0` y queda igual de válida, sólo que menos
> vistosa en una cita. Dímelo y ajusto los tres ficheros para que digan lo mismo.

## 5 · Esperar y coger el DOI

Vuelve a Zenodo → menú de perfil → **GitHub** → **pedibot**. En un rato (depende del tamaño y de
la cola de Zenodo) aparece la versión con su DOI. Tendrás **dos**:

- el **DOI de la versión**, que apunta a `v2.0.0` para siempre;
- y el **DOI de concepto**, que apunta siempre a la última versión. **Éste es el que se pone en
  la web y en las solicitudes.**

## 6 · Pegarlo donde cuenta

Cuando lo tengas, mándamelo y yo lo pongo en su sitio: el distintivo en el README, el campo
`identifier` de `CITATION.cff`, y la respuesta del indicador 3 de la solicitud de bien público
digital, donde un DOI vale más que una frase.

---

## Lo que ya está hecho por mi parte

- **`.zenodo.json`** en la raíz del repositorio, que es lo que Zenodo lee para rellenar el
  registro: título, descripción, autoría, licencia `agpl-3.0-or-later`, palabras clave y los
  enlaces a la web y al catálogo. Los identificadores de licencia y de relación **están
  comprobados contra el vocabulario de Zenodo**, no escritos de memoria: un identificador que no
  existe hace fallar el archivado en silencio.
- Deliberadamente **no lleva campo `version`**, para que tome la de la etiqueta que publiques y
  no haya dos números distintos diciendo cosas diferentes.
- Si el repositorio tiene `.zenodo.json` y `CITATION.cff`, **Zenodo usa sólo el primero** y no
  mira el segundo. El `CITATION.cff` se queda porque es lo que enseña GitHub en su botón «Cite
  this repository», que es otro público.
