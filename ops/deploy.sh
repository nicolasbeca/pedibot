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
# tar adds and overwrites; it never deletes. So a guide the server removed came back from the
# local copy on the next deploy, and one removed here came back from the server. Whichever side
# is the source of truth mirrors, and says what it drops — this deletes written work.
if [ $NO_PULL -eq 0 ]; then
  echo "== pull guides generated on the server (web/content)"
  $SSH "cd /opt/pedibot && tar czf - web/content 2>/dev/null" | tar xzf - -C "$ROOT" || true
  $SSH "cd /opt/pedibot && ls web/content/*/*.md 2>/dev/null" | tr -d '\r' | sort > /tmp/pedibot_remote_guides
  if [ -s /tmp/pedibot_remote_guides ]; then
    (cd "$ROOT" && ls web/content/*/*.md 2>/dev/null | sort) > /tmp/pedibot_local_guides
    comm -23 /tmp/pedibot_local_guides /tmp/pedibot_remote_guides | while read -r f; do
      echo "   - retirando local (ya no está en el servidor): $f"; rm -f "$ROOT/$f"
    done
  fi
  # The ops database lives ONLY on the server: the daily backup writes beside it, on the same
  # disk, so it survives a mistake and not the machine. 384 KB holding every question ever asked.
  # Brought down next to the guides — not a schedule, but it makes the copy exist twice.
  mkdir -p "$ROOT/backups"
  if $SSH "test -f /opt/pedibot/data/pedibot_ops.db"; then
    scp -q -i "$KEY" root@$IP:/opt/pedibot/data/pedibot_ops.db \
      "$ROOT/backups/pedibot_ops_$(date +%F).db" && \
      echo "   copia local de la base de operaciones: backups/pedibot_ops_$(date +%F).db"
    # thirty days of daily copies of a 384 KB file is 11 MB; older ones go
    find "$ROOT/backups" -name 'pedibot_ops_*.db' -mtime +30 -delete 2>/dev/null || true
  fi
else
  echo "== skipping the pull: local web/content wins this time"
  (cd "$ROOT" && ls web/content/*/*.md 2>/dev/null | sort) > /tmp/pedibot_local_guides
  if [ -s /tmp/pedibot_local_guides ]; then
    $SSH "cd /opt/pedibot && ls web/content/*/*.md 2>/dev/null" | tr -d '\r' | sort > /tmp/pedibot_remote_guides
    comm -13 /tmp/pedibot_local_guides /tmp/pedibot_remote_guides | while read -r f; do
      echo "   - retirando del servidor (ya no está aquí): $f"; $SSH "rm -f /opt/pedibot/$f"
    done
  fi
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
# A unit deleted from the repo has to disappear from the server too. The upload does not
# delete, so removing pedibot-publish.* from git left it running and a deploy reinstalled it
# from the copy still sitting in /opt/pedibot/ops/systemd. Prune first, then copy.
for f in /etc/systemd/system/pedibot-*.service /etc/systemd/system/pedibot-*.timer; do
  [ -e "$f" ] || continue
  if [ ! -e "/opt/pedibot/ops/systemd/$(basename "$f")" ]; then
    echo "== retirando unidad que ya no está en el repositorio: $(basename "$f")"
    systemctl disable --now "$(basename "$f")" >/dev/null 2>&1 || true
    rm -f "$f"
  fi
done
cp /opt/pedibot/ops/systemd/*.service /opt/pedibot/ops/systemd/*.timer /etc/systemd/system/
cp /opt/pedibot/ops/Caddyfile /etc/caddy/Caddyfile
# admin panel password: created once (ops/README), hash kept outside the repo
if [ -f /etc/caddy/admin.hash ]; then sed -i "s|__ADMIN_HASH__|$(cat /etc/caddy/admin.hash)|" /etc/caddy/Caddyfile; else sed -i '/@admin path/,/^	}/d' /etc/caddy/Caddyfile; echo '!! no /etc/caddy/admin.hash: /admin disabled'; fi
systemctl daemon-reload
systemctl enable --now pedibot-api.service pedibot-telegram.service pedibot-acp.service pedibot-watchdog.timer pedibot-backup.timer pedibot-token.timer pedibot-token-alert.timer pedibot-weekly.timer pedibot-daily.timer pedibot-tweets.timer pedibot-indexnow.timer >/dev/null 2>&1 || true
systemctl restart pedibot-api.service pedibot-telegram.service pedibot-acp.service
caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1 && systemctl reload caddy
systemctl is-active pedibot-api.service pedibot-telegram.service caddy | tr '\n' ' '; echo
# The API was restarted a moment ago and takes a few seconds to open its port. A single curl
# after `sleep 3` raced it: the deploy did everything right and still exited 7 (curl: could not
# connect), which reads exactly like a failed deploy. Wait for it before calling it broken.
OUT=""
for _ in $(seq 1 20); do
  OUT=$(curl -s --max-time 3 http://127.0.0.1:8601/api/health || true)
  if [ -n "$OUT" ]; then break; fi
  sleep 1
done
if [ -n "$OUT" ]; then echo "$OUT"; else echo "!! el API no responde tras 20 s"; exit 1; fi
REMOTE
echo "== done: https://pedibot.xyz"
