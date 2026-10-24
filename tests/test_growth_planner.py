"""Tests for Capability C: Eligibility Growth Planner."""

import pytest
from schemas.applicant import ApplicantProfile
from schemas.scheme import Scheme, EligibilityRule
from schemas.results import SchemeEvaluation, RuleEvaluationResult
from specialists.application_planner import ApplicationPlanningSpecialist


@pytest.fixture
def planner():
    return ApplicationPlanningSpecialist()


def test_growth_planner_identifies_actionable_gaps(planner):
    profile = ApplicantProfile(occupation="student", state="Rajasthan")

    evaluations = [
        SchemeEvaluation(
            scheme_id="scheme_a",
            scheme_name="Scholarship Scheme A",
            short_name="SCH-A",
            category="education",
            overall_status="POTENTIALLY_ELIGIBLE",
            unknown_conditions=["Annual family income must not exceed ₹2,50,000"],
            benefit_summary="Assistance",
            geographic_coverage="All India",
            official_portal_url="https://scholarships.gov.in",
            application_dates="Rolling",
            last_verified="2026-03-01",
            verification_status="VERIFIED",
        ),
        SchemeEvaluation(
            scheme_id="internship_b",
            opportunity_type="internship",
            scheme_name="Government Tech Internship",
            short_name="TECH-INT",
            category="internship",
            overall_status="POTENTIALLY_ELIGIBLE",
            unknown_conditions=["Must have programming skill in Python"],
            benefit_summary="Stipend",
            geographic_coverage="All India",
            official_portal_url="https://internship.gov.in",
            application_dates="Rolling",
            last_verified="2026-03-01",
            verification_status="VERIFIED",
        ),
    ]

    growth_plan = planner.generate_growth_plan(evaluations, profile)
    assert growth_plan is not None
    assert len(growth_plan.actionable_gaps) >= 2

    # Verify income document gap
    income_gap = next((g for g in growth_plan.actionable_gaps if "income" in g.requirement_name.lower()), None)
    assert income_gap is not None
    assert income_gap.gap_type == "missing_document"
    assert income_gap.is_actionable is True
    assert income_gap.satisfaction_guarantee == "satisfies_requirement"
    assert "Tehsildar" in income_gap.recommended_action

    # Verify skill gap
    skill_gap = next((g for g in growth_plan.actionable_gaps if g.gap_type == "missing_skill"), None)
    assert skill_gap is not None
    assert skill_gap.satisfaction_guarantee == "improves_preparedness"
    assert "swayam.gov.in" in skill_gap.action_url
    assert "does not automatically guarantee selection" in skill_gap.notes.lower()


def test_growth_planner_identifies_high_leverage_actions(planner):
    profile = ApplicantProfile(occupation="student")

    evaluations = [
        SchemeEvaluation(
            scheme_id="sch_1",
            scheme_name="Merit Scholarship 1",
            short_name="MS-1",
            category="education",
            overall_status="POTENTIALLY_ELIGIBLE",
            unknown_conditions=["Family annual income below 2.5 Lakh"],
            benefit_summary="₹12,000",
            geographic_coverage="All India",
            official_portal_url="https://scholarships.gov.in",
            application_dates="Rolling",
            last_verified="2026-03-01",
            verification_status="VERIFIED",
        ),
        SchemeEvaluation(
            scheme_id="sch_2",
            scheme_name="Post Matric Scholarship 2",
            short_name="PMS-2",
            category="education",
            overall_status="POTENTIALLY_ELIGIBLE",
            unknown_conditions=["Family annual income limit verification"],
            benefit_summary="Fee waiver",
            geographic_coverage="All India",
            official_portal_url="https://scholarships.gov.in",
            application_dates="Rolling",
            last_verified="2026-03-01",
            verification_status="VERIFIED",
        ),
    ]

    growth_plan = planner.generate_growth_plan(evaluations, profile)
    assert len(growth_plan.high_leverage_actions) >= 1

    income_hl = next((g for g in growth_plan.high_leverage_actions if "income" in g.requirement_name.lower()), None)
    assert income_hl is not None
    assert len(income_hl.target_opportunity_titles) >= 2
    assert "MS-1" in income_hl.target_opportunity_titles
    assert "PMS-2" in income_hl.target_opportunity_titles


def test_fixed_restrictions_are_not_presented_as_actionable_gaps(planner):
    """Statutory boundaries (age limit, taxpayer exclusion) must be marked non-actionable."""
    profile = ApplicantProfile(age=29, is_taxpayer=True)

    evaluations = [
        SchemeEvaluation(
            scheme_id="pmis",
            opportunity_type="internship",
            scheme_name="PM Internship Scheme",
            short_name="PMIS",
            category="internship",
            overall_status="NOT_ELIGIBLE",
            unmet_conditions=[
                "Applicant age (29 yrs) is outside the eligible window [21-24].",
                "Applicant or spouse is an income tax payer (statutorily excluded).",
            ],
            benefit_summary="Stipend",
            geographic_coverage="All India",
            official_portal_url="https://pminternship.mca.gov.in",
            application_dates="Rolling",
            last_verified="2026-03-20",
            verification_status="VERIFIED",
        )
    ]

    growth_plan = planner.generate_growth_plan(evaluations, profile)
    assert len(growth_plan.fixed_restrictions) >= 1

    for fixed in growth_plan.fixed_restrictions:
        assert fixed.is_actionable is False
        assert fixed.satisfaction_guarantee == "fixed_ineligible"
        assert "statutory" in fixed.notes.lower()
        # Verify it is NOT promoted as a legitimate actionable gap
        assert fixed not in growth_plan.actionable_gaps
