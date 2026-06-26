#!/usr/bin/env bash
# CampDash deploy: build the mobile UI, then bring up Postgres + API via docker-compose.
# Run on the server (or locally) from the campdash/ folder. Requires Docker + Node/npm + a filled .env.
set -euo pipefail
cd "$(dirname "$0")"

echo ">> building the mobile UI…"
( cd frontend && npm install && npm run build )
rm -rf web && cp -R frontend/dist web

echo ">> building + starting containers…"
docker compose up -d --build

echo ">> done. API + UI on http://localhost:8080  (put HTTPS/Cloudflare in front for prod)."
echo "   health: curl -s localhost:8080/health"
