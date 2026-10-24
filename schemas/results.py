"""Result schemas for specialists, growth planner, and orchestrator workflow."""

from __future__ import annotations

from typing import Any, Literal, Optional, List
from pydantic import BaseModel, Field

from schemas.scheme import Scheme


RuleEvaluationStatus = Literal["MET", "NOT_MET", "UNKNOWN"]
OverallEligibility = Literal["ELIGIBLE", "LIKELY_ELIGIBLE", "POTENTIALLY_ELIGIBLE", "NOT_ELIGIBLE"]
GapCategory = Literal[
    "missing_document",
    "missing_registration",
    "missing_skill",
    "missing_qualification",
    "experience_requirement",
    "unmet_fixed_condition",
    "unknown_or_unverifiable",
]
SatisfactionGuarantee = Literal[
    "satisfies_requirement",
    "improves_preparedness",
    "fixed_ineligible",
]


class RuleEvaluationResult(BaseModel):
    """Result of evaluating one specific rule for an applicant."""

    rule_name: str
    description: str
    status: RuleEvaluationStatus
    reason: str


class ActionableGap(BaseModel):
    """Identified eligibility gap with evidence-backed legitimate next steps."""

    gap_type: GapCategory
    requirement_name: str
    description: str
    official_source_url: str
    recommended_action: str
    action_url: Optional[str] = None
    target_opportunity_ids: List[str] = Field(default_factory=list)
    target_opportunity_titles: List[str] = Field(default_factory=list)
    satisfaction_guarantee: SatisfactionGuarantee
    is_actionable: bool = True
    notes: Optional[str] = None


class EligibilityGrowthPlan(BaseModel):
    """Actionable roadmap connecting published eligibility requirements to concrete next steps."""

    summary: str
    actionable_gaps: List[ActionableGap] = Field(default_factory=list)
    high_leverage_actions: List[ActionableGap] = Field(
        default_factory=list,
        description="Actions that unlock or improve eligibility for multiple opportunities",
    )
    fixed_restrictions: List[ActionableGap] = Field(
        default_factory=list,
        description="Statutory legal or fixed conditions that cannot be altered via courses or documents",
    )
    unknown_conditions: List[ActionableGap] = Field(default_factory=list)


class SchemeEvaluation(BaseModel):
    """Consolidated assessment of an applicant's eligibility for a specific scheme or internship."""

    scheme_id: str
    opportunity_type: Literal["scheme", "internship"] = "scheme"
    scheme_name: str
    short_name: str
    category: str
    host_type: Optional[str] = None
    stipend: Optional[str] = None
    duration: Optional[str] = None
    work_mode: Optional[str] = "on_site"
    field_of_study: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    overall_status: OverallEligibility
    met_conditions: List[str] = Field(default_factory=list)
    unmet_conditions: List[str] = Field(default_factory=list)
    unknown_conditions: List[str] = Field(default_factory=list)
    rule_results: List[RuleEvaluationResult] = Field(default_factory=list)
    benefit_summary: str
    benefit_amount: Optional[str] = None
    geographic_coverage: str
    required_documents: List[str] = Field(default_factory=list)
    application_steps: List[str] = Field(default_factory=list)
    official_portal_url: str
    evidence_urls: List[str] = Field(default_factory=list)
    application_dates: str
    last_verified: str
    verification_status: str
    notes: Optional[str] = None
    source_warning: Optional[str] = None
    actionable_gaps: List[ActionableGap] = Field(default_factory=list)


class VerificationCheckResult(BaseModel):
    """Result from the Verification specialist checking scheme source references."""

    scheme_id: str
    is_valid: bool
    has_official_source: bool
    is_secure_https: bool
    is_stale: bool
    last_verified: str
    findings: List[str] = Field(default_factory=list)


class DiscoveryResult(BaseModel):
    """Result of Opportunity Discovery search."""

    category: Optional[str] = None
    opportunity_type: Optional[str] = None
    location_filter: Optional[str] = None
    total_found: int = 0
    schemes: List[Scheme] = Field(default_factory=list)
    reasons: dict[str, str] = Field(default_factory=dict)


class AssessmentReport(BaseModel):
    """Complete multi-specialist citizen assessment result."""

    applicant_summary: dict[str, Any]
    evaluations: List[SchemeEvaluation] = Field(default_factory=list)
    growth_plan: Optional[EligibilityGrowthPlan] = None
    total_opportunities_evaluated: int = 0
    eligible_count: int = 0
    disclaimer: str = (
        "Disclaimer: CivicBridge provides advisory eligibility guidance based on official government records. "
        "This is not an official government sanction or legal guarantee of benefit approval. "
        "Final approval rests exclusively with the respective government departments."
    )
