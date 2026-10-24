"""Repository for persistent SQLite scheme storage and retrieval."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from database.models import init_db
from schemas.scheme import Scheme, EligibilityRule


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "civicbridge.db"


class SchemeRepository:
    """Provides structured data access to schemes stored in SQLite."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_initialized()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_initialized(self) -> None:
        with self._get_connection() as conn:
            init_db(conn)

    def _row_to_scheme(self, row: sqlite3.Row) -> Scheme:
        rules_data = json.loads(row["rules_json"])
        rules = [EligibilityRule(**r) for r in rules_data]

        return Scheme(
            scheme_id=row["scheme_id"],
            name=row["name"],
            short_name=row["short_name"],
            description=row["description"],
            category=row["category"],
            governing_department=row["governing_department"],
            benefit_summary=row["benefit_summary"],
            benefit_amount=row["benefit_amount"],
            geographic_coverage=row["geographic_coverage"],
            target_residence=row["target_residence"],
            rules=rules,
            required_documents=json.loads(row["required_documents_json"]),
            application_steps=json.loads(row["application_steps_json"]),
            official_portal_url=row["official_portal_url"],
            evidence_urls=json.loads(row["evidence_urls_json"]),
            application_dates=row["application_dates"],
            last_verified=row["last_verified"],
            verification_status=row["verification_status"],
            notes=row["notes"],
        )

    def save(self, scheme: Scheme) -> None:
        """Insert or replace a scheme record."""
        rules_json = json.dumps([r.model_dump() for r in scheme.rules])
        req_docs_json = json.dumps(scheme.required_documents)
        app_steps_json = json.dumps(scheme.application_steps)
        evidence_urls_json = json.dumps(scheme.evidence_urls)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO schemes (
                    scheme_id, name, short_name, description, category,
                    governing_department, benefit_summary, benefit_amount,
                    geographic_coverage, target_residence, rules_json,
                    required_documents_json, application_steps_json,
                    official_portal_url, evidence_urls_json, application_dates,
                    last_verified, verification_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scheme.scheme_id,
                    scheme.name,
                    scheme.short_name,
                    scheme.description,
                    scheme.category,
                    scheme.governing_department,
                    scheme.benefit_summary,
                    scheme.benefit_amount,
                    scheme.geographic_coverage,
                    scheme.target_residence,
                    rules_json,
                    req_docs_json,
                    app_steps_json,
                    scheme.official_portal_url,
                    evidence_urls_json,
                    scheme.application_dates,
                    scheme.last_verified,
                    scheme.verification_status,
                    scheme.notes,
                ),
            )

    def get_by_id(self, scheme_id: str) -> Optional[Scheme]:
        """Fetch scheme by its unique identifier."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM schemes WHERE scheme_id = ?", (scheme_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_scheme(row)
            return None

    def list_all(self) -> list[Scheme]:
        """Return all schemes stored in the database."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM schemes ORDER BY category, name")
            return [self._row_to_scheme(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Count total stored schemes."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM schemes")
            return cursor.fetchone()[0]

    def find_by_category(self, category: str) -> list[Scheme]:
        """Find schemes matching category."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM schemes WHERE LOWER(category) = LOWER(?) ORDER BY name",
                (category,),
            )
            return [self._row_to_scheme(row) for row in cursor.fetchall()]

    def search(
        self,
        category: Optional[str] = None,
        residence: Optional[str] = None,
        state: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[Scheme]:
        """Filter schemes by category, residence, location, and optional text search."""
        clauses = []
        params = []

        if category:
            clauses.append("LOWER(category) = LOWER(?)")
            params.append(category)

        if residence and residence != "both":
            # Scheme applies if target_residence is 'all' or matches applicant's residence
            clauses.append("(target_residence = 'all' OR target_residence = ?)")
            params.append(residence)

        if state and state != "All India":
            clauses.append("(geographic_coverage LIKE 'All India%' OR geographic_coverage LIKE ?)")
            params.append(f"%{state}%")

        if query:
            q_param = f"%{query.lower()}%"
            clauses.append("(LOWER(name) LIKE ? OR LOWER(short_name) LIKE ? OR LOWER(description) LIKE ?)")
            params.extend([q_param, q_param, q_param])

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM schemes {where_stmt} ORDER BY name"

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [self._row_to_scheme(row) for row in cursor.fetchall()]
