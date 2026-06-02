import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

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
