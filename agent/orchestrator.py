"""Multi-specialist orchestrator for CivicBridge government benefits and opportunity navigation."""

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
from schemas.results import SchemeEvaluation, EligibilityGrowthPlan, ActionableGap
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
    """Tracks state, accumulated profile, and growth plan for an active citizen chat session."""

    def __init__(self, sender_id: str, conversation_id: Optional[str] = None) -> None:
        self.sender_id = sender_id
        self.conversation_id = conversation_id
        self.profile = ApplicantProfile()
        self.last_evaluations: List[SchemeEvaluation] = []
        self.growth_plan: Optional[EligibilityGrowthPlan] = None
        self.state: str = "INITIAL"
        self.turn_count: int = 0
        self.pending_question_field: Optional[str] = None


class CivicBridgeOrchestrator:
    """Coordinates specialist components to assess eligibility and deliver growth pathways."""

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

    def _get_session_key(self, sender_id: str, conversation_id: Optional[str] = None) -> str:
        """Generate isolated session key by sender and conversation/session identifier."""
        if conversation_id:
            return f"{sender_id}:{conversation_id}"
        return sender_id

    def get_or_create_session(
        self, sender_id: str, conversation_id: Optional[str] = None
    ) -> UserSession:
        key = self._get_session_key(sender_id, conversation_id)
        if key not in self._sessions:
            self._sessions[key] = UserSession(sender_id, conversation_id)
        return self._sessions[key]

    def reset_session(
        self, sender_id: str, conversation_id: Optional[str] = None
    ) -> UserSession:
        """Clear and re-initialize session state for a citizen."""
        key = self._get_session_key(sender_id, conversation_id)
        self._sessions[key] = UserSession(sender_id, conversation_id)
        return self._sessions[key]

    def clear_session(
        self, sender_id: str, conversation_id: Optional[str] = None
    ) -> None:
        """Remove a citizen session."""
        key = self._get_session_key(sender_id, conversation_id)
        self._sessions.pop(key, None)

    def _is_legitimate_follow_up(self, text: str, session: UserSession) -> bool:
        """Determine whether an inbound message is a continuous follow-up to the current conversation
        or a new independent inquiry / persona that should begin with a clean profile."""
        if session.turn_count == 0 or (session.state == "INITIAL" and not session.last_evaluations):
            return False

        lower = text.lower().strip()

        # Explicit reset signals
        if lower in ("start", "/start", "restart", "reset", "new chat", "start over", "clear"):
            return False

        # Card button action or back action
        if self._parse_card_action(text):
            return True

        # Explicit follow-up inquiries or evaluation requests
        if any(
            phrase in lower
            for phrase in [
                "what can i apply",
                "what should i do",
                "what next",
                "tell me more",
                "show me",
                "how to apply",
                "eligibility",
                "am i eligible",
                "eligible for",
                "can i get",
                "what schemes",
                "which schemes",
                "what scholarships",
                "which scholarships",
                "what internships",
                "which internships",
                "my options",
                "my opportunities",
                "what about",
            ]
        ):
            return True

        # Specific scheme name mentioned from current evaluations
        if session.last_evaluations:
            for item in session.last_evaluations:
                if (
                    item.short_name.lower() == lower
                    or item.scheme_id.lower() == lower
                    or re.search(r"\b" + re.escape(item.short_name.lower()) + r"\b", lower)
                    or re.search(r"\b" + re.escape(item.short_name.lower().replace("-", " ")) + r"\b", lower)
                ):
                    return True

        # Check for persona / occupation declaration
        # e.g. "I am a student...", "I am a farmer...", "I am an artisan..."
        new_occ_match = re.search(
            r"\b(?:i am a|i am an|am a|am an|myself a|myself an)\s+(farmer|student|artisan|street\s+vendor|vendor|worker|unorganized\s+worker|salaried|job\s+seeker)\b",
            lower,
        )
        if new_occ_match:
            new_occ = new_occ_match.group(1).replace(" ", "_")
            if session.profile.occupation and session.profile.occupation != new_occ:
                # Occupation changed (e.g. from farmer to student) -> New inquiry, not a follow-up
                return False

        # Check for fresh top-level standalone queries
        if re.search(
            r"^(?:i am a|i am an|am a|am an)\s+\w+.*(?:looking for|search for|find|need|want)\s+(?:government\s+)?(?:schemes?|internships?|scholarships?|benefits?|welfare|assistance|loans?)",
            lower,
        ):
            # A full standalone query such as "I am a student looking for government internship"
            return False

        # Explicit request to reuse prior profile
        if any(phrase in lower for phrase in ["use my previous profile", "use my existing profile", "remember my details"]):
            return True

        # If in COLLECTING_PROFILE state, answers to pending questions are legitimate follow-ups
        if session.state == "COLLECTING_PROFILE":
            return True

        # If user is providing incremental details (e.g., income, category, land, age, education, or "skip")
        incremental_patterns = [
            r"\b(?:income|earning|salary|lakh|lac|lpa)\b",
            r"\b(?:sc|st|obc|ews|general)\b",
            r"\b(?:hectare|acre|land)\b",
            r"\b(?:bpl|ration\s+card|pucca|house)\b",
            r"\b(?:class\s+8|class\s+10|class\s+12|undergraduate|graduate|post\s+graduate|degree|btech|bsc|b\.sc|msc|m\.sc|ba|bcom)\b",
            r"\b(?:skip|show me|what can i apply|continue|more|next|actually)\b",
        ]
        if any(re.search(pat, lower) for pat in incremental_patterns):
            return True

        # Default fallback: If not reliably established as follow-up, do not contaminate!
        return False

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

    def _is_document_checklist_query(self, lower: str) -> bool:
        """Detect questions asking for documents, certificates, paperwork, or checklists."""
        if any(w in lower for w in ["my income", "income:", "currently in", "i am a", "my caste", "my age", "my marks"]):
            return False
        return bool(
            re.search(r"\b(?:what|which|list\s+of)?\s*(?:documents?|certificates?|paperwork|papers?|proofs?|checklist)\s*(?:might\s+i\s+need|are\s+needed|are\s+required|do\s+i\s+need|needed|required|checklist)\b", lower)
            or re.search(r"\b(?:what\s+documents?|which\s+documents?|document\s+checklist|documents?\s+(?:for|to\s+apply))\b", lower)
            or re.search(r"\b(?:what\s+certificates?|which\s+certificates?|certificate\s+checklist)\b", lower)
            or lower.startswith("what documents")
            or lower.startswith("documents for")
            or lower.startswith("checklist for")
        )

    def _is_profile_intake_query(self, lower: str) -> bool:
        """Detect meta-questions about what information CivicBridge needs from the citizen."""
        return bool(
            re.search(r"\bwhat\s+(?:information|details|info|data|inputs?)\s+(?:do\s+you|is|are)?\s*(?:need|require|ask|wanted)\b", lower)
            or re.search(r"\bwhat\s+do\s+you\s+need\s+(?:from\s+me|to\s+find|to\s+assess|to\s+check)\b", lower)
            or re.search(r"\bwhat\s+(?:should|do)\s+i\s+(?:tell|provide|share|give)\s+(?:you\s+)?(?:to\s+find|to\s+get|for)?\b", lower)
            or re.search(r"\bwhat\s+(?:details|information)\s+should\s+i\s+(?:give|provide|share)\b", lower)
        )

    def _is_application_steps_official_sources_query(self, lower: str) -> bool:
        """Detect procedure and official source verification inquiries."""
        return bool(
            re.search(r"\b(?:next\s+steps?|steps?\s+before\s+applying)\s+and\s+(?:official\s+sources?|where\s+to\s+check)\b", lower)
            or re.search(r"\b(?:next\s+steps?|official\s+sources?)\s+(?:i\s+should\s+check|before\s+applying)\b", lower)
            or re.search(r"\bofficial\s+sources?\s+(?:to\s+check|and\s+next\s+steps)\b", lower)
            or re.search(r"\bhow\s+do\s+i\s+(?:verify|check)\s+(?:if\s+a\s+scheme\s+is\s+official|official\s+sources?)\b", lower)
            or re.search(r"\bwhat\s+steps\s+should\s+i\s+take\s+before\s+applying\b", lower)
        )

    def _is_hypothetical_marks_query(self, lower: str) -> bool:
        """Detect hypothetical eligibility questions where marks are required but unprovided."""
        has_req = bool(re.search(
            r"\b(?:requires?|requiring|condition|needs?)\s+(?:at\s+least\s+)?[0-9]{2}(?:\.[0-9]+)?\s*(?:%|\bpercent\b|\bpercentage\b)",
            lower,
        ))
        has_unprovided = bool(
            re.search(r"\b(?:haven't|have\s+not|didn't|did\s+not|not)\s+(?:told|shared|given|provided|mentioned)\s+(?:you\s+)?(?:my\s+)?marks\b", lower)
            or re.search(r"\bwithout\s+(?:knowing\s+)?(?:my\s+)?marks\b", lower)
        )
        return has_req and has_unprovided

    def _is_general_capabilities_query(self, lower: str) -> bool:
        """Detect inquiries about CivicBridge supported categories and scope."""
        return bool(
            re.search(r"\b(?:what\s+schemes\s+do\s+you\s+support|what\s+categories\s+(?:are\s+available|do\s+you\s+cover|are\s+there)|what\s+can\s+(?:you|civicbridge)\s+do|how\s+can\s+civicbridge\s+help|tell\s+me\s+about\s+civicbridge)\b", lower)
        )

    def _handle_profile_intake_query(self) -> ChatMessage:
        """Respond with a clear, concise intake guide explaining needed inputs without assuming defaults."""
        text = (
            "### 📋 CivicBridge Profile Intake Guide\n\n"
            "To accurately match you with relevant Indian government welfare schemes, scholarships, and official internships, CivicBridge evaluates a few non-sensitive demographic and educational criteria:\n\n"
            "#### 1. Core Profile Details (Most Helpful):\n"
            "• **Target Opportunity**: Whether you are looking for welfare schemes, scholarships, official internships, or all opportunities.\n"
            "• **Current Occupation / Activity**: (e.g., Student, Small/Marginal Farmer, Street Vendor, Artisan, Unorganized Worker, Salaried, or Job Seeker).\n"
            "• **Location**: Your State or Union Territory, and whether your residence is **Rural** (village) or **Urban** (city/municipality).\n"
            "• **Family Annual Income**: Approximate total family income (or whether you hold a BPL / Antyodaya ration card).\n\n"
            "#### 2. Educational Details (For Students & Graduates):\n"
            "• **Current or Completed Education Level**: e.g., Class 8, Class 10, Class 12, undergraduate (college), or postgraduate.\n"
            "• **Degree Status & Field of Study**: Whether you are currently pursuing a degree (e.g., 2nd year B.Sc., B.Tech, B.Com) or a fresh graduate, and your discipline (Science, CS, Engineering, Commerce, Arts).\n"
            "• **Academic Marks (Optional)**: If you are applying for merit-based scholarships or internships with academic cutoffs (such as NITI Aayog or Digital India).\n\n"
            "#### 3. Category & Social Criteria (Optional):\n"
            "• **Age**: Some programs have statutory age windows (e.g., 18–40 for pensions, 21–24 for PM Internship Scheme).\n"
            "• **Reservation Category**: (General, SC, ST, OBC, EWS) — relevant only for category-specific scholarships and welfare quotas.\n\n"
            "---\n"
            "🔒 **CivicBridge Privacy Protection Guarantee:**\n"
            "• **Never share Aadhaar numbers, bank account numbers, passwords, or OTPs.** CivicBridge never asks for or stores sensitive identifiers.\n"
            "• Eligibility is assessed deterministically using public government norms.\n\n"
            "👉 **How to Proceed:**\n"
            "You can share your details in a simple sentence, for example:\n"
            "> *'I am a 20-year-old undergraduate student in Maharashtra from SC category with family income under 2 lakh'*\n\n"
            "Or if you prefer not to share personal information, simply type **'Show all schemes'** to browse general opportunities!"
        )
        return ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=text)],
        )

    def _handle_next_steps_official_sources_query(self, query_text: str, session: UserSession) -> ChatMessage:
        """Provide verified next steps, authoritative portals, and safety guidelines before applying."""
        text = (
            "### 🏛️ Official Application Procedure & Source Verification Guide\n\n"
            "Before applying for any Indian government welfare scheme, scholarship, or internship, follow this verified 5-step roadmap to ensure your application is successful and secure:\n\n"
            "#### Step 1: Verify on Official Government Domains (`.gov.in` / `.nic.in`)\n"
            "Always verify scheme details and submit applications exclusively through authorized government portals:\n"
            "• **Comprehensive Welfare Portal**: [myScheme.gov.in](https://www.myscheme.gov.in) *(Central directory of Central & State schemes)*\n"
            "• **Scholarships**: [scholarships.gov.in](https://scholarships.gov.in) *(National Scholarship Portal - NSP)*\n"
            "• **Government & MCA Internships**: [pminternship.mca.gov.in](https://pminternship.mca.gov.in) *(PM Internship Scheme)* and [internship.aicte-india.org](https://internship.aicte-india.org) *(TULIP & AICTE)*\n"
            "• **Agriculture**: [pmkisan.gov.in](https://pmkisan.gov.in) *(PM-KISAN)* and state Bhulekh portals for land records.\n"
            "• **Housing**: [pmayg.nic.in](https://pmayg.nic.in) *(PMAY-Gramin)* and [pmaymis.gov.in](https://pmaymis.gov.in) *(PMAY-Urban)*\n"
            "• **Health**: [pmjay.gov.in](https://pmjay.gov.in) *(Ayushman Bharat PM-JAY)*\n\n"
            "#### Step 2: Review Current-Year Operational Guidelines\n"
            "• Download the official scheme guidelines or notification for the current financial / academic year.\n"
            "• Verify whether the scheme application window is currently active and note the official deadline.\n"
            "• Confirm specific eligibility criteria: age limits, parental income ceilings, and domicile requirements.\n\n"
            "#### Step 3: Complete Pre-Requisite Linkages & Certification\n"
            "• **Aadhaar-Bank Seeding**: Confirm that your bank account is active and seeded with Aadhaar on the NPCI mapper for Direct Benefit Transfer (DBT).\n"
            "• **One-Time Registration (OTR)**: Complete your Aadhaar-based e-KYC on the relevant portal (e.g. NSP OTR).\n"
            "• **Procure Government Certificates**: Obtain digital Income, Caste, and Domicile certificates from your State e-District portal or local CSC center.\n\n"
            "#### Step 4: Submit Online & Preserve Tracking Reference\n"
            "• Fill in application details matching your official Aadhaar and marksheet records exactly.\n"
            "• Upload certified PDF copies of all requested documents.\n"
            "• Save your generated **Application Reference Number / Acknowledgement Receipt** and print a copy for institution/district nodal officer verification.\n\n"
            "#### Step 5: Anti-Fraud Advisory & Safety Checklist\n"
            "• ⚠️ **Zero Fees**: Government benefit applications on official `.gov.in` portals are free of cost.\n"
            "• ⚠️ **Never Pay Intermediaries**: Do not pay money to unauthorized agents promising guaranteed selection.\n"
            "• ⚠️ **Guard Confidential Data**: Never share your Aadhaar OTP, net banking password, or UPI PIN with anyone.\n\n"
            "---\n"
            "👉 **Next Step:** If you want specific next steps for a particular scheme (such as `PM-KISAN`, `Post-Matric SC`, or `PMIS`), tell me the scheme name and I will provide its verified portal link and application steps!"
        )
        return ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=text)],
        )

    def _handle_hypothetical_marks_query(self, query_text: str, session: UserSession) -> ChatMessage:
        """Address hypothetical marks eligibility queries truthfully without fabricating scores."""
        text = (
            "### 📊 Eligibility Assessment: Mandatory Academic Marks Criteria\n\n"
            "**Short Answer: No, eligibility cannot be confirmed without your actual marks.**\n\n"
            "Here is how academic eligibility requirements work under official government and internship guidelines:\n\n"
            "1. **Academic Marks Are a Mandatory Statutory Prerequisite**:\n"
            "   • For opportunities with published academic benchmarks (such as the **Digital India Internship** requiring at least **60% aggregate marks**, or the **NITI Aayog Internship** requiring **85% in Class 12**), the cutoff is a non-negotiable statutory requirement.\n\n"
            "2. **Absent Marks Remain 'UNKNOWN / PENDING VERIFICATION'**:\n"
            "   • CivicBridge strictly adheres to evidence-backed evaluation: we **never fabricate a default score** (such as 0% or 60.0%).\n"
            "   • Because you have not shared your marks, the academic performance condition is marked as **❓ UNKNOWN (Pending Verification)**.\n"
            "   • An opportunity cannot be marked as `🟢 ELIGIBILITY CONFIRMED` or `🟡 LIKELY ELIGIBLE` when a mandatory criterion is unverified.\n\n"
            "3. **Other Conditions Evaluated Independently**:\n"
            "   • If you have provided other details (such as current student enrollment or your field of study), those specific conditions can be evaluated independently.\n"
            "   • However, final qualification requires satisfying all mandatory conditions simultaneously.\n\n"
            "---\n"
            "👉 **To Verify Your Eligibility:** Simply reply with your aggregate marks or percentage (e.g. *'My marks are 68%'* or *'Class 12 marks: 72%'*), and I will evaluate your eligibility immediately!"
        )
        return ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=text)],
        )

    def _handle_document_checklist_query(self, query_text: str, session: UserSession) -> ChatMessage:
        """Provide detailed document checklist directly before initiating unrelated profile collection."""
        lower = query_text.lower()

        # 1. Check if user mentioned a specific scheme by acronym or name in the query
        all_schemes = self.discovery.search_tool.repository.list_all()
        matched_scheme = None
        for s in all_schemes:
            if (
                s.short_name.lower() in lower
                or s.scheme_id.lower() in lower
                or (len(lower) >= 6 and s.name.lower() in lower)
            ):
                matched_scheme = s
                break

        if matched_scheme:
            eval_res = self.eligibility.evaluate_scheme(matched_scheme, session.profile)
            audited = self.verification.verify_and_annotate(matched_scheme, eval_res)
            plan = self.planner.generate_plan(audited, session.profile)
            markdown = self._format_scheme_detail_markdown(plan)
            return create_scheme_detail_chat_message(markdown, plan)

        # 2. Category-based general document guidance
        if any(w in lower for w in ["scholarship", "scholarships", "student", "education", "college", "school"]):
            category_title = "Government Scholarships & Educational Assistance"
            category_docs = [
                ("Institutional Bonafide Student Certificate / ID Card", "Issued by Head of School/College confirming regular enrollment in current academic year."),
                ("Previous Qualifying Marksheet(s)", "Class 10th, 12th, or last semester marksheet verifying academic eligibility."),
                ("Current Academic Year Fee Receipt / Admission Letter", "Valid receipt showing active enrollment and fee structure."),
                ("Family Income Certificate", "Issued by competent Revenue Authority (Tehsildar/SDM). Mandatory for means-tested scholarships."),
                ("Caste / Community Certificate (SC/ST/OBC/EWS)", "Mandatory only if applying under reserved categories (e.g. Post-Matric SC)."),
                ("Disability Certificate (if applicable)", "Minimum 40% benchmark disability issued by District Medical Board for PwD scholarships."),
                ("National Scholarship Portal (NSP) OTR Registration", "One-Time Registration reference number generated using Aadhaar e-KYC on scholarships.gov.in."),
            ]
            caveat = "Scholarship document requirements vary significantly between pre-matric (school), post-matric (higher education), and merit-cum-means schemes."
        elif any(w in lower for w in ["farm", "farmer", "agriculture", "kisan", "crop"]):
            category_title = "Agriculture & Farmer Welfare Schemes (e.g. PM-KISAN, PM-KMY)"
            category_docs = [
                ("Cultivable Land Ownership Record (Khatauni / RoR)", "Digitally signed Record of Rights from State Bhulekh portal proving agricultural land title."),
                ("Aadhaar Card of the Landholder", "Mandatory for biometric/OTP e-KYC authentication."),
                ("Aadhaar-Seeded Bank Passbook / Mandate", "Active bank account mapped with NPCI for Direct Benefit Transfer (DBT)."),
                ("Self-Declaration / Domicile Certificate", "Proof of actual residence in the state and farming status."),
            ]
            caveat = "Tenants and landless agricultural workers are not covered under land-ownership schemes like PM-KISAN, but can access rural livelihood programs."
        elif any(w in lower for w in ["house", "housing", "awas", "pmay"]):
            category_title = "Housing Welfare Schemes (PMAY-G / PMAY-U)"
            category_docs = [
                ("Aadhaar Cards of All Family Members", "Identity proof for all household beneficiaries."),
                ("Income Certificate / BPL Ration Card", "Valid Below Poverty Line (BPL) or EWS income certificate."),
                ("Land Ownership / Patta Document", "Document proving ownership of plot for rural construction."),
                ("Affidavit / Self-Declaration", "Statutory declaration that the beneficiary does not own a concrete pucca house anywhere in India."),
            ]
            caveat = "Urban housing (PMAY-U) and rural housing (PMAY-G) have distinct income cutoffs and municipal verification requirements."
        else:
            category_title = "Government Welfare Schemes & Opportunities"
            category_docs = [
                ("Aadhaar Card", "Primary proof of identity and citizenship for all DBT schemes."),
                ("Active Bank Passbook", "Account must be seeded with Aadhaar on NPCI for direct DBT benefit transfer."),
                ("Income Certificate", "Issued by competent Revenue Authority (Tehsildar/SDM) within the past 6-12 months."),
                ("Residence / Domicile Certificate", "State resident certificate issued by competent authority."),
                ("Caste / Reservation Certificate (if applicable)", "Required only when claiming reservation or affirmative action benefits."),
            ]
            caveat = "Document requirements vary across central, state, and department-specific schemes."

        lines = [
            f"### 📂 Document Checklist: {category_title}",
            "To prepare a complete and successful application, here is the verified document checklist:\n",
            "#### 1. Universal Identity & Account Documentation:",
            "- [ ] **Aadhaar Card of Applicant**: Must be linked to an active mobile number for biometric / OTP e-KYC.",
            "- [ ] **Aadhaar-Seeded Bank Passbook / Cancelled Cheque**: Bank account must be in applicant's name and mapped to NPCI for Direct Benefit Transfer (DBT).",
            "- [ ] **Recent Passport-size Photographs** (white background).",
            "\n#### 2. Key Scheme-Specific Documents:",
        ]

        for doc_name, doc_desc in category_docs:
            lines.append(f"- [ ] **{doc_name}**: {doc_desc}")

        lines.extend([
            "\n---",
            "⚠️ **Important Statutory Caveat:**",
            f"• {caveat}",
            "• Clearly distinguish confirmed statutory requirements from items that require verification for your specific case.",
            "• Never assume an optional certificate is mandatory unless specified in the official scheme operational guidelines.",
            "\n👉 **Next Step:** If you have a specific scheme in mind (e.g. `Post-Matric SC`, `NMMSS`, `PM-KISAN`) or want to share your profile details, I can provide the exact official checklist and evaluate your eligibility directly!",
        ])

        return ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text="\n".join(lines))],
        )

    def _handle_capabilities_query(self) -> ChatMessage:
        """Provide an authoritative overview of supported CivicBridge sectors and opportunities."""
        text = (
            "### 🇮🇳 CivicBridge Navigator: Capabilities & Supported Opportunities\n\n"
            "CivicBridge is an AI-powered government benefits and opportunity navigator for Indian citizens. We help you discover, evaluate eligibility for, and navigate application procedures across 6 core sectors:\n\n"
            "#### 1. 🎓 Scholarships & Educational Assistance\n"
            "• **NMMSS (National Means-cum-Merit Scholarship)**: ₹12,000/yr for meritorious students in secondary school (Classes IX–XII).\n"
            "• **Post-Matric Scholarship for SC Students**: Full tuition reimbursement + annual maintenance allowance for post-matric study.\n\n"
            "#### 2. 💼 Government & Official Internships\n"
            "• **PM Internship Scheme (PMIS)**: 12-month internship with ₹5,000/mo stipend in top 500 companies via MCA portal.\n"
            "• **NITI Aayog Internship**: Project-based policy research internship with Govt think-tank.\n"
            "• **Digital India Internship (MeitY)**: ₹10,000/mo tech & governance internship for CS/IT/Electronics students.\n"
            "• **TULIP (The Urban Learning Internship Program)**: Urban governance internships with Smart Cities & ULBs.\n"
            "• **RBI Summer Internship**: Research & economic policy internship with the Reserve Bank of India.\n\n"
            "#### 3. 🌾 Agriculture & Farmer Welfare\n"
            "• **PM-KISAN**: ₹6,000/yr direct income support for cultivable landholding farmer families.\n"
            "• **PM-KMY (Kisan Maan-Dhan Yojana)**: Assured pension of ₹3,000/month for small & marginal farmers aged 60+.\n\n"
            "#### 4. 🏠 Housing Assistance\n"
            "• **PMAY-G (Gramin)**: Financial assistance up to ₹1,30,000 for building a rural pucca house.\n"
            "• **PMAY-U (Urban)**: Subsidy up to ₹2,50,000 under Beneficiary-Led Construction & CLSS.\n\n"
            "#### 5. 🏥 Healthcare & Maternity\n"
            "• **Ayushman Bharat (PM-JAY)**: Up to ₹5,00,000/yr cashless secondary and tertiary hospitalization.\n"
            "• **PMMVY (Matru Vandana)**: Direct cash incentive up to ₹6,000 for pregnant and lactating mothers.\n\n"
            "#### 6. 🛡️ Pensions & Social Security\n"
            "• **Atal Pension Yojana (APY)**: Guaranteed monthly pension of ₹1,000 to ₹5,000 starting at age 60.\n"
            "• **IGNOAPS**: Monthly old-age pension for BPL senior citizens aged 60+.\n"
            "• **PM-SVANidhi & PM-Vishwakarma**: Working capital loans & toolkit grants for street vendors and traditional artisans.\n\n"
            "---\n"
            "👉 **How to Get Started:** Tell me your situation (e.g., *'I am a college student in Rajasthan looking for internships'* or *'I am a small farmer with 1 hectare in UP'*), and I will evaluate your opportunities!"
        )
        return ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=text)],
        )

    def _format_shortlist_markdown(
        self,
        profile: ApplicantProfile,
        evaluations: List[SchemeEvaluation],
        growth_plan: Optional[EligibilityGrowthPlan] = None,
    ) -> str:
        """Render concise, evidence-backed presentation of candidate schemes, internships, and growth plan."""
        profile_parts = []
        if profile.state:
            profile_parts.append(f"**State:** {profile.state}")
        if profile.residence:
            profile_parts.append(f"**Residence:** {profile.residence.title()}")
        if profile.age:
            profile_parts.append(f"**Age:** {profile.age} yrs")
        if profile.occupation:
            profile_parts.append(f"**Occupation:** {profile.occupation.replace('_', ' ').title()}")
        if profile.education_level:
            profile_parts.append(f"**Education:** {profile.education_level.replace('_', ' ').title()}")
        if profile.field_of_study:
            profile_parts.append(f"**Field:** {profile.field_of_study.replace('_', ' ').title()}")
        if profile.skills:
            profile_parts.append(f"**Skills:** {', '.join(profile.skills)}")
        if profile.annual_income:
            profile_parts.append(f"**Income:** ₹{profile.annual_income:,.0f}/yr")

        profile_header = " · ".join(profile_parts) if profile_parts else "General Citizen Profile"

        lines = [
            "### 🇮🇳 CivicBridge Opportunities & Growth Assessment",
            f"*{profile_header}*\n",
        ]

        if not evaluations:
            lines.append("No active government schemes or internships matched your exact criteria in our verified catalog.")
            lines.append("Try specifying a broader interest (e.g. 'internships', 'education', 'farming', 'housing', 'employment').")
            return "\n".join(lines)

        # Split into Schemes and Internships
        schemes = [e for e in evaluations if e.opportunity_type == "scheme"]
        internships = [e for e in evaluations if e.opportunity_type == "internship"]

        # SECTION 1: SCHEMES
        if schemes:
            lines.append(f"#### 📜 Government Schemes & Welfare Programs ({len(schemes)} found):")
            for idx, item in enumerate(schemes, 1):
                if item.overall_status == "ELIGIBLE":
                    badge = "🟢 **ELIGIBILITY CONFIRMED (ELIGIBLE by available info)**"
                elif item.overall_status == "LIKELY_ELIGIBLE":
                    badge = "🟡 **LIKELY ELIGIBLE (Pending full verification)**"
                elif item.overall_status == "POTENTIALLY_ELIGIBLE":
                    badge = "⚪ **POTENTIALLY RELEVANT (Insufficient info to assess)**"
                else:
                    badge = "🔴 **NOT ELIGIBLE (Criteria unmet)**"
                lines.append(f"**{idx}. [{item.short_name}] {item.scheme_name}** — {badge}")
                lines.append(f"   • **Benefit:** {item.benefit_summary}")
                if item.benefit_amount:
                    lines.append(f"   • **Assistance Value:** `{item.benefit_amount}`")
                if item.met_conditions:
                    lines.append(f"   • ✅ **Met:** {'; '.join(item.met_conditions[:2])}")
                if item.unknown_conditions:
                    lines.append(f"   • ❓ **Pending Verification:** {'; '.join(item.unknown_conditions[:2])}")
                if item.unmet_conditions:
                    lines.append(f"   • ❌ **Unmet:** {'; '.join(item.unmet_conditions[:1])}")
                lines.append(f"   • 🔗 **Official Portal:** [{item.official_portal_url}]({item.official_portal_url}) *(Verified: {item.last_verified})*")
                lines.append("")

        # SECTION 2: INTERNSHIPS
        if internships:
            lines.append(f"#### 💼 Government & Official Internships ({len(internships)} found):")
            for idx, item in enumerate(internships, 1):
                if item.overall_status == "ELIGIBLE":
                    badge = "🟢 **ELIGIBILITY CONFIRMED (ELIGIBLE by available info)**"
                elif item.overall_status == "LIKELY_ELIGIBLE":
                    badge = "🟡 **LIKELY ELIGIBLE (Pending full verification)**"
                elif item.overall_status == "POTENTIALLY_ELIGIBLE":
                    badge = "⚪ **POTENTIALLY RELEVANT (Insufficient info to assess)**"
                else:
                    badge = "🔴 **NOT ELIGIBLE (Criteria unmet)**"
                host_str = "🏛️ Government Department" if item.host_type == "government" else "🏢 Official Portal Listed Companies"
                lines.append(f"**{idx}. [{item.short_name}] {item.scheme_name}** — {badge}")
                lines.append(f"   • **Host:** {host_str}")
                if item.stipend:
                    lines.append(f"   • **Stipend:** `{item.stipend}` | **Duration:** {item.duration or 'Project-based'} ({item.work_mode or 'on_site'})")
                lines.append(f"   • **Focus / Disciplines:** {', '.join(item.field_of_study[:4]) if item.field_of_study else 'General'}")
                if item.met_conditions:
                    lines.append(f"   • ✅ **Met:** {'; '.join(item.met_conditions[:2])}")
                if item.unknown_conditions:
                    lines.append(f"   • ❓ **Pending Verification:** {'; '.join(item.unknown_conditions[:2])}")
                if item.unmet_conditions:
                    lines.append(f"   • ❌ **Unmet:** {'; '.join(item.unmet_conditions[:1])}")
                lines.append(f"   • 🔗 **Official Portal:** [{item.official_portal_url}]({item.official_portal_url}) *(Verified: {item.last_verified})*")
                lines.append("")

        # SECTION 3: ELIGIBILITY GROWTH PLAN
        if growth_plan and (growth_plan.actionable_gaps or growth_plan.fixed_restrictions):
            lines.append("---")
            lines.append("### 🚀 CivicBridge Eligibility Growth Plan")
            lines.append(f"*{growth_plan.summary}*\n")

            # High-Leverage Actions
            if growth_plan.high_leverage_actions:
                lines.append("#### 🌟 High-Leverage Next Steps (Unlocks Multiple Opportunities):")
                for gap in growth_plan.high_leverage_actions:
                    opps = ", ".join(gap.target_opportunity_titles)
                    lines.append(f"- **{gap.requirement_name}** (Benefits: *{opps}*)")
                    lines.append(f"  • **Action:** {gap.recommended_action}")
                    if gap.action_url:
                        lines.append(f"  • **Official Procedure Portal:** [{gap.action_url}]({gap.action_url})")
                    impact_text = "Fulfills statutory prerequisite" if gap.satisfaction_guarantee == "satisfies_requirement" else "Improves selection preparedness"
                    lines.append(f"  • **Impact:** {impact_text}")
                    lines.append("")

            # Additional Actionable Next Steps
            other_actions = [g for g in growth_plan.actionable_gaps if g not in growth_plan.high_leverage_actions]
            if other_actions:
                lines.append("#### 📋 Recommended Pathway Actions:")
                for gap in other_actions[:3]:
                    lines.append(f"- **{gap.requirement_name}**: {gap.recommended_action}")
                    if gap.action_url:
                        lines.append(f"  • Link: [{gap.action_url}]({gap.action_url})")

            # Fixed Legal Restrictions
            if growth_plan.fixed_restrictions:
                lines.append("\n#### ⚠️ Fixed Statutory Restrictions (Non-negotiable limits):")
                for fixed in growth_plan.fixed_restrictions[:2]:
                    lines.append(f"- **{fixed.requirement_name}**: {fixed.description}. *Note: Statutory legal boundaries cannot be changed through courses or documentation.*")

        lines.append("\n---")
        lines.append("👉 **Next Step:** Type an opportunity acronym (e.g. `PMIS`, `NITI-Internship`, `Post-Matric SC`, `PM-KISAN`) or tap the card button below for your detailed document checklist and application steps.")
        lines.append("\n*Disclaimer: Eligibility guidance is advisory and based on verified public norms. Final approval rests with the respective government departments.*")

        return "\n".join(lines)

    def _format_scheme_detail_markdown(
        self, plan: Dict[str, Any]
    ) -> str:
        """Render detailed document checklist and application roadmap."""
        status = plan.get("eligibility_status")
        if status == "ELIGIBLE":
            badge = "🟢 **ELIGIBILITY CONFIRMED (ELIGIBLE by available info)**"
        elif status == "LIKELY_ELIGIBLE":
            badge = "🟡 **LIKELY ELIGIBLE (Pending full verification)**"
        elif status == "POTENTIALLY_ELIGIBLE":
            badge = "⚪ **POTENTIALLY RELEVANT (Insufficient info to assess)**"
        else:
            badge = "🔴 **NOT ELIGIBLE (Criteria unmet)**"
        type_str = "💼 Internship" if plan.get("opportunity_type") == "internship" else "📜 Welfare Scheme"

        lines = [
            f"### 📋 Application Roadmap: {plan.get('short_name')} ({type_str})",
            f"**{plan.get('scheme_name')}** ({badge})\n",
            f"**Overview:** {plan.get('benefit_summary')}",
        ]

        if plan.get("stipend"):
            lines.append(f"**Stipend:** `{plan.get('stipend')}` | **Duration:** {plan.get('duration') or 'Project-based'} ({plan.get('work_mode') or 'on_site'})")
        if plan.get("host_type"):
            lines.append(f"**Host Entity:** {'Government Department' if plan.get('host_type') == 'government' else 'Top Companies via Official MCA Portal'}")

        lines.extend([
            f"**Official Portal:** [{plan.get('official_portal_url')}]({plan.get('official_portal_url')})",
            f"**Application Timeline:** {plan.get('application_dates')}\n",
            "#### 📂 Personalized Document Checklist:",
        ])

        for doc in plan.get("documents_checklist", []):
            lines.append(f"- [ ] {doc}")

        lines.append("\n#### 🚀 Step-by-Step Application Procedure:")
        for idx, step in enumerate(plan.get("application_steps", []), 1):
            lines.append(f"{idx}. {step}")

        if plan.get("prerequisites"):
            lines.append("\n#### ⚠️ Important Pre-requisites & Pathway Advice:")
            for pre in plan.get("prerequisites", []):
                lines.append(f"- {pre}")

        lines.append(f"\n*Record verified as of {plan.get('last_verified')}. Never share Aadhaar OTP or bank passwords with unauthorized individuals.*")
        lines.append("\n*Type 'back' or 'schemes' to return to your opportunities overview.*")

        return "\n".join(lines)

    async def handle_citizen_message(
        self,
        sender_id: str,
        message_text: str,
        conversation_id: Optional[str] = None,
        is_new_session_signal: bool = False,
    ) -> ChatMessage:
        """Process an inbound natural language message or card action from a citizen."""
        text = (message_text or "").strip()

        if is_new_session_signal:
            self.reset_session(sender_id, conversation_id)

        session = self.get_or_create_session(sender_id, conversation_id)

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
                    markdown = self._format_shortlist_markdown(
                        session.profile, session.last_evaluations, session.growth_plan
                    )
                    return create_schemes_list_chat_message(
                        markdown, session.last_evaluations, session.growth_plan
                    )
                text = "Show my opportunities"

            elif action == "view_checklist":
                scheme_id = card_action.get("scheme_id")
                target_eval = next((e for e in session.last_evaluations if e.scheme_id == scheme_id), None)
                if not target_eval:
                    s = self.discovery.search_tool.get_scheme_by_id(scheme_id)
                    if s:
                        target_eval = self.eligibility.evaluate_scheme(s, session.profile)
                        target_eval = self.verification.verify_and_annotate(s, target_eval)

                if target_eval:
                    plan = self.planner.generate_plan(target_eval, session.profile)
                    markdown = self._format_scheme_detail_markdown(plan)
                    return create_scheme_detail_chat_message(markdown, plan)

        # Check if user mentioned a specific scheme or internship short_name to view details
        lower = text.lower().strip()
        matched_eval = None

        GENERIC_DISCOVERY_WORDS = {
            "scheme", "schemes", "internship", "internships", "scholarship", "scholarships",
            "yojana", "benefit", "benefits", "assistance", "government", "welfare",
            "program", "programs", "opportunity", "opportunities", "student", "farmer",
            "aid", "grant", "grants", "loan", "loans", "pension", "pensions", "financial aid",
            "government schemes", "government benefits", "all schemes", "show schemes"
        }

        # Do not match single scheme drilldowns on broad category inquiries
        if lower not in GENERIC_DISCOVERY_WORDS:
            if session.last_evaluations:
                for item in session.last_evaluations:
                    pattern = r"\b" + re.escape(item.short_name.lower()) + r"\b"
                    pattern_spaced = r"\b" + re.escape(item.short_name.lower().replace("-", " ")) + r"\b"
                    pattern_id = r"\b" + re.escape(item.scheme_id.lower()) + r"\b"
                    if (
                        item.short_name.lower() == lower
                        or item.scheme_id.lower() == lower
                        or re.search(pattern, lower)
                        or re.search(pattern_spaced, lower)
                        or re.search(pattern_id, lower)
                    ):
                        matched_eval = item
                        break

            if not matched_eval and len(lower) >= 3:
                all_schemes = self.discovery.search_tool.repository.list_all()
                for s in all_schemes:
                    pattern = r"\b" + re.escape(s.short_name.lower()) + r"\b"
                    pattern_spaced = r"\b" + re.escape(s.short_name.lower().replace("-", " ")) + r"\b"
                    pattern_id = r"\b" + re.escape(s.scheme_id.lower()) + r"\b"
                    if (
                        s.short_name.lower() == lower
                        or s.scheme_id.lower() == lower
                        or re.search(pattern, lower)
                        or re.search(pattern_spaced, lower)
                        or re.search(pattern_id, lower)
                        or (len(lower) >= 8 and lower in s.name.lower())
                    ):
                        eval_res = self.eligibility.evaluate_scheme(s, session.profile)
                        matched_eval = self.verification.verify_and_annotate(s, eval_res)
                        break

            if matched_eval:
                plan = self.planner.generate_plan(matched_eval, session.profile)
                markdown = self._format_scheme_detail_markdown(plan)
                return create_scheme_detail_chat_message(markdown, plan)

        # 2. Greeting or help request / session restart
        if lower in ("hi", "hello", "namaste", "help", "start", "/start", "restart", "reset", "clear", "new chat", "start over"):
            if lower in ("start", "/start", "restart", "reset", "clear", "new chat", "start over"):
                session = self.reset_session(sender_id, conversation_id)
            welcome = (
                "👋 **Namaste! Welcome to CivicBridge — your AI Government Benefits & Opportunity Navigator.**\n\n"
                "I help Indian citizens discover, qualify for, and grow into:\n"
                "• **Government Welfare Schemes** (PM-KISAN, PMAY Housing, Ayushman Bharat PM-JAY, APY Pensions)\n"
                "• **Scholarships & Educational Assistance** (NMMSS, Post-Matric SC)\n"
                "• **Government & Official Internships** (PM Internship Scheme, NITI Aayog, Digital India / MeitY, TULIP, RBI)\n"
                "• **Eligibility Growth Pathways** (Evidence-backed steps to unlock high-impact opportunities)\n\n"
                "Tell me about your situation (e.g., *'I am a student from Rajasthan looking for financial assistance and internships'* or "
                "*'I am a small farmer in UP with 1 hectare of land'*)."
            )
            return ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=welcome)],
            )

        # Intent Check A: Profile Intake Query ("What information do you need from me?")
        if self._is_profile_intake_query(lower):
            session.turn_count += 1
            return self._handle_profile_intake_query()

        # Intent Check B: Hypothetical Marks Query ("Requires 60% but haven't told my marks")
        if self._is_hypothetical_marks_query(lower):
            session.turn_count += 1
            return self._handle_hypothetical_marks_query(text, session)

        # Intent Check C: Next Steps & Official Sources Query ("What are next steps and official sources...")
        if self._is_application_steps_official_sources_query(lower):
            session.turn_count += 1
            return self._handle_next_steps_official_sources_query(text, session)

        # Intent Check D: Document Checklist Query ("What documents might I need?")
        if self._is_document_checklist_query(lower):
            session.turn_count += 1
            return self._handle_document_checklist_query(text, session)

        # Intent Check E: General Capabilities Query ("What schemes do you support?")
        if self._is_general_capabilities_query(lower):
            session.turn_count += 1
            return self._handle_capabilities_query()

        # 3. Check follow-up status and extract/update profile attributes safely
        is_follow_up = self._is_legitimate_follow_up(text, session)
        if not is_follow_up and session.turn_count > 0:
            logger.info(f"Resetting session for fresh query/persona from {sender_id} (conv={conversation_id})")
            session = self.reset_session(sender_id, conversation_id)

        session.profile = extract_profile_from_text(
            text,
            existing_profile=session.profile if is_follow_up else None,
            is_follow_up=is_follow_up,
        )
        session.turn_count += 1
        logger.info(f"Updated citizen profile: {session.profile.summary_dict()}")

        # 4. Check if we have sufficient info to search
        if not session.profile.has_sufficient_info_for_search():
            clarification = (
                "To help you find the right government schemes and internships, please share a few details:\n\n"
                "1. What are you looking for? (Government schemes, scholarships, internships, or both)\n"
                "2. Your state of residence and current occupation (e.g. student, farmer, artisan, job seeker).\n"
                "3. Your approximate age and current education level / field of study."
            )
            return ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=clarification)],
            )

        # 5. Check if critical category-specific fields are missing
        # If user explicitly asked for immediate assessment ("what can i apply", "what should i work on", "based on my profile", "skip")
        # we evaluate immediately with UNKNOWN for missing criteria, feeding the Growth Planner.
        immediate_eval_requested = any(phrase in lower for phrase in [
            "what can i apply", "what should i work on", "based on my profile",
            "eligible for", "show me", "skip", "growth"
        ])

        missing_critical = session.profile.missing_fields_for_category()
        if len(missing_critical) >= 2 and session.state == "INITIAL" and not immediate_eval_requested:
            session.state = "COLLECTING_PROFILE"
            follow_up = (
                f"I found relevant opportunities for you! "
                f"To refine your exact eligibility and growth pathways, could you also quickly share:\n"
                + "\n".join(f"• {field.capitalize()}" for field in missing_critical)
                + "\n\n*(You can reply with these details, or type 'skip' to see all matches)*"
            )
            return ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=follow_up)],
            )

        # 6. Execute specialist pipeline:
        # A. Discovery (Schemes + Internships)
        discovery_res = self.discovery.discover(session.profile)
        candidates = discovery_res.schemes

        # B. Eligibility Evaluation (Deterministic MET, NOT_MET, UNKNOWN)
        evaluations = self.eligibility.evaluate_all(candidates, session.profile)

        # C. Verification Audit (Domain & Freshness)
        audited_evaluations = self.verification.audit_batch(candidates, evaluations)
        session.last_evaluations = audited_evaluations

        # D. Eligibility Growth Planner (Identifies actionable gaps, high-leverage actions, fixed limits)
        growth_plan = self.planner.generate_growth_plan(audited_evaluations, session.profile)
        session.growth_plan = growth_plan
        session.state = "SHOWING_SHORTLIST"

        # E. Format comprehensive response with Schemes, Internships, Growth Plan, and Cards
        markdown = self._format_shortlist_markdown(
            session.profile, audited_evaluations, growth_plan
        )
        return create_schemes_list_chat_message(
            markdown, audited_evaluations, growth_plan=growth_plan
        )
