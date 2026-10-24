"""Eligibility Specialist evaluating structured rules deterministically."""

from __future__ import annotations

import logging
from typing import List

from schemas.applicant import ApplicantProfile
from schemas.scheme import Scheme
from schemas.results import SchemeEvaluation, OverallEligibility, RuleEvaluationResult
from tools.eligibility_rules import evaluate_rule

logger = logging.getLogger(__name__)


class EligibilitySpecialist:
    """Specialist responsible for deterministic, evidence-backed eligibility assessments."""

    def evaluate_scheme(self, scheme: Scheme, profile: ApplicantProfile) -> SchemeEvaluation:
        """Evaluate a single scheme or internship against citizen attributes deterministically."""
        rule_results: List[RuleEvaluationResult] = []
        met: List[str] = []
        unmet: List[str] = []
        unknown: List[str] = []

        for rule in scheme.rules:
            result = evaluate_rule(rule, profile)
            rule_results.append(result)
            if result.status == "MET":
                met.append(f"{rule.description} ({result.reason})")
            elif result.status == "NOT_MET":
                unmet.append(f"{rule.description} ({result.reason})")
            else:
                unknown.append(f"{rule.description} ({result.reason})")

        # Determine overall status deterministically:
        # If any condition is NOT_MET, the applicant is NOT_ELIGIBLE.
        # If all conditions are MET, the applicant is ELIGIBLE.
        # If no NOT_MET, but some UNKNOWN:
        #   - LIKELY_ELIGIBLE if at least 1 condition is MET.
        #   - POTENTIALLY_ELIGIBLE if all conditions are UNKNOWN.
        overall: OverallEligibility
        if unmet:
            overall = "NOT_ELIGIBLE"
        elif not unknown and met:
            overall = "ELIGIBLE"
        elif met and unknown:
            overall = "LIKELY_ELIGIBLE"
        elif not met and not unknown:
            overall = "ELIGIBLE"  # Opportunity had no restrictive conditions
        else:
            overall = "POTENTIALLY_ELIGIBLE"

        return SchemeEvaluation(
            scheme_id=scheme.scheme_id,
            opportunity_type=scheme.opportunity_type,
            scheme_name=scheme.name,
            short_name=scheme.short_name,
            category=scheme.category,
            host_type=scheme.host_type,
            stipend=scheme.stipend,
            duration=scheme.duration,
            work_mode=scheme.work_mode or "on_site",
            field_of_study=scheme.field_of_study,
            required_skills=scheme.required_skills,
            overall_status=overall,
            met_conditions=met,
            unmet_conditions=unmet,
            unknown_conditions=unknown,
            rule_results=rule_results,
            benefit_summary=scheme.benefit_summary,
            benefit_amount=scheme.benefit_amount,
            geographic_coverage=scheme.geographic_coverage,
            required_documents=scheme.required_documents,
            application_steps=scheme.application_steps,
            official_portal_url=scheme.official_portal_url,
            evidence_urls=scheme.evidence_urls,
            application_dates=scheme.application_dates,
            last_verified=scheme.last_verified,
            verification_status=scheme.verification_status,
            notes=scheme.notes,
        )

    def evaluate_all(self, schemes: List[Scheme], profile: ApplicantProfile) -> List[SchemeEvaluation]:
        """Evaluate all candidate opportunities for an applicant, sorted by relevance and eligibility."""
        evaluations = [self.evaluate_scheme(s, profile) for s in schemes]

        # Order by: ELIGIBLE > LIKELY_ELIGIBLE > POTENTIALLY_ELIGIBLE > NOT_ELIGIBLE
        priority = {
            "ELIGIBLE": 0,
            "LIKELY_ELIGIBLE": 1,
            "POTENTIALLY_ELIGIBLE": 2,
            "NOT_ELIGIBLE": 3,
        }
        evaluations.sort(key=lambda e: priority.get(e.overall_status, 4))
        return evaluations
