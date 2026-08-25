# STATE.md — estado vivo de PediBot v2

Última actualización: **2026-08-24, noche** (fin de la primera sesión de construcción).

## Fase actual

**F1 Ingesta — HECHA en local. F2 Motor — en marcha (esqueleto completo, sin LLM real todavía).** Todo corre en local; no hay VPS, dominio ni clave de DeepSeek aún.

## Decisiones del operador (24-ago, respuestas a las dudas D-01…D-13)

| Duda | Decisión |
|---|---|
| D-01 dominio | Nuevo (era pedibotai.com; da igual cuál). Pendiente elegir y comprar. |
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
| Ingesta | ✅ pymupdf → limpieza → secciones (tamaño de fuente/mayúsculas/"¿…?") → chunks (320-480 palabras, fusión de trozos < 40) → clasificación por reglas (`config/taxonomia.yaml`) → JSONL + SQLite FTS5. **47 documentos, 4.792 chunks, 71 de signos de alarma, 278 con posología.** Idempotente por hash. Informe en `index/ingest_report.csv`. | `src/pedibot/ingest/`, `src/pedibot/index/` |
| Catálogo | ✅ 49 fuentes con organismo, título, año, tema, tipo, evidencia, uso, edades. 2 URLs verificadas (SEUP fiebre, acudir_urgencias). | `config/fuentes.yaml` (código) · `FUENTES/CATALOGO.md` (lectura) |
| Triaje | ✅ 31 reglas es/en (`config/red_flags.yaml`), 3 niveles + salud mental, parser de edad, regla dura "<3 meses + fiebre". 34 casos de test (recall y precisión). | `src/pedibot/bot/triage.py` |
| Calculadora de dosis | ✅ paracetamol / ibuprofeno con rangos de la guía AEPap, topes duros, edad/peso mínimos, ml por presentación; test por fila + property-based (hypothesis) de que nunca supera los topes. | `src/pedibot/bot/dose.py` |
| Motor de respuesta | ✅ pipeline completo: triaje → (enrutador de dosis determinista) → (pregunta la edad si falta con fiebre) → recuperación con expansión cross-lingüe (`config/synonyms.yaml` + LLM opcional) → prompt `answer_v1` → **verificador** (citas existentes, ninguna cifra mg/ml sin tabla de dosis) → 1 regeneración → fallback "no tengo fuente" → ensamblado con banner por país (`config/emergency_numbers.yaml`, 18 países). Proveedor LLM intercambiable (`FakeProvider` en tests; DeepSeek vía cliente OpenAI). | `src/pedibot/bot/answer.py`, `retrieval.py`, `llm.py`, `prompts/answer_v1.md` |
| API HTTP | ✅ FastAPI: `POST /api/ask` (JSON: question, country, lang, session), `POST /api/feedback` (👍/👎 solo desde la sesión propietaria), `GET /api/health`, `GET /api/stats`. Registro anonimizado en `data/pedibot_ops.db` (sesión aleatoria, IP solo como hash con sal, tokens/coste/latencia/versión de prompt). Rate limit por IP (20/10 min, 200/día) y **modo degradado** al superar `MAX_DAILY_LLM_USD`: devuelve pasajes sin LLM. CORS solo a `ALLOWED_ORIGINS`. 7 tests con `TestClient`. `pedibot serve` arranca uvicorn en 127.0.0.1:8601. | `src/pedibot/api.py`, `src/pedibot/ops/store.py` |
| Publicación | ✅ Generador de artículos (`publish/articles.py`): plan de 28 temas anclados en hojas para padres, prompt `article_v1` (TITLE/SUMMARY/BODY con 4 secciones fijas, siempre "cuándo ir a urgencias"), **mismo verificador de citas/dosis que el bot** (1 reintento, si falla se descarta), salida Markdown con frontmatter (`web/content/<lang>/<slug>.md`) + texto para X en `publish/queue/x/` (publicación manual). `pedibot publish [--topic] [--lang] [--n] [--fake]`. 5 tests. Sin LLM real todavía. | `src/pedibot/publish/` |
| Web (prototipo servible) | ✅ `web/static/index.html`: el boceto convertido en página real — el chat llama a `/api/ask`, renderiza banner/citas/fuentes con enlace al PDF, 👍/👎 a `/api/feedback`, selector de país (auto por idioma del navegador), sesión en localStorage. La API la sirve en `/` (`pedibot serve` → http://127.0.0.1:8601). Probado end-to-end con `LLM_PROVIDER=fake`. Astro/i18n/artículos siguen pendientes (Node). | `web/static/` |
| CLI | ✅ `pedibot ingest / search / triage / dose / ask [--fake] / eval / serve / publish` | `src/pedibot/cli.py` |
| Golden set + eval | ✅ `eval/golden.jsonl` (60 preguntas es/en con nivel, reglas, documento esperado o ruta esperada) y `pedibot eval` (sin LLM). **Resultado 25-ago: triaje 1,0 · recall red flags 1,0 · precisión 1,0 · reglas 1,0 · fuente en top-3 0,96 · enrutado 1,0.** Informe en `eval/reports/`. Mejoras que lo lograron: pesos por tipo de documento (hoja_padres ×1,6, libro ×0,55), boost por tema de la taxonomía, sinónimos es→es coloquiales, filtro de bibliografías en la ingesta, regla fuera-de-ámbito (sin tema pediátrico → 3 términos o silencio). | `src/pedibot/eval.py` |
| Tests | ✅ **94 tests verdes**, ruff + mypy limpios. | `tests/` |
| Web | 🎨 Boceto v1 (HTML autocontenido, día/noche, chat demo operable con 3 conversaciones guionizadas, pipeline en 3 pasos, herramientas, muro de fuentes, sección del token con libro de cuentas). Sin Astro todavía (no hay Node en el equipo). | `web/mockups/home.html` · artefacto publicado |

## Lo que NO está hecho / conocido

- **Sin LLM real**: falta la clave de DeepSeek en `.env` (`DEEPSEEK_API_KEY`) y confirmar el nombre exacto del modelo V4 Flash (`DEEPSEEK_MODEL`). El pipeline se ha probado solo con `FakeProvider`. ⚠️ En este Windows el AVG mata procesos Python con TLS (L06): la primera prueba real puede necesitar el guard o hacerse desde el VPS.
- **Recuperación de tablas de dosis floja**: la guía AEPap es una tabla y BM25 no la puntúa bien ("how much paracetamol for 12 kg" no sube la tabla pediátrica). Mitigado por el enrutador determinista (pregunta con peso → calculadora sin LLM). Solución de fondo: embeddings (extra `[embeddings]`, e5-small) en F2.
- **El golden set mide triaje/recuperación/enrutado, NO la calidad de la redacción**: fidelidad a la fuente y validez de citas con el LLM real quedan pendientes de la clave de DeepSeek (métricas `citation_validity` y juez de fidelidad del PRD §5.5).
- Fallos abiertos del golden set (2 de 60): g49 "¿cuánto tiene que dormir un niño de 2 años?" (la guía OMS está en inglés y no hay expansión es→en, I-17) y g60 recién nacido que rechaza tomas (fuente AEP no sube; el triaje sí lo marca urgente).
- **OCR pendiente** de `las_50_principales_consultas.pdf` (sin tesseract local).
- **Fuentes en inglés** se indexan tal cual; la expansión de sinónimos solo va en→es (para una pregunta en español sobre una guía de la OMS en inglés no hay expansión es→en).
- **Sin Astro ni VPS**; la web real (i18n, artículos renderizados, SEO) espera a Node. El prototipo estático ya funciona contra la API.
- 7 fuentes con licencia `?` en el catálogo (aceptadas provisionalmente como `citar_solo`).

## Deudas técnicas

| Id | Qué | Prioridad |
|---|---|---|
| D1 | Rotar todas las claves de `pass.txt` (Gmail, Pinecone, Qdrant, Wix, Meta) y borrar el fichero. | **Alta, operador** |
| D2 | OCR de `las_50_principales_consultas.pdf` (VPS/WSL). | F1 tail |
| D3 | Confirmar año de las hojas SEUP. | F1 tail |
| D4 | Instalar Node/Astro para la web real. | F3 |
| D5 | Dominio + DNS. | F4 |

## Próximos pasos (orden propuesto)

1. Operador: clave de DeepSeek en `.env` → primera respuesta real con `uv run pedibot ask "..."` y ampliar `pedibot eval` con `citation_validity` + juez de fidelidad.
2. API FastAPI (`/api/ask`, SSE) + persistencia anonimizada + coste por consulta + rate limit.
3. Embeddings opcionales (e5-small + sqlite-vec) y RRF, solo si el golden set con LLM lo pide.
4. Astro + widget a partir del boceto (requiere Node).

## Calendario

- 2026-08-24 — Arranque v2: docs, catálogo, ingesta completa, triaje, calculadora, motor con verificador, CLI, 80 tests, boceto web v1.
