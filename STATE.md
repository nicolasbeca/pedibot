# STATE.md — estado vivo de PediBot v2

Última actualización: **2026-08-24** (arranque del relanzamiento).

## Fase actual

**F0 — Cimientos.** Repo creado en `D:/Nicolas/pedibot`, documentos base redactados, catálogo de fuentes inventariado. Sin código todavía. Dudas abiertas enviadas al operador (ver §Dudas).

## Qué existe hoy

| Activo | Estado |
|---|---|
| Fuentes PDF | 50 ficheros en `FUENTES/` (122 MB). 48 con texto extraíble; **2 escaneados sin texto** (`Subidos/14_Estreñimiento.pdf`, `Subidos/las_50_principales_consultas.pdf`) → OCR pendiente. 1 con texto corrupto/protegido (`dermatologia_pedi.pdf`, Elsevier) → excluido. Detalle en `FUENTES/CATALOGO.md`. |
| Logos | `LOGOS/` — logo principal (burbuja + bebé + wordmark), variante cara, logo de familia sin fondo |
| Dossier inversores | `25-10-10_Pedibot_ProjectPresentation.pdf` + `.docx` (oct-2025). Métricas de ahí NO se reutilizan sin medir. |
| Cuenta X | @pedibotai, dormida, "unos cientos" de seguidores (no verificado en esta sesión) |
| Correo | pedibot.ai@gmail.com |
| Token PDBT | Base, `0x196A67BA334DbeD501E19BAEc47D217BB2FC15E1`, Virtuals AgentTokenV2, graduado a Uniswap (pool `0x94dfe42f6dc61d1caad037a79214b684f5377784`), FDV ≈ 24,9 k$, 3.938 holders, vol 24 h ≈ 77 $ (24-ago) |
| Web v1 (Wix) | Estado desconocido — duda D-01 |
| Dominio | Desconocido — duda D-01 |
| Credenciales v1 | `pass.txt` con claves en claro (Gmail, Pinecone, Qdrant, Wix, Instagram/Meta). Ignorado por git. **Rotar y borrar** (deuda D1). |
| VPS | Ninguno todavía para PediBot (se creará en F4) |

## Herramientas locales verificadas

- `uv` ✅ (Python 3.12 disponible), `pdftotext` ✅ (poppler en Git Bash), `pdfinfo` ❌, `tesseract`/`ocrmypdf` ❌ (OCR se hará en el VPS o WSL), `pandoc` ❌.
- ⚠️ AVG local inyecta `SSLKEYLOGFILE` y mata procesos Python que abren TLS (lección heredada de MultiBot, L65 allí). Cualquier script local que llame a la API de DeepSeek necesita el mismo `conftest`/guard, o se ejecuta en el VPS.

## Deudas técnicas / tareas abiertas

| Id | Qué | Prioridad |
|---|---|---|
| D1 | Rotar todas las claves de `pass.txt` (Gmail app password, Pinecone, Qdrant, Wix, Meta/Instagram) y borrar el fichero. Las que no se vayan a usar (Pinecone, Qdrant, Wix) → revocar. | **Alta, operador** |
| D2 | OCR de los 2 PDF escaneados | F1 |
| D3 | Decidir licencia/uso de las fuentes marcadas `?` en el catálogo | F0/F1, operador |
| D4 | Confirmar año de publicación de cada hoja SEUP (no consta en el texto extraído) | F1 |
| D5 | Dominio + DNS | F3/F4, operador |
| D6 | Cuenta de desarrollador de X (pago por uso) | F6 |
| D7 | Método de donación (Ko-fi / Stripe / Buy Me a Coffee) | F3, operador |

## Calendario

- 2026-08-24 — Arranque v2. Docs base, catálogo, repo.
- (siguiente) — Respuestas del operador a las dudas → F0 cierre → F1 ingesta.

## Dudas abiertas (enviadas al operador el 2026-08-24)

D-01 dominio/web Wix · D-02 nombre y ubicación del repo/GitHub · D-03 fuentes con licencia dudosa · D-04 idioma/mercado inicial (solo España) · D-05 año de las hojas SEUP · D-06 X de pago · D-07 revisión humana de artículos · D-08 SEO: expectativas · D-09 política de recompras del token · D-10 asesoría legal · D-11 donaciones · D-12 tamaño de VPS y OCR · D-13 proveedor de respaldo del LLM. Texto completo en el mensaje de cierre de la sesión del 24-ago; respuestas se registran aquí.
