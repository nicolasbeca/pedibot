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
| CLI | ✅ `pedibot ingest / search / triage / dose / ask [--fake]` | `src/pedibot/cli.py` |
| Tests | ✅ **80 tests verdes**, ruff limpio. | `tests/` |
| Web | 🎨 Boceto v1 (HTML autocontenido, día/noche, chat demo operable con 3 conversaciones guionizadas, pipeline en 3 pasos, herramientas, muro de fuentes, sección del token con libro de cuentas). Sin Astro todavía (no hay Node en el equipo). | `web/mockups/home.html` · artefacto publicado |

## Lo que NO está hecho / conocido

- **Sin LLM real**: falta la clave de DeepSeek en `.env` (`DEEPSEEK_API_KEY`) y confirmar el nombre exacto del modelo V4 Flash (`DEEPSEEK_MODEL`). El pipeline se ha probado solo con `FakeProvider`. ⚠️ En este Windows el AVG mata procesos Python con TLS (L06): la primera prueba real puede necesitar el guard o hacerse desde el VPS.
- **Recuperación de tablas de dosis floja**: la guía AEPap es una tabla y BM25 no la puntúa bien ("how much paracetamol for 12 kg" no sube la tabla pediátrica). Mitigado por el enrutador determinista (pregunta con peso → calculadora sin LLM). Solución de fondo: embeddings (extra `[embeddings]`, e5-small) en F2.
- **Golden set (`eval/golden.jsonl`) vacío** — siguiente tarea de F2.
- **OCR pendiente** de `las_50_principales_consultas.pdf` (sin tesseract local).
- **Fuentes en inglés** se indexan tal cual; la expansión de sinónimos solo va en→es (para una pregunta en español sobre una guía de la OMS en inglés no hay expansión es→en).
- **Sin API HTTP ni widget real**; sin persistencia de conversaciones ni coste; sin Astro; sin VPS.
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

1. Operador: clave de DeepSeek en `.env` → primera respuesta real con `uv run pedibot ask "..."`.
2. `eval/golden.jsonl` (≥50 preguntas) + comando `pedibot eval` con las métricas del PRD §5.5.
3. Embeddings opcionales (e5-small + sqlite-vec) y RRF.
4. API FastAPI + SSE + persistencia anonimizada + coste por consulta.
5. Astro + widget a partir del boceto.

## Calendario

- 2026-08-24 — Arranque v2: docs, catálogo, ingesta completa, triaje, calculadora, motor con verificador, CLI, 80 tests, boceto web v1.
