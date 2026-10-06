"""SQLite connection helpers for data/campus_customs.db."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

HW4_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = HW4_DIR / "data"
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "campus_customs.db"))
IMAGES_DIR = DATA_DIR / "products"


def connect(readonly: bool = True) -> sqlite3.Connection:
    """Read-only by default so catalogue/chat lookups can never modify data."""
    if readonly:
        conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the app-owned tables that the seed database does not ship with."""
    with connect(readonly=False) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")
        # Chat history is always read per user, newest first.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)"
        )
