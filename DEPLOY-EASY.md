# CampDash — easy deploy (Railway, no VM)

Deploys straight from GitHub: managed host builds the Docker image, you add a Postgres + env vars,
attach campdash.shop. ~10 min, no SSH, no capacity errors. (Render works the same way — see bottom.)

## Railway (recommended — always-on, no cold starts)
1. Go to **railway.app** → sign in with GitHub.
2. **New Project → Deploy from GitHub repo** → pick **sethipriyanshu/campdash**. It detects the
   `Dockerfile` and starts building.
3. **Add Postgres:** in the project, **New → Database → PostgreSQL**. Railway auto-exposes a
   `DATABASE_URL` to the app (our config reads it automatically).
4. **Set env vars** on the campdash service (Variables tab):
   - `CD_FERNET_KEY=xWH4ilKkKsOQrPlqAMuWF1SqoLr_qHLLnymy2dpgPbU=`
   - `CD_ADMIN_KEY=codedaycodeday12`
   - `CD_BANK_API_URL=https://bucks.shady.tel`
   - `CD_HOUSE_PAN=8997986672600085`
   - `CD_SMTP_HOST=smtp.gmail.com`  `CD_SMTP_PORT=587`
   - `CD_SMTP_USER=mrabraxos@gmail.com`  `CD_SMTP_PASSWORD=cfddozmuyeylrxtx`
   - `CD_MAIL_FROM=CampDash <mrabraxos@gmail.com>`
   - `CD_CORS_ORIGINS=["https://campdash.shop"]`
   (Postgres `DATABASE_URL` is provided by the plugin — don't set CD_DATABASE_URL.)
5. **Custom domain:** service → **Settings → Networking → Custom Domain** → add `campdash.shop`.
   Railway shows a **CNAME target** (e.g. `xxx.up.railway.app`).
6. **Cloudflare DNS:** add a **CNAME**, name `@` (or `campdash`), target = Railway's CNAME, proxy ON.
   (Cloudflare allows CNAME at root via "CNAME flattening.")
7. Done. Visit **https://campdash.shop** → menu loads → order → photo email. Admin at `/admin`.

Cost: Railway Hobby is ~$5/mo (small app + Postgres). No sleep, instant scans.

## Render (free, but sleeps after 15 min + free Postgres expires ~30 days)
1. render.com → New → **Web Service** → connect the repo → it builds the Dockerfile.
2. New → **PostgreSQL** (free) → copy its Internal Database URL → set `CD_DATABASE_URL` (or
   `DATABASE_URL`) on the web service. Add the same env vars as above.
3. Settings → **Custom Domain** → `campdash.shop` → add the shown record in Cloudflare.
Free tier cold-starts (~30–50s on first scan after idle); fine for testing, less ideal live.

## Notes
- Real money: prod points at the live bank; orders credit `8997986672600085`.
- After deploy, set the QR (`campdash-qr.png`) → it already targets https://campdash.shop/.
