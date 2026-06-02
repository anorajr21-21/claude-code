import httpx
from twilio.rest import Client as TwilioClient
from config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM,
    TELEGRAM_BOT_TOKEN,
)

_twilio: TwilioClient = None


def _twilio_client() -> TwilioClient:
    global _twilio
    if _twilio is None:
        _twilio = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _twilio


def send_whatsapp(to_phone: str, message: str) -> dict:
    """Send a WhatsApp message via Twilio. to_phone must be E.164 format."""
    if not to_phone.startswith("+"):
        raise ValueError(f"Phone must be E.164 format (e.g. +34600123456), got: {to_phone}")

    to = f"whatsapp:{to_phone}"
    msg = _twilio_client().messages.create(
        body=message,
        from_=TWILIO_WHATSAPP_FROM,
        to=to,
    )
    return {"sid": msg.sid, "status": msg.status}


def send_telegram(chat_id: str, message: str) -> dict:
    """Send a Telegram message via Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = httpx.post(url, json={
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_telegram_updates(offset: int = 0) -> list[dict]:
    """Poll Telegram for incoming messages."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    resp = httpx.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
    resp.raise_for_status()
    return resp.json().get("result", [])
