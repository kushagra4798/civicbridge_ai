"""Scheme Search Tool connecting to local SQLite Scheme Repository."""

from __future__ import annotations

from typing import Optional
from database.repository import SchemeRepository
from schemas.applicant import ApplicantProfile
from schemas.scheme import Scheme
from schemas.results import DiscoveryResult


class SchemeSearchTool:
    """Tool for querying and ranking schemes from the database based on applicant attributes."""

    def __init__(self, repository: Optional[SchemeRepository] = None) -> None:
        self.repository = repository or SchemeRepository()

    def discover_schemes(self, profile: ApplicantProfile) -> DiscoveryResult:
        """Find candidate schemes matching citizen profile parameters.
        
        Applies hierarchical filtering:
        1. If category_interest is given, filters primarily on category.
        2. Applies residence (rural/urban) filtering if specified.
        3. Applies state geographic filtering if specified.
        4. When category is unspecified, infers from occupation or searches across all.
        """
        category = profile.category_interest
        if not category and profile.occupation:
            if profile.occupation == "farmer":
                category = "agriculture"
            elif profile.occupation == "student":
                category = "education"
            elif profile.occupation in ("street_vendor", "artisan"):
                category = "employment"

        candidates: list[Scheme] = []
        reasons: dict[str, str] = {}

        if category:
            candidates = self.repository.search(
                category=category,
                residence=profile.residence,
                state=profile.state,
            )
            for c in candidates:
                reasons[c.scheme_id] = f"Matched primary benefit category '{category}'"
        else:
            # Broad search across all schemes
            candidates = self.repository.search(
                residence=profile.residence,
                state=profile.state,
            )
            for c in candidates:
                reasons[c.scheme_id] = "Candidate across general welfare programs"

        # If candidates are empty, try fallback without residence constraint
        if not candidates and profile.residence:
            candidates = self.repository.search(category=category, state=profile.state)
            for c in candidates:
                reasons[c.scheme_id] = f"Matched category '{category}' (residence constraint relaxed)"

        return DiscoveryResult(
            category=category,
            location_filter=f"{profile.state or 'All India'} ({profile.residence or 'All'})",
            total_found=len(candidates),
            schemes=candidates,
            reasons=reasons,
        )

    def get_scheme_by_id(self, scheme_id: str) -> Optional[Scheme]:
        """Fetch scheme by unique ID."""
        return self.repository.get_by_id(scheme_id)
