"""Database schema definitions for SQLite."""

from __future__ import annotations

import sqlite3
from typing import Any


SCHEMA_SQL = """
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

CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category);
CREATE INDEX IF NOT EXISTS idx_schemes_residence ON schemes(target_residence);
"""


def init_db(connection: sqlite3.Connection) -> None:
    """Initialize database tables and indexes."""
    with connection:
        connection.executescript(SCHEMA_SQL)
