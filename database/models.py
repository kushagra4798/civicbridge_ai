"""Database schema definitions and migrations for SQLite."""

from __future__ import annotations

import sqlite3


BASE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schemes (
    scheme_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    governing_department TEXT NOT NULL,
    benefit_summary TEXT NOT NULL,
    benefit_amount TEXT,
    geographic_coverage TEXT NOT NULL DEFAULT 'All India',
    target_residence TEXT NOT NULL DEFAULT 'all',
    rules_json TEXT NOT NULL,
    required_documents_json TEXT NOT NULL,
    application_steps_json TEXT NOT NULL,
    official_portal_url TEXT NOT NULL,
    evidence_urls_json TEXT NOT NULL,
    application_dates TEXT NOT NULL,
    last_verified TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'VERIFIED',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Columns added in subsequent versions (with safe defaults)
OPTIONAL_COLUMNS = [
    ("opportunity_type", "TEXT NOT NULL DEFAULT 'scheme'"),
    ("host_type", "TEXT"),
    ("stipend", "TEXT"),
    ("duration", "TEXT"),
    ("work_mode", "TEXT DEFAULT 'on_site'"),
    ("field_of_study_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("required_skills_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("application_deadline", "TEXT"),
]

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category);
CREATE INDEX IF NOT EXISTS idx_schemes_residence ON schemes(target_residence);
CREATE INDEX IF NOT EXISTS idx_schemes_opp_type ON schemes(opportunity_type);
"""


def init_db(connection: sqlite3.Connection) -> None:
    """Initialize database tables, indexes, and apply backward-compatible column migrations."""
    with connection:
        # 1. Ensure base table exists
        connection.executescript(BASE_SCHEMA_SQL)

        # 2. Check and add any missing columns safely
        cursor = connection.execute("PRAGMA table_info(schemes)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        for col_name, col_type in OPTIONAL_COLUMNS:
            if col_name not in existing_cols:
                try:
                    connection.execute(f"ALTER TABLE schemes ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # 3. Create indexes now that all columns are guaranteed to exist
        connection.executescript(INDEXES_SQL)
