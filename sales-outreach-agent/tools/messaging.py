import httpx
from twilio.rest import Client as TwilioClient
from config import (
    DRY_RUN,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM,
    TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_CHAT_ID,
)

_twilio: TwilioClient = None


def _twilio_client() -> TwilioClient:
    global _twilio
    if _twilio is None:
        _twilio = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _twilio


def send_whatsapp(to_phone: str, message: str) -> dict:
    """Send a WhatsApp message via Twilio. to_phone must be E.164 format."""
    if DRY_RUN:
        print(f"\n[DRY RUN] WhatsApp -> {to_phone}\n{'-'*40}\n{message}\n{'-'*40}")
        return {"sid": "dry-run", "status": "simulated"}

    if not to_phone.startswith("+"):
        raise ValueError(f"Phone must be E.164 format (e.g. +34600123456), got: {to_phone}")

    msg = _twilio_client().messages.create(
        body=message,
        from_=TWILIO_WHATSAPP_FROM,
        to=f"whatsapp:{to_phone}",
    )
    return {"sid": msg.sid, "status": msg.status}


def send_telegram(chat_id: str, message: str, business_name: str = "") -> dict:
    """Send a Telegram message.

    - If chat_id is a @handle: send directly to that business Telegram
    - If chat_id is empty: forward draft to owner's chat for manual sending
    """
    if DRY_RUN:
        dest = f"@{chat_id}" if chat_id else f"owner ({OWNER_TELEGRAM_CHAT_ID}) as draft"
        print(f"\n[DRY RUN] Telegram -> {dest}\n{'-'*40}\n{message}\n{'-'*40}")
        return {"ok": True, "simulated": True}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    if chat_id:
        target = chat_id if chat_id.startswith("@") else f"@{chat_id}"
        resp = httpx.post(url, json={"chat_id": target, "text": message}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    else:
        if not OWNER_TELEGRAM_CHAT_ID:
            return {"ok": False, "reason": "No telegram_handle and OWNER_TELEGRAM_CHAT_ID not set in .env"}
        label = f"*Черновик для {business_name}*\n_(нет Telegram — отправьте вручную)_\n\n"
        resp = httpx.post(url, json={
            "chat_id": OWNER_TELEGRAM_CHAT_ID,
            "text": label + message,
            "parse_mode": "Markdown",
        }, timeout=10)
        resp.raise_for_status()
        return {"ok": True, "forwarded_to_owner": True}


def get_telegram_updates(offset: int = 0) -> list[dict]:
    """Poll Telegram for incoming messages."""
    if DRY_RUN:
        return []

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    resp = httpx.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
    resp.raise_for_status()
    return resp.json().get("result", [])
