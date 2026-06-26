#!/usr/bin/env bash
# CampDash one-shot VM setup (Ubuntu, e.g. Oracle Always-Free).
# Installs Docker + Node + Caddy, deploys the app, and serves https://campdash.fun.
#
# Usage on the VM (after `git clone` + editing .env):
#   cd campdash && cp .env.prod.example .env && nano .env   # fill secrets
#   chmod +x vm-setup.sh && ./vm-setup.sh
set -euo pipefail
cd "$(dirname "$0")"

DOMAIN="${1:-campdash.fun}"

if [ ! -f .env ]; then
  echo "!! No .env found. Run: cp .env.prod.example .env  then edit it, then re-run."
  exit 1
fi

echo ">> [1/5] Installing Docker, Node, Caddy…"
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-v2 nodejs npm debian-keyring debian-archive-keyring apt-transport-https curl
# Caddy (automatic HTTPS)
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y && sudo apt-get install -y caddy
fi
sudo usermod -aG docker "$USER" || true

echo ">> [2/5] Opening the firewall (80/443)…"
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT || true
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT || true
sudo netfilter-persistent save 2>/dev/null || true

echo ">> [3/5] Building + starting the app (docker compose)…"
sudo ./deploy.sh

echo ">> [4/5] Configuring Caddy reverse proxy for ${DOMAIN}…"
echo "${DOMAIN} {
    reverse_proxy localhost:8080
}" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl restart caddy

echo ">> [5/5] Done."
echo "   - App container:  curl -s localhost:8080/health"
echo "   - Public (after DNS): https://${DOMAIN}/   admin: https://${DOMAIN}/admin"
echo "   Make sure ${DOMAIN}'s DNS A record points at this VM's public IP (Cloudflare)."
