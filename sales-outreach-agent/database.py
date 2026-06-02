import sqlite3
from typing import Optional
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS leads (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id          TEXT UNIQUE,
                name              TEXT NOT NULL,
                address           TEXT,
                phone             TEXT,
                telegram_handle   TEXT,
                category          TEXT,
                rating            REAL,
                website           TEXT,
                city              TEXT,
                stage             TEXT DEFAULT 'new',
                notes             TEXT,
                created_at        TEXT DEFAULT (datetime('now')),
                updated_at        TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS outreach_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id     INTEGER REFERENCES leads(id),
                channel     TEXT,           -- 'whatsapp' | 'telegram'
                direction   TEXT,           -- 'sent' | 'received'
                message     TEXT,
                sent_at     TEXT DEFAULT (datetime('now')),
                status      TEXT DEFAULT 'sent'
            );

            CREATE TABLE IF NOT EXISTS followups (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id         INTEGER REFERENCES leads(id),
                scheduled_at    TEXT,
                attempt_number  INTEGER DEFAULT 1,
                done            INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS meetings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id     INTEGER REFERENCES leads(id),
                scheduled_at TEXT,
                notes       TEXT,
                confirmed   INTEGER DEFAULT 0
            );
        """)


def upsert_lead(data: dict) -> int:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM leads WHERE place_id = ?", (data.get("place_id"),)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            """INSERT INTO leads (place_id, name, address, phone, telegram_handle, category, rating, website, city)
               VALUES (:place_id, :name, :address, :phone, :telegram_handle, :category, :rating, :website, :city)""",
            data,
        )
        return cur.lastrowid


def update_lead_stage(lead_id: int, stage: str, notes: str = None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE leads SET stage=?, notes=COALESCE(?,notes), updated_at=datetime('now') WHERE id=?",
            (stage, notes, lead_id),
        )


def get_lead(lead_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        return dict(row) if row else None


def get_leads_by_stage(stage: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE stage=? ORDER BY created_at", (stage,)
        ).fetchall()
        return [dict(r) for r in rows]


def log_message(lead_id: int, channel: str, direction: str, message: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO outreach_log (lead_id, channel, direction, message) VALUES (?,?,?,?)",
            (lead_id, channel, direction, message),
        )


def schedule_followup(lead_id: int, scheduled_at: str, attempt_number: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO followups (lead_id, scheduled_at, attempt_number) VALUES (?,?,?)",
            (lead_id, scheduled_at, attempt_number),
        )


def get_due_followups() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT f.*, l.name, l.phone, l.stage, l.city
               FROM followups f JOIN leads l ON f.lead_id = l.id
               WHERE f.done=0 AND f.scheduled_at <= datetime('now')
               ORDER BY f.scheduled_at""",
        ).fetchall()
        return [dict(r) for r in rows]


def mark_followup_done(followup_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE followups SET done=1 WHERE id=?", (followup_id,))


def add_meeting(lead_id: int, scheduled_at: str, notes: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO meetings (lead_id, scheduled_at, notes, confirmed) VALUES (?,?,?,1)",
            (lead_id, scheduled_at, notes),
        )


def get_pipeline_summary() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT stage, COUNT(*) as count FROM leads GROUP BY stage"
        ).fetchall()
        return {r["stage"]: r["count"] for r in rows}
