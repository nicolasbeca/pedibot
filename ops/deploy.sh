#!/usr/bin/env bash
# Incremental deploy from the PC (Git Bash on Windows: no rsync → tar over ssh).
# Usage: bash ops/deploy.sh <IP> [--no-index] [--no-pull]
# Flow: pull server-generated guides back into the repo → upload code + site sources (+ index)
#       → install deps → units → rebuild the site ON THE SERVER (its content is the source of truth).
set -euo pipefail
IP="${1:?usage: deploy.sh <IP> [--no-index]}"; shift || true
KEY="${SSH_KEY:-$HOME/.ssh/multibot_hetzner_auto}"
SSH="ssh -i $KEY root@$IP"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NO_INDEX=0; NO_PULL=0
for a in "$@"; do case "$a" in --no-index) NO_INDEX=1;; --no-pull) NO_PULL=1;; esac; done
cd "$ROOT"

# The server writes new guides, so normally its web/content wins. --no-pull is for the other
# direction: when the guides were edited HERE (a heading fix across every file, say) and pulling
# first would quietly throw that work away before uploading it back.
if [ $NO_PULL -eq 0 ]; then
  echo "== pull guides generated on the server (web/content)"
  $SSH "cd /opt/pedibot && tar czf - web/content 2>/dev/null" | tar xzf - -C "$ROOT" || true
else
  echo "== skipping the pull: local web/content wins this time"
fi

echo "== code (+ site sources for the rebuild on the server)"
tar czf - --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.mypy_cache' --exclude='.ruff_cache' \
  src config scripts eval pyproject.toml uv.lock Makefile README.md ops web/content \
  web/site/src web/site/public web/site/package.json web/site/package-lock.json \
  web/site/astro.config.mjs web/site/tsconfig.json \
  | $SSH "tar xzf - -C /opt/pedibot"

if [ $NO_INDEX -eq 0 ]; then
  echo "== index ($(du -h index/pedibot.db | cut -f1))"
  scp -q -i "$KEY" index/pedibot.db root@$IP:/opt/pedibot/index/pedibot.db
fi

echo "== install + units + site build"
$SSH bash -s <<'REMOTE'
set -euo pipefail
# Editing a script from Windows can leave CRLF, and bash then fails with the useless
# "set: pipefail: invalid option name". Normalise on arrival instead of debugging it again.
# (tr with an octal code, so this line survives being edited from Windows itself.)
python3 -c "import glob,pathlib;[pathlib.Path(f).write_bytes(pathlib.Path(f).read_bytes().replace(bytes([13]),bytes())) for f in glob.glob('/opt/pedibot/ops/*.sh')]"
chown -R pedibot:pedibot /opt/pedibot
usermod -aG systemd-journal pedibot 2>/dev/null || true
chmod o+x /opt/pedibot /opt/pedibot/web /opt/pedibot/web/site
[ -f /opt/pedibot/.env ] || echo "!! /opt/pedibot/.env missing — copy it first (chmod 600)"
sudo -u pedibot bash -c 'cd /opt/pedibot && ~/.local/bin/uv sync --no-dev -q'
sudo -u pedibot bash -c 'cd /opt/pedibot/web/site && if [ ! -d node_modules ] || ! cmp -s package-lock.json node_modules/.package-lock.json; then npm ci --no-audit --no-fund --silent; fi'
sudo -u pedibot bash -c 'cd /opt/pedibot && ~/.local/bin/uv run --no-dev python scripts/export_catalog.py >/dev/null && cd web/site && SITE_URL=https://pedibot.xyz npm run build 2>&1 | grep -E "page\(s\)|rror"'
chmod -R o+rX /opt/pedibot/web/site/dist
cp /opt/pedibot/ops/systemd/*.service /opt/pedibot/ops/systemd/*.timer /etc/systemd/system/
cp /opt/pedibot/ops/Caddyfile /etc/caddy/Caddyfile
# admin panel password: created once (ops/README), hash kept outside the repo
if [ -f /etc/caddy/admin.hash ]; then sed -i "s|__ADMIN_HASH__|$(cat /etc/caddy/admin.hash)|" /etc/caddy/Caddyfile; else sed -i '/@admin path/,/^	}/d' /etc/caddy/Caddyfile; echo '!! no /etc/caddy/admin.hash: /admin disabled'; fi
systemctl daemon-reload
systemctl enable --now pedibot-api.service pedibot-telegram.service pedibot-acp.service pedibot-watchdog.timer pedibot-backup.timer pedibot-publish.timer pedibot-token.timer pedibot-token-alert.timer pedibot-weekly.timer >/dev/null 2>&1 || true
systemctl restart pedibot-api.service pedibot-telegram.service pedibot-acp.service pedibot-publish.timer
caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1 && systemctl reload caddy
sleep 3
systemctl is-active pedibot-api.service pedibot-telegram.service caddy | tr '\n' ' '; echo
curl -s http://127.0.0.1:8601/api/health && echo
REMOTE
echo "== done: https://pedibot.xyz"
