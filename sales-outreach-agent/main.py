#!/usr/bin/env python3
"""
Too Good To Go — B2B Sales Outreach Agent
CLI entry point.
"""

import argparse
import os
import database
from agent import run_agent


def cmd_run(args):
    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        print("[DRY RUN] Messages will be printed, not sent.\n")

    task = args.task or (
        f"Find {args.category} businesses in {args.city}, enrich their contact details, "
        f"draft personalized outreach messages, send them via {args.channel}, "
        f"schedule follow-ups, and update the pipeline. "
        f"Start by searching for leads, then enrich each one, draft messages, and send them."
    )
    print(f"\nStarting outreach agent...\nTask: {task}\n")
    result = run_agent(task)
    print(f"\n{'='*60}\n{result}\n")


def cmd_followups(args):
    """Process all due follow-ups now."""
    database.init_db()
    due = database.get_due_followups()
    print(f"Due follow-ups: {len(due)}")
    for item in due:
        print(f"  Lead {item['lead_id']}: {item['name']} — attempt {item['attempt_number']}")


def cmd_pipeline(args):
    """Show pipeline summary."""
    database.init_db()
    summary = database.get_pipeline_summary()
    print("\nPipeline Summary")
    print("─" * 30)
    for stage, count in summary.items():
        bar = "█" * count
        print(f"  {stage:<20} {count:>4}  {bar}")
    print()


def cmd_leads(args):
    """List leads in a stage."""
    database.init_db()
    leads = database.get_leads_by_stage(args.stage)
    print(f"\nLeads in stage '{args.stage}' ({len(leads)} total)")
    print("─" * 60)
    for l in leads:
        phone = l.get("phone") or "no phone"
        print(f"  [{l['id']:>4}] {l['name']:<35} {phone:<20} {l['city']}")
    print()


def cmd_chat(args):
    """Interactive chat mode — describe what you want the agent to do."""
    database.init_db()
    print("Too Good To Go Outreach Agent — Interactive Mode")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            task = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if task.lower() in ("exit", "quit"):
            break
        if not task:
            continue
        result = run_agent(task)
        print(f"\nAgent: {result}\n")


def main():
    parser = argparse.ArgumentParser(description="Too Good To Go Sales Outreach Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run outreach for a city")
    p_run.add_argument("--city", default="Tashkent, Uzbekistan", help="Target city")
    p_run.add_argument("--category", default="beauty_salon", choices=["beauty_salon", "car_wash", "barbershop", "spa"], help="Business category")
    p_run.add_argument("--channel", default="telegram", choices=["whatsapp", "telegram"])
    p_run.add_argument("--task", help="Custom task description (overrides city/category)")
    p_run.add_argument("--dry-run", action="store_true", help="Print messages instead of sending them")
    p_run.set_defaults(func=cmd_run)

    # followups
    p_fu = sub.add_parser("followups", help="Process due follow-ups")
    p_fu.set_defaults(func=cmd_followups)

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="Show pipeline summary")
    p_pipe.set_defaults(func=cmd_pipeline)

    # leads
    p_leads = sub.add_parser("leads", help="List leads by stage")
    p_leads.add_argument("stage", choices=["new", "contacted", "replied", "meeting_scheduled", "onboarded", "rejected"])
    p_leads.set_defaults(func=cmd_leads)

    # chat
    p_chat = sub.add_parser("chat", help="Interactive agent chat")
    p_chat.set_defaults(func=cmd_chat)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
