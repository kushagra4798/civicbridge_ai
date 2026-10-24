"""Scheme and rule schema models."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class EligibilityRule(BaseModel):
    """Deterministic eligibility rule condition for a government scheme."""

    rule_name: str = Field(..., description="Unique rule identifier within scheme, e.g. age_limit, max_income")
    description: str = Field(..., description="Human-readable condition statement")
    rule_type: Literal[
        "age_range",
        "residence",
        "occupation",
        "income_limit",
        "caste",
        "landholding_max",
        "is_landholder",
        "education_min",
        "disqualification",
        "gender",
        "maternity",
        "bpl_required",
    ] = Field(..., description="Machine-evaluable condition category")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Thresholds or allowed values for deterministic evaluation",
    )


class Scheme(BaseModel):
    """Model representing an official Indian Government Welfare or Benefit Scheme."""

    scheme_id: str = Field(..., description="Stable unique scheme identifier, e.g. 'pm_kisan'")
    name: str = Field(..., description="Full official title of the scheme")
    short_name: str = Field(..., description="Common acronym or short title, e.g. 'PM-KISAN'")
    description: str = Field(..., description="Comprehensive description of purpose and scope")
    category: Literal[
        "agriculture",
        "healthcare",
        "housing",
        "education",
        "pensions",
        "employment",
    ] = Field(..., description="Primary benefit category")
    governing_department: str = Field(..., description="Ministry or department administering the scheme")
    benefit_summary: str = Field(..., description="Direct summary of benefits provided (cash, subsidy, health cover)")
    benefit_amount: Optional[str] = Field(None, description="Quantified benefit value (e.g. ₹6,000/year, ₹5,00,000)")
    geographic_coverage: str = Field("All India", description="State or nationwide coverage")
    target_residence: Literal["rural", "urban", "all"] = Field(
        "all", description="Urban/Rural applicability"
    )
    rules: list[EligibilityRule] = Field(
        default_factory=list, description="Structured deterministic eligibility rules"
    )
    required_documents: list[str] = Field(
        default_factory=list, description="List of officially required supporting documents"
    )
    application_steps: list[str] = Field(
        default_factory=list, description="Ordered procedural steps for applying"
    )
    official_portal_url: str = Field(..., description="Primary official government portal URL")
    evidence_urls: list[str] = Field(
        default_factory=list, description="Official gazette, ministry or myScheme source URLs"
    )
    application_dates: str = Field(
        "Year-round open application", description="Official application window or dates"
    )
    last_verified: str = Field(..., description="ISO 8601 or YYYY-MM-DD verification date")
    verification_status: Literal["VERIFIED", "UNVERIFIED", "STALE"] = Field(
        "VERIFIED", description="Authenticity and verification state"
    )
    notes: Optional[str] = Field(None, description="Important cautions or special conditions")
