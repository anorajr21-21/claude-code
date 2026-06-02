import os
from dotenv import load_dotenv

load_dotenv()

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TWOGIS_API_KEY = os.environ["TWOGIS_API_KEY"]

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Your own Telegram chat ID — drafts for businesses without a Telegram handle are sent here
OWNER_TELEGRAM_CHAT_ID = os.environ.get("OWNER_TELEGRAM_CHAT_ID", "")

SENDER_NAME = os.environ.get("SENDER_NAME", "Sales Team")
SENDER_COMPANY = os.environ.get("SENDER_COMPANY", "Too Good To Go Partner Team")
SENDER_PHONE = os.environ.get("SENDER_PHONE", "")
MEETING_LINK = os.environ.get("MEETING_LINK", "")

MODEL = "claude-sonnet-4-6"
DB_PATH = "outreach.db"

# Pipeline stages
STAGES = ["new", "contacted", "replied", "meeting_scheduled", "onboarded", "rejected"]

# Days between follow-ups per stage
FOLLOWUP_INTERVALS = {
    "contacted": 3,
    "replied": 2,
}
MAX_FOLLOWUPS = 3
