"""Tests for conversation isolation, applicant field inference, and profile source tracking (Bugs 1 & 2)."""

import pytest
from schemas.applicant import ApplicantProfile, extract_profile_from_text
from schemas.scheme import EligibilityRule
from tools.eligibility_rules import evaluate_rule
from agent.orchestrator import CivicBridgeOrchestrator
from specialists.eligibility import EligibilitySpecialist
from uagents_core.contrib.protocols.chat import TextContent


def extract_text(msg) -> str:
    """Helper to extract text from ACP ChatMessage."""
    return "".join(c.text for c in msg.content if isinstance(c, TextContent))


# ==============================================================================
# TEST A: Conversation Isolation — No Profile Leakage Across New Conversations
# ==============================================================================
@pytest.mark.asyncio
async def test_conversation_isolation_no_leakage_between_conversations():
    """TEST A: When a user finishes Conv A ('32, UP, Computer Science') and starts Conv B
    ('student looking for government internships'), Conv B must NOT inherit age 32, UP, or CS.
    """
    orchestrator = CivicBridgeOrchestrator()
    sender_id = "agent1q_test_citizen_returning"

    # Turn 1 in Conversation A: Farmer / CS demographic in UP
    conv_a_text = "I am a 32 years old farmer in Uttar Pradesh and I study Computer Science"
    await orchestrator.handle_citizen_message(
        sender_id=sender_id, message_text=conv_a_text, conversation_id="conv_a"
    )

    session_a = orchestrator.get_or_create_session(sender_id, conversation_id="conv_a")
    assert session_a.profile.age == 32
    assert session_a.profile.state == "Uttar Pradesh"
    assert session_a.profile.field_of_study == "computer_science"

    # Turn 1 in Conversation B: Separate conversation ID
    conv_b_text = "I am a student looking for government internship"
    await orchestrator.handle_citizen_message(
        sender_id=sender_id, message_text=conv_b_text, conversation_id="conv_b"
    )

    session_b = orchestrator.get_or_create_session(sender_id, conversation_id="conv_b")
    # Must NOT inherit any unverified facts from Conversation A
    assert session_b.profile.age is None, "Age 32 leaked from Conv A to Conv B!"
    assert session_b.profile.state is None, "State Uttar Pradesh leaked from Conv A to Conv B!"
    assert session_b.profile.field_of_study is None, "Field of study leaked from Conv A to Conv B!"
    assert session_b.profile.occupation == "student"
    assert session_b.profile.opportunity_interest == "internships"

    # Also test same sender WITHOUT conversation ID (safe fallback for Agentverse web chat)
    orchestrator_fallback = CivicBridgeOrchestrator()
    # Turn 1: 32 yr old farmer in UP
    await orchestrator_fallback.handle_citizen_message(
        sender_id=sender_id,
        message_text="I am a 32 years old farmer in Uttar Pradesh with 1.5 hectares of land",
    )
    s1 = orchestrator_fallback.get_or_create_session(sender_id)
    assert s1.profile.age == 32
    assert s1.profile.state == "Uttar Pradesh"

    # Turn 2: New persona / standalone query without conversation ID
    await orchestrator_fallback.handle_citizen_message(
        sender_id=sender_id,
        message_text="I am a student looking for government internship",
    )
    s2 = orchestrator_fallback.get_or_create_session(sender_id)
    assert s2.profile.age is None, "Age leaked across persona boundary without conversation ID!"
    assert s2.profile.state is None, "State leaked across persona boundary without conversation ID!"
    assert s2.profile.field_of_study is None, "Field of study leaked across persona boundary!"
    assert s2.profile.occupation == "student"


# ==============================================================================
# TEST B: Applicant Fields Are Not Incorrectly Inferred (Farmer is not CS)
# ==============================================================================
def test_farmer_query_does_not_infer_computer_science_or_default_values():
    """TEST B: Asking about a farmer must NEVER infer Computer Science as field of study
    nor invent landholding, age, or state default values.
    """
    farmer_query = "I am a farmer looking for government schemes"
    profile = extract_profile_from_text(farmer_query)

    assert profile.occupation == "farmer"
    assert profile.category_interest == "agriculture"
    assert profile.opportunity_interest == "schemes"

    # Field of study must NOT be Computer Science
    assert profile.field_of_study is None, "Farmer was falsely assigned Computer Science!"
    assert profile.get_source("field_of_study") == "unknown"

    # Unstated attributes must be UNKNOWN / None
    assert profile.age is None
    assert profile.state is None
    assert profile.landholding_ha is None
    assert profile.is_landholder is None
    assert profile.annual_income is None
    assert profile.education_level is None

    # Source tracking
    assert profile.get_source("occupation") == "explicitly_supplied"
    assert profile.get_source("age") == "unknown"
    assert profile.get_source("state") == "unknown"


# ==============================================================================
# TEST C: Missing Age on Scholarship Query Results in UNKNOWN Status
# ==============================================================================
def test_missing_age_results_in_unknown_status_for_age_rule():
    """TEST C: Missing age on an age-restricted opportunity returns UNKNOWN for the age rule,
    never marking it MET with false certainty.
    """
    age_rule = EligibilityRule(
        rule_name="intern_age",
        description="Applicant must be between 21 and 24 years old",
        rule_type="age_range",
        parameters={"min_age": 21, "max_age": 24},
    )

    profile_no_age = ApplicantProfile(occupation="student", education_level="graduate")
    result = evaluate_rule(age_rule, profile_no_age)

    assert result.status == "UNKNOWN"
    assert "unknown" in result.reason.lower()

    # When age is provided
    profile_with_age = ApplicantProfile(age=22, occupation="student")
    res_met = evaluate_rule(age_rule, profile_with_age)
    assert res_met.status == "MET"


# ==============================================================================
# TEST D: Legitimate Follow-Up Context Preserved Within Same Conversation Only
# ==============================================================================
@pytest.mark.asyncio
async def test_legitimate_follow_up_preserves_context_within_conversation():
    """TEST D: In one conversation, user provides state and occupation, then provides
    income follow-up; preserves state and occupation only within that conversation.
    """
    orchestrator = CivicBridgeOrchestrator()
    sender_id = "agent1q_test_follow_up_user"
    conv_id = "session_journey_01"

    # Turn 1: State + Occupation
    t1_text = "I am a student in Rajasthan looking for education schemes"
    r1 = await orchestrator.handle_citizen_message(sender_id, t1_text, conversation_id=conv_id)
    assert r1 is not None

    s = orchestrator.get_or_create_session(sender_id, conversation_id=conv_id)
    assert s.profile.state == "Rajasthan"
    assert s.profile.occupation == "student"
    assert s.profile.annual_income is None

    # Turn 2: Legitimate follow-up providing income
    t2_text = "My family income is 2 lakh rupees"
    r2 = await orchestrator.handle_citizen_message(sender_id, t2_text, conversation_id=conv_id)
    assert r2 is not None

    s_after = orchestrator.get_or_create_session(sender_id, conversation_id=conv_id)
    # Both state and occupation must be preserved!
    assert s_after.profile.state == "Rajasthan"
    assert s_after.profile.occupation == "student"
    assert s_after.profile.annual_income == 200000.0

    # Turn 3: User starts a NEW conversation
    conv_id_2 = "session_journey_02"
    t3_text = "I am a farmer looking for government schemes"
    await orchestrator.handle_citizen_message(sender_id, t3_text, conversation_id=conv_id_2)

    s_new = orchestrator.get_or_create_session(sender_id, conversation_id=conv_id_2)
    assert s_new.profile.occupation == "farmer"
    assert s_new.profile.state is None, "State leaked into separate conversation!"
    assert s_new.profile.annual_income is None, "Income leaked into separate conversation!"


# ==============================================================================
# TEST E: Cross-User Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_cross_user_isolation():
    """TEST E: Cross-user isolation between user_1 and user_2."""
    orchestrator = CivicBridgeOrchestrator()

    # User 1 sets farmer profile in UP
    await orchestrator.handle_citizen_message(
        "user_farmer_1", "I am a 45-year-old farmer in Uttar Pradesh with 2 hectares"
    )
    s1 = orchestrator.get_or_create_session("user_farmer_1")
    assert s1.profile.occupation == "farmer"
    assert s1.profile.state == "Uttar Pradesh"
    assert s1.profile.age == 45

    # User 2 makes inquiry
    await orchestrator.handle_citizen_message(
        "user_student_2", "I am looking for government scholarships"
    )
    s2 = orchestrator.get_or_create_session("user_student_2")
    assert s2.profile.occupation == "student"
    assert s2.profile.state is None
    assert s2.profile.age is None

    # User 1 is unaffected
    assert s1.profile.occupation == "farmer"
    assert s1.profile.age == 45
    assert s1.profile.state == "Uttar Pradesh"


# ==============================================================================
# TEST F: Scheme Requiring Academic Marks Returns UNKNOWN When Omitted
# ==============================================================================
def test_missing_academic_marks_returns_unknown():
    """TEST F: Scheme requiring academic marks returns UNKNOWN / Pending Verification
    when marks percentage is omitted.
    """
    marks_rule = EligibilityRule(
        rule_name="min_academic_marks",
        description="Must have scored at least 60% in qualifying degree",
        rule_type="marks_minimum",
        parameters={"min_percentage": 60.0},
    )

    # Applicant without marks declared
    student_no_marks = ApplicantProfile(occupation="student", education_level="graduate")
    res_unknown = evaluate_rule(marks_rule, student_no_marks)
    assert res_unknown.status == "UNKNOWN"
    assert "not specified" in res_unknown.reason

    # Applicant with marks declared
    student_with_marks = ApplicantProfile(
        occupation="student", education_level="graduate", marks_percentage=75.0
    )
    res_met = evaluate_rule(marks_rule, student_with_marks)
    assert res_met.status == "MET"


# ==============================================================================
# TEST G: Existing Pipeline (Discovery, Eligibility, Internships, Growth Planner)
# ==============================================================================
@pytest.mark.asyncio
async def test_full_pipeline_with_badges_and_growth_plan():
    """TEST G: Existing discovery, deterministic eligibility, internships, and Growth Planner
    run successfully with the new status badges.
    """
    orchestrator = CivicBridgeOrchestrator()
    prompt = (
        "I am a 21 years old undergraduate student in Rajasthan studying economics. "
        "My family annual income is 1.5 Lakh. What government scholarships and internships can I apply for?"
    )

    msg = await orchestrator.handle_citizen_message("user_pipeline_test", prompt)
    text = extract_text(msg)

    # Must contain both opportunities and Growth Plan
    assert "CivicBridge Opportunities & Growth Assessment" in text
    assert "CivicBridge Eligibility Growth Plan" in text
    assert "Rajasthan" in text
    assert "Economics" in text

    # Must contain proper badges
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

    # Must contain actionable growth next steps
    assert "High-Leverage" in text or "Recommended" in text or "Procedure Portal" in text
