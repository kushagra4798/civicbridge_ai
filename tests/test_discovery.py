"""Tests for Scheme Discovery Specialist and SchemeSearchTool."""

import pytest
from schemas.applicant import ApplicantProfile
from specialists.discovery import SchemeDiscoverySpecialist
from tools.scheme_search import SchemeSearchTool
from database.repository import SchemeRepository


@pytest.fixture
def search_tool():
    # Uses the local SQLite database
    repo = SchemeRepository()
    return SchemeSearchTool(repository=repo)


@pytest.fixture
def discovery_specialist(search_tool):
    return SchemeDiscoverySpecialist(search_tool=search_tool)


def test_category_filtering_agriculture(discovery_specialist):
    profile = ApplicantProfile(category_interest="agriculture", occupation="farmer")
    result = discovery_specialist.discover(profile)

    assert result.total_found >= 1
    scheme_ids = [s.scheme_id for s in result.schemes]
    assert "pm_kisan" in scheme_ids
    assert all(s.category == "agriculture" for s in result.schemes)


def test_category_filtering_education(discovery_specialist):
    profile = ApplicantProfile(category_interest="education", occupation="student")
    result = discovery_specialist.discover(profile)

    assert result.total_found >= 2
    scheme_ids = [s.scheme_id for s in result.schemes]
    assert "nmmss" in scheme_ids
    assert "post_matric_sc" in scheme_ids


def test_category_filtering_employment(discovery_specialist):
    profile = ApplicantProfile(category_interest="employment", occupation="street_vendor")
    result = discovery_specialist.discover(profile)

    assert result.total_found >= 1
    scheme_ids = [s.scheme_id for s in result.schemes]
    assert "pm_svanidhi" in scheme_ids


def test_geographic_residence_filtering(discovery_specialist):
    # PMAY-G is rural only; PMAY-U is urban only
    rural_profile = ApplicantProfile(category_interest="housing", residence="rural")
    rural_result = discovery_specialist.discover(rural_profile)
    rural_ids = [s.scheme_id for s in rural_result.schemes]

    assert "pmay_g" in rural_ids
    assert "pmay_u" not in rural_ids

    urban_profile = ApplicantProfile(category_interest="housing", residence="urban")
    urban_result = discovery_specialist.discover(urban_profile)
    urban_ids = [s.scheme_id for s in urban_result.schemes]

    assert "pmay_u" in urban_ids
    assert "pmay_g" not in urban_ids


def test_empty_search_fallback(discovery_specialist):
    # Non-existent category
    profile = ApplicantProfile(category_interest="crypto_trading")
    result = discovery_specialist.discover(profile)
    assert result.total_found == 0


def test_scheme_retrieval_by_id(search_tool):
    scheme = search_tool.get_scheme_by_id("pm_kisan")
    assert scheme is not None
    assert scheme.short_name == "PM-KISAN"
    assert scheme.official_portal_url == "https://pmkisan.gov.in"

    missing = search_tool.get_scheme_by_id("non_existent_id")
    assert missing is None
