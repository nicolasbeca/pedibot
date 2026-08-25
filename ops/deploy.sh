#!/usr/bin/env bash
# Incremental deploy from the PC (Git Bash on Windows: no rsync → tar over ssh).
# Usage: bash ops/deploy.sh <IP> [--no-index] [--no-dist]
set -euo pipefail
IP="${1:?usage: deploy.sh <IP> [--no-index] [--no-dist]}"; shift || true
KEY="${SSH_KEY:-$HOME/.ssh/multibot_hetzner_auto}"
SSH="ssh -i $KEY root@$IP"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NO_INDEX=0; NO_DIST=0
for a in "$@"; do case "$a" in --no-index) NO_INDEX=1;; --no-dist) NO_DIST=1;; esac; done
cd "$ROOT"

echo "== code (+ site sources for the daily rebuild on the server)"
tar czf - --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.mypy_cache' --exclude='.ruff_cache' \
  src config scripts eval pyproject.toml uv.lock Makefile README.md ops web/content \
  web/site/src web/site/public web/site/package.json web/site/package-lock.json \
  web/site/astro.config.mjs web/site/tsconfig.json \
  | $SSH "tar xzf - -C /opt/pedibot"

if [ $NO_INDEX -eq 0 ]; then
  echo "== index ($(du -h index/pedibot.db | cut -f1))"
  scp -q -i "$KEY" index/pedibot.db root@$IP:/opt/pedibot/index/pedibot.db
fi
if [ $NO_DIST -eq 0 ]; then
  echo "== web dist"
  $SSH "rm -rf /opt/pedibot/web/site/dist.new && mkdir -p /opt/pedibot/web/site/dist.new"
  tar czf - -C web/site/dist . | $SSH "tar xzf - -C /opt/pedibot/web/site/dist.new && rm -rf /opt/pedibot/web/site/dist && mv /opt/pedibot/web/site/dist.new /opt/pedibot/web/site/dist"
fi

echo "== install + units"
$SSH bash -s <<'REMOTE'
set -euo pipefail
chown -R pedibot:pedibot /opt/pedibot
# Caddy (user caddy) must traverse to dist: home dirs are created 750
chmod o+x /opt/pedibot /opt/pedibot/web /opt/pedibot/web/site && chmod -R o+rX /opt/pedibot/web/site/dist
[ -f /opt/pedibot/.env ] || echo "!! /opt/pedibot/.env missing — copy it first (chmod 600)"
sudo -u pedibot bash -c 'cd /opt/pedibot && ~/.local/bin/uv sync --no-dev -q'
# site deps for the daily rebuild on the server (once, or when package-lock changes)
sudo -u pedibot bash -c 'cd /opt/pedibot/web/site && if [ ! -d node_modules ] || ! cmp -s package-lock.json node_modules/.package-lock.json; then npm ci --no-audit --no-fund --silent; fi'
cp /opt/pedibot/ops/systemd/*.service /opt/pedibot/ops/systemd/*.timer /etc/systemd/system/
cp /opt/pedibot/ops/Caddyfile /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now pedibot-api.service pedibot-telegram.service pedibot-watchdog.timer pedibot-backup.timer pedibot-publish.timer >/dev/null 2>&1 || true
systemctl restart pedibot-api.service pedibot-telegram.service pedibot-publish.timer
caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1 && systemctl reload caddy
sleep 3
systemctl is-active pedibot-api.service pedibot-telegram.service caddy
curl -s http://127.0.0.1:8601/api/health && echo
REMOTE
echo "== done: https://pedibot.xyz/api/health"
