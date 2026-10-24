"""Scheme Discovery Specialist for finding relevant welfare schemes."""

from __future__ import annotations

import logging
from typing import Optional

from schemas.applicant import ApplicantProfile
from schemas.results import DiscoveryResult
from tools.scheme_search import SchemeSearchTool

logger = logging.getLogger(__name__)


class SchemeDiscoverySpecialist:
    """Specialist responsible for searching and filtering government schemes."""

    def __init__(self, search_tool: Optional[SchemeSearchTool] = None) -> None:
        self.search_tool = search_tool or SchemeSearchTool()

    def discover(self, profile: ApplicantProfile) -> DiscoveryResult:
        """Find candidate schemes matching applicant criteria."""
        logger.info(
            f"Discovering schemes for category='{profile.category_interest}', "
            f"occupation='{profile.occupation}', residence='{profile.residence}', state='{profile.state}'"
        )
        return self.search_tool.discover_schemes(profile)
