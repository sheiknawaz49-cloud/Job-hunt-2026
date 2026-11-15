# db/database.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "outreach.db"


def init_db():
    """Initializes the SQLite outreach tracking table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outreach_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            job_title TEXT NOT NULL,
            target_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_html TEXT NOT NULL,
            match_score INTEGER,
            pitch_source TEXT,
            gmail_draft_id TEXT,
            status TEXT DEFAULT 'DRAFT_STAGED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def log_outreach_attempt(
    company_name: str,
    job_title: str,
    target_email: str,
    subject: str,
    body_html: str,
    match_score: int,
    pitch_source: str,
    gmail_draft_id: str | None = None,
    status: str = "DRAFT_STAGED"
) -> int:
    """Inserts a completed outreach record into SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO outreach_records (
            company_name, job_title, target_email, subject, body_html,
            match_score, pitch_source, gmail_draft_id, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        company_name, job_title, target_email, subject, body_html,
        match_score, pitch_source, gmail_draft_id, status
    ))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_all_outreach_history(limit: int = 50) -> list[dict]:
    """Retrieves previous applications for review on the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, company_name, job_title, target_email, subject,
               body_html, match_score, pitch_source, gmail_draft_id, status, created_at
        FROM outreach_records
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


init_db()