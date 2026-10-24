"""Repository for persistent SQLite scheme and internship storage and retrieval."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from database.models import init_db
from schemas.scheme import Scheme, EligibilityRule


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "civicbridge.db"


class SchemeRepository:
    """Provides structured data access to schemes and internships stored in SQLite."""

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
        keys = row.keys()

        opportunity_type = row["opportunity_type"] if "opportunity_type" in keys else "scheme"
        host_type = row["host_type"] if "host_type" in keys else None
        stipend = row["stipend"] if "stipend" in keys else None
        duration = row["duration"] if "duration" in keys else None
        work_mode = row["work_mode"] if "work_mode" in keys else "on_site"
        app_deadline = row["application_deadline"] if "application_deadline" in keys else None

        field_of_study = []
        if "field_of_study_json" in keys and row["field_of_study_json"]:
            try:
                field_of_study = json.loads(row["field_of_study_json"])
            except Exception:
                pass

        required_skills = []
        if "required_skills_json" in keys and row["required_skills_json"]:
            try:
                required_skills = json.loads(row["required_skills_json"])
            except Exception:
                pass

        return Scheme(
            scheme_id=row["scheme_id"],
            opportunity_type=opportunity_type or "scheme",
            name=row["name"],
            short_name=row["short_name"],
            description=row["description"],
            category=row["category"],
            governing_department=row["governing_department"],
            host_type=host_type,
            benefit_summary=row["benefit_summary"],
            benefit_amount=row["benefit_amount"],
            stipend=stipend,
            duration=duration,
            work_mode=work_mode or "on_site",
            geographic_coverage=row["geographic_coverage"],
            target_residence=row["target_residence"],
            field_of_study=field_of_study,
            required_skills=required_skills,
            rules=rules,
            required_documents=json.loads(row["required_documents_json"]),
            application_steps=json.loads(row["application_steps_json"]),
            official_portal_url=row["official_portal_url"],
            evidence_urls=json.loads(row["evidence_urls_json"]),
            application_dates=row["application_dates"],
            application_deadline=app_deadline,
            last_verified=row["last_verified"],
            verification_status=row["verification_status"],
            notes=row["notes"],
        )

    def save(self, scheme: Scheme) -> None:
        """Insert or replace a scheme or internship record."""
        rules_json = json.dumps([r.model_dump() for r in scheme.rules])
        req_docs_json = json.dumps(scheme.required_documents)
        app_steps_json = json.dumps(scheme.application_steps)
        evidence_urls_json = json.dumps(scheme.evidence_urls)
        field_study_json = json.dumps(scheme.field_of_study)
        skills_json = json.dumps(scheme.required_skills)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO schemes (
                    scheme_id, opportunity_type, name, short_name, description, category,
                    governing_department, host_type, benefit_summary, benefit_amount,
                    stipend, duration, work_mode, geographic_coverage, target_residence,
                    field_of_study_json, required_skills_json, rules_json,
                    required_documents_json, application_steps_json, official_portal_url,
                    evidence_urls_json, application_dates, application_deadline,
                    last_verified, verification_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scheme.scheme_id,
                    scheme.opportunity_type,
                    scheme.name,
                    scheme.short_name,
                    scheme.description,
                    scheme.category,
                    scheme.governing_department,
                    scheme.host_type,
                    scheme.benefit_summary,
                    scheme.benefit_amount,
                    scheme.stipend,
                    scheme.duration,
                    scheme.work_mode,
                    scheme.geographic_coverage,
                    scheme.target_residence,
                    field_study_json,
                    skills_json,
                    rules_json,
                    req_docs_json,
                    app_steps_json,
                    scheme.official_portal_url,
                    evidence_urls_json,
                    scheme.application_dates,
                    scheme.application_deadline,
                    scheme.last_verified,
                    scheme.verification_status,
                    scheme.notes,
                ),
            )

    def get_by_id(self, scheme_id: str) -> Optional[Scheme]:
        """Fetch opportunity by its unique identifier."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM schemes WHERE scheme_id = ?", (scheme_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_scheme(row)
            return None

    def list_all(self) -> list[Scheme]:
        """Return all schemes and internships stored in the database."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM schemes ORDER BY opportunity_type, category, name")
            return [self._row_to_scheme(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Count total stored opportunities."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM schemes")
            return cursor.fetchone()[0]

    def find_by_category(self, category: str) -> list[Scheme]:
        """Find opportunities matching category."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM schemes WHERE LOWER(category) = LOWER(?) ORDER BY name",
                (category,),
            )
            return [self._row_to_scheme(row) for row in cursor.fetchall()]

    def search(
        self,
        category: Optional[str] = None,
        opportunity_type: Optional[str] = None,
        residence: Optional[str] = None,
        state: Optional[str] = None,
        field_of_study: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[Scheme]:
        """Filter opportunities by category, opportunity_type, residence, location, and query."""
        clauses = []
        params = []

        if opportunity_type and opportunity_type != "both":
            clauses.append("opportunity_type = ?")
            params.append(opportunity_type)

        if category and category != "all":
            clauses.append("LOWER(category) = LOWER(?)")
            params.append(category)

        if residence and residence != "both":
            clauses.append("(target_residence = 'all' OR target_residence = ?)")
            params.append(residence)

        if state and state != "All India":
            clauses.append("(geographic_coverage LIKE 'All India%' OR geographic_coverage LIKE ?)")
            params.append(f"%{state}%")

        if field_of_study:
            f_param = f"%{field_of_study.lower()}%"
            clauses.append(
                "(field_of_study_json LIKE ? OR field_of_study_json LIKE '%\"general\"%' OR field_of_study_json LIKE '%\"any\"%' OR field_of_study_json = '[]')"
            )
            params.append(f_param)

        if query:
            q_param = f"%{query.lower()}%"
            clauses.append("(LOWER(name) LIKE ? OR LOWER(short_name) LIKE ? OR LOWER(description) LIKE ?)")
            params.extend([q_param, q_param, q_param])

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM schemes {where_stmt} ORDER BY opportunity_type DESC, name ASC"

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [self._row_to_scheme(row) for row in cursor.fetchall()]
