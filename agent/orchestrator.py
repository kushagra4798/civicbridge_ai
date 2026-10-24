"""Multi-specialist orchestrator for CivicBridge government benefits navigation."""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from uuid import uuid4

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    TextContent,
    EndSessionContent,
)

from schemas.applicant import ApplicantProfile, extract_profile_from_text
from schemas.results import SchemeEvaluation
from specialists.discovery import SchemeDiscoverySpecialist
from specialists.eligibility import EligibilitySpecialist
from specialists.verification import VerificationSpecialist
from specialists.application_planner import ApplicationPlanningSpecialist
from agent.cards import (
    create_schemes_list_chat_message,
    create_scheme_detail_chat_message,
)

logger = logging.getLogger(__name__)

# Regular expressions for detecting card selections in text
CARD_SELECTION_RE = re.compile(r"scheme[_\s-]?id[\s:=\"']*([A-Za-z0-9_\-]+)", re.IGNORECASE)
BACK_TO_SCHEMES_RE = re.compile(r"back[_\s-]?to[_\s-]?schemes", re.IGNORECASE)
SENSITIVE_12_DIGIT_RE = re.compile(r"\b[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\b")


class UserSession:
    """Tracks state and accumulated profile for an active citizen chat session."""

    def __init__(self, sender_id: str) -> None:
        self.sender_id = sender_id
        self.profile = ApplicantProfile()
        self.last_evaluations: List[SchemeEvaluation] = []
        self.state: str = "INITIAL"
        self.pending_question_field: Optional[str] = None


class CivicBridgeOrchestrator:
    """Coordinates specialist components to assess citizen eligibility and deliver guidance."""

    def __init__(
        self,
        discovery_specialist: Optional[SchemeDiscoverySpecialist] = None,
        eligibility_specialist: Optional[EligibilitySpecialist] = None,
        verification_specialist: Optional[VerificationSpecialist] = None,
        planner_specialist: Optional[ApplicationPlanningSpecialist] = None,
    ) -> None:
        self.discovery = discovery_specialist or SchemeDiscoverySpecialist()
        self.eligibility = eligibility_specialist or EligibilitySpecialist()
        self.verification = verification_specialist or VerificationSpecialist()
        self.planner = planner_specialist or ApplicationPlanningSpecialist()
        self._sessions: Dict[str, UserSession] = {}

    def get_or_create_session(self, sender_id: str) -> UserSession:
        if sender_id not in self._sessions:
            self._sessions[sender_id] = UserSession(sender_id)
        return self._sessions[sender_id]

    def _parse_card_action(self, text: str) -> Optional[Dict[str, str]]:
        """Parse card selection JSON or prose forwarded by chat UI."""
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                if isinstance(data, dict):
                    return {k: str(v) for k, v in data.items()}
            except Exception:
                pass

        if BACK_TO_SCHEMES_RE.search(stripped):
            return {"action": "back_to_schemes"}

        match = CARD_SELECTION_RE.search(stripped)
        if match:
            return {"action": "view_checklist", "scheme_id": match.group(1)}

        return None

    def _format_shortlist_markdown(
        self, profile: ApplicantProfile, evaluations: List[SchemeEvaluation]
    ) -> str:
        """Render concise, evidence-backed markdown presentation of candidate schemes."""
        profile_parts = []
        if profile.state:
            profile_parts.append(f"**State:** {profile.state}")
        if profile.residence:
            profile_parts.append(f"**Residence:** {profile.residence.title()}")
        if profile.age:
            profile_parts.append(f"**Age:** {profile.age} yrs")
        if profile.occupation:
            profile_parts.append(f"**Occupation:** {profile.occupation.replace('_', ' ').title()}")
        if profile.annual_income:
            profile_parts.append(f"**Income:** ₹{profile.annual_income:,.0f}/yr")
        if profile.education_level:
            profile_parts.append(f"**Education:** {profile.education_level.replace('_', ' ').title()}")

        profile_header = " · ".join(profile_parts) if profile_parts else "General Citizen Profile"

        lines = [
            "### 🇮🇳 CivicBridge Benefits Assessment",
            f"*{profile_header}*\n",
        ]

        if not evaluations:
            lines.append("No active government schemes matched your exact criteria in our verified catalog.")
            lines.append("Try specifying a different benefit category (agriculture, education, housing, healthcare, pensions, employment).")
            return "\n".join(lines)

        lines.append(f"Found **{len(evaluations)} candidate schemes** matching your profile:\n")

        for idx, item in enumerate(evaluations, 1):
            badge = "🟢 **ELIGIBLE**" if item.overall_status == "ELIGIBLE" else (
                "🟡 **LIKELY ELIGIBLE**" if item.overall_status == "LIKELY_ELIGIBLE" else (
                    "⚪ **POTENTIALLY ELIGIBLE**" if item.overall_status == "POTENTIALLY_ELIGIBLE" else "🔴 **NOT ELIGIBLE**"
                )
            )

            lines.append(f"#### {idx}. [{item.short_name}] {item.scheme_name} — {badge}")
            lines.append(f"**Benefit:** {item.benefit_summary}")
            if item.benefit_amount:
                lines.append(f"**Assistance Value:** `{item.benefit_amount}`")
            lines.append(f"**Geographic Coverage:** {item.geographic_coverage}")

            # Breakdown of conditions
            if item.met_conditions:
                lines.append(f"- ✅ **Met Conditions:** {'; '.join(item.met_conditions[:3])}")
            if item.unknown_conditions:
                lines.append(f"- ❓ **Pending Verification:** {'; '.join(item.unknown_conditions[:3])}")
            if item.unmet_conditions:
                lines.append(f"- ❌ **Unmet Condition:** {'; '.join(item.unmet_conditions[:2])}")

            # Official links and freshness
            lines.append(f"- 🔗 **Official Portal:** [{item.official_portal_url}]({item.official_portal_url})")
            lines.append(f"- 📅 **Application Window:** {item.application_dates} *(Verified: {item.last_verified})*")

            if item.source_warning:
                lines.append(f"- ⚠️ *{item.source_warning}*")

            lines.append("")

        lines.append("---")
        lines.append("👉 **Next Step:** Type the scheme acronym (e.g. `PM-KISAN`, `PM-JAY`, `NMMSS`) or tap the card button below for your customized document checklist and step-by-step application instructions.")
        lines.append("\n*Disclaimer: Eligibility guidance is advisory and based on verified public norms. Final approval rests with the respective government departments.*")

        return "\n".join(lines)

    def _format_scheme_detail_markdown(
        self, plan: Dict[str, Any]
    ) -> str:
        """Render detailed document checklist and application roadmap."""
        badge = "🟢 **ELIGIBLE**" if plan.get("eligibility_status") == "ELIGIBLE" else (
            "🟡 **LIKELY ELIGIBLE**" if plan.get("eligibility_status") == "LIKELY_ELIGIBLE" else "⚪ **POTENTIALLY ELIGIBLE**"
        )

        lines = [
            f"### 📋 Application Roadmap: {plan.get('short_name')}",
            f"**{plan.get('scheme_name')}** ({badge})\n",
            f"**Benefit Provided:** {plan.get('benefit_summary')}",
            f"**Official Portal:** [{plan.get('official_portal_url')}]({plan.get('official_portal_url')})",
            f"**Application Timeline:** {plan.get('application_dates')}\n",
            "#### 📂 Personalized Document Checklist:",
        ]

        for doc in plan.get("documents_checklist", []):
            lines.append(f"- [ ] {doc}")

        lines.append("\n#### 🚀 Step-by-Step Application Procedure:")
        for idx, step in enumerate(plan.get("application_steps", []), 1):
            lines.append(f"{idx}. {step}")

        if plan.get("prerequisites"):
            lines.append("\n#### ⚠️ Important Pre-requisites:")
            for pre in plan.get("prerequisites", []):
                lines.append(f"- {pre}")

        lines.append(f"\n*Record verified as of {plan.get('last_verified')}. Never share Aadhaar OTP or bank passwords with unauthorized individuals.*")
        lines.append("\n*Type 'back' or 'schemes' to return to your schemes overview.*")

        return "\n".join(lines)

    async def handle_citizen_message(
        self, sender_id: str, message_text: str
    ) -> ChatMessage:
        """Process an inbound natural language message or card action from a citizen."""
        text = (message_text or "").strip()
        session = self.get_or_create_session(sender_id)

        # Security check: detect Aadhaar number pattern
        if SENSITIVE_12_DIGIT_RE.search(text):
            return ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[
                    TextContent(
                        type="text",
                        text="⚠️ **Privacy Protection:** CivicBridge detected what looks like a 12-digit identification number. "
                             "Please **do not share Aadhaar numbers, bank account numbers, or passwords**. "
                             "CivicBridge evaluates eligibility using non-sensitive demographic criteria only.",
                    )
                ],
            )

        # 1. Check for card button selection or back action
        card_action = self._parse_card_action(text)
        if card_action:
            action = card_action.get("action")
            if action == "back_to_schemes":
                if session.last_evaluations:
                    markdown = self._format_shortlist_markdown(session.profile, session.last_evaluations)
                    return create_schemes_list_chat_message(markdown, session.last_evaluations)
                text = "Show my schemes"

            elif action == "view_checklist":
                scheme_id = card_action.get("scheme_id")
                # Look up from last evaluations or directly
                target_eval = next((e for e in session.last_evaluations if e.scheme_id == scheme_id), None)
                if not target_eval:
                    # Look up scheme directly
                    s = self.discovery.search_tool.get_scheme_by_id(scheme_id)
                    if s:
                        target_eval = self.eligibility.evaluate_scheme(s, session.profile)
                        target_eval = self.verification.verify_and_annotate(s, target_eval)

                if target_eval:
                    plan = self.planner.generate_plan(target_eval, session.profile)
                    markdown = self._format_scheme_detail_markdown(plan)
                    return create_scheme_detail_chat_message(markdown, plan)

        # Check if user mentioned a specific scheme short_name in text to view details
        lower = text.lower()
        if session.last_evaluations:
            for item in session.last_evaluations:
                if (
                    item.short_name.lower() in lower
                    or item.scheme_id.lower() in lower
                    or (item.short_name.lower().replace("-", " ") in lower)
                ):
                    plan = self.planner.generate_plan(item, session.profile)
                    markdown = self._format_scheme_detail_markdown(plan)
                    return create_scheme_detail_chat_message(markdown, plan)

        # 2. Greeting or help request
        if lower in ("hi", "hello", "namaste", "help", "start", "/start"):
            welcome = (
                "👋 **Namaste! Welcome to CivicBridge — your AI Government Benefits Navigator.**\n\n"
                "I help Indian citizens discover and qualify for welfare schemes across:\n"
                "• **Agriculture & Farmer Support** (e.g. PM-KISAN, PM-KMY)\n"
                "• **Education & Scholarships** (e.g. NMMSS, Post-Matric SC)\n"
                "• **Healthcare Assistance** (e.g. Ayushman Bharat PM-JAY, PMMVY)\n"
                "• **Housing Assistance** (e.g. PMAY-Gramin, PMAY-Urban)\n"
                "• **Pensions & Social Welfare** (e.g. Atal Pension Yojana, IGNOAPS)\n"
                "• **Employment & Skill Development** (e.g. PM SVANidhi, PM Vishwakarma, PMEGP)\n\n"
                "Tell me about your situation (e.g., *'I am a small farmer in UP with 1 hectare of land'* or "
                "*'I am an urban street vendor looking for a working capital loan'*)."
            )
            return ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=welcome)],
            )

        # 3. Extract and update profile attributes
        session.profile = extract_profile_from_text(text, existing_profile=session.profile)
        logger.info(f"Updated citizen profile: {session.profile.summary_dict()}")

        # 4. Check if we have sufficient info to search schemes
        if not session.profile.has_sufficient_info_for_search():
            clarification = (
                "To help you find the right government schemes, please tell me a bit more about your need:\n\n"
                "1. Which benefit area are you looking for? (Farming, Education/Scholarship, Housing, Health, Pension, or Business/Loan)\n"
                "2. Which state do you live in, and is it a rural village or city/town?\n"
                "3. Your approximate age and current occupation."
            )
            return ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=clarification)],
            )

        # 5. Check if critical category-specific fields are missing
        missing_critical = session.profile.missing_fields_for_category()
        # If too many critical fields are missing and this is the very first specific query, ask a gentle follow-up
        if len(missing_critical) >= 2 and session.state == "INITIAL":
            session.state = "COLLECTING_PROFILE"
            follow_up = (
                f"I found relevant {session.profile.category_interest or 'welfare'} schemes for you! "
                f"To determine your exact eligibility, could you also quickly share:\n"
                + "\n".join(f"• {field.capitalize()}" for field in missing_critical)
                + "\n\n*(You can reply with these details, or type 'skip' to see all general schemes)*"
            )
            return ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=follow_up)],
            )

        # 6. Execute specialist pipeline:
        # A. Discovery
        discovery_res = self.discovery.discover(session.profile)
        candidates = discovery_res.schemes

        # B. Eligibility Evaluation
        evaluations = self.eligibility.evaluate_all(candidates, session.profile)

        # C. Verification Audit
        audited_evaluations = self.verification.audit_batch(candidates, evaluations)
        session.last_evaluations = audited_evaluations
        session.state = "SHOWING_SHORTLIST"

        # D. Format response with both markdown and cards
        markdown = self._format_shortlist_markdown(session.profile, audited_evaluations)
        return create_schemes_list_chat_message(markdown, audited_evaluations)
