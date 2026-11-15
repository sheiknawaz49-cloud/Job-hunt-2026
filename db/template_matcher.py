# db/template_matcher.py
import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "outreach.db"


def init_fts_store():
    """Initializes SQLite FTS5 table with BM25 keyword ranking."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pitch_search USING fts5(
            category,
            keywords,
            subject,
            pitch,
            tokenize = 'porter ascii'
        )
    """)

    cursor.execute("SELECT count(*) FROM pitch_search")
    if cursor.fetchone()[0] == 0:
        seed_data = [
            (
                "agentic_ai",
                "ai agent agents langgraph langchain llm prompt orchestration autonomous stateful multiagent rag tool tools",
                "Application: {job_title} - Agentic AI & Systems",
                "I architect production-ready Agentic AI systems and autonomous workflows using LangGraph and LangChain. I focus on stateful checkpointing, human-in-the-loop decision boundaries, and structured LLM tool integration."
            ),
            (
                "scraping_automation",
                "scraping scraper playwright selenium crawler parsing automation beautifulsoup etl pipeline ingestion dom",
                "Application: {job_title} - Data Automation & Scraping",
                "I have extensive experience architecting automated scraping engines and headless browser workflows with Playwright and BeautifulSoup, capable of bypassing client-side hydration barriers to build reliable ETL ingestion pipelines."
            ),
            (
                "backend_engineering",
                "python fastapi backend api apis microservices postgres sql docker concurrency redis async highthroughput worker",
                "Application: {job_title} - Backend & Distributed Systems",
                "I specialize in designing high-throughput Python backends using FastAPI, async worker queues, and SQL performance tuning. I build resilient, low-latency microservices engineered for high concurrency."
            )
        ]

        cursor.executemany("""
            INSERT INTO pitch_search (category, keywords, subject, pitch)
            VALUES (?, ?, ?, ?)
        """, seed_data)
        conn.commit()

    conn.close()


def find_best_pitch_bm25(job_text: str) -> dict:
    """Ranks templates against job posting keywords using SQLite BM25."""
    init_fts_store()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    words = re.findall(r"\b[a-zA-Z]{3,15}\b", job_text.lower())
    clean_query = " OR ".join(set(words[:40])) or "python backend api"

    try:
        cursor.execute("""
            SELECT category, subject, pitch, bm25(pitch_search) as rank
            FROM pitch_search
            WHERE pitch_search MATCH ?
            ORDER BY rank
            LIMIT 1
        """, (clean_query,))
        row = cursor.fetchone()
    except Exception:
        row = None

    conn.close()

    if row:
        return {"category": row[0], "subject": row[1], "pitch": row[2]}

    return {
        "category": "backend_engineering",
        "subject": "Application: {job_title} - Backend Systems",
        "pitch": "I specialize in backend engineering with Python, designing resilient APIs, database optimizations, and scalable worker pipelines."
    }
    