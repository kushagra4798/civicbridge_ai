"""Opportunity Search Tool connecting to local SQLite Scheme & Internship Repository."""

from __future__ import annotations

from typing import Optional, List
from database.repository import SchemeRepository
from schemas.applicant import ApplicantProfile
from schemas.scheme import Scheme
from schemas.results import DiscoveryResult

SCHEME_SPECIFIC_CATEGORIES = {"agriculture", "housing", "healthcare", "pensions"}
VALID_CATEGORIES = {"agriculture", "housing", "healthcare", "pensions", "education", "employment", "internship"}


class SchemeSearchTool:
    """Tool for querying and ranking schemes and internships from the database based on applicant attributes."""

    def __init__(self, repository: Optional[SchemeRepository] = None) -> None:
        self.repository = repository or SchemeRepository()

    def discover_schemes(self, profile: ApplicantProfile) -> DiscoveryResult:
        """Find candidate schemes and/or internships matching citizen profile parameters.
        
        Applies multi-channel retrieval:
        1. Identifies opportunity types requested (schemes, internships, or both).
        2. Retrieves domain-matching welfare schemes.
        3. Retrieves field- and qualification-matching internships when requested or relevant.
        4. Applies location, residence, and field-of-study filters with progressive relaxation.
        """
        category = profile.category_interest
        opp_interest = profile.opportunity_interest or "both"

        # If user explicitly specified an unknown category (e.g. crypto_trading), return empty
        if category and category.lower() not in VALID_CATEGORIES and opp_interest != "internships":
            return DiscoveryResult(
                category=category,
                opportunity_type=opp_interest,
                location_filter=f"{profile.state or 'All India'} ({profile.residence or 'All'})",
                total_found=0,
                schemes=[],
                reasons={},
            )

        if not category and profile.occupation:
            if profile.occupation == "farmer":
                category = "agriculture"
            elif profile.occupation == "student":
                category = "education"
            elif profile.occupation in ("street_vendor", "artisan"):
                category = "employment"

        candidates: List[Scheme] = []
        reasons: dict[str, str] = {}

        # Channel 1: Schemes
        if opp_interest in ("schemes", "both") and category != "internship":
            scheme_res = self.repository.search(
                category=category if category != "internship" else None,
                opportunity_type="scheme",
                residence=profile.residence,
                state=profile.state,
            )
            for c in scheme_res:
                candidates.append(c)
                reasons[c.scheme_id] = f"Matched welfare category '{c.category}'"

            # If no schemes found and residence was restrictive, relax residence
            if not scheme_res and profile.residence and category:
                relaxed = self.repository.search(
                    category=category,
                    opportunity_type="scheme",
                    state=profile.state,
                )
                for c in relaxed:
                    candidates.append(c)
                    reasons[c.scheme_id] = f"Matched welfare category '{c.category}' (location relaxed)"

        # Channel 2: Internships
        # Search internships if:
        # - User explicitly requested internships (opp_interest == "internships")
        # - Category is "internship"
        # - opp_interest is "both" AND category is not restricted to farmer/housing/health/pensions AND not unknown category
        should_search_internships = False
        if opp_interest == "internships" or category == "internship":
            should_search_internships = True
        elif opp_interest == "both":
            if category in ("education", "employment", None):
                should_search_internships = True
            elif profile.occupation in ("student", "scholar", None) and category not in SCHEME_SPECIFIC_CATEGORIES:
                should_search_internships = True

        if should_search_internships:
            intern_res = self.repository.search(
                opportunity_type="internship",
                field_of_study=profile.field_of_study,
                state=profile.state,
            )
            # If restrictive field of study returned few, fetch all national internships
            if len(intern_res) < 2:
                all_interns = self.repository.search(opportunity_type="internship")
                for item in all_interns:
                    if item.scheme_id not in [c.scheme_id for c in intern_res]:
                        intern_res.append(item)

            for i in intern_res:
                if i.scheme_id not in [c.scheme_id for c in candidates]:
                    candidates.append(i)
                    host_label = "Govt" if i.host_type == "government" else "Public/Private Portal"
                    reasons[i.scheme_id] = f"Matched official internship opportunity ({host_label})"

        # Deduplicate candidates preserving insertion order
        seen = set()
        deduped = []
        for c in candidates:
            if c.scheme_id not in seen:
                seen.add(c.scheme_id)
                deduped.append(c)

        return DiscoveryResult(
            category=category,
            opportunity_type=opp_interest,
            location_filter=f"{profile.state or 'All India'} ({profile.residence or 'All'})",
            total_found=len(deduped),
            schemes=deduped,
            reasons=reasons,
        )

    def get_scheme_by_id(self, scheme_id: str) -> Optional[Scheme]:
        """Fetch scheme or internship by unique ID."""
        return self.repository.get_by_id(scheme_id)
