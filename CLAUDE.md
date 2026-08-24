# CLAUDE.md — PediBot

> Documento "alma" del proyecto. Claude Code lo lee al arrancar cada sesión, junto con `PRD.md`, `STATE.md` y `LESSONS.md`. Aquí vive **cómo se trabaja**. El "qué/por qué" detallado vive en `PRD.md`. El estado vivo en `STATE.md`. Los fallos pasados en `LESSONS.md`. Las ideas sin decidir en `IDEAS.md`.

## Qué es PediBot

Asistente pediátrico para madres, padres y cuidadores, en español, que responde **solo a partir de fuentes médicas verificadas** (guías de la AEP, SEUP, AEPap, OMS, AAP, Ministerio de Sanidad, Junta de Andalucía…) y **cita la fuente concreta** en cada respuesta. No sustituye al pediatra: es el primer punto de referencia para reducir la incertidumbre a las 3 de la mañana y decir con claridad cuándo hay que ir a urgencias.

Es un **relanzamiento**. La v1 (2025) corría en n8n + OpenAI + Wix Premium: no llegó a funcionar bien y era cara de mantener. La v2 se construye desde cero, con código propio, en un VPS de Hetzner (mismo patrón que MultiBot), con motor LLM barato (DeepSeek) y una web estática muy profesional que es la carta de presentación.

Activos que se heredan: las **fuentes PDF** (`FUENTES/`, 50 documentos, catálogo en `FUENTES/CATALOGO.md`), los **logos** (`LOGOS/`), la cuenta de X **@pedibotai** (unos cientos de seguidores, dormida), el correo `pedibot.ai@gmail.com`, el dossier de inversores (`25-10-10_*`), y el token **PDBT** en Base (Virtuals, contrato `0x196A67BA334DbeD501E19BAEc47D217BB2FC15E1`, FDV ≈ 25 k$, ~3.900 holders, volumen ≈ 0).

**Lo que NO es**:
- ❌ NO es ChatGPT con un logo. Si la respuesta no está en las fuentes, el bot lo dice y no inventa. Cada afirmación clínica lleva referencia.
- ❌ NO es un servicio médico ni diagnostica. No pauta tratamientos: cita lo que dice la guía y remite al pediatra.
- ❌ NO es un proyecto web3. El token existe como vía de financiación altruista y transparente, **nunca** como requisito para usar nada (ni staking, ni "token-gating"). La plataforma es web2 y para todo el mundo.
- ❌ NO es un juguete de RAG genérico: la calidad se mide con un banco de preguntas de evaluación (golden set) antes de abrir al público, y el "cero respuestas peligrosas" es un gate, no un deseo.

## Los 5 bloques del sistema

Cada bloque es independiente, con su propio código, tests y unit de systemd. Uno roto no tumba a los demás.

1. **Ingesta (`ingest/`)** — el "pequeño bot que trocea": PDF → texto (OCR si hace falta) → limpieza → troceado por secciones → clasificación (tema, edad, tipo de documento, organismo, nivel de evidencia) → export a JSONL + índice SQLite (FTS5 léxico + vectores). Determinista, reproducible, se ejecuta en local y en el VPS con el mismo comando. Ver PRD §4.
2. **Motor de respuesta (`bot/`)** — API FastAPI. Pipeline: triaje de gravedad (reglas + LLM) → recuperación híbrida (BM25 + embeddings, RRF) → redacción con DeepSeek forzada a citar → verificación de citas (cada cita apunta a un chunk real) → respuesta con banner de urgencias si aplica. Ver PRD §5.
3. **Web (`web/`)** — sitio estático (Astro) muy cuidado, SEO fuerte, con el widget de chat embebido, biblioteca de artículos temáticos con fuentes, páginas de herramientas (calculadora de dosis, percentiles, calendario vacunal) y página "Apoya el proyecto" (donación + token). Ver PRD §6.
4. **Publicación (`publish/`)** — generador de artículos cortos a partir de las fuentes (revisión humana opcional por cola), rebuild del sitio, sitemap, y post en X. Ver PRD §7.
5. **Operación (`ops/`)** — despliegue en Hetzner, Caddy, systemd, backups, watchdog, métricas de uso y coste por consulta, alertas por Telegram (reutilizamos el patrón del outbox de MultiBot). Ver PRD §8.

## Reglas clínicas innegociables

Esto no son recomendaciones. Son gates que el código y los tests hacen cumplir.

1. **Fuente o silencio.** Si la recuperación no devuelve ningún fragmento por encima del umbral de relevancia, el bot responde "no tengo información fiable sobre esto" y sugiere consultar al pediatra. Nunca rellena con conocimiento del modelo.
2. **Cita verificable en cada afirmación clínica.** Formato `[Organismo, Documento, sección/página]`. Un post-procesador comprueba que cada cita corresponde a un chunk realmente recuperado; si el LLM cita algo que no existe, la respuesta se regenera o se descarta.
3. **Signos de alarma → urgencias, siempre y arriba.** Un clasificador de gravedad corre ANTES de redactar. Si detecta señales de alarma (lista canónica en `config/red_flags.yaml`, extraída de `acudir_urgencias.pdf` y de las hojas SEUP), la respuesta abre con el bloque "Llama al 112 / acude a urgencias ahora" y solo después informa. Recall del clasificador sobre el set de prueba: 100 % o no se despliega.
4. **Dosis: nunca las calcula el LLM.** La calculadora de dosis es una función determinista con tablas transcritas de la guía de dosificación, límites máximos duros y test por cada fármaco. El LLM solo puede citar la tabla; no puede multiplicar.
5. **Menores de 3 meses con fiebre = urgencias.** Regla dura hardcoded, independiente del LLM.
6. **Salud mental (autolesión, ideación suicida)**: respuesta con protocolo fijo (teléfono 024, 112, hoja SEUP) antes de cualquier otra cosa.
7. **Disclaimer visible** en cada conversación y en cada artículo. Consentimiento explícito de "esto no es consejo médico" en el primer uso.
8. **Sin datos personales.** No se pide nombre, ni fecha de nacimiento exacta, ni se guardan IPs en claro. Las conversaciones se guardan anonimizadas con fines de evaluación (hash de sesión, sin identificadores). Privacidad por diseño: RGPD desde el día 1.

## Reglas de calidad del motor

- **Golden set antes que features.** Antes de tocar el prompt o el retrieval hay un banco de ≥50 preguntas reales de padres con respuesta esperada, fuente esperada y nivel de gravedad esperado (`eval/golden.jsonl`). Cada cambio se mide contra él: precisión de la fuente citada, recall de red flags, tasa de "no sé" correcta. Sin regresión, no se despliega.
- **Prompt versionado.** Los prompts viven en `bot/prompts/*.md` con versión en cabecera. Cada respuesta guarda con qué versión de prompt, modelo e índice se generó.
- **Proveedor LLM intercambiable.** Interfaz `LLMProvider` con implementaciones `deepseek`, `anthropic`, `openai_compatible`. El motor por defecto es DeepSeek V4 Flash (≈ 0,14 $/M entrada, 0,28 $/M salida). Nada de acoplarse a un vendor.
- **Coste por consulta medido**, no estimado. Cada llamada guarda tokens de entrada/salida y coste. Objetivo: < 0,002 € por respuesta.
- **Determinismo donde se pueda.** Triaje por reglas antes que por LLM; calculadoras sin LLM; retrieval reproducible (mismo índice → mismos chunks).

## Stack técnico

- **Lenguaje**: Python 3.12 gestionado por `uv`. NO pip plano.
- **Ingesta**: `pymupdf` (texto y layout), `ocrmypdf`/`tesseract` (idioma `spa`) para los escaneados, `pydantic` para el esquema de chunk.
- **Índice**: SQLite con **FTS5** (búsqueda léxica) + **`sqlite-vec`** (vectores). Embeddings locales con `multilingual-e5-small` vía `sentence-transformers` (cabe en el CX22; sin coste por consulta). Un solo fichero `index/pedibot.db`. Sin Pinecone/Qdrant (los de la v1 se abandonan).
- **LLM**: DeepSeek (API compatible OpenAI, cliente `openai`). Streaming SSE al widget.
- **API**: FastAPI + uvicorn en `127.0.0.1:8601`, detrás de Caddy. Rate limit por IP (`slowapi`), CORS solo al dominio propio.
- **Web**: **Astro** (estático, content collections para artículos, sitemap, RSS, JSON-LD). Sin React salvo el widget del chat (vanilla JS/TS). Fuentes: Inter + JetBrains Mono. Paleta del logo (ver PRD §6.2).
- **Publicación**: script Python que genera artículos (LLM + fuentes) en Markdown con frontmatter, `astro build`, y post a X con `tweepy` (X API de pago por uso: 0,015 $/post sin enlace, 0,20 $/post con enlace).
- **Persistencia operativa**: SQLite `data/pedibot_ops.db` (conversaciones anonimizadas, feedback 👍/👎, costes, outbox Telegram).
- **Logging**: `loguru` JSON. Toda respuesta es auditable a posteriori (qué chunks, qué prompt, qué modelo, qué coste).
- **Test / dev**: `pytest` + `pytest-asyncio`, `hypothesis` en calculadoras, `ruff` (line-length 100), `mypy`. Golden set en `eval/`.
- **Hosting**: VPS Hetzner nuevo (CX22/CX23, Ubuntu 24.04), Caddy con TLS automático, systemd units, backups diarios. Coste objetivo total: **< 15 €/mes** (VPS ≈ 4-5 €, DeepSeek ≈ 1-3 €, X ≈ 1-6 €, dominio).

## Comandos

```bash
make install     # uv sync
make ingest      # troceado + índice completo (idempotente, por hash de fichero)
make eval        # golden set contra el motor actual → informe en eval/reports/
make test        # uv run pytest tests/ -v
make lint        # uv run ruff check src/ tests/ scripts/
make typecheck   # uv run mypy src/
make web-dev     # astro dev (en web/)
make web-build   # astro build → web/dist
make publish     # genera artículo(s) del día + build + X (respeta cola de revisión)
make deploy      # rsync + restart units en el VPS
```

## Convenciones críticas

- **Secretos**: nunca en el repo. `.env` (en `.gitignore`) cargado con `pydantic-settings`. `.env.example` documenta cada variable. ⚠️ El fichero `pass.txt` heredado de la v1 contiene credenciales en claro: está en `.gitignore`, hay que **rotar** todas esas claves (ver STATE.md, deuda D1) y borrarlo.
- **Las fuentes (`FUENTES/`) no se commitean** (122 MB, algunos documentos con copyright editorial). Se commitea el catálogo `FUENTES/CATALOGO.md` y los chunks derivados solo de fuentes con licencia de redistribución permitida. Copia de seguridad de las fuentes fuera del repo.
- **Licencias de fuentes**: cada documento tiene en el catálogo un campo `uso` ∈ {`publico`, `citar_solo`, `excluido`}. `excluido` (p. ej. el tratado de dermatología de Elsevier) no entra en el índice del bot público.
- **Un chunk = una unidad citable**: id estable (`<doc_id>#<seccion>#<n>`), título de sección, página(s), organismo, año, tema, franja de edad. Sin eso no hay cita verificable.
- **Commits pequeños y revisables**. Mensaje en presente; español para docs/infra, inglés para código.
- **Antes de implementar algo nuevo: leer `LESSONS.md`.**
- **TDD estricto** (skill `test-driven-development`) para cualquier feature o bugfix. **`systematic-debugging`** para cualquier bug reproducible. Mismo régimen que en MultiBot.
- **NO inventar métricas.** El dossier de inversores de 2025 cita "100+ usuarios diarios" y "9,8 % CTR": no están medidos en la v2 y no se repiten en la web ni en X hasta que la v2 los mida.

## Reglas de trabajo conmigo (perfil del usuario)

- Soy arquitecto, no programador, y padre reciente. **Español llano**; cada término técnico explicado en una línea.
- **Pregunta antes de asumir** en decisiones de producto o clínicas. Las dudas se acumulan y se envían al final de cada bloque de trabajo.
- Trabajo en Windows con Chrome. Comandos Bash en sintaxis Unix.
- **Las ideas nuevas van a `IDEAS.md`**, no se implementan sobre la marcha. Las decidimos juntos.
- Toda la sensibilidad del tema médico manda: ante la duda, más conservador, más "ve al pediatra".

## Documentos del proyecto

- **[CLAUDE.md](CLAUDE.md)** — este documento. Filosofía y cómo se trabaja.
- **[PRD.md](PRD.md)** — plan canónico: producto, arquitectura por bloque, fases, criterios de salida, web, token, publicación.
- **[STATE.md](STATE.md)** — estado vivo: fase actual, qué hay desplegado, deudas, calendario.
- **[LESSONS.md](LESSONS.md)** — lecciones aprendidas (arranca con las heredadas de la v1 y de MultiBot que aplican aquí).
- **[IDEAS.md](IDEAS.md)** — cuaderno de ideas y mejoras sin decidir.
- **[FUENTES/CATALOGO.md](FUENTES/CATALOGO.md)** — inventario de las 50 fuentes: organismo, año, tema, estado de texto/OCR, licencia de uso.

## Lista "Nunca hacer esto"

- ❌ Responder sin fuente recuperada ("alucinar").
- ❌ Dejar que el LLM calcule una dosis o una edad de vacunación.
- ❌ Ocultar o bajar de posición el aviso de urgencias por "estética".
- ❌ Guardar datos personales de niños o padres.
- ❌ Usar una fuente marcada `excluido` en el índice público.
- ❌ Hardcodear secretos; commitear `pass.txt`, `.env` o `FUENTES/`.
- ❌ Token-gating, staking obligatorio o cualquier requisito web3 para usar el producto.
- ❌ Comprar seguidores, bots de engagement o "trending" pagado para el token o la cuenta de X.
- ❌ Publicar artículos sin la lista de fuentes al pie y sin disclaimer.
- ❌ Desplegar un cambio de prompt/retrieval sin pasar `make eval` sin regresión.
- ❌ Repetir métricas del dossier 2025 como si fueran actuales.
- ❌ Implementar algo sin haber leído `LESSONS.md` primero.
