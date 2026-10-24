"""Tests for deterministic eligibility rules engine and EligibilitySpecialist."""

import pytest
from schemas.applicant import ApplicantProfile
from schemas.scheme import EligibilityRule, Scheme
from tools.eligibility_rules import evaluate_rule
from specialists.eligibility import EligibilitySpecialist


def test_age_range_rule_evaluations():
    rule = EligibilityRule(
        rule_name="age_condition",
        description="Must be between 18 and 40 years old",
        rule_type="age_range",
        parameters={"min_age": 18, "max_age": 40},
    )

    # 1. MET
    res_met = evaluate_rule(rule, ApplicantProfile(age=25))
    assert res_met.status == "MET"
    assert "within the eligible window" in res_met.reason

    # 2. NOT_MET (too young)
    res_young = evaluate_rule(rule, ApplicantProfile(age=16))
    assert res_young.status == "NOT_MET"

    # 3. NOT_MET (too old)
    res_old = evaluate_rule(rule, ApplicantProfile(age=55))
    assert res_old.status == "NOT_MET"

    # 4. UNKNOWN
    res_unknown = evaluate_rule(rule, ApplicantProfile(age=None))
    assert res_unknown.status == "UNKNOWN"
    assert "unknown" in res_unknown.reason.lower()


def test_residence_rule_evaluations():
    rule = EligibilityRule(
        rule_name="rural_only",
        description="Must reside in rural village",
        rule_type="residence",
        parameters={"allowed": ["rural"]},
    )

    # MET
    assert evaluate_rule(rule, ApplicantProfile(residence="rural")).status == "MET"

    # NOT_MET
    assert evaluate_rule(rule, ApplicantProfile(residence="urban")).status == "NOT_MET"

    # UNKNOWN
    assert evaluate_rule(rule, ApplicantProfile(residence=None)).status == "UNKNOWN"


def test_occupation_rule_evaluations():
    rule = EligibilityRule(
        rule_name="farmer_only",
        description="Must be a practicing farmer",
        rule_type="occupation",
        parameters={"allowed": ["farmer", "cultivator"]},
    )

    assert evaluate_rule(rule, ApplicantProfile(occupation="farmer")).status == "MET"
    assert evaluate_rule(rule, ApplicantProfile(occupation="student")).status == "NOT_MET"
    assert evaluate_rule(rule, ApplicantProfile(occupation=None)).status == "UNKNOWN"


def test_income_limit_rule_evaluations():
    rule = EligibilityRule(
        rule_name="income_cap",
        description="Annual income up to 2.5 Lakh",
        rule_type="income_limit",
        parameters={"max_annual_income": 250000.0},
    )

    # MET (within limit)
    assert evaluate_rule(rule, ApplicantProfile(annual_income=180000.0)).status == "MET"

    # NOT_MET (exceeds limit)
    assert evaluate_rule(rule, ApplicantProfile(annual_income=450000.0)).status == "NOT_MET"

    # UNKNOWN (no income stated)
    assert evaluate_rule(rule, ApplicantProfile(annual_income=None)).status == "UNKNOWN"

    # MET via BPL card exception
    assert evaluate_rule(rule, ApplicantProfile(annual_income=None, is_bpl=True)).status == "MET"


def test_caste_rule_evaluations():
    rule = EligibilityRule(
        rule_name="sc_only",
        description="Scheduled Caste community members only",
        rule_type="caste",
        parameters={"allowed_castes": ["SC"]},
    )

    assert evaluate_rule(rule, ApplicantProfile(caste_category="SC")).status == "MET"
    assert evaluate_rule(rule, ApplicantProfile(caste_category="General")).status == "NOT_MET"
    assert evaluate_rule(rule, ApplicantProfile(caste_category=None)).status == "UNKNOWN"


def test_landholding_rule_evaluations():
    rule = EligibilityRule(
        rule_name="small_farmer",
        description="Landholding up to 2.0 hectares",
        rule_type="landholding_max",
        parameters={"max_hectares": 2.0},
    )

    assert evaluate_rule(rule, ApplicantProfile(landholding_ha=1.5)).status == "MET"
    assert evaluate_rule(rule, ApplicantProfile(landholding_ha=3.5)).status == "NOT_MET"
    assert evaluate_rule(rule, ApplicantProfile(landholding_ha=None)).status == "UNKNOWN"


def test_disqualification_taxpayer_rule():
    rule = EligibilityRule(
        rule_name="taxpayer_disqualification",
        description="Income tax payers are excluded",
        rule_type="disqualification",
        parameters={"disqualify_if_taxpayer": True},
    )

    assert evaluate_rule(rule, ApplicantProfile(is_taxpayer=False)).status == "MET"
    assert evaluate_rule(rule, ApplicantProfile(is_taxpayer=True)).status == "NOT_MET"
    assert evaluate_rule(rule, ApplicantProfile(is_taxpayer=None)).status == "UNKNOWN"


def test_overall_eligibility_aggregation():
    specialist = EligibilitySpecialist()

    scheme = Scheme(
        scheme_id="test_scheme",
        name="Test Scheme",
        short_name="TEST",
        description="Testing aggregation logic",
        category="agriculture",
        governing_department="Test Dept",
        benefit_summary="Test benefit",
        geographic_coverage="All India",
        target_residence="all",
        rules=[
            EligibilityRule(
                rule_name="age_check",
                description="Age 18-40",
                rule_type="age_range",
                parameters={"min_age": 18, "max_age": 40},
            ),
            EligibilityRule(
                rule_name="occupation_check",
                description="Must be farmer",
                rule_type="occupation",
                parameters={"allowed": ["farmer"]},
            ),
        ],
        required_documents=["Aadhaar"],
        application_steps=["Apply online"],
        official_portal_url="https://test.gov.in",
        last_verified="2026-03-01",
    )

    # 1. All MET -> ELIGIBLE
    eval_eligible = specialist.evaluate_scheme(scheme, ApplicantProfile(age=25, occupation="farmer"))
    assert eval_eligible.overall_status == "ELIGIBLE"
    assert len(eval_eligible.met_conditions) == 2
    assert len(eval_eligible.unmet_conditions) == 0

    # 2. At least one NOT_MET -> NOT_ELIGIBLE
    eval_not_eligible = specialist.evaluate_scheme(scheme, ApplicantProfile(age=50, occupation="farmer"))
    assert eval_not_eligible.overall_status == "NOT_ELIGIBLE"
    assert len(eval_not_eligible.unmet_conditions) == 1

    # 3. Some MET, some UNKNOWN -> LIKELY_ELIGIBLE
    eval_likely = specialist.evaluate_scheme(scheme, ApplicantProfile(age=25, occupation=None))
    assert eval_likely.overall_status == "LIKELY_ELIGIBLE"
    assert len(eval_likely.met_conditions) == 1
    assert len(eval_likely.unknown_conditions) == 1

    # 4. All UNKNOWN -> POTENTIALLY_ELIGIBLE
    eval_potential = specialist.evaluate_scheme(scheme, ApplicantProfile(age=None, occupation=None))
    assert eval_potential.overall_status == "POTENTIALLY_ELIGIBLE"
    assert len(eval_potential.unknown_conditions) == 2
