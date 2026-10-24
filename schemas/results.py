"""Result schemas for specialists and orchestrator workflow."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from schemas.scheme import Scheme


RuleEvaluationStatus = Literal["MET", "NOT_MET", "UNKNOWN"]
OverallEligibility = Literal["ELIGIBLE", "LIKELY_ELIGIBLE", "POTENTIALLY_ELIGIBLE", "NOT_ELIGIBLE"]


class RuleEvaluationResult(BaseModel):
    """Result of evaluating one specific rule for an applicant."""

    rule_name: str
    description: str
    status: RuleEvaluationStatus
    reason: str


class SchemeEvaluation(BaseModel):
    """Consolidated assessment of an applicant's eligibility for a specific scheme."""

    scheme_id: str
    scheme_name: str
    short_name: str
    category: str
    overall_status: OverallEligibility
    met_conditions: list[str] = Field(default_factory=list)
    unmet_conditions: list[str] = Field(default_factory=list)
    unknown_conditions: list[str] = Field(default_factory=list)
    rule_results: list[RuleEvaluationResult] = Field(default_factory=list)
    benefit_summary: str
    benefit_amount: Optional[str] = None
    geographic_coverage: str
    required_documents: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)
    official_portal_url: str
    evidence_urls: list[str] = Field(default_factory=list)
    application_dates: str
    last_verified: str
    verification_status: str
    notes: Optional[str] = None
    source_warning: Optional[str] = None


class VerificationCheckResult(BaseModel):
    """Result from the Verification specialist checking scheme source references."""

    scheme_id: str
    is_valid: bool
    has_official_source: bool
    is_secure_https: bool
    is_stale: bool
    last_verified: str
    findings: list[str] = Field(default_factory=list)


class DiscoveryResult(BaseModel):
    """Result of Scheme Discovery search."""

    category: Optional[str] = None
    location_filter: Optional[str] = None
    total_found: int = 0
    schemes: list[Scheme] = Field(default_factory=list)
    reasons: dict[str, str] = Field(default_factory=dict)


class AssessmentReport(BaseModel):
    """Complete multi-specialist citizen assessment result."""

    applicant_summary: dict[str, Any]
    evaluations: list[SchemeEvaluation] = Field(default_factory=list)
    total_schemes_evaluated: int = 0
    eligible_count: int = 0
    disclaimer: str = (
        "Disclaimer: CivicBridge provides advisory eligibility guidance based on official government records. "
        "This is not an official government sanction or legal guarantee of benefit approval. "
        "Final approval rests exclusively with the respective government departments."
    )
