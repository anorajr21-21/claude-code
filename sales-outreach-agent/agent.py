"""
Too Good To Go — B2B Sales Outreach Agent
Powered by Claude claude-sonnet-4-6 with tool use.
"""

import json
from datetime import datetime
import anthropic
import database
from tools.lead_discovery import search_businesses, get_place_details
from tools.messaging import send_whatsapp, send_telegram
from tools.scheduler import compute_next_followup_date, should_followup
from prompts import SYSTEM_PROMPT, INITIAL_OUTREACH_TEMPLATE, FOLLOWUP_TEMPLATE, REPLY_RESPONSE_TEMPLATE
from config import MODEL, MEETING_LINK

client = anthropic.Anthropic()

# ──────────────────────────────────────────────
# Tool definitions (Claude sees these)
# ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_leads",
        "description": "Search Google Maps for food businesses (restaurants, cafes, bakeries, etc.) in a city that could become Too Good To Go partners.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name and country, e.g. 'Barcelona, Spain'"},
                "category": {
                    "type": "string",
                    "enum": ["beauty_salon", "car_wash", "barbershop", "spa"],
                    "description": "Type of service business to search for",
                },
                "radius_m": {"type": "integer", "description": "Search radius in metres (default 5000)", "default": 5000},
                "max_results": {"type": "integer", "description": "Max businesses to return (default 20)", "default": 20},
            },
            "required": ["city", "category"],
        },
    },
    {
        "name": "enrich_lead",
        "description": "Fetch full contact details (phone, website) for a lead using its Google Place ID, then save to DB.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer", "description": "DB lead ID"},
                "place_id": {"type": "string", "description": "Google Maps place_id"},
            },
            "required": ["lead_id", "place_id"],
        },
    },
    {
        "name": "send_outreach",
        "description": "Send the initial outreach message to a lead via WhatsApp or Telegram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "channel": {"type": "string", "enum": ["whatsapp", "telegram"]},
                "message": {"type": "string", "description": "The personalized outreach message to send"},
                "contact": {"type": "string", "description": "Phone number (E.164) for WhatsApp, or Telegram chat_id"},
            },
            "required": ["lead_id", "channel", "message", "contact"],
        },
    },
    {
        "name": "schedule_followup",
        "description": "Schedule a follow-up message for a lead who hasn't responded.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "attempt_number": {"type": "integer", "description": "Which follow-up attempt this is (1, 2, or 3)"},
            },
            "required": ["lead_id", "attempt_number"],
        },
    },
    {
        "name": "send_followup",
        "description": "Send a follow-up message to a non-responding lead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "channel": {"type": "string", "enum": ["whatsapp", "telegram"]},
                "message": {"type": "string"},
                "contact": {"type": "string"},
            },
            "required": ["lead_id", "channel", "message", "contact"],
        },
    },
    {
        "name": "schedule_meeting",
        "description": "Log a scheduled meeting with a prospect who showed interest.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "scheduled_at": {"type": "string", "description": "ISO datetime of the meeting"},
                "notes": {"type": "string"},
            },
            "required": ["lead_id", "scheduled_at"],
        },
    },
    {
        "name": "update_lead_status",
        "description": "Update the pipeline stage and notes for a lead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "stage": {
                    "type": "string",
                    "enum": ["new", "contacted", "replied", "meeting_scheduled", "onboarded", "rejected"],
                },
                "notes": {"type": "string"},
            },
            "required": ["lead_id", "stage"],
        },
    },
    {
        "name": "get_pipeline_summary",
        "description": "Get a count of leads in each pipeline stage.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_leads_by_stage",
        "description": "List all leads currently in a given pipeline stage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stage": {
                    "type": "string",
                    "enum": ["new", "contacted", "replied", "meeting_scheduled", "onboarded", "rejected"],
                }
            },
            "required": ["stage"],
        },
    },
    {
        "name": "draft_message",
        "description": "Ask Claude to draft a personalized outreach, follow-up, or reply message for a lead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "template": {"type": "string", "enum": ["initial", "followup", "reply"]},
                "lead_id": {"type": "integer"},
                "extra": {"type": "string", "description": "Additional context, e.g. the prospect's reply text"},
            },
            "required": ["template", "lead_id"],
        },
    },
]


# ──────────────────────────────────────────────
# Tool execution
# ──────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "search_leads":
            results = search_businesses(
                city=inputs["city"],
                category=inputs.get("category", "beauty_salon"),
                radius_m=inputs.get("radius_m", 5000),
                max_results=inputs.get("max_results", 20),
            )
            if not results:
                return json.dumps({
                    "found": 0,
                    "leads": [],
                    "IMPORTANT": "2GIS returned no results. Do NOT invent fake leads or IDs. Stop here and tell the user the API returned nothing."
                })
            saved_ids = []
            for biz in results:
                lead_id = database.upsert_lead(biz)
                saved_ids.append({"lead_id": lead_id, "name": biz["name"], "place_id": biz["place_id"]})
            return json.dumps({"found": len(saved_ids), "leads": saved_ids})

        elif name == "enrich_lead":
            details = get_place_details(inputs["place_id"])
            with database.get_conn() as conn:
                conn.execute(
                    "UPDATE leads SET phone=?, website=?, updated_at=datetime('now') WHERE id=?",
                    (details.get("phone"), details.get("website"), inputs["lead_id"]),
                )
            return json.dumps({"lead_id": inputs["lead_id"], **details})

        elif name == "send_outreach":
            lead_id = inputs["lead_id"]
            channel = inputs["channel"]
            message = inputs["message"]
            contact = inputs["contact"]

            if channel == "whatsapp":
                result = send_whatsapp(contact, message)
            else:
                result = send_telegram(contact, message)

            database.log_message(lead_id, channel, "sent", message)
            database.update_lead_stage(lead_id, "contacted")
            return json.dumps({"ok": True, **result})

        elif name == "schedule_followup":
            lead = database.get_lead(inputs["lead_id"])
            attempt = inputs["attempt_number"]
            if not should_followup(lead["stage"], attempt):
                return json.dumps({"ok": False, "reason": "Max follow-ups reached or wrong stage"})
            scheduled_at = compute_next_followup_date(lead["stage"], attempt)
            database.schedule_followup(inputs["lead_id"], scheduled_at, attempt)
            return json.dumps({"ok": True, "scheduled_at": scheduled_at})

        elif name == "send_followup":
            lead_id = inputs["lead_id"]
            channel = inputs["channel"]
            message = inputs["message"]
            contact = inputs["contact"]

            if channel == "whatsapp":
                result = send_whatsapp(contact, message)
            else:
                result = send_telegram(contact, message)

            database.log_message(lead_id, channel, "sent", message)
            return json.dumps({"ok": True, **result})

        elif name == "schedule_meeting":
            database.add_meeting(
                inputs["lead_id"],
                inputs["scheduled_at"],
                inputs.get("notes"),
            )
            database.update_lead_stage(inputs["lead_id"], "meeting_scheduled", inputs.get("notes"))
            return json.dumps({"ok": True})

        elif name == "update_lead_status":
            database.update_lead_stage(inputs["lead_id"], inputs["stage"], inputs.get("notes"))
            return json.dumps({"ok": True})

        elif name == "get_pipeline_summary":
            return json.dumps(database.get_pipeline_summary())

        elif name == "get_leads_by_stage":
            leads = database.get_leads_by_stage(inputs["stage"])
            return json.dumps({"count": len(leads), "leads": leads})

        elif name == "draft_message":
            return _draft_message(inputs["template"], inputs["lead_id"], inputs.get("extra", ""))

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


def _draft_message(template: str, lead_id: int, extra: str) -> str:
    lead = database.get_lead(lead_id)
    if not lead:
        return json.dumps({"error": "Lead not found"})

    if template == "initial":
        prompt = (
            INITIAL_OUTREACH_TEMPLATE
            .replace("{{business_name}}", lead["name"])
            .replace("{{category}}", lead["category"] or "food business")
            .replace("{{city}}", lead["city"] or "")
            .replace("{{rating}}", str(lead["rating"] or "N/A"))
        )
    elif template == "followup":
        attempt = extra or "1"
        prompt = (
            FOLLOWUP_TEMPLATE
            .replace("{{business_name}}", lead["name"])
            .replace("{{city}}", lead["city"] or "")
            .replace("{{attempt}}", str(attempt))
        )
    elif template == "reply":
        prompt = (
            REPLY_RESPONSE_TEMPLATE
            .replace("{{business_name}}", lead["name"])
            .replace("{{city}}", lead["city"] or "")
            .replace("{{reply}}", extra)
            .replace("{{meeting_link}}", MEETING_LINK)
        )
    else:
        return json.dumps({"error": "Unknown template"})

    # Inner Claude call just for message drafting
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    drafted = resp.content[0].text.strip()
    return json.dumps({"message": drafted})


# ──────────────────────────────────────────────
# Main agentic loop
# ──────────────────────────────────────────────

def run_agent(user_task: str) -> str:
    """Run the outreach agent with a task description and return the final response."""
    database.init_db()

    messages = [{"role": "user", "content": user_task}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Done."

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [tool] {block.name}({json.dumps(block.input)[:120]})")
                    result = execute_tool(block.name, block.input)
                    print(f"  [result] {result[:200]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason
            break

    return "Agent stopped unexpectedly."
