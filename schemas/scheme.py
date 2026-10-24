"""Scheme and opportunity schema models."""

from __future__ import annotations

from typing import Any, Literal, Optional, List
from pydantic import BaseModel, Field


class EligibilityRule(BaseModel):
    """Deterministic eligibility rule condition for a government scheme or internship."""

    rule_name: str = Field(..., description="Unique rule identifier within scheme, e.g. age_limit, max_income, skills_req")
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
        "education_level",
        "field_of_study",
        "skills",
        "marks_minimum",
        "degree_status",
        "fixed_condition",
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
    """Model representing an official Indian Government Welfare Scheme or Internship Opportunity."""

    scheme_id: str = Field(..., description="Stable unique opportunity identifier, e.g. 'pm_kisan', 'pmis_internship'")
    opportunity_type: Literal["scheme", "internship"] = Field(
        "scheme", description="Opportunity type: scheme or internship"
    )
    name: str = Field(..., description="Full official title of the scheme or internship")
    short_name: str = Field(..., description="Common acronym or short title, e.g. 'PM-KISAN', 'PMIS'")
    description: str = Field(..., description="Comprehensive description of purpose, scope, or learning outcomes")
    category: str = Field(
        ...,
        description="Primary category: agriculture, healthcare, housing, education, pensions, employment, internship",
    )
    governing_department: str = Field(..., description="Ministry, department, or portal administering the opportunity")
    host_type: Optional[Literal["government", "public_sector", "private_via_official_portal"]] = Field(
        None, description="Host organization classification (especially for internships)"
    )
    benefit_summary: str = Field(..., description="Direct summary of benefits provided (cash, subsidy, health cover, learning)")
    benefit_amount: Optional[str] = Field(None, description="Quantified benefit value (e.g. ₹6,000/year, ₹5,00,000)")
    stipend: Optional[str] = Field(None, description="Monthly stipend amount (e.g. ₹5,000 / month, Unstipended)")
    duration: Optional[str] = Field(None, description="Opportunity duration (e.g. 12 months, 6 weeks to 6 months)")
    work_mode: Optional[Literal["on_site", "virtual", "hybrid"]] = Field(
        "on_site", description="Work mode: on_site, virtual, hybrid"
    )
    geographic_coverage: str = Field("All India", description="State or nationwide coverage")
    target_residence: Literal["rural", "urban", "all"] = Field(
        "all", description="Urban/Rural applicability"
    )
    field_of_study: List[str] = Field(
        default_factory=list, description="Target academic fields (e.g. computer_science, engineering, public_policy)"
    )
    required_skills: List[str] = Field(
        default_factory=list, description="Required or preferred technical/functional skills"
    )
    rules: List[EligibilityRule] = Field(
        default_factory=list, description="Structured deterministic eligibility rules"
    )
    required_documents: List[str] = Field(
        default_factory=list, description="List of officially required supporting documents"
    )
    application_steps: List[str] = Field(
        default_factory=list, description="Ordered procedural steps for applying"
    )
    official_portal_url: str = Field(..., description="Primary official government portal URL")
    evidence_urls: List[str] = Field(
        default_factory=list, description="Official gazette, ministry or portal source URLs"
    )
    application_dates: str = Field(
        "Year-round open application", description="Official application window or dates"
    )
    application_deadline: Optional[str] = Field(
        None, description="Specific deadline date or cycle info"
    )
    last_verified: str = Field(..., description="ISO 8601 or YYYY-MM-DD verification date")
    verification_status: Literal["VERIFIED", "UNVERIFIED", "STALE"] = Field(
        "VERIFIED", description="Authenticity and verification state"
    )
    notes: Optional[str] = Field(None, description="Important cautions or special conditions")
