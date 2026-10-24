"""
database.py
SQLite persistence layer with schema migrations and FTS5 full-text search.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional
from src.macro_expert.logging_config import setup_logger

logger = setup_logger("horizon.database")

SCHEMA_SQL = """
-- Users and authentication
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    username TEXT,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success INTEGER NOT NULL
);

-- Video inventory
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    title TEXT NOT NULL,
    video_url TEXT,
    publish_date TEXT,
    duration_seconds INTEGER,
    access_method TEXT DEFAULT 'manual',
    rights_status TEXT DEFAULT 'authorized_personal_use',
    ingestion_status TEXT DEFAULT 'pending',
    audio_path TEXT,
    transcript_path TEXT,
    transcription_status TEXT DEFAULT 'pending',
    extraction_status TEXT DEFAULT 'pending',
    review_status TEXT DEFAULT 'unreviewed',
    checksum TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

-- Transcript segments
CREATE TABLE IF NOT EXISTS transcript_segments (
    segment_id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    start_seconds REAL NOT NULL,
    end_seconds REAL NOT NULL,
    text TEXT NOT NULL,
    confidence REAL,
    review_status TEXT DEFAULT 'unreviewed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE
);

-- Claims
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    subtopic TEXT,
    claim_text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    mechanism TEXT,
    conditions TEXT,
    indicators TEXT,
    assets_affected TEXT,
    time_horizon TEXT,
    confidence_expression TEXT,
    evidence_text TEXT,
    timestamp_range TEXT,
    review_status TEXT DEFAULT 'unreviewed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE
);

-- Frameworks
CREATE TABLE IF NOT EXISTS frameworks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT DEFAULT 'verified',
    content_markdown TEXT NOT NULL,
    key_variables TEXT,
    transmission_chain TEXT,
    triggers TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cases
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    topic TEXT NOT NULL,
    era TEXT,
    countries TEXT,
    key_indicators TEXT,
    mechanisms TEXT NOT NULL,
    creator_comparative_take TEXT NOT NULL,
    source_video_id TEXT,
    timestamp TEXT,
    review_status TEXT DEFAULT 'verified',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Forecasts
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    forecast_date TEXT NOT NULL,
    target_variable TEXT NOT NULL,
    direction TEXT NOT NULL,
    target_value TEXT,
    horizon TEXT,
    conditions TEXT,
    forecast_text TEXT NOT NULL,
    review_status TEXT DEFAULT 'unreviewed',
    outcome TEXT DEFAULT 'pending',
    outcome_date TEXT,
    outcome_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(video_id) ON DELETE CASCADE
);

-- Conversations and Chat
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    user_id TEXT DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model_name TEXT,
    citations_json TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

-- Usage and Cost events
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Package versions
CREATE TABLE IF NOT EXISTS package_versions (
    version TEXT PRIMARY KEY,
    manifest_json TEXT NOT NULL,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_segments_video_id ON transcript_segments(video_id);
CREATE INDEX IF NOT EXISTS idx_claims_topic ON claims(topic);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip_address, attempted_at);
"""

FTS5_INIT_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    record_id UNINDEXED,
    source_type,
    title,
    content,
    tokenize='trigram'
);
"""

class Database:
    def __init__(self, db_path: str = "./data/app.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.session() as conn:
            conn.executescript(SCHEMA_SQL)
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT DEFAULT 'default';")
            except Exception:
                pass
            try:
                conn.execute("UPDATE conversations SET user_id = 'admin' WHERE user_id IS NULL OR user_id = 'default';")
            except Exception:
                pass
            try:
                conn.executescript(FTS5_INIT_SQL)
            except sqlite3.OperationalError as e:
                logger.warning(f"FTS5 initialization warning (may already exist or tokenizer fallback): {e}")
        logger.info(f"Database initialized at {self.db_path}")

    def rebuild_fts_index(self) -> int:
        """Populates knowledge_fts from claims, frameworks, cases, and transcript_segments."""
        total_indexed = 0
        with self.session() as conn:
            conn.execute("DELETE FROM knowledge_fts;")

            # 1. Index frameworks
            for row in conn.execute("SELECT id, title, content_markdown FROM frameworks;"):
                conn.execute(
                    "INSERT INTO knowledge_fts(record_id, source_type, title, content) VALUES (?, ?, ?, ?);",
                    (row["id"], "framework", row["title"], row["content_markdown"])
                )
                total_indexed += 1

            # 2. Index claims
            for row in conn.execute("SELECT claim_id, topic, claim_text, mechanism, evidence_text FROM claims;"):
                content = f"{row['claim_text']} {row['mechanism'] or ''} {row['evidence_text'] or ''}"
                conn.execute(
                    "INSERT INTO knowledge_fts(record_id, source_type, title, content) VALUES (?, ?, ?, ?);",
                    (row["claim_id"], "claim", row["topic"], content)
                )
                total_indexed += 1

            # 3. Index cases
            for row in conn.execute("SELECT case_id, name, mechanisms, creator_comparative_take FROM cases;"):
                content = f"{row['mechanisms']} {row['creator_comparative_take']}"
                conn.execute(
                    "INSERT INTO knowledge_fts(record_id, source_type, title, content) VALUES (?, ?, ?, ?);",
                    (row["case_id"], "case", row["name"], content)
                )
                total_indexed += 1

            # 4. Index transcript segments
            for row in conn.execute("SELECT segment_id, video_id, text FROM transcript_segments;"):
                conn.execute(
                    "INSERT INTO knowledge_fts(record_id, source_type, title, content) VALUES (?, ?, ?, ?);",
                    (row["segment_id"], "transcript_segment", row["video_id"], row["text"])
                )
                total_indexed += 1

        logger.info(f"FTS index rebuilt with {total_indexed} records.")
        return total_indexed
