# CampDash — deploy to campdash.shop (Oracle Always-Free VM, single deploy)

One container stack serves the mobile UI (`/`), the API, photos (`/media`), and `/admin` from one
origin — a QR code → `https://campdash.shop` → menu → order → photo in your inbox. Verified to build
and run via `docker compose`.

```
Phone scans QR → https://campdash.shop ──(Cloudflare DNS+HTTPS)──► Oracle VM (docker compose)
                                                                  ├ api  (UI + API + /admin + /media)
                                                                  └ db   (Postgres, persisted volume)
                                                                       ├► bucks.shady.tel (charge ShadyBucks)
                                                                       └► Gmail SMTP (email the food photo)
```

## A. One-time: things only you can do
1. **Domain:** register **campdash.shop** at Porkbun or Cloudflare Registrar (~$1–3). Add it to a
   free **Cloudflare** account (free DNS + HTTPS).
2. **Oracle Cloud "Always Free" VM:** create an Ampere/Ubuntu VM (free forever). Open ports 80/443
   in the VM security list + `ufw`. Install Docker + the compose plugin + Node (for the UI build):
   `sudo apt update && sudo apt install -y docker.io docker-compose-v2 nodejs npm && sudo usermod -aG docker $USER`

## B. Ship the code to the VM
Easiest: push this repo to GitHub, then on the VM `git clone` it. (Or `scp` the campdash/ folder.)
The `media/` photos and `frontend/` build inputs travel with the repo.

## C. Configure (.env on the VM)
```bash
cd campdash
cp .env.prod.example .env
# edit .env: set POSTGRES_PASSWORD, CD_FERNET_KEY (generate), CD_ADMIN_KEY (strong),
# CD_SMTP_* (your Gmail + App Password), CD_MAIL_FROM, CD_CORS_ORIGINS=["https://campdash.shop"]
# (CD_BANK_API_URL + CD_HOUSE_PAN are already set for live)
```

## D. Deploy (one command)
```bash
./deploy.sh          # builds the UI, then docker compose up -d --build
curl -s localhost:8080/health     # -> {"status":"ok"}
```
Migrations run automatically (`alembic upgrade head`); the menu seeds on first boot.

## E. Put HTTPS in front (campdash.shop → :8080)
Use Cloudflare (proxied) + a tiny reverse proxy, or Caddy for automatic TLS. Simplest is **Caddy**:
```
# /etc/caddy/Caddyfile
campdash.shop {
    reverse_proxy localhost:8080
}
```
Point the Cloudflare DNS A record for `campdash.shop` at the VM's public IP. Done — HTTPS is automatic.

## F. QR codes
Generate a QR pointing at **https://campdash.shop/** and print it on table tents / signage. Scanning
goes straight to the mobile menu.

## Operate
- **Admin:** `https://campdash.shop/admin` → enter `CD_ADMIN_KEY` → see every order (item, email,
  address, status, sales total). **Resend photo** for any EMAIL_FAILED order.
- **Menu/photos:** edit items/prices in `app/seed.py`; photos in `media/` (`photo_path` → `/media/<file>`).
  After changes: clear `menu_items` and re-run, or extend the admin to manage items.
- **Reconcile:** house sales = sum of orders = real bucks credited to `8997986672600085`.
- **Email cap:** Gmail ~500/day. Over that, orders still record PAID — Resend later from /admin.

## Security checklist
- [ ] Strong `POSTGRES_PASSWORD`, fresh `CD_FERNET_KEY`. (`CD_ADMIN_KEY` is intentionally kept as
      `codedaycodeday12` across the event apps.)
- [ ] `CD_CORS_ORIGINS` = `["https://campdash.shop"]`; HTTPS only.
- [ ] `.env` never committed; Gmail App Password (revocable) not your main password.
- [ ] Per-card checkout rate limit on (default 8 / 5 min).
