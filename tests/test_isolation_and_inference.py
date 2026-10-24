"""Regression test suite for CivicBridge Navigator (Tests A through M).
Verifies:
- Test A: Direct document guidance
- Test B: Preserved applicant details across legitimate follow-ups
- Test C: NMMS education mismatch (undergraduate disallowed)
- Test D: Unknown academic marks (no fabrication of scores)
- Test E: New conversation isolation (no cross-conversation profile leakage)
- Test F: Farmer profile isolation (no student/CS inference)
- Test G: Direct profile intake without pre-filling
- Test H: Legitimate follow-up context preservation
- Test I: Multiple independent users isolation
- Test J: Consecutive message reliability (5 varied inquiries)
- Test K: Partial or missing information handling
- Test L: Contradictory or corrected information updates
- Test M: Existing features (discovery, eligibility, badges, growth planner)
"""

import pytest
from schemas.applicant import ApplicantProfile, extract_profile_from_text
from schemas.scheme import EligibilityRule
from tools.eligibility_rules import evaluate_rule
from agent.orchestrator import CivicBridgeOrchestrator
from specialists.eligibility import EligibilitySpecialist
from database.repository import SchemeRepository
from uagents_core.contrib.protocols.chat import TextContent


def extract_text(msg) -> str:
    """Helper to extract text from ACP ChatMessage."""
    return "".join(c.text for c in msg.content if isinstance(c, TextContent))


# ==============================================================================
# TEST A: Direct Document Guidance
# ==============================================================================
@pytest.mark.asyncio
async def test_a_direct_document_guidance():
    """TEST A: Asking for document guidance returns checklist directly without
    replacing the answer with an unrelated profile intake questionnaire.
    """
    orchestrator = CivicBridgeOrchestrator()
    query = "What documents might I need for a government scholarship application?"
    msg = await orchestrator.handle_citizen_message("test_user_a", query, conversation_id="conv_a")
    text = extract_text(msg)

    # Must provide the document checklist directly
    assert "Document Checklist" in text
    assert "Scholarship" in text
    assert "Aadhaar Card" in text
    assert "Bonafide Student Certificate" in text or "Marksheet" in text

    # Must NOT replace the answer with an intake questionnaire
    assert "To help you find the right government schemes and internships, please share a few details" not in text


# ==============================================================================
# TEST B: Preserved Applicant Details Across Legitimate Follow-Up Turns
# ==============================================================================
@pytest.mark.asyncio
async def test_b_preserved_applicant_details():
    """TEST B: Details provided in follow-up turn (income ₹2,40,000, 2nd year B.Sc.)
    are preserved accurately and not dropped or misidentified.
    """
    orchestrator = CivicBridgeOrchestrator()
    conv_id = "conv_b_session"

    # Turn 1: General document question
    await orchestrator.handle_citizen_message(
        "test_user_b", "What documents might I need for a government scholarship application?", conversation_id=conv_id
    )

    # Turn 2: Details supplied
    turn2_text = "Family annual income: ₹2,40,000. Education level: currently in 2nd year of B.Sc. at a government college."
    msg2 = await orchestrator.handle_citizen_message(
        "test_user_b", turn2_text, conversation_id=conv_id
    )
    text2 = extract_text(msg2)

    session = orchestrator.get_or_create_session("test_user_b", conversation_id=conv_id)
    assert session.profile.annual_income == 240000.0, "Income ₹2,40,000 was lost or dropped!"
    assert session.profile.education_level == "undergraduate", "Undergraduate education was not preserved!"
    assert session.profile.occupation == "student"
    assert session.profile.caste_category is None, "B.Sc. was falsely extracted as Scheduled Caste!"

    # Response should reflect the profile and perform assessment
    assert "240,000" in text2 or "2.4" in text2
    assert "Undergraduate" in text2 or "Student" in text2


# ==============================================================================
# TEST C: NMMS Education Mismatch
# ==============================================================================
def test_c_nmms_education_mismatch():
    """TEST C: NMMS scholarship is NOT eligible for an undergraduate student.
    A school-enrollment requirement incompatible with undergraduate level is NOT_MET.
    """
    repo = SchemeRepository("D:/CivicBridge/civicbridge_ai/database/civicbridge.db")
    nmmss = repo.get_by_id("nmmss")
    assert nmmss is not None, "NMMSS scheme not found in database!"

    profile_ug = ApplicantProfile(
        occupation="student",
        education_level="undergraduate",
        current_degree_status="pursuing",
        annual_income=240000.0,
    )

    specialist = EligibilitySpecialist()
    eval_res = specialist.evaluate_scheme(nmmss, profile_ug)

    # Must NOT be ELIGIBLE or LIKELY_ELIGIBLE
    assert eval_res.overall_status == "NOT_ELIGIBLE", f"NMMSS was incorrectly marked {eval_res.overall_status} for an undergraduate!"

    # Unmet conditions must explain the school stage restriction
    unmet_text = " ".join(eval_res.unmet_conditions).lower()
    assert "undergraduate" in unmet_text or "secondary school" in unmet_text
    assert "restricted" in unmet_text or "class_8" in unmet_text or "class_10" in unmet_text


# ==============================================================================
# TEST D: Unknown Marks (No Score Fabrication)
# ==============================================================================
@pytest.mark.asyncio
async def test_d_unknown_marks():
    """TEST D: Asking hypothetical questions with 60% or 85% cutoffs when marks
    are unprovided must NOT fabricate a score. Marks requirement remains UNKNOWN.
    """
    orchestrator = CivicBridgeOrchestrator()

    # Query with 60% threshold
    q60 = "An internship requires at least 60 percent marks, but I have not told you my marks. Am I eligible?"
    msg60 = await orchestrator.handle_citizen_message("test_user_d1", q60)
    t60 = extract_text(msg60)

    session60 = orchestrator.get_or_create_session("test_user_d1")
    assert session60.profile.marks_percentage is None, "Marks percentage was fabricated for 60% inquiry!"
    assert "UNKNOWN" in t60 or "Pending Verification" in t60 or "cannot be confirmed without your actual marks" in t60
    assert "never fabricate" in t60 or "Pending Verification" in t60

    # Query with 85% threshold
    q85 = "A scholarship requires at least 85% marks, but I have not given you my marks. Am I eligible?"
    msg85 = await orchestrator.handle_citizen_message("test_user_d2", q85)
    t85 = extract_text(msg85)

    session85 = orchestrator.get_or_create_session("test_user_d2")
    assert session85.profile.marks_percentage is None, "Marks percentage was fabricated for 85% inquiry!"
    assert "UNKNOWN" in t85 or "cannot be confirmed" in t85

    # Direct rule evaluation check
    marks_rule = EligibilityRule(
        rule_name="min_academic_marks",
        description="Must have scored at least 60% in qualifying degree",
        rule_type="marks_minimum",
        parameters={"min_percentage": 60.0},
    )
    rule_res = evaluate_rule(marks_rule, ApplicantProfile(occupation="student"))
    assert rule_res.status == "UNKNOWN"
    assert "not specified" in rule_res.reason


# ==============================================================================
# TEST E: New Conversation Isolation (No Profile Leakage)
# ==============================================================================
@pytest.mark.asyncio
async def test_e_new_conversation_isolation():
    """TEST E: Starting a new conversation does NOT inherit facts from an earlier conversation."""
    orchestrator = CivicBridgeOrchestrator()
    sender_id = "citizen_returning_e"

    # Conversation A
    conv_a_text = "I am 32, live in Uttar Pradesh, and study Computer Science."
    await orchestrator.handle_citizen_message(sender_id, conv_a_text, conversation_id="conv_a")

    session_a = orchestrator.get_or_create_session(sender_id, conversation_id="conv_a")
    assert session_a.profile.age == 32
    assert session_a.profile.state == "Uttar Pradesh"
    assert session_a.profile.field_of_study == "computer_science"

    # Conversation B: Distinct conversation
    conv_b_text = "I am a student looking for government internships."
    await orchestrator.handle_citizen_message(sender_id, conv_b_text, conversation_id="conv_b")

    session_b = orchestrator.get_or_create_session(sender_id, conversation_id="conv_b")
    assert session_b.profile.age is None, "Age 32 leaked from Conv A to Conv B!"
    assert session_b.profile.state is None, "State UP leaked from Conv A to Conv B!"
    assert session_b.profile.field_of_study is None, "Computer Science leaked from Conv A to Conv B!"
    assert session_b.profile.occupation == "student"


# ==============================================================================
# TEST F: Farmer Profile Isolation
# ==============================================================================
def test_f_farmer_profile_isolation():
    """TEST F: Fresh farmer profile does NOT infer Computer Science or invent default values."""
    farmer_query = "I am a farmer looking for government schemes."
    profile = extract_profile_from_text(farmer_query)

    assert profile.occupation == "farmer"
    assert profile.category_interest == "agriculture"
    assert profile.opportunity_interest == "schemes"
    assert profile.field_of_study is None, "Farmer was falsely assigned Computer Science!"
    assert profile.age is None
    assert profile.state is None
    assert profile.landholding_ha is None
    assert profile.is_landholder is None
    assert profile.annual_income is None
    assert profile.education_level is None


# ==============================================================================
# TEST G: Direct Profile Intake (Explains Needed Info Without Pre-filling)
# ==============================================================================
@pytest.mark.asyncio
async def test_g_direct_profile_intake():
    """TEST G: Asking what info is needed returns an intake guide without pre-filling
    unverified attributes or jumping into search.
    """
    orchestrator = CivicBridgeOrchestrator()
    q = "What information do you need from me to find suitable schemes, scholarships, or internships?"
    msg = await orchestrator.handle_citizen_message("test_user_g", q)
    text = extract_text(msg)

    assert "Profile Intake Guide" in text
    assert "Occupation" in text
    assert "State" in text or "Location" in text
    assert "Annual Income" in text or "Income" in text
    assert "Education Level" in text or "Education" in text

    session = orchestrator.get_or_create_session("test_user_g")
    assert session.profile.occupation is None, "Intake inquiry pre-filled an occupation!"
    assert session.profile.state is None
    assert session.profile.annual_income is None


# ==============================================================================
# TEST H: Legitimate Follow-Up Context Preservation
# ==============================================================================
@pytest.mark.asyncio
async def test_h_legitimate_follow_up():
    """TEST H: Within one identifiable conversation, provide state and field,
    then ask a follow-up question; fields are preserved.
    """
    orchestrator = CivicBridgeOrchestrator()
    sender_id = "test_user_h"
    conv_id = "conv_h_session"

    # Turn 1: State + Field of study
    t1 = "I am a student in Rajasthan studying economics"
    await orchestrator.handle_citizen_message(sender_id, t1, conversation_id=conv_id)

    s1 = orchestrator.get_or_create_session(sender_id, conversation_id=conv_id)
    assert s1.profile.state == "Rajasthan"
    assert s1.profile.field_of_study == "economics"
    assert s1.profile.occupation == "student"

    # Turn 2: Follow-up question
    t2 = "What scholarships am I eligible for?"
    await orchestrator.handle_citizen_message(sender_id, t2, conversation_id=conv_id)

    s2 = orchestrator.get_or_create_session(sender_id, conversation_id=conv_id)
    assert s2.profile.state == "Rajasthan", "State lost in follow-up!"
    assert s2.profile.field_of_study == "economics", "Field of study lost in follow-up!"
    assert s2.profile.occupation == "student", "Occupation lost in follow-up!"


# ==============================================================================
# TEST I: Multiple Independent Users Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_i_multiple_independent_users():
    """TEST I: Distinct senders submitting different profiles remain isolated."""
    orchestrator = CivicBridgeOrchestrator()

    # User 1: Farmer in UP
    await orchestrator.handle_citizen_message(
        "sender_farmer_1", "I am a 45-year-old farmer in Uttar Pradesh with 2 hectares"
    )
    s1 = orchestrator.get_or_create_session("sender_farmer_1")
    assert s1.profile.occupation == "farmer"
    assert s1.profile.state == "Uttar Pradesh"
    assert s1.profile.age == 45

    # User 2: Student in MP
    await orchestrator.handle_citizen_message(
        "sender_student_2", "I am a 20-year-old student in Madhya Pradesh"
    )
    s2 = orchestrator.get_or_create_session("sender_student_2")
    assert s2.profile.occupation == "student"
    assert s2.profile.state == "Madhya Pradesh"
    assert s2.profile.age == 20

    # User 1 remains unchanged
    assert s1.profile.occupation == "farmer"
    assert s1.profile.state == "Uttar Pradesh"
    assert s1.profile.age == 45


# ==============================================================================
# TEST J: Consecutive Message Reliability (5 Varied Questions)
# ==============================================================================
@pytest.mark.asyncio
async def test_j_consecutive_message_reliability():
    """TEST J: Submit at least 5 varied valid project questions sequentially.
    Every handled question produces a valid ACP ChatMessage response.
    """
    orchestrator = CivicBridgeOrchestrator()
    sender_id = "test_user_j_reliability"

    queries = [
        # 1. Scheme discovery
        "I am a 21-year-old student in Maharashtra with annual income 2 lakh looking for schemes and internships",
        # 2. Scholarship document question
        "What documents might I need for a government scholarship application?",
        # 3. Internship marks question
        "An internship requires at least 60 percent marks, but I have not told you my marks. Am I eligible?",
        # 4. Profile-intake question
        "What information do you need from me to find suitable schemes, scholarships, or internships?",
        # 5. Application steps and official sources
        "What are next steps and official sources I should check before applying?",
    ]

    for idx, q in enumerate(queries, 1):
        msg = await orchestrator.handle_citizen_message(sender_id, q, conversation_id="conv_j")
        assert msg is not None, f"Query #{idx} returned None!"
        assert msg.content, f"Query #{idx} returned empty content!"
        text = extract_text(msg)
        assert len(text) > 50, f"Query #{idx} returned insufficient text ({len(text)} chars)!"


# ==============================================================================
# TEST K: Partial or Missing Information Handling
# ==============================================================================
def test_k_partial_or_missing_information():
    """TEST K: Missing facts result in UNKNOWN for dependent rules while
    supported rules evaluate deterministically.
    """
    age_rule = EligibilityRule(
        rule_name="rule_age",
        description="Age 18 to 40",
        rule_type="age_range",
        parameters={"min_age": 18, "max_age": 40},
    )
    income_rule = EligibilityRule(
        rule_name="rule_income",
        description="Annual income <= 250000",
        rule_type="income_limit",
        parameters={"max_annual_income": 250000.0},
    )
    occupation_rule = EligibilityRule(
        rule_name="rule_occ",
        description="Must be student",
        rule_type="occupation",
        parameters={"allowed": ["student"]},
    )

    # Profile with ONLY occupation
    partial_profile = ApplicantProfile(occupation="student")

    res_age = evaluate_rule(age_rule, partial_profile)
    res_income = evaluate_rule(income_rule, partial_profile)
    res_occ = evaluate_rule(occupation_rule, partial_profile)

    assert res_age.status == "UNKNOWN", "Missing age was falsely resolved!"
    assert res_income.status == "UNKNOWN", "Missing income was falsely resolved!"
    assert res_occ.status == "MET", "Supplied occupation was not evaluated!"


# ==============================================================================
# TEST L: Contradictory or Corrected Information Updates
# ==============================================================================
def test_l_contradictory_or_corrected_information():
    """TEST L: Explicit corrections in follow-up overwrite old values cleanly."""
    # Turn 1
    p1 = extract_profile_from_text("I am a student in Maharashtra with annual income 3 lakh")
    assert p1.annual_income == 300000.0
    assert p1.state == "Maharashtra"
    assert p1.occupation == "student"

    # Turn 2: Correction
    p2 = extract_profile_from_text(
        "Actually my annual income is 1.8 lakh and I live in Gujarat",
        existing_profile=p1,
        is_follow_up=True,
    )
    assert p2.annual_income == 180000.0, "Corrected income was not updated!"
    assert p2.state == "Gujarat", "Corrected state was not updated!"
    assert p2.occupation == "student", "Compatible occupation was lost!"


# ==============================================================================
# TEST M: Existing Features (Discovery, Eligibility, Growth Planner)
# ==============================================================================
@pytest.mark.asyncio
async def test_m_existing_features():
    """TEST M: Full discovery, deterministic eligibility, internships, and Growth Planner
    run successfully with the status badges.
    """
    orchestrator = CivicBridgeOrchestrator()
    prompt = (
        "I am a 21 years old undergraduate student in Rajasthan studying economics. "
        "My family annual income is 1.5 Lakh. What government scholarships and internships can I apply for?"
    )

    msg = await orchestrator.handle_citizen_message("user_pipeline_m", prompt)
    text = extract_text(msg)

    assert "CivicBridge Opportunities & Growth Assessment" in text
    assert "CivicBridge Eligibility Growth Plan" in text
    assert "Rajasthan" in text
    assert "Economics" in text

    has_valid_badge = any(
        badge in text
        for badge in [
            "🟢 **ELIGIBILITY CONFIRMED",
            "🟡 **LIKELY ELIGIBLE",
            "⚪ **POTENTIALLY RELEVANT",
            "🔴 **NOT ELIGIBLE",
        ]
    )
    assert has_valid_badge is True
