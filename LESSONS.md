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
