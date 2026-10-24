"""Regression tests for Agent Chat Protocol (ACP v0.3.0) handler and message flow."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from uagents import Context
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    StartSessionContent,
    EndSessionContent,
    TextContent,
    MetadataContent,
)

from agent.main import handle_chat_message
from agent.orchestrator import CivicBridgeOrchestrator


def make_chat_message(content_items) -> ChatMessage:
    """Helper to construct ACP ChatMessage with unique ID and timestamp."""
    return ChatMessage(
        msg_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        content=content_items,
    )


def extract_text(msg: ChatMessage) -> str:
    """Extract concatenated text content from a ChatMessage."""
    return "".join(c.text for c in msg.content if isinstance(c, TextContent))


@pytest.fixture
def mock_context():
    """Mock uAgent Context with async send and logger."""
    ctx = MagicMock(spec=Context)
    ctx.logger = MagicMock()
    ctx.send = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_acp_handler_with_start_session_and_text(mock_context):
    """CRITICAL REGRESSION TEST: When Agentverse web chat sends StartSessionContent AND TextContent,
    the handler must extract the user's text and return the actual answer, NOT the welcome message.
    """
    sender = "agent1test_sender_01"
    incoming = make_chat_message([
        StartSessionContent(),
        TextContent(type="text", text="I am a 32 years old farmer in Uttar Pradesh with 1.2 hectares of land"),
    ])

    await handle_chat_message(mock_context, sender, incoming)

    # Context.send should be called at least twice:
    # 1. ChatAcknowledgement
    # 2. Actual response ChatMessage
    assert mock_context.send.call_count >= 2

    # Check acknowledgement
    ack_call = mock_context.send.call_args_list[0]
    assert ack_call[0][0] == sender
    assert isinstance(ack_call[0][1], ChatAcknowledgement)
    assert ack_call[0][1].acknowledged_msg_id == incoming.msg_id

    # Check response ChatMessage
    response_call = mock_context.send.call_args_list[1]
    assert response_call[0][0] == sender
    response_msg = response_call[0][1]
    assert isinstance(response_msg, ChatMessage)

    response_text = extract_text(response_msg)
    # Must NOT be a generic welcome message
    assert "Namaste! Welcome to CivicBridge" not in response_text
    # Must contain relevant farming scheme results
    assert "PM-KISAN" in response_text or "Uttar Pradesh" in response_text


@pytest.mark.asyncio
async def test_acp_handler_empty_start_session_returns_greeting(mock_context):
    """When a client sends StartSessionContent with NO user text, deliver the welcome greeting."""
    sender = "agent1test_sender_02"
    incoming = make_chat_message([StartSessionContent()])

    await handle_chat_message(mock_context, sender, incoming)

    assert mock_context.send.call_count == 2
    response_msg = mock_context.send.call_args_list[1][0][1]
    response_text = extract_text(response_msg)
    assert "Namaste! Welcome to CivicBridge" in response_text


@pytest.mark.asyncio
async def test_scholarship_vs_farming_produce_distinct_responses():
    """Verify that a scholarship question and a farming-scheme question receive contextually distinct responses."""
    orchestrator = CivicBridgeOrchestrator()

    # Query 1: Scholarship
    r1 = await orchestrator.handle_citizen_message(
        "user_scholarship", "I am a college student from SC category looking for scholarship schemes"
    )
    t1 = extract_text(r1)

    # Query 2: Farming
    r2 = await orchestrator.handle_citizen_message(
        "user_farmer", "I am a small farmer in Uttar Pradesh with 1 hectare of agricultural land"
    )
    t2 = extract_text(r2)

    # Responses must be completely different
    assert t1 != t2

    s1 = orchestrator.get_or_create_session("user_scholarship")
    s2 = orchestrator.get_or_create_session("user_farmer")

    # Query 1 focuses on education/scholarships
    eval_names_1 = [e.short_name for e in s1.last_evaluations]
    assert "Post-Matric SC" in eval_names_1 or "NMMSS" in eval_names_1
    assert "PM-KISAN" not in eval_names_1

    # Query 2 focuses on agriculture/farming
    eval_names_2 = [e.short_name for e in s2.last_evaluations]
    assert "PM-KISAN" in eval_names_2 or "PM-KMY" in eval_names_2
    assert "Post-Matric SC" not in eval_names_2


@pytest.mark.asyncio
async def test_internship_query_reaches_internship_logic():
    """Verify that an internship query returns official government internships."""
    orchestrator = CivicBridgeOrchestrator()
    sender = "user_intern_test"

    response = await orchestrator.handle_citizen_message(
        sender, "I am looking for government internships for computer science graduates"
    )
    text = extract_text(response)

    # Must contain internship section and specific internships
    assert "Internship" in text
    assert ("PMIS" in text or "Digital-India-Internship" in text or "TULIP" in text)


@pytest.mark.asyncio
async def test_scheme_specific_query_returns_scheme_details():
    """Verify that querying a specific scheme acronym like PM-KISAN returns detailed checklist & roadmap."""
    orchestrator = CivicBridgeOrchestrator()
    sender = "user_pmkisan_test"

    response = await orchestrator.handle_citizen_message(sender, "PM-KISAN")
    text = extract_text(response)

    assert "Application Roadmap: PM-KISAN" in text
    assert "pmkisan.gov.in" in text
    assert "Aadhaar Card" in text
    assert "Land Ownership Document" in text


@pytest.mark.asyncio
async def test_missing_details_marked_as_unknown():
    """Verify that missing demographic details result in UNKNOWN status rather than false certainty."""
    orchestrator = CivicBridgeOrchestrator()
    sender = "user_unknown_test"

    # User mentions occupation and state, but omits income and caste
    response = await orchestrator.handle_citizen_message(
        sender, "I am a student in Rajasthan looking for education schemes, what can I apply for now?"
    )
    text = extract_text(response)

    # Pending verification / unknown conditions must be noted
    assert "Pending Verification" in text or "UNKNOWN" in text or "Rajasthan" in text
    session = orchestrator.get_or_create_session(sender)
    assert session.last_evaluations
    # Check that at least one evaluation has unknown conditions
    has_unknown = any(len(e.unknown_conditions) > 0 for e in session.last_evaluations)
    assert has_unknown is True


@pytest.mark.asyncio
async def test_acp_handler_exception_safety(mock_context):
    """Verify that if an exception occurs during orchestrator processing, it is logged and a fallback message is sent."""
    sender = "agent1error_test"
    incoming = make_chat_message([TextContent(type="text", text="crash test")])

    with patch("agent.main.orchestrator.handle_citizen_message", side_effect=RuntimeError("Simulated database failure")):
        await handle_chat_message(mock_context, sender, incoming)

    # Must log exception
    mock_context.logger.exception.assert_called_once()
    # Must send fallback ChatMessage
    assert mock_context.send.call_count == 2
    fallback_msg = mock_context.send.call_args_list[1][0][1]
    assert isinstance(fallback_msg, ChatMessage)
    fallback_text = extract_text(fallback_msg)
    assert "unexpected issue" in fallback_text or "Simulated database failure" in fallback_text


@pytest.mark.asyncio
async def test_session_isolation_and_reset():
    """Verify that different users have isolated profiles and session reset clears state."""
    orchestrator = CivicBridgeOrchestrator()

    # User 1 sets farming profile
    await orchestrator.handle_citizen_message("user_alpha", "I am a farmer in UP with 2 hectares")
    s1 = orchestrator.get_or_create_session("user_alpha")
    assert s1.profile.occupation == "farmer"
    assert s1.profile.state == "Uttar Pradesh"

    # User 2 sets student profile
    await orchestrator.handle_citizen_message("user_beta", "I am a student in Maharashtra")
    s2 = orchestrator.get_or_create_session("user_beta")
    assert s2.profile.occupation == "student"
    assert s2.profile.state == "Maharashtra"

    # User 1 profile was not modified by User 2
    assert s1.profile.occupation == "farmer"

    # Reset User 1 session
    orchestrator.reset_session("user_alpha")
    s1_fresh = orchestrator.get_or_create_session("user_alpha")
    assert s1_fresh.profile.occupation is None
    assert s1_fresh.profile.state is None
