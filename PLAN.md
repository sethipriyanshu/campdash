# CampDash — Development Plan

A satirical **DoorDash dupe** running on **ShadyBucks** (the ToorCamp event currency via the
open-source `Shadytel/shadybank`). Browse a few food items, "order" one, pay with ShadyBucks, and
the **delivery is a photo of the food emailed to you** the instant payment clears. The delivery
address field is **for show** (collected/displayed, never used).

> Reuses the proven ShadyBucks rail from ShadyPredict/GoShadeMe/ShadySlot (shadybank client,
> house account, PUSH payment, double-entry ledger). The one new dependency is **email delivery**.

---

## 1. The experience (user flow)
1. **Browse menu** (public, no login) — a grid of a few food items: photo, name, blurb, price in SB.
2. **Order** — pick an item (qty), go to checkout.
3. **Checkout / payment** — a form collects:
   - **Email** (required — where the "delivery" photo is sent)
   - **Delivery address** (required field, satirical — shown on the receipt, never acted on)
   - **ShadyBucks card number + OTP** (to pay)
4. **Pay** — backend charges the price in ShadyBucks into the **house account**, records the order.
5. **"Delivery"** — immediately emails the customer the **photo of the food item** they ordered,
   with a satirical receipt ("Your CampDash has arrived. Bon appétit.").
6. **Confirmation screen** — order placed, photo on its way.

## 2. Money flow (same rail as the other apps)
`checkout (card + OTP) → PUSH price to house → order PAID → email the photo`
- Payment is a **one-shot PUSH**: at checkout we log in to shadybank with the customer's PAN + OTP,
  then `credit` the order total to the **house account**. No persistent wallet/accounts needed —
  CampDash is a one-off purchase per order, not a balance.
- Recorded in a light double-entry ledger (`EXTERNAL → HOUSE` per order) for reconciliation, plus
  an `orders` row. House profit = sum of order totals (it's a straight sale, no payouts).
- House account: **same as the other apps** (`8997986672600085`) unless you want it separate.

## 3. Email delivery (the new piece)
On a confirmed payment, send the customer an email containing the **food item's photo** (attached
and/or inline) + a short satirical receipt.
- **Provider:** a transactional email service via API is the most reliable. **Resend** has a simple
  free tier (good for an event); alternatives: SMTP (Gmail app-password), SendGrid, Mailgun.
- **Sender:** a from-address on a domain you control (e.g. `orders@campdash.<something>`), or the
  provider's sandbox sender for testing.
- **Send is best-effort + logged:** payment success is recorded even if the email hiccups; failed
  sends are retryable from an admin view. (We never "un-charge" for an email failure — we resend.)
- **Photos:** the same item images shown in the menu, stored in the repo / served statically;
  attached to the email so they render even in clients that block remote images.

## 4. Tech stack (consistent with the other projects)
- **Backend:** Python **FastAPI** + **PostgreSQL** (SQLAlchemy async) + **Alembic**.
- **Bank client:** copy `bank/client.py` (login + credit).
- **Email:** a small `mailer.py` wrapper around the chosen provider (swappable).
- **Frontend:** **Vite + React**, a **DoorDash look-alike** (our own branding/assets; footer labels
  it satire) — menu grid, item card, checkout, confirmation. Single-deploy friendly (backend serves
  the built app), same pattern as ShadySlot.
- **MOBILE-FIRST (hard requirement):** people reach CampDash by **scanning QR codes on their phones**,
  so the UI is designed phone-first — single-column responsive layout, large tap targets, big
  numeric/email inputs, sticky bottom checkout button, fast load, `viewport` + safe-area handling.
  Desktop is just a centered narrow column. Test at 390px width first, scale up second.

## 5. Data model (sketch)
```
menu_items(id, name, blurb, price_cents, photo_path, available bool, sort)

-- light ledger for reconciliation
ledger_accounts(id, type[EXTERNAL|HOUSE], label)
ledger_tx(id, type[SALE], meta, created_at)
ledger_entry(id, tx_id, from_account_id, to_account_id, amount_cents)

orders(id, item_id, qty, total_cents, email, address, shadybank_account_id,
       status[PAID|EMAIL_FAILED], bank_desc, tx_id, email_sent_at, created_at)
```
Money is integer **cents**; menu defined in seed/config. Address stored as free text (display only).

### Endpoints
- **Public:** `GET /api/menu`, `GET /api/menu/{id}`
- **Checkout:** `POST /api/orders` `{item_id, qty, email, address, pan, otp}` →
  logs in to bank, `credit`s house, creates order, sends photo email, returns confirmation.
- **Admin (`X-Admin-Key`):** `GET /api/admin/orders` (list/sales total),
  `POST /api/admin/orders/{id}/resend-email`, `GET /api/admin/reconcile?otp=`.
- Static: `/media/<photo>` (menu + email images); single-deploy serves the built frontend.

## 6. Phased build
- **Phase 0 — scaffold + rail + email spike.** New folder/repo; copy bank client + ledger + config.
  FastAPI + Postgres. Prove (a) a PUSH charge to the house against the local bank, and (b) sending
  a test email with an image attachment via the chosen provider. *Exit:* a script charges a test
  card and emails a photo.
- **Phase 1 — menu + orders API.** `menu_items` (seed a few foods + photos), public menu endpoints,
  `POST /api/orders` doing charge → order record → email, idempotent. *Exit:* a real order charges
  ShadyBucks and lands a photo email; address + email captured.
- **Phase 2 — DoorDash-style UI.** Menu grid, item page, checkout form (email + address + card+OTP),
  confirmation screen; our branding, satire footer. *Exit:* full browse→order→"it's in your inbox".
- **Phase 3 — admin + hardening.** Admin orders list + resend-email + reconcile; Alembic migrations;
  abuse limits (per-card/email rate limit), input validation; single-deploy (backend serves UI);
  prod config (real admin key, CORS, TLS). *Exit:* deployable, reconciles, resilient email.

## 7. Reuse map (from the other apps)
| Reuse directly | Adapt | New |
|---|---|---|
| `bank/client.py`, ledger, security, house-login, config pattern, admin-key gate, Alembic, single-deploy static serving | deposit/donation → **one-shot SALE charge** | menu items + photos; orders; **email delivery (mailer)**; DoorDash UI |

## 8. Decisions
**Decided:**
- **Email = Resend** (free API tier). Needs a Resend account + `CD_RESEND_API_KEY`.
- **Menu + photos: provided by the user.** Phase 0/1 builds the schema + admin/seed path; real
  items, prices, and images get dropped in (placeholders only as a temporary stand-in until then).
- **House account = same `8997986672600085`** (shared with the other apps).
- **Checkout auth = per-order PAN + OTP** (no persistent accounts).

**Still to provide (not blocking Phase 0):**
- Resend **API key** + a verified **sender address/domain** (e.g. `orders@…`). Until a domain is
  verified, Resend's test sender works for dev.
- The actual **food items** (name, blurb, price) and their **photos**.
