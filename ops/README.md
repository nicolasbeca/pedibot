# ops/ — despliegue de PediBot en Hetzner (F4)

Patrón heredado de MultiBot: un VPS Ubuntu 24.04, usuario de servicio, `uv`, systemd, Caddy con TLS automático, backups diarios y watchdog con avisos por Telegram. Todo en `/opt/pedibot`.

## Paso a paso (cuando exista el servidor)

1. **Crear el VPS** en Hetzner Cloud: CX22 (2 vCPU, 4 GB) o CX23, Ubuntu 24.04, ubicación Nuremberg o Helsinki, con la clave SSH `multibot_hetzner_auto`. Anotar la IP.
2. **DNS en Cloudflare**: registro `A` `pedibot.xyz` → IP del VPS y `A` `www` → misma IP. **Proxy desactivado (nube gris)** al principio para que Caddy obtenga el certificado; después se puede activar el proxy naranja (entonces Caddy debe usar el certificado de origen de Cloudflare o modo "Full (strict)" con el certificado de Let's Encrypt — lo simple: dejar gris).
3. **Bootstrap** (desde el PC, con la IP): `bash ops/bootstrap.sh <IP>` — instala paquetes, crea el usuario `pedibot`, clona/sincroniza el repo, instala `uv`, Node, Caddy, y los units.
4. **Secretos**: copiar `.env` a `/opt/pedibot/.env` (600, propietario `pedibot`). Contiene `DEEPSEEK_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ALLOWED_ORIGINS=https://pedibot.xyz,https://www.pedibot.xyz`, `SITE_URL=https://pedibot.xyz`.
5. **Fuentes**: subir `FUENTES/` (rsync) y ejecutar `make ingest` en el VPS (o subir `index/pedibot.db` ya construido — 30 MB — que es lo que hace `ops/deploy.sh`).
6. **Web**: `make web-build` en el VPS (Node) o subir `web/site/dist` desde el PC (lo hace `ops/deploy.sh`).
7. `systemctl enable --now pedibot-api pedibot-watchdog.timer pedibot-backup.timer pedibot-publish.timer` y comprobar `https://pedibot.xyz/api/health`.

## Ficheros

| Fichero | Qué |
|---|---|
| `bootstrap.sh` | Instalación inicial del VPS (una vez). |
| `deploy.sh` | Despliegue incremental desde el PC: rsync del código, `index/pedibot.db`, `web/site/dist`; `uv sync`; restart de la API. |
| `Caddyfile` | `pedibot.xyz` → estático `dist` + `/api/*` y `/a/*` → `127.0.0.1:8601`. Cabeceras de seguridad. |
| `systemd/pedibot-api.service` | uvicorn en 127.0.0.1:8601 como usuario `pedibot`. |
| `systemd/pedibot-telegram.service` | El mismo motor por Telegram (long polling, `pedibot telegram`), token `TELEGRAM_PUBLIC_BOT_TOKEN`. |
| `systemd/pedibot-watchdog.{service,timer}` | Cada 10 min: `/api/health`, saldo DeepSeek (< 20 % → CRITICAL), disco, coste del día. Avisa por Telegram. |
| `systemd/pedibot-backup.{service,timer}` | Diario 05:30: `data/pedibot_ops.db` + `web/content/` a `/opt/pedibot/backups/` (30 días). |
| `systemd/pedibot-publish.{service,timer}` | **Diario 07:00 UTC**: `pedibot publish --n 1` en EN y ES (+ Bluesky/canal Telegram si hay credenciales) + build de la web en el servidor. |
| `watchdog.py` | Lógica del watchdog (usa `pedibot balance` y el outbox de Telegram). |

## Costes

CX22 ≈ 4,35 €/mes. Sin IPv4 adicional. Backups off-site: pendiente (Storage Box 3,81 €/mes o B2).
