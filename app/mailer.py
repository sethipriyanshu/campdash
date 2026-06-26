"""Email delivery. Provider is auto-selected:
  - SMTP (e.g. Gmail) if CD_SMTP_HOST + CD_SMTP_USER are set
  - else Resend if CD_RESEND_API_KEY is set
  - else DEV mode: logs the email to media/_sent_emails/ instead of sending
The food photo is attached so it renders in any client. Swap creds without code changes.
"""
from __future__ import annotations

import asyncio
import base64
import json
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path

import httpx

from app.config import get_settings

RESEND_URL = "https://api.resend.com/emails"
_DEV_OUTBOX = Path("media/_sent_emails")


def _resolve_photo(photo_path: str | None) -> Path | None:
    if not photo_path:
        return None
    p = Path(photo_path.lstrip("/")) if photo_path.startswith("/") else Path(photo_path)
    return p if p.exists() else None


def _send_smtp(*, to: str, subject: str, html: str, photo: Path | None, photo_name: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    name, addr = parseaddr(s.mail_from)
    # Gmail rewrites From to the authenticated account; keep a friendly display name.
    msg["From"] = formataddr((name or "CampDash", addr or s.smtp_user))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("Your CampDash order — view this email in an HTML client.")
    msg.add_alternative(html, subtype="html")
    if photo:
        msg.add_attachment(photo.read_bytes(), maintype="image", subtype="jpeg", filename=photo_name)
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as server:
        server.starttls()
        server.login(s.smtp_user, s.smtp_password)
        server.send_message(msg)


def order_email_html(item_name: str, qty: int, total_sb: str, address: str) -> str:
    if "slushie" in item_name.lower():
        ps = ("You’re welcome to come by <b>CodeDay Village</b> to say hi and grab an "
              "actual slushie. 🧊")
    else:
        ps = ("PS — show this email at <b>Fried Rice</b> in the Night Market tonight for a "
              "discount. 🍚")
    return f"""\
<div style="font-family:system-ui,-apple-system,sans-serif;max-width:480px;margin:auto;color:#191919">
  <h2 style="color:#ff3008;margin:0 0 4px">CampDash</h2>
  <p style="margin:0 0 16px;color:#767676">Your order has arrived. Bon appétit. 🍽️</p>
  <p style="font-size:16px;margin:0 0 8px"><b>{qty}× {item_name}</b></p>
  <p style="margin:0 0 16px">See your delicious delivery attached.</p>
  <hr style="border:none;border-top:1px solid #eee"/>
  <p style="font-size:13px;color:#767676;margin:12px 0 0">Delivered to: {address}</p>
  <p style="font-size:13px;color:#767676;margin:4px 0 0">Total paid: {total_sb} SB</p>
  <p style="font-size:14px;color:#191919;margin:16px 0 0">{ps}</p>
  <p style="font-size:12px;color:#aaa;margin:16px 0 0">CampDash is a satire. ShadyBucks aren't real
  money and no actual food was harmed (or delivered) in this transaction.</p>
</div>"""


async def send_order_email(
    *, to: str, subject: str, html: str, photo_path: str | None, photo_name: str = "your-order.jpg",
) -> None:
    """Send the order email with the food photo attached. Raises on hard failure."""
    s = get_settings()
    photo = _resolve_photo(photo_path)

    # 1) SMTP (e.g. Gmail) — preferred when configured; sends to any recipient.
    if s.smtp_host and s.smtp_user:
        await asyncio.to_thread(_send_smtp, to=to, subject=subject, html=html,
                                photo=photo, photo_name=photo_name)
        return

    # 2) Resend API.
    if s.resend_api_key:
        payload = {"from": s.mail_from, "to": [to], "subject": subject, "html": html}
        if photo:
            payload["attachments"] = [{"filename": photo_name,
                                       "content": base64.b64encode(photo.read_bytes()).decode()}]
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(RESEND_URL, headers={"Authorization": f"Bearer {s.resend_api_key}"}, json=payload)
            if r.status_code >= 300:
                raise RuntimeError(f"Resend error {r.status_code}: {r.text[:200]}")
        return

    # 3) DEV mode — log instead of sending so the flow stays verifiable.
    _DEV_OUTBOX.mkdir(parents=True, exist_ok=True)
    rec = {"to": to, "subject": subject, "attachment": photo_name if photo else None, "_mode": "dev-no-send"}
    (_DEV_OUTBOX / f"{to.replace('/', '_')}.json").write_text(json.dumps(rec, indent=2))
    print(f"[mailer:dev] would email {to} — subject={subject!r} attachment={'yes' if photo else 'no'}")
