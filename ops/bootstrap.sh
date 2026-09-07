#!/usr/bin/env bash
# One-time VPS setup. Usage (from the PC): bash ops/bootstrap.sh <IP>
# Assumes root SSH access with key multibot_hetzner_auto (same pattern as MultiBot).
set -euo pipefail
IP="${1:?usage: bootstrap.sh <IP>}"
KEY="${SSH_KEY:-$HOME/.ssh/multibot_hetzner_auto}"

ssh -i "$KEY" -o StrictHostKeyChecking=accept-new root@"$IP" bash -s <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -q && apt-get install -y -q curl git rsync ufw tesseract-ocr tesseract-ocr-spa ocrmypdf logrotate debian-keyring debian-archive-keyring apt-transport-https

# --- journal size cap ---
# journald corre sin límite por defecto y logrotate NO lo toca: el journal binario tiene su propio
# tope y hay que ponérselo. En el VPS de MultiBot había crecido hasta 4 GB antes de que nadie
# mirara. Un disco lleno no avisa: se lleva por delante la base de datos, el despliegue y el API.
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/pedibot-size.conf <<'CONF'
[Journal]
SystemMaxUse=300M
MaxRetentionSec=1month
CONF
systemctl restart systemd-journald || true

# --- caddy (official repo) ---
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q && apt-get install -y -q caddy
fi

# --- node LTS (for astro build on the server; optional, deploy.sh can upload dist instead) ---
if ! command -v node >/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y -q nodejs
fi

# --- service user + dirs ---
id -u pedibot >/dev/null 2>&1 || useradd -r -m -d /opt/pedibot -s /bin/bash pedibot
mkdir -p /opt/pedibot/{data,index,backups,web/site/dist,FUENTES}
chown -R pedibot:pedibot /opt/pedibot

# --- uv for the service user ---
sudo -u pedibot bash -c 'command -v ~/.local/bin/uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh'

# --- firewall ---
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable

# --- caddy log dir ---
mkdir -p /var/log/caddy && chown caddy:caddy /var/log/caddy
echo "bootstrap done"
REMOTE

echo "Next: bash ops/deploy.sh $IP   (uploads code, index, dist, units, Caddyfile; needs /opt/pedibot/.env on the server)"
