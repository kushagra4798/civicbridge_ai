"""Tests for Government Internship Discovery, Field of Study, and Deterministic Matching."""

import pytest
from schemas.applicant import ApplicantProfile
from specialists.discovery import SchemeDiscoverySpecialist
from specialists.eligibility import EligibilitySpecialist
from tools.scheme_search import SchemeSearchTool
from database.repository import SchemeRepository


@pytest.fixture
def search_tool():
    return SchemeSearchTool(repository=SchemeRepository())


@pytest.fixture
def discovery_specialist(search_tool):
    return SchemeDiscoverySpecialist(search_tool=search_tool)


@pytest.fixture
def eligibility_specialist():
    return EligibilitySpecialist()


def test_discover_internships_category(discovery_specialist):
    """Verify that asking for internships returns verified government and official portal internships."""
    profile = ApplicantProfile(
        opportunity_interest="internships",
        category_interest="internship",
        occupation="student",
    )
    result = discovery_specialist.discover(profile)

    assert result.total_found >= 4
    opp_ids = [s.scheme_id for s in result.schemes]
    assert "pmis_internship" in opp_ids
    assert "niti_aayog_internship" in opp_ids
    assert "digital_india_internship" in opp_ids
    assert "tulip_internship" in opp_ids


def test_distinguish_government_vs_private_portal_hosts(search_tool):
    """Verify that government-hosted internships are clearly distinguished from official portal company internships."""
    pmis = search_tool.get_scheme_by_id("pmis_internship")
    assert pmis.host_type == "private_via_official_portal"
    assert "top 500" in pmis.description.lower()
    assert pmis.official_portal_url == "https://pminternship.mca.gov.in"

    niti = search_tool.get_scheme_by_id("niti_aayog_internship")
    assert niti.host_type == "government"
    assert "niti aayog" in niti.governing_department.lower()

    digital_india = search_tool.get_scheme_by_id("digital_india_internship")
    assert digital_india.host_type == "government"


def test_internship_matching_by_field_of_study_cs(search_tool, eligibility_specialist):
    """Test matching and rule evaluation for Computer Science / IT internships."""
    digital_india = search_tool.get_scheme_by_id("digital_india_internship")
    assert digital_india is not None

    # CS student with >=60% marks
    cs_student = ApplicantProfile(
        occupation="student",
        education_level="graduate",
        field_of_study="computer_science",
        current_degree_status="pursuing",
        marks_percentage=72.5,
    )
    evaluation = eligibility_specialist.evaluate_scheme(digital_india, cs_student)
    assert evaluation.overall_status == "ELIGIBLE"
    assert len(evaluation.met_conditions) >= 2
    assert len(evaluation.unmet_conditions) == 0

    # Non-CS student (e.g. Arts)
    arts_student = ApplicantProfile(
        occupation="student",
        education_level="graduate",
        field_of_study="arts",
        current_degree_status="pursuing",
        marks_percentage=75.0,
    )
    eval_arts = eligibility_specialist.evaluate_scheme(digital_india, arts_student)
    assert eval_arts.overall_status == "NOT_ELIGIBLE"
    assert any("field of study" in u.lower() for u in eval_arts.unmet_conditions)


def test_internship_matching_by_academic_marks_cutoff(search_tool, eligibility_specialist):
    """NITI Aayog requires min 85% in Class 12 for undergraduate applicants."""
    niti = search_tool.get_scheme_by_id("niti_aayog_internship")

    # High-achieving student (88%)
    student_88 = ApplicantProfile(
        occupation="student",
        field_of_study="economics",
        current_degree_status="pursuing",
        marks_percentage=88.0,
    )
    eval_88 = eligibility_specialist.evaluate_scheme(niti, student_88)
    assert eval_88.overall_status == "ELIGIBLE"

    # Student with 78% (below 85% cutoff)
    student_78 = ApplicantProfile(
        occupation="student",
        field_of_study="economics",
        current_degree_status="pursuing",
        marks_percentage=78.0,
    )
    eval_78 = eligibility_specialist.evaluate_scheme(niti, student_78)
    assert eval_78.overall_status == "NOT_ELIGIBLE"
    assert any("below required cutoff" in u.lower() for u in eval_78.unmet_conditions)


def test_internship_matching_by_degree_status_tulip(search_tool, eligibility_specialist):
    """TULIP requires fresh graduates within 18-24 months of degree completion."""
    tulip = search_tool.get_scheme_by_id("tulip_internship")

    # Fresh graduate
    fresh_grad = ApplicantProfile(
        education_level="graduate",
        current_degree_status="fresh_graduate",
    )
    eval_grad = eligibility_specialist.evaluate_scheme(tulip, fresh_grad)
    assert eval_grad.overall_status == "ELIGIBLE"

    # Currently pursuing student (not yet graduated)
    pursuing = ApplicantProfile(
        education_level="class_12_pass",
        current_degree_status="pursuing",
    )
    eval_pursuing = eligibility_specialist.evaluate_scheme(tulip, pursuing)
    assert eval_pursuing.overall_status == "NOT_ELIGIBLE"
