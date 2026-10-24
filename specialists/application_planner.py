"""Application Planning Specialist creating customized checklists and application roadmaps."""

from __future__ import annotations

import logging
from typing import List, Dict, Any
from schemas.applicant import ApplicantProfile
from schemas.results import SchemeEvaluation

logger = logging.getLogger(__name__)


class ApplicationPlanningSpecialist:
    """Specialist responsible for generating actionable step-by-step guidance and personalized document checklists."""

    def generate_plan(
        self, evaluation: SchemeEvaluation, profile: ApplicantProfile
    ) -> Dict[str, Any]:
        """Produce an actionable, personalized application roadmap."""
        # 1. Tailored document checklist
        personalized_docs: List[str] = []
        for doc in evaluation.required_documents:
            # Add applicant-specific notes
            doc_lower = doc.lower()
            if "caste" in doc_lower and profile.caste_category:
                personalized_docs.append(
                    f"{doc} (for {profile.caste_category} category verification from Tehsildar/SDO)"
                )
            elif "income" in doc_lower and profile.annual_income:
                personalized_docs.append(
                    f"{doc} (certifying annual family income under ₹{profile.annual_income:,.0f})"
                )
            elif "land" in doc_lower and profile.landholding_ha:
                personalized_docs.append(
                    f"{doc} (showing current holding of ~{profile.landholding_ha} hectares)"
                )
            else:
                personalized_docs.append(doc)

        # 2. Key Action Items & Preconditions
        action_items: List[str] = []
        if evaluation.unknown_conditions:
            action_items.append(
                "Resolve pending conditions: " + "; ".join(evaluation.unknown_conditions[:2])
            )

        action_items.append("Ensure your Aadhaar is linked with your active mobile number for OTP e-KYC.")
        action_items.append("Ensure your bank account is active and seeded with Aadhaar (NPCI mapping for DBT).")

        return {
            "scheme_id": evaluation.scheme_id,
            "scheme_name": evaluation.scheme_name,
            "short_name": evaluation.short_name,
            "eligibility_status": evaluation.overall_status,
            "benefit_summary": evaluation.benefit_summary,
            "official_portal_url": evaluation.official_portal_url,
            "application_dates": evaluation.application_dates,
            "documents_checklist": personalized_docs,
            "application_steps": evaluation.application_steps,
            "prerequisites": action_items,
            "source_warning": evaluation.source_warning,
            "last_verified": evaluation.last_verified,
        }
