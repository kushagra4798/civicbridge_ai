"""Application & Pathway Planning Specialist.

Generates:
1. Tailored document checklists and step-by-step application roadmaps for specific opportunities.
2. The CivicBridge Eligibility Growth Planner — connecting published requirements to concrete,
   evidence-backed legitimate next steps, high-leverage multi-opportunity actions, and fixed restrictions.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from schemas.applicant import ApplicantProfile
from schemas.results import (
    SchemeEvaluation,
    ActionableGap,
    EligibilityGrowthPlan,
    GapCategory,
    SatisfactionGuarantee,
)

logger = logging.getLogger(__name__)


class ApplicationPlanningSpecialist:
    """Specialist responsible for application roadmaps and the Eligibility Growth Planner."""

    def generate_plan(
        self, evaluation: SchemeEvaluation, profile: ApplicantProfile
    ) -> Dict[str, Any]:
        """Produce an actionable, personalized application roadmap for a single selected opportunity."""
        personalized_docs: List[str] = []
        for doc in evaluation.required_documents:
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

        action_items: List[str] = []
        if evaluation.unknown_conditions:
            action_items.append(
                "Resolve pending conditions: " + "; ".join(evaluation.unknown_conditions[:2])
            )

        # Standard DBT and e-KYC prerequisites
        action_items.append("Ensure your Aadhaar is linked with your active mobile number for OTP e-KYC.")
        action_items.append("Ensure your bank account is active and seeded with Aadhaar (NPCI mapping for DBT).")

        return {
            "scheme_id": evaluation.scheme_id,
            "opportunity_type": evaluation.opportunity_type,
            "scheme_name": evaluation.scheme_name,
            "short_name": evaluation.short_name,
            "host_type": evaluation.host_type,
            "stipend": evaluation.stipend,
            "duration": evaluation.duration,
            "work_mode": evaluation.work_mode,
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

    def generate_growth_plan(
        self, evaluations: List[SchemeEvaluation], profile: ApplicantProfile
    ) -> EligibilityGrowthPlan:
        """Construct the Eligibility Growth Plan comparing profile against candidate requirements.
        
        Identifies actionable gaps, maps them to official next steps, classifies high-leverage actions
        that unlock multiple opportunities, and marks fixed statutory restrictions honestly.
        """
        all_gaps: List[ActionableGap] = []
        action_map: Dict[str, ActionableGap] = {}

        for eval_item in evaluations:
            # 1. Analyze UNMET conditions
            for unmet_desc in eval_item.unmet_conditions:
                lower = unmet_desc.lower()

                # Check: Is this a fixed legal restriction?
                if any(w in lower for w in ["outside the eligible window", "age", "taxpayer", "income tax", "pucca house"]):
                    gap = ActionableGap(
                        gap_type="unmet_fixed_condition",
                        requirement_name=f"Fixed Criterion: {eval_item.short_name}",
                        description=unmet_desc,
                        official_source_url=eval_item.official_portal_url,
                        recommended_action=(
                            "Statutory condition cannot be altered through documentation or courses. "
                            "Focus on alternative opportunities with compatible eligibility boundaries."
                        ),
                        action_url=None,
                        target_opportunity_ids=[eval_item.scheme_id],
                        target_opportunity_titles=[eval_item.short_name],
                        satisfaction_guarantee="fixed_ineligible",
                        is_actionable=False,
                        notes="Strict statutory requirement; never attempt to circumvent or falsify.",
                    )
                    all_gaps.append(gap)

                elif "skill" in lower:
                    # Missing skill gap
                    action_key = "skill_dev"
                    if action_key not in action_map:
                        action_map[action_key] = ActionableGap(
                            gap_type="missing_skill",
                            requirement_name="Technical & Practical Skill Competencies",
                            description="Opportunity requires verified competency in domain skills.",
                            official_source_url=eval_item.official_portal_url,
                            recommended_action=(
                                "Enroll in free government-recognized certification courses on SWAYAM / NPTEL "
                                "(e.g., Python, Data Analytics, GIS) to build verifiable skills and portfolio projects."
                            ),
                            action_url="https://swayam.gov.in",
                            target_opportunity_ids=[eval_item.scheme_id],
                            target_opportunity_titles=[eval_item.short_name],
                            satisfaction_guarantee="improves_preparedness",
                            is_actionable=True,
                            notes="Completing training improves preparedness and fulfills prerequisite knowledge, but does not automatically guarantee selection.",
                        )
                    else:
                        action_map[action_key].target_opportunity_ids.append(eval_item.scheme_id)
                        action_map[action_key].target_opportunity_titles.append(eval_item.short_name)

                elif "percentage" in lower or "cutoff" in lower or "marks" in lower:
                    # Academic marks qualification
                    gap = ActionableGap(
                        gap_type="missing_qualification",
                        requirement_name=f"Academic Score Cutoff ({eval_item.short_name})",
                        description=unmet_desc,
                        official_source_url=eval_item.official_portal_url,
                        recommended_action=(
                            "Academic aggregate is below this scheme's minimum cutoff. "
                            "Focus on academic coursework for upcoming terms, or target opportunities without rigid cutoffs (e.g. PMIS or TULIP)."
                        ),
                        action_url=None,
                        target_opportunity_ids=[eval_item.scheme_id],
                        target_opportunity_titles=[eval_item.short_name],
                        satisfaction_guarantee="improves_preparedness",
                        is_actionable=False,
                    )
                    all_gaps.append(gap)

            # 2. Analyze UNKNOWN / PENDING conditions (Actionable gaps)
            for unknown_desc in eval_item.unknown_conditions:
                lower = unknown_desc.lower()

                # A. Income proof
                if "income" in lower:
                    action_key = "doc_income"
                    if action_key not in action_map:
                        action_map[action_key] = ActionableGap(
                            gap_type="missing_document",
                            requirement_name="Official Family Income Certificate",
                            description="Annual family income limit verification.",
                            official_source_url=eval_item.official_portal_url,
                            recommended_action=(
                                "Apply for a formal Family Income Certificate from the Tehsildar / Sub-Divisional Magistrate "
                                "via your State e-District portal or nearest Common Services Centre (CSC)."
                            ),
                            action_url="https://services.india.gov.in/service/search?query=income+certificate",
                            target_opportunity_ids=[eval_item.scheme_id],
                            target_opportunity_titles=[eval_item.short_name],
                            satisfaction_guarantee="satisfies_requirement",
                            is_actionable=True,
                            notes="Valid for 1 financial year; required by all economic assistance programs.",
                        )
                    else:
                        action_map[action_key].target_opportunity_ids.append(eval_item.scheme_id)
                        action_map[action_key].target_opportunity_titles.append(eval_item.short_name)

                # B. Caste / Social Category proof
                elif "caste" in lower or "social" in lower:
                    action_key = "doc_caste"
                    if action_key not in action_map:
                        action_map[action_key] = ActionableGap(
                            gap_type="missing_document",
                            requirement_name="Caste / Social Category Certificate",
                            description="Verification of reservation category (SC / ST / OBC-NCL / EWS).",
                            official_source_url=eval_item.official_portal_url,
                            recommended_action=(
                                "Obtain a verified Category Certificate / Non-Creamy Layer (NCL) certificate issued "
                                "by the competent Revenue Authority (Tehsildar / SDO)."
                            ),
                            action_url="https://services.india.gov.in/service/search?query=caste+certificate",
                            target_opportunity_ids=[eval_item.scheme_id],
                            target_opportunity_titles=[eval_item.short_name],
                            satisfaction_guarantee="satisfies_requirement",
                            is_actionable=True,
                        )
                    else:
                        action_map[action_key].target_opportunity_ids.append(eval_item.scheme_id)
                        action_map[action_key].target_opportunity_titles.append(eval_item.short_name)

                # C. Land records
                elif "land" in lower:
                    action_key = "doc_land"
                    if action_key not in action_map:
                        action_map[action_key] = ActionableGap(
                            gap_type="missing_document",
                            requirement_name="Agricultural Land Ownership Record (Khatauni / RoR)",
                            description="Cultivable landholding title proof.",
                            official_source_url=eval_item.official_portal_url,
                            recommended_action=(
                                "Download your digitally signed Record of Rights (RoR / Khatauni) from your state land records (Bhulekh) portal."
                            ),
                            action_url="https://services.india.gov.in/service/search?query=land+records+khatauni",
                            target_opportunity_ids=[eval_item.scheme_id],
                            target_opportunity_titles=[eval_item.short_name],
                            satisfaction_guarantee="satisfies_requirement",
                            is_actionable=True,
                        )
                    else:
                        action_map[action_key].target_opportunity_ids.append(eval_item.scheme_id)
                        action_map[action_key].target_opportunity_titles.append(eval_item.short_name)

                # D. College NOC / Bonafide
                elif "degree" in lower or "marks" in lower or "student" in lower or "bonafide" in lower:
                    action_key = "doc_bonafide"
                    if action_key not in action_map:
                        action_map[action_key] = ActionableGap(
                            gap_type="missing_document",
                            requirement_name="Institutional Bonafide Certificate & NOC",
                            description="Official proof of ongoing college enrollment and permission to intern.",
                            official_source_url=eval_item.official_portal_url,
                            recommended_action=(
                                "Request an official Bonafide Certificate and No Objection Certificate (NOC) from your "
                                "College Principal / Dean / HOD on institute letterhead."
                            ),
                            action_url=None,
                            target_opportunity_ids=[eval_item.scheme_id],
                            target_opportunity_titles=[eval_item.short_name],
                            satisfaction_guarantee="satisfies_requirement",
                            is_actionable=True,
                            notes="Required by NITI Aayog, Digital India, and RBI internship verification committees.",
                        )
                    else:
                        action_map[action_key].target_opportunity_ids.append(eval_item.scheme_id)
                        action_map[action_key].target_opportunity_titles.append(eval_item.short_name)

                # E. Skills declaration
                elif "skill" in lower:
                    action_key = "skill_dev"
                    if action_key not in action_map:
                        action_map[action_key] = ActionableGap(
                            gap_type="missing_skill",
                            requirement_name="Technical & Functional Skills",
                            description="Prerequisite project skills (Python, GIS, Data Analysis).",
                            official_source_url=eval_item.official_portal_url,
                            recommended_action=(
                                "Complete recognized online courses on SWAYAM / NPTEL (Government of India) "
                                "and publish code or analysis samples in a portfolio."
                            ),
                            action_url="https://swayam.gov.in",
                            target_opportunity_ids=[eval_item.scheme_id],
                            target_opportunity_titles=[eval_item.short_name],
                            satisfaction_guarantee="improves_preparedness",
                            is_actionable=True,
                            notes="Prepares for technical screening; does not automatically guarantee selection.",
                        )
                    else:
                        action_map[action_key].target_opportunity_ids.append(eval_item.scheme_id)
                        action_map[action_key].target_opportunity_titles.append(eval_item.short_name)

        # 3. Add Portal Registrations as universal high-leverage actions if relevant
        has_student_opps = any(
            e.category in ("education", "internship") or e.opportunity_type == "internship"
            for e in evaluations
        )
        if has_student_opps:
            # National Scholarship Portal OTR
            action_map["reg_nsp"] = ActionableGap(
                gap_type="missing_registration",
                requirement_name="National Scholarship Portal (NSP) One-Time Registration",
                description="Universal student registration for Central and State scholarships.",
                official_source_url="https://scholarships.gov.in",
                recommended_action=(
                    "Complete One-Time Registration (OTR) on the National Scholarship Portal using Aadhaar e-KYC."
                ),
                action_url="https://scholarships.gov.in",
                target_opportunity_ids=["nmmss", "post_matric_sc"],
                target_opportunity_titles=["NMMSS", "Post-Matric SC"],
                satisfaction_guarantee="satisfies_requirement",
                is_actionable=True,
                notes="Generates a unique OTR ID valid across all educational schemes.",
            )
            # AICTE Portal Registration
            action_map["reg_aicte"] = ActionableGap(
                gap_type="missing_registration",
                requirement_name="AICTE National Internship Portal Registration",
                description="Centralized student profile for government and urban internships.",
                official_source_url="https://internship.aicte-india.org",
                recommended_action=(
                    "Register and build a student profile on the AICTE National Internship Portal to apply directly for TULIP and urban bodies."
                ),
                action_url="https://internship.aicte-india.org",
                target_opportunity_ids=["tulip_internship"],
                target_opportunity_titles=["TULIP"],
                satisfaction_guarantee="satisfies_requirement",
                is_actionable=True,
            )

        # 4. Classify into High-Leverage Actions vs Regular vs Fixed
        actionable_gaps = list(action_map.values())
        # Deduplicate opportunity titles
        for g in actionable_gaps:
            g.target_opportunity_titles = list(dict.fromkeys(g.target_opportunity_titles))

        high_leverage = [g for g in actionable_gaps if len(g.target_opportunity_titles) >= 2]
        fixed_restrictions = [g for g in all_gaps if g.gap_type == "unmet_fixed_condition"]

        summary = (
            f"CivicBridge identified {len(actionable_gaps)} actionable next steps. "
            f"{len(high_leverage)} action(s) offer high cross-opportunity leverage to qualify for multiple schemes and internships."
        )

        return EligibilityGrowthPlan(
            summary=summary,
            actionable_gaps=actionable_gaps,
            high_leverage_actions=high_leverage,
            fixed_restrictions=fixed_restrictions,
            unknown_conditions=[g for g in all_gaps if g.gap_type == "unknown_or_unverifiable"],
        )
