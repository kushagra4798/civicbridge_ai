"""Seed script to populate SQLite database from curated data/schemes.json."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is in path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.repository import SchemeRepository
from schemas.scheme import Scheme, EligibilityRule

logger = logging.getLogger(__name__)


def seed_database(
    json_path: Optional[str | Path] = None,
    db_path: Optional[str | Path] = None,
) -> int:
    """Load curated schemes and internships JSON into the SQLite repository."""
    source_json = Path(json_path) if json_path else PROJECT_ROOT / "data" / "schemes.json"

    if not source_json.exists():
        raise FileNotFoundError(f"Scheme seed dataset not found at {source_json}")

    with open(source_json, "r", encoding="utf-8") as f:
        records = json.load(f)

    repo = SchemeRepository(db_path=db_path)
    count = 0
    for item in records:
        rules = [EligibilityRule(**r) for r in item.get("rules", [])]
        scheme = Scheme(
            scheme_id=item["scheme_id"],
            opportunity_type=item.get("opportunity_type", "scheme"),
            name=item["name"],
            short_name=item["short_name"],
            description=item["description"],
            category=item["category"],
            governing_department=item["governing_department"],
            host_type=item.get("host_type"),
            benefit_summary=item["benefit_summary"],
            benefit_amount=item.get("benefit_amount"),
            stipend=item.get("stipend"),
            duration=item.get("duration"),
            work_mode=item.get("work_mode", "on_site"),
            geographic_coverage=item.get("geographic_coverage", "All India"),
            target_residence=item.get("target_residence", "all"),
            field_of_study=item.get("field_of_study", []),
            required_skills=item.get("required_skills", []),
            rules=rules,
            required_documents=item.get("required_documents", []),
            application_steps=item.get("application_steps", []),
            official_portal_url=item["official_portal_url"],
            evidence_urls=item.get("evidence_urls", []),
            application_dates=item.get("application_dates", "Open year-round"),
            application_deadline=item.get("application_deadline"),
            last_verified=item.get("last_verified", "2026-03-01"),
            verification_status=item.get("verification_status", "VERIFIED"),
            notes=item.get("notes"),
        )
        repo.save(scheme)
        count += 1

    print(f"Successfully seeded {count} official opportunities (schemes & internships) into database: {repo.db_path}")
    return count


if __name__ == "__main__":
    seed_database()
