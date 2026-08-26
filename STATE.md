# STATE.md — estado vivo de PediBot v2

Última actualización: **2026-08-25, 16:30** — **EN PRODUCCIÓN en https://pedibot.xyz**.

## Fase actual

**F1–F3 HECHAS. F4 Despliegue — HECHO el 25-ago**: VPS Hetzner `46.225.74.13` (1 vCPU / 2 GB, Ubuntu 24.04, hostname `pedibot`), Caddy con certificado Let's Encrypt para `pedibot.xyz` (DNS en Cloudflare, nube gris), units `pedibot-api`, `pedibot-telegram` (@Pedichat_bot), watchdog cada 10 min (alertas a @Pedibot_ops_bot), backup 05:30, guías lunes/jueves 07:00. Despliegue desde el PC: `bash ops/deploy.sh 46.225.74.13` (tar sobre SSH; la web se construye en el PC con `make web-build`). **Siguiente: F5 beta cerrada** (10-20 padres, revisar TODAS las conversaciones).

Para probarlo en el navegador: `uv run pedibot serve` y abrir http://127.0.0.1:8601 (con `LLM_PROVIDER=fake` en `.env` funciona sin clave, pero las respuestas serán el fallback "no tengo fuente"; con `DEEPSEEK_API_KEY` responde de verdad).

## Decisiones del operador (24-ago, respuestas a las dudas D-01…D-13)

| Duda | Decisión |
|---|---|
| D-01 dominio | **pedibot.xyz** — comprado el 25-ago, DNS en Cloudflare (en registro). |
| D-02 repo | Solo local por ahora; a GitHub más adelante. |
| D-03 licencias | Propuesta aceptada: obras de referencia = `citar_solo`; Elsevier excluido. |
| D-04 mercado | **Internacional desde el inicio. Inglés primero, español después, otros idiomas más tarde.** |
| D-05 año hojas SEUP | Buscarlo nosotros. En seup.org la serie cuelga de `wp-content/uploads/2025/05/` (subida mayo 2025); el año de edición no consta en el texto → citamos sin año hasta confirmarlo. |
| D-06 X | Creía que había API gratis; **no la hay desde feb-2026** (pago por uso, 0,20 $/post con enlace) → **X descartado**; el generador deja el texto listo para pegar a mano. |
| D-07 artículos | **Auto-publicar** (con verificador de citas como único filtro). |
| D-08 SEO | Sin datos previos; se parte de cero con Search Console. |
| D-09 token | La política del PRD §9 es punto de partida. El operador tiene muchos PDBT. |
| D-10 legal | Sin asesoría; disclaimer genérico. |
| D-11 donaciones | No por ahora; el token es la vía de financiación. |
| D-12 VPS | Más adelante; ahora todo local. |
| D-13 LLM | DeepSeek (el más barato). |

## Qué hay construido (commit de esta sesión)

| Bloque | Estado | Dónde |
|---|---|---|
| Ingesta | ✅ PDF (pymupdf) **y HTML** (BeautifulSoup: `main`/`#topic-summary`, sin nav/pies/formularios; los `h2/h3` hacen de títulos) → limpieza → secciones (tamaño de fuente/mayúsculas/"¿…?") → chunks (320-480 palabras, fusión de trozos < 40) → clasificación por reglas (`config/taxonomia.yaml`) → JSONL + SQLite FTS5. **210 documentos, ~5.500 chunks, 278 con posología** (antes de las fuentes web: 47 docs / 4.792 chunks). Idempotente por hash. Informe en `index/ingest_report.csv`. | `src/pedibot/ingest/`, `src/pedibot/index/` |
| Catálogo | ✅ **212 fuentes**: 49 PDF (`config/fuentes.yaml`) + **163 páginas web públicas internacionales** descargadas el 25-ago (`config/fuentes_web.yaml`, generado por `scripts/fetch_web_sources.py`): NHS 57 (OGL v3), MedlinePlus 50 EN + 24 ES (dominio público, solo el resumen), CDC 19 (dominio público), OMS 8 EN + 6 ES (CC BY-NC-SA). Descartadas por licencia: Raising Children, HealthyChildren/AAP, KidsHealth. Detalle y licencias en `FUENTES/CATALOGO.md`. | `config/fuentes*.yaml` · `FUENTES/CATALOGO.md` |
| Triaje | ✅ 31 reglas es/en (`config/red_flags.yaml`), 3 niveles + salud mental, parser de edad, regla dura "<3 meses + fiebre". 34 casos de test (recall y precisión). | `src/pedibot/bot/triage.py` |
| Calculadora de dosis | ✅ paracetamol / ibuprofeno con rangos de la guía AEPap, topes duros, edad/peso mínimos, ml por presentación; test por fila + property-based (hypothesis) de que nunca supera los topes. | `src/pedibot/bot/dose.py` |
| Motor de respuesta | ✅ pipeline completo: triaje → (enrutador de dosis determinista) → (pregunta la edad si falta con fiebre) → recuperación con expansión cross-lingüe (`config/synonyms.yaml` + LLM opcional) → prompt `answer_v1` → **verificador** (citas existentes, ninguna cifra mg/ml sin tabla de dosis) → 1 regeneración → fallback "no tengo fuente" → ensamblado con banner por país (`config/emergency_numbers.yaml`, 18 países). Proveedor LLM intercambiable (`FakeProvider` en tests; DeepSeek vía cliente OpenAI). | `src/pedibot/bot/answer.py`, `retrieval.py`, `llm.py`, `prompts/answer_v1.md` |
| API HTTP | ✅ FastAPI: `POST /api/ask` (JSON: question, country, lang, session), `POST /api/feedback` (👍/👎 solo desde la sesión propietaria), `GET /api/health`, `GET /api/stats`. Registro anonimizado en `data/pedibot_ops.db` (sesión aleatoria, IP solo como hash con sal, tokens/coste/latencia/versión de prompt). Rate limit por IP (20/10 min, 200/día) y **modo degradado** al superar `MAX_DAILY_LLM_USD`: devuelve pasajes sin LLM. CORS solo a `ALLOWED_ORIGINS`. 7 tests con `TestClient`. `pedibot serve` arranca uvicorn en 127.0.0.1:8601. | `src/pedibot/api.py`, `src/pedibot/ops/store.py` |
| Publicación | ✅ Generador de artículos (`publish/articles.py`): plan de **73 temas** (28 SEUP + 45 anclados en NHS/MedlinePlus/CDC/OMS, 25-ago) anclados en hojas para padres, prompt `article_v1` (TITLE/SUMMARY/BODY con 4 secciones fijas, siempre "cuándo ir a urgencias"), **mismo verificador de citas/dosis que el bot** (1 reintento, si falla se descarta), salida Markdown con frontmatter (`web/content/<lang>/<slug>.md`) + texto para X en `publish/queue/x/`. **Sindicación automática** (`publish/social.py`, 25-ago): Bluesky y canal de Telegram (gratis) si hay credenciales; X solo con `X_POST_ENABLED=true` (pago por uso, ~0,20 $/post con enlace). **Cadencia en producción: diaria 07:00 UTC, 1 EN + 1 ES.** RSS: `/rss.xml` y `/es/rss.xml`. `pedibot publish [--topic] [--lang] [--n] [--fake]`. 5 tests. Sin LLM real todavía. | `src/pedibot/publish/` |
| Web (prototipo servible) | ✅ `web/static/index.html`: el boceto convertido en página real — el chat llama a `/api/ask`, renderiza banner/citas/fuentes con enlace al PDF, 👍/👎 a `/api/feedback`, selector de país (auto por idioma del navegador), sesión en localStorage. La API la sirve en `/` (`pedibot serve` → http://127.0.0.1:8601). Probado end-to-end con `LLM_PROVIDER=fake`. Astro/i18n/artículos siguen pendientes (Node). | `web/static/` |
| Memoria de conversación (I-31) | ✅ `Engine.ask(..., history=[...])`: ventana de 6 turnos; la edad dicha en un turno anterior cuenta (regla <3 meses incluida); los síntomas viejos NO re-disparan el banner; la recuperación de un seguimiento corto ("¿y si además vomita?") usa también el mensaje anterior; el prompt recibe CONVERSATION SO FAR. Turnos por sesión en `data/pedibot_ops.db` (24 h). Probado con el modelo real: el seguimiento recupera la hoja de vómitos y mantiene los 4 años. | `bot/answer.py`, `ops/store.py`, `api.py` |
| Kit de despliegue (F4) | ✅ `ops/`: `bootstrap.sh` (paquetes, Caddy, Node, usuario `pedibot`, uv, ufw), `deploy.sh` (rsync código + índice + dist, `uv sync`, units, Caddy reload), `Caddyfile` (pedibot.xyz, cabeceras, `/api/*` y `/a/*` → 8601), units systemd (`pedibot-api`, watchdog 10 min con **aviso de saldo DeepSeek <20 % por Telegram**, backup 05:30, publish lunes/jueves 07:00). Paso a paso en `ops/README.md`. Sin probar hasta tener el VPS. | `ops/` |
| Telegram (chatbot público) | ✅ `src/pedibot/telegram_bot.py`: el mismo `Engine`, sesión = hash del chat (sin datos personales), memoria por chat, botones 👍/👎, `/country`, `/lang`, `/help`. `pedibot telegram` (long polling) + `ops/systemd/pedibot-telegram.service`. Necesita `TELEGRAM_PUBLIC_BOT_TOKEN` (bot NUEVO de @BotFather; el de alertas es otro: `TELEGRAM_BOT_TOKEN`). 3 tests sin red. | `telegram_bot.py` |
| Suero oral (I-30) | ✅ `bot/ors.py`: pauta por edad tomada del **prospecto AEMPS de Sueroral Hiposódico** (CIMA 59877: lactante >1 mes 1–1,5× la toma; ≥1 año ~200 ml por deposición en tandas de 25–30 ml cada 10–15 min) y de la hoja SEUP de vómitos (5–10 ml cada 10 min). `/api/ors`, sección en `/dose`. El prospecto está en el índice. El PIL de Dioralyte (emc) se descartó: la página se renderiza con JS y no capturó texto. | `bot/ors.py` |
| Herramientas deterministas nuevas (26-ago) | ✅ **Vacunas** ES/GB/US (`config/vaccines.yaml` transcrito del Ministerio 2025, NHS y CDC 2025; `/vaccines`, `/api/vaccines`; el chat enruta preguntas de vacunas con país conocido). **Foto** de signos de alarma (`bot/photo.py`, `deepseek-v4-flash-vision-exp`, ≈0,0001 $/foto; solo petequias/cianosis/hinchazón; probado en producción). **Aclaración** (mensaje vago que menciona al niño → 7 opciones). **Avisos** de salud pública (`ops/alerts_fetch.py` → banner en la home). **Panel `/admin`** con basic auth (métricas 7/30/90 d, PDBT, conversaciones, flag). **Guías comparativas** y **calendario estacional** en publish. **`/api/agent/ask`** para ACP (`AGENT_API_KEYS`). | ver IDEAS «Lote del 26-ago» |
| CLI | ✅ `pedibot ingest / search / triage / dose / ask [--fake] / eval [--llm --judge] / serve / publish / balance` | `src/pedibot/cli.py` |
| Golden set + eval | ✅ `eval/golden.jsonl` (60 preguntas es/en con nivel, reglas, documento esperado o ruta esperada) y `pedibot eval` (sin LLM). **Resultado 25-ago: triaje 1,0 · recall red flags 1,0 · precisión 1,0 · reglas 1,0 · fuente en top-3 0,96 · enrutado 1,0.** Informe en `eval/reports/`. Mejoras que lo lograron: pesos por tipo de documento (hoja_padres ×1,6, libro ×0,55), boost por tema de la taxonomía, sinónimos es→es coloquiales, filtro de bibliografías en la ingesta, regla fuera-de-ámbito (sin tema pediátrico → 3 términos o silencio). | `src/pedibot/eval.py` |
| Tests | ✅ **147 tests verdes**, ruff + mypy limpios. | `tests/` |
| Web Astro (F3) | ✅ **Node 24 instalado el 25-ago (winget, autorizado por el operador)**. Sitio en `web/site` (Astro 7 + sitemap): i18n `en` (raíz) / `es` (`/es`), layout con canonical/hreflang/OpenGraph/JSON-LD (Organization, WebApplication, MedicalWebPage), tema **siempre claro** (noche solo con el botón; el ajuste del navegador se ignora — decisión operador), tokens del boceto v2. Páginas: home chat-first (widget real contra `/api/ask` con chips de país/edad/peso enviados en el mensaje, sesión y país en localStorage, 👍/👎, `?q=` precarga), `/dose` (calculadora contra `/api/dose` con marcas), `/sources` (tabla desde `config/fuentes.yaml` vía `scripts/export_catalog.py`), `/guides` + `/guides/<slug>` (colección desde `web/content/<lang>/*.md`). **Primeras 2 guías reales generadas con DeepSeek** (fiebre EN+ES, 0,0006 $ cada una). `make web-build` → `web/site/dist`, que la API sirve en `/` cuando existe (probado: 10 páginas, chat real OK). | `web/site/`, `web/content/` |
| Boceto | 🎨 v1 y v2 (`web/mockups/`), v2 = dirección aprobada. | artefactos publicados |

## LLM real (desde el 25-ago)

- Clave en `.env` (el operador la dejó como `.env.txt`; renombrada). Saldo cargado: **10 USD el 25-ago**. `uv run pedibot balance --initial-usd 10` consulta el saldo real y avisa por debajo del 20 % (exit 2) — **pendiente cablearlo al watchdog/Telegram en F4**; mientras, se comprueba a mano en cada sesión.
- Modelo verificado: `deepseek-v4-flash` (también existen `deepseek-v4-pro` y `-vision-exp`). **V4 razona por defecto**: los tokens de razonamiento se facturan como salida y consumen `max_tokens` (la primera respuesta se cortó a 900 tokens). Desactivado con `extra_body={"thinking": {"type": "disabled"}}`. Coste medido: **0,0003-0,0005 $ por respuesta** (≈ 2.000-3.000 tokens de entrada, 180-240 de salida), 8-12 s de latencia.
- Dos correcciones que solo se vieron con el modelo real: (1) respondía en el idioma de las fuentes (español) a preguntas en inglés → línea `ANSWER LANGUAGE` explícita; (2) a un bebé de 2 meses con fiebre le sugería "paracetamol o ibuprofeno a la dosis de su pediatra" copiando la hoja genérica → contexto de edad en el prompt (`<3 meses: nada de medicación en casa`, `<6 meses: sin ibuprofeno`). Con eso la respuesta pasa a "no le dé ningún medicamento sin indicación médica; debe ser evaluado hoy".
- El AVG **no** mató la conexión TLS en este Windows (L06 no aplicó aquí).
- **`pedibot eval --llm` (25-ago, 55 preguntas del golden set con `deepseek-v4-flash`)**: 54 redactadas (1 fuera de ámbito → silencio correcto), **validez de citas 1,0** (ninguna cita inventada, ninguna cifra de dosis fuera de tabla), **0 regeneraciones**, 100 % con fuentes, coste total **0,0198 $** (0,00037 $/respuesta), latencia p95 3,9 s. Informe: `eval/reports/eval_llm_2026-08-25.json`. Saldo tras la prueba: 9,98 $. - **Juez de fidelidad (`eval --llm --judge`, 25-ago, 1.ª pasada, prompt v2)**: 40/54 "fiel" (**74 %**), 6 "minor_issue", 8 "unfaithful". Diagnóstico: 6 de las 8 eran frases de seguridad que el modelo copió de nuestro contexto de edad/banner sin pasaje que citar (L16); 2 eran contaminación del boost de signos de alarma entre temas (umbrales de la hoja de golpe de calor atribuidos a la de fiebre, L17); 1 (g20) inventó el momento de la triple vírica. Correcciones aplicadas (inyección del chunk de la regla como pasaje citable + boost por tema). **2.ª pasada: 78 %** (42/54), validez de citas 1,0, 0,036 $ la pasada. Restos: g58 (golpe de calor sigue colándose en fiebre → penalización fuera de tema añadida), g13 (diarrea recuperaba pasajes clínicos, no la hoja SEUP → sinónimo diarrea→gastroenteritis), g20 (inventa fechas de vacunas → argumento para la herramienta tabulada I-19), y varios "infieles" discutibles del juez ("llama a emergencias" vs "acude a urgencias"). El juez es una **señal ruidosa**: sirve para encontrar clases de fallo, no como cifra de calidad; la lectura humana de respuestas sigue siendo el gate de la beta (F5). Coste con juez: 0,00066 $/respuesta.
- **Prompt `answer_v2`** (25-ago): la fuente se nombra en la frase ("According to the SEUP…") además del [n]; tono calmado; regla explícita sobre instrucciones de seguridad sin pasaje.
- **Calculadora con marcas** (`config/drugs.yaml`): 20 marcas de 12 países para paracetamol/ibuprofeno con su concentración; `/api/dose`, `/api/drugs`; el chat enruta "how much Calpol for 14 kg" a la calculadora.

## Políticas de comunicación (decisiones del operador)

- **Costes e interioridades son privados** (25-ago): la web y los textos públicos dicen que mantener PediBot cuesta dinero y que el token lo financia, pero **no cifras** (servidor, coste por respuesta, saldo) ni detalles de infraestructura. El «libro de cuentas» público se retiró; en su lugar, tarjeta «qué financia el token» y novedades periódicas de producto. Los informes con cifras van solo al Telegram del operador.
- **Respuestas sin bloque de fuentes** (25-ago): el organismo se nombra en la frase; sin enlaces, títulos ni marcadores. Máximo ~110 palabras.

## Lo que NO está hecho / conocido

- **Recuperación de tablas de dosis floja**: la guía AEPap es una tabla y BM25 no la puntúa bien ("how much paracetamol for 12 kg" no sube la tabla pediátrica). Mitigado por el enrutador determinista (pregunta con peso → calculadora sin LLM). Solución de fondo: embeddings (extra `[embeddings]`, e5-small) en F2.
- **El golden set mide triaje/recuperación/enrutado, NO la calidad de la redacción**: fidelidad a la fuente y validez de citas con el LLM real quedan pendientes de la clave de DeepSeek (métricas `citation_validity` y juez de fidelidad del PRD §5.5).
- Fallos abiertos del golden set (2 de 60): g49 "¿cuánto tiene que dormir un niño de 2 años?" (la guía OMS está en inglés y no hay expansión es→en, I-17) y g60 recién nacido que rechaza tomas (fuente AEP no sube; el triaje sí lo marca urgente).
- **OCR pendiente** de `las_50_principales_consultas.pdf` (sin tesseract local).
- **Fuentes en inglés** se indexan tal cual; la expansión de sinónimos solo va en→es (para una pregunta en español sobre una guía de la OMS en inglés no hay expansión es→en).
- **Producción**: el servidor es de 1 vCPU/2 GB (no CX22): suficiente para API+bot; la web se construye en el PC. Cloudflare en modo DNS-only; si se activa el proxy naranja hay que poner SSL «Full (strict)». De las ideas aceptadas faltan: T-06 Virtuals ACP (investigado; tras F4), W-06 pediatras revisores (contactos). Telegram: falta el token del bot nuevo. Hechas el 25-ago: diario+recordatorio, checklist urgencias, explícaselo a mi hijo, voz, mapa, temporada, compartir, 685 páginas de dosis SEO por idioma, /support, /legal.
- 7 fuentes con licencia `?` en el catálogo (aceptadas provisionalmente como `citar_solo`).

## Deudas técnicas

| Id | Qué | Prioridad |
|---|---|---|
| D1 | Rotar todas las claves de `pass.txt` (Gmail, Pinecone, Qdrant, Wix, Meta) y borrar el fichero. | **Alta, operador** |
| D2 | OCR de `las_50_principales_consultas.pdf` (VPS/WSL). | F1 tail |
| D3 | Confirmar año de las hojas SEUP. | F1 tail |
| D4 | Instalar Node/Astro para la web real. | F3 |
| D5 | ~~Dominio~~ pedibot.xyz comprado; DNS Cloudflare → apuntar al VPS en F4. | F4 |

## Próximos pasos (orden propuesto)

1. Operador: clave de DeepSeek en `.env` → primera respuesta real con `uv run pedibot ask "..."` y ampliar `pedibot eval` con `citation_validity` + juez de fidelidad.
2. API FastAPI (`/api/ask`, SSE) + persistencia anonimizada + coste por consulta + rate limit.
3. Embeddings opcionales (e5-small + sqlite-vec) y RRF, solo si el golden set con LLM lo pide.
4. Astro + widget a partir del boceto (requiere Node).

## Calendario

- 2026-08-24 — Arranque v2: docs, catálogo, ingesta completa, triaje, calculadora, motor con verificador, CLI, 80 tests, boceto web v1.
