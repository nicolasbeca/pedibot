# LESSONS.md — lecciones aprendidas de PediBot

> Consulta obligada antes de implementar algo nuevo. Se añade una entrada por cada fallo, corrección o sutileza no documentada. Las L0x son heredadas de la v1 (n8n/OpenAI/Wix) y de MultiBot, y siguen vigentes.

## Heredadas de la v1 de PediBot (2025)

- **L01 — No-code sin control del retrieval no sirve para un bot médico.** n8n + OpenAI daba respuestas fluidas pero no había forma de forzar citas verificables ni de medir si el bot acertaba. Un bot que cita fuentes necesita controlar el troceado, el índice y el verificador. → v2 en código propio.
- **L02 — Coste fijo mata a un producto gratuito con poco uso.** Wix Premium + vector DB gestionada + OpenAI eran cuota mensual independientemente del tráfico. → v2: VPS barato, SQLite, LLM de pago por uso.
- **L03 — Las métricas de tracción del dossier no estaban instrumentadas.** "100 usuarios/día" y "9,8 % CTR" salían de Meta Ads y de Wix; no había medición propia ni por consulta. → v2: cada consulta se registra con coste, fuente y feedback; no se publica ninguna cifra que no salga de la DB.
- **L04 — Las credenciales en un `.txt` acaban en cualquier sitio.** `pass.txt` con claves de 5 servicios en claro dentro de la carpeta del proyecto. → `.env` + `.gitignore` + rotación (deuda D1).
- **L05 — Las fuentes hay que catalogarlas ANTES de indexarlas.** En la v1 se subieron PDFs sueltos a un vector store sin organismo, año ni licencia; imposible citar bien y dudas de copyright después. → catálogo con `uso` por documento y esquema de chunk con cita completa.

## Heredadas de MultiBot (aplican aquí)

- **L06 — AVG inyecta `SSLKEYLOGFILE` y mata procesos Python con TLS en el Windows local** (MultiBot L65). Cualquier script local que llame a una API HTTPS puede morir en silencio. → Guard en `conftest.py`; scripts con red se ejecutan en el VPS.
- **L07 — Los wrappers `.sh` a 100644 pierden `+x` en checkout** (MultiBot, go-live 2026-07-06). → Los units de systemd invocan `uv run …` directamente, o el deploy hace `chmod +x`.
- **L08 — `exec` en pipeline ≠ reemplazar al shell** (MultiBot L71): el SIGINT de systemd moría en bash. → Sin pipes en `ExecStart`; logs por journald.
- **L09 — Outbox SQLite para Telegram con retry** funciona y es barato. → Reutilizar el patrón, no reescribir.
- **L10 — Un cambio sin golden set es un cambio sin medir.** MultiBot exige walk-forward y sensibilidad antes de desplegar; aquí el equivalente es `make eval` sin regresión. Sin excepciones.

## Propias de la v2

(Se añaden a partir de F1.)

- **L11 — Las guías en formato tabla se trocean en confeti si se confía en la detección de títulos.** La guía de dosificación AEPap produjo 693 chunks, 422 de ellos de < 15 palabras (cada nombre de fármaco en mayúsculas era "título"). → `merge_small` fusiona los trozos < 40 palabras en el vecino conservando el título dentro del texto ("PARACETAMOL: …"). De 6.981 chunks a 4.792, y solo 10 pequeños.
- **L12 — Nombres de fichero con ñ vienen descompuestos (n + U+0303) desde Windows.** `14_Estreñimiento.pdf` no casaba con el catálogo y pdftotext (Git Bash) devolvía 0 palabras, lo que se interpretó como "escaneado". → normalizar NFC en ambos lados; era un PDF con texto.
- **L13 — YAML convierte `112` o `911` en enteros.** Un `re.escape(112)` revienta con un TypeError críptico dentro de `re`. → `str(k)` siempre en listas de palabras clave; o entrecomillar en el YAML.
- **L14 — `\b` dentro de un heredoc de Python no crudo es un BACKSPACE.** Al generar código con `python - <<'EOF'` y cadenas normales, `"\b"` se escribe como `\b` (0x08) invisible en el fichero y la regex deja de casar sin error. → escribir regex siempre con `r"..."` en el fichero final y comprobar `'\x08' not in text` tras generar código.
- **L15 — BM25 no encuentra tablas.** "how much paracetamol for 12 kg" no sube la tabla pediátrica de la AEPap aunque exista. → las preguntas de dosis con peso van por un enrutador determinista a la calculadora (sin LLM); los embeddings quedan para F2.
- **L16 — El modelo repite las instrucciones del prompt como si fueran de la fuente.** El juez de fidelidad (25-ago, 54 respuestas) dio 74 % "fiel"; 6 de las 8 "infieles" eran frases como "debe ser evaluado hoy" o "no le dé medicación" que venían de NUESTRO contexto de edad/banner, no de un pasaje citado. Verdaderas y seguras, pero no citables → el juez las marca. → Cuando una regla de triaje dispara, se inyecta el chunk de signos de alarma de SU fuente (`seup_acudir_urgencias`, etc.) como primer pasaje, y el prompt pide citar el pasaje [WARNING SIGNS] o, si no existe, decirlo sin atribuirlo a ningún organismo.
- **L17 — El boost de "signos de alarma" contamina entre temas.** Con una pregunta de fiebre, el chunk "cuándo consultar" de la hoja de GOLPE DE CALOR subía (contiene "fiebre") y el modelo atribuía sus umbrales (39 °C) a la hoja de fiebre. → el boost de red flag solo se aplica a chunks del mismo tema que la pregunta.
