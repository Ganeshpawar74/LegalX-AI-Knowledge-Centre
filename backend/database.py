"""
SQLite database layer for the LegalX AI Knowledge Centre.

Stores:
- topics: generated knowledge cards (description, summary, key info, audio path)
- chat_history: AI Legal Assistant Q&A history per topic, per session
"""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime

from backend.config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they do not already exist."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                topic_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                short_description TEXT,
                summary TEXT,
                key_rights TEXT,        -- JSON list
                important_provisions TEXT,  -- JSON list
                penalties TEXT,         -- JSON list
                who_benefits TEXT,      -- JSON list
                audio_path TEXT,
                source_hash TEXT,       -- to detect if reprocessing is needed
                generated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL,
                role TEXT NOT NULL,        -- 'user' or 'assistant'
                content TEXT NOT NULL,
                sources TEXT,               -- JSON list of cited chunk ids
                created_at TEXT,
                FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
            )
        """)


def upsert_topic_card(topic_id: str, name: str, card: dict, audio_path: str, source_hash: str):
    """Insert or update a generated knowledge card for a topic."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO topics (
                topic_id, name, short_description, summary,
                key_rights, important_provisions, penalties, who_benefits,
                audio_path, source_hash, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_id) DO UPDATE SET
                name=excluded.name,
                short_description=excluded.short_description,
                summary=excluded.summary,
                key_rights=excluded.key_rights,
                important_provisions=excluded.important_provisions,
                penalties=excluded.penalties,
                who_benefits=excluded.who_benefits,
                audio_path=excluded.audio_path,
                source_hash=excluded.source_hash,
                generated_at=excluded.generated_at
        """, (
            topic_id, name,
            card.get("short_description", ""),
            card.get("summary", ""),
            json.dumps(card.get("key_rights", [])),
            json.dumps(card.get("important_provisions", [])),
            json.dumps(card.get("penalties", [])),
            json.dumps(card.get("who_benefits", [])),
            audio_path,
            source_hash,
            datetime.utcnow().isoformat(),
        ))


def get_topic_card(topic_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM topics WHERE topic_id = ?", (topic_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ["key_rights", "important_provisions", "penalties", "who_benefits"]:
            d[key] = json.loads(d[key]) if d[key] else []
        return d


def get_all_topic_cards():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM topics ORDER BY name").fetchall()
        results = []
        for row in rows:
            d = dict(row)
            for key in ["key_rights", "important_provisions", "penalties", "who_benefits"]:
                d[key] = json.loads(d[key]) if d[key] else []
            results.append(d)
        return results


def add_chat_message(topic_id: str, role: str, content: str, sources=None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO chat_history (topic_id, role, content, sources, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (topic_id, role, content, json.dumps(sources or []), datetime.utcnow().isoformat()))


def get_chat_history(topic_id: str, limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM chat_history WHERE topic_id = ?
            ORDER BY id ASC LIMIT ?
        """, (topic_id, limit)).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["sources"] = json.loads(d["sources"]) if d["sources"] else []
            results.append(d)
        return results


def clear_chat_history(topic_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_history WHERE topic_id = ?", (topic_id,))
