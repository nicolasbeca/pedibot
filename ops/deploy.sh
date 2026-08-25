#!/usr/bin/env bash
# Incremental deploy from the PC. Usage: bash ops/deploy.sh <IP> [--no-index] [--no-dist]
# Uploads: code (src, config, scripts, pyproject, uv.lock), index/pedibot.db, web/site/dist, ops units.
set -euo pipefail
IP="${1:?usage: deploy.sh <IP> [--no-index] [--no-dist]}"; shift || true
KEY="${SSH_KEY:-$HOME/.ssh/multibot_hetzner_auto}"
SSH="ssh -i $KEY root@$IP"
RS="rsync -az --delete -e \"ssh -i $KEY\""
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NO_INDEX=0; NO_DIST=0
for a in "$@"; do case "$a" in --no-index) NO_INDEX=1;; --no-dist) NO_DIST=1;; esac; done

echo "== code"
eval $RS --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.mypy_cache' --exclude '.ruff_cache' \
  "$ROOT/src" "$ROOT/config" "$ROOT/scripts" "$ROOT/eval" "$ROOT/pyproject.toml" "$ROOT/uv.lock" "$ROOT/Makefile" "$ROOT/README.md" "$ROOT/ops" \
  root@$IP:/opt/pedibot/
eval $RS "$ROOT/web/content" root@$IP:/opt/pedibot/web/

if [ $NO_INDEX -eq 0 ]; then
  echo "== index (30 MB)"; eval rsync -az -e "\"ssh -i $KEY\"" "$ROOT/index/pedibot.db" root@$IP:/opt/pedibot/index/pedibot.db
fi
if [ $NO_DIST -eq 0 ]; then
  echo "== web dist"; eval $RS "$ROOT/web/site/dist/" root@$IP:/opt/pedibot/web/site/dist/
fi

echo "== install + units"
$SSH bash -s <<'REMOTE'
set -euo pipefail
chown -R pedibot:pedibot /opt/pedibot
[ -f /opt/pedibot/.env ] || { echo "!! /opt/pedibot/.env missing — copy it first (chmod 600)"; }
sudo -u pedibot bash -c 'cd /opt/pedibot && ~/.local/bin/uv sync --no-dev -q'
cp /opt/pedibot/ops/systemd/*.service /opt/pedibot/ops/systemd/*.timer /etc/systemd/system/
cp /opt/pedibot/ops/Caddyfile /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now pedibot-api.service pedibot-telegram.service pedibot-watchdog.timer pedibot-backup.timer pedibot-publish.timer
systemctl restart pedibot-api.service
caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy
sleep 2
curl -s http://127.0.0.1:8601/api/health && echo
REMOTE
echo "== done: https://pedibot.xyz/api/health"
