"""Deterministic eligibility rules evaluator for Indian government schemes."""

from __future__ import annotations

from typing import Tuple
from schemas.applicant import ApplicantProfile
from schemas.scheme import EligibilityRule
from schemas.results import RuleEvaluationResult, RuleEvaluationStatus


# Hierarchy for education levels to allow deterministic comparisons
EDUCATION_RANK = {
    "none": 0,
    "class_8_pass": 1,
    "class_10_pass": 2,
    "class_12_pass": 3,
    "graduate": 4,
    "post_graduate": 5,
}


def evaluate_rule(rule: EligibilityRule, profile: ApplicantProfile) -> RuleEvaluationResult:
    """Evaluate a single structured rule against an applicant profile deterministically.
    
    Returns:
        RuleEvaluationResult with status MET, NOT_MET, or UNKNOWN, and human-readable explanation.
    """
    params = rule.parameters
    r_type = rule.rule_type
    r_name = rule.rule_name
    desc = rule.description

    # 1. AGE RANGE
    if r_type == "age_range":
        min_age = params.get("min_age", 0)
        max_age = params.get("max_age", 125)
        if profile.age is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Applicant age is unknown; requires age between {min_age} and {max_age} years.",
            )
        if min_age <= profile.age <= max_age:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Applicant age ({profile.age} yrs) is within the eligible window [{min_age}-{max_age}].",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Applicant age ({profile.age} yrs) is outside the eligible window [{min_age}-{max_age}].",
        )

    # 2. RESIDENCE (Rural / Urban)
    if r_type == "residence":
        allowed = params.get("allowed", [])
        if profile.residence is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Residence type (rural/urban) is not specified; scheme requires {', '.join(allowed)}.",
            )
        if profile.residence in allowed or "all" in allowed:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Applicant residence ({profile.residence}) satisfies requirement ({', '.join(allowed)}).",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Applicant residence ({profile.residence}) does not match allowed locations ({', '.join(allowed)}).",
        )

    # 3. OCCUPATION
    if r_type == "occupation":
        allowed = params.get("allowed", [])
        if profile.occupation is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Occupation is not specified; requires applicant to be in: {', '.join(allowed)}.",
            )
        if profile.occupation in allowed:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Applicant occupation '{profile.occupation}' matches eligible occupations.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Applicant occupation '{profile.occupation}' is not listed in eligible categories ({', '.join(allowed)}).",
        )

    # 4. INCOME CEILING
    if r_type == "income_limit":
        max_income = float(params.get("max_annual_income", 0.0))
        if profile.annual_income is None:
            # If BPL is confirmed, low income is inferred
            if profile.is_bpl:
                return RuleEvaluationResult(
                    rule_name=r_name,
                    description=desc,
                    status="MET",
                    reason=f"Income verified via BPL ration card status (scheme limit: ₹{max_income:,.0f}).",
                )
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Family annual income is unknown; must not exceed ₹{max_income:,.0f} per year.",
            )
        if profile.annual_income <= max_income:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Annual family income (₹{profile.annual_income:,.0f}) is within limit of ₹{max_income:,.0f}.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Annual family income (₹{profile.annual_income:,.0f}) exceeds maximum threshold of ₹{max_income:,.0f}.",
        )

    # 5. CASTE / SOCIAL RESERVATION
    if r_type == "caste":
        allowed = params.get("allowed_castes", [])
        if profile.caste_category is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Social / caste category is not specified; scheme requires {', '.join(allowed)}.",
            )
        if profile.caste_category in allowed:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Caste category ({profile.caste_category}) is eligible.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Caste category ({profile.caste_category}) is not in target categories ({', '.join(allowed)}).",
        )

    # 6. LANDHOLDING CEILING
    if r_type == "landholding_max":
        max_ha = float(params.get("max_hectares", 2.0))
        if profile.landholding_ha is None:
            if profile.is_landholder is False:
                # Landless is within <= 2.0 ha ceiling
                return RuleEvaluationResult(
                    rule_name=r_name,
                    description=desc,
                    status="MET",
                    reason="Landless applicant meets maximum land ceiling condition.",
                )
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Landholding acreage is not confirmed; ceiling is {max_ha} hectares.",
            )
        if profile.landholding_ha <= max_ha:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Landholding ({profile.landholding_ha} ha) is within ceiling of {max_ha} hectares.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Landholding ({profile.landholding_ha} ha) exceeds ceiling of {max_ha} hectares.",
        )

    # 7. IS LANDHOLDER (Cultivable Land Ownership)
    if r_type == "is_landholder":
        if profile.is_landholder is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason="Cultivable land ownership status is unknown; requires land title in family name.",
            )
        if profile.is_landholder is True:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason="Applicant owns cultivable agricultural land.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason="Scheme requires ownership of agricultural land (tenant/landless farmers not covered under this specific component).",
        )

    # 8. MINIMUM EDUCATION
    if r_type == "education_min":
        min_level = params.get("min_level", "none")
        if profile.education_level is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Education qualification is not specified; requires at least {min_level.replace('_', ' ').title()}.",
            )
        applicant_rank = EDUCATION_RANK.get(profile.education_level, 0)
        required_rank = EDUCATION_RANK.get(min_level, 0)
        if applicant_rank >= required_rank:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Education level ({profile.education_level.replace('_', ' ')}) meets minimum requirement ({min_level.replace('_', ' ')}).",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Education level ({profile.education_level.replace('_', ' ')}) is below required {min_level.replace('_', ' ')}.",
        )

    # 9. DISQUALIFYING CRITERIA (Income tax, existing pucca house)
    if r_type == "disqualification":
        if params.get("disqualify_if_taxpayer"):
            if profile.is_taxpayer is None:
                return RuleEvaluationResult(
                    rule_name=r_name,
                    description=desc,
                    status="UNKNOWN",
                    reason="Income tax payer status unknown; income tax payers are disqualified.",
                )
            if profile.is_taxpayer is True:
                return RuleEvaluationResult(
                    rule_name=r_name,
                    description=desc,
                    status="NOT_MET",
                    reason="Applicant or spouse is an income tax payer (statutorily excluded).",
                )
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason="Applicant does not pay income tax; meets non-taxpayer requirement.",
            )

        if params.get("no_pucca_house"):
            # If citizen already has pucca house, disqualified for PMAY
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason="No record of existing pucca house ownership.",
            )

        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="MET",
            reason="No disqualifying conditions triggered.",
        )

    # 10. GENDER
    if r_type == "gender":
        allowed_gender = params.get("allowed_gender")
        if profile.gender is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason=f"Gender is not specified; scheme requires {allowed_gender}.",
            )
        if profile.gender == allowed_gender:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason=f"Gender condition ({allowed_gender}) satisfied.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason=f"Scheme is designated exclusively for {allowed_gender} applicants.",
        )

    # 11. MATERNITY
    if r_type == "maternity":
        if profile.is_pregnant_or_lactating is None:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason="Maternity / pregnancy status unknown; scheme requires pregnant or lactating mother.",
            )
        if profile.is_pregnant_or_lactating is True:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason="Confirmed pregnant or lactating mother.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason="Scheme provides maternity benefits exclusively to pregnant and lactating mothers.",
        )

    # 12. BPL / SECC
    if r_type == "bpl_required":
        if profile.is_bpl is None:
            if profile.annual_income is not None and profile.annual_income <= 150000.0:
                return RuleEvaluationResult(
                    rule_name=r_name,
                    description=desc,
                    status="MET",
                    reason=f"Low income (₹{profile.annual_income:,.0f}) supports economic deprivation eligibility.",
                )
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="UNKNOWN",
                reason="BPL / SECC 2011 inclusion or low-income status is not confirmed.",
            )
        if profile.is_bpl is True:
            return RuleEvaluationResult(
                rule_name=r_name,
                description=desc,
                status="MET",
                reason="Applicant confirmed Below Poverty Line (BPL) ration card holder.",
            )
        return RuleEvaluationResult(
            rule_name=r_name,
            description=desc,
            status="NOT_MET",
            reason="Scheme requires BPL / SECC 2011 economic deprivation status.",
        )

    # Fallback for generic or unhandled rule types
    return RuleEvaluationResult(
        rule_name=r_name,
        description=desc,
        status="UNKNOWN",
        reason=f"Condition '{r_name}' requires manual review at application time.",
    )
