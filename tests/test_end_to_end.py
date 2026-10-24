"""End-to-End tests simulating complete citizen journeys across multiple categories."""

import pytest
from uagents_core.contrib.protocols.chat import TextContent, MetadataContent
from agent.orchestrator import CivicBridgeOrchestrator


@pytest.fixture
def orchestrator():
    return CivicBridgeOrchestrator()


@pytest.mark.asyncio
async def test_profile_1_farmer_in_uttar_pradesh(orchestrator):
    """Citizen Profile 1: Small landholding farmer in Uttar Pradesh.
    
    Details: 32 years old, rural UP, owns 1.2 hectares of land, does not pay income tax.
    Expected: Matches PM-KISAN (ELIGIBLE) and PM-KMY (ELIGIBLE).
    """
    user_id = "user_up_farmer_01"
    prompt = (
        "Namaste, I am a 32 years old farmer living in a village in Uttar Pradesh. "
        "I own 1.2 hectares of cultivable land and I do not pay income tax. "
        "What government benefits or schemes can I apply for?"
    )

    response = await orchestrator.handle_citizen_message(user_id, prompt)
    assert response is not None
    assert len(response.content) >= 1

    text_content = next((c for c in response.content if isinstance(c, TextContent)), None)
    assert text_content is not None
    text = text_content.text

    # Verify shortlisting and matching
    assert "PM-KISAN" in text
    assert "ELIGIBLE" in text
    assert "pmkisan.gov.in" in text
    assert "Uttar Pradesh" in text

    # Verify interactive card metadata is present
    meta_content = next((c for c in response.content if isinstance(c, MetadataContent)), None)
    assert meta_content is not None
    assert meta_content.metadata.get("card_kind") == "custom"
    assert "PM-KISAN" in meta_content.metadata.get("card_payload")

    # Step 2 of workflow: Citizen requests detailed checklist for PM-KISAN
    drilldown_prompt = "Tell me the documents required and steps for PM-KISAN"
    drill_response = await orchestrator.handle_citizen_message(user_id, drilldown_prompt)
    drill_text = next((c for c in drill_response.content if isinstance(c, TextContent)), None).text

    assert "Application Roadmap: PM-KISAN" in drill_text
    assert "Aadhaar Card" in drill_text
    assert "Khatauni" in drill_text
    assert "https://pmkisan.gov.in" in drill_text


@pytest.mark.asyncio
async def test_profile_2_student_in_maharashtra(orchestrator):
    """Citizen Profile 2: SC college student in Maharashtra.
    
    Details: 20 years old, college student, SC category, annual family income ₹1.8 Lakh.
    Expected: Matches Post-Matric Scholarship for SC Students (ELIGIBLE).
    """
    user_id = "user_mh_student_02"
    prompt = (
        "I am a 20 year old college student in Maharashtra from SC category. "
        "My family annual income is 1.8 Lakh rupees. Are there any scholarships for me?"
    )

    response = await orchestrator.handle_citizen_message(user_id, prompt)
    assert response is not None

    text_content = next((c for c in response.content if isinstance(c, TextContent)), None)
    assert text_content is not None
    text = text_content.text

    assert "Post-Matric SC" in text
    assert "scholarships.gov.in" in text
    assert "ELIGIBLE" in text

    # Step 2: Request application checklist
    drilldown_prompt = "Show me the checklist for Post-Matric SC"
    drill_response = await orchestrator.handle_citizen_message(user_id, drilldown_prompt)
    drill_text = next((c for c in drill_response.content if isinstance(c, TextContent)), None).text

    assert "Application Roadmap: Post-Matric SC" in drill_text
    assert "Caste Certificate" in drill_text
    assert "Income Certificate" in drill_text


@pytest.mark.asyncio
async def test_profile_3_urban_street_vendor(orchestrator):
    """Citizen Profile 3: Urban street vendor in Delhi seeking business loan.
    
    Details: 28 years old, urban street vendor / hawker in Delhi.
    Expected: Matches PM SVANidhi (ELIGIBLE).
    """
    user_id = "user_delhi_vendor_03"
    prompt = (
        "I am a 28 years old street vendor running a fruit stall in Delhi city. "
        "I need a small working capital loan for my business."
    )

    response = await orchestrator.handle_citizen_message(user_id, prompt)
    assert response is not None

    text_content = next((c for c in response.content if isinstance(c, TextContent)), None)
    assert text_content is not None
    text = text_content.text

    assert "PM-SVANidhi" in text
    assert "pmsvanidhi.mohua.gov.in" in text
    assert "ELIGIBLE" in text

    # Step 2: Drilldown
    drilldown_prompt = "PM-SVANidhi details please"
    drill_response = await orchestrator.handle_citizen_message(user_id, drilldown_prompt)
    drill_text = next((c for c in drill_response.content if isinstance(c, TextContent)), None).text

    assert "PM-SVANidhi" in drill_text
    assert "Certificate of Vending" in drill_text or "Urban Local Body" in drill_text


@pytest.mark.asyncio
async def test_privacy_protection_aadhaar_warning(orchestrator):
    """Privacy test: Ensure agent rejects / warns against sharing 12-digit Aadhaar number."""
    user_id = "user_privacy_check"
    prompt = "My Aadhaar number is 1234 5678 9012 and I need assistance."

    response = await orchestrator.handle_citizen_message(user_id, prompt)
    assert response is not None
    text = next((c for c in response.content if isinstance(c, TextContent)), None).text

    assert "Privacy Protection" in text
    assert "do not share Aadhaar" in text
    # Verify the number was not echoed back or stored
    assert "1234 5678 9012" not in orchestrator.get_or_create_session(user_id).profile.summary_dict().values()


@pytest.mark.asyncio
async def test_multistep_conversational_workflow(orchestrator):
    """Test full conversational journey: Greeting -> Follow-up -> Shortlist -> Card Button Click."""
    user_id = "user_flow_04"

    # Turn 1: Greeting
    r1 = await orchestrator.handle_citizen_message(user_id, "Hello")
    t1 = next((c for c in r1.content if isinstance(c, TextContent)), None).text
    assert "Namaste! Welcome to CivicBridge" in t1

    # Turn 2: Vague requirement
    r2 = await orchestrator.handle_citizen_message(user_id, "I need a house")
    t2 = next((c for c in r2.content if isinstance(c, TextContent)), None).text
    assert "housing" in t2.lower() or "residence" in t2.lower()

    # Turn 3: Provides specific details
    r3 = await orchestrator.handle_citizen_message(user_id, "I live in a rural village, low income family without a pucca house")
    t3 = next((c for c in r3.content if isinstance(c, TextContent)), None).text
    assert "PMAY-G" in t3

    # Turn 4: Card button click event (emulated JSON)
    card_click = '{"action": "view_checklist", "scheme_id": "pmay_g"}'
    r4 = await orchestrator.handle_citizen_message(user_id, card_click)
    t4 = next((c for c in r4.content if isinstance(c, TextContent)), None).text
    assert "Application Roadmap: PMAY-G" in t4
    assert "pmayg.nic.in" in t4


@pytest.mark.asyncio
async def test_partial_specialist_failure_handling(orchestrator):
    """Test resilience when a specialist receives edge-case inputs or partial results."""
    user_id = "user_edge_case"

    # Query with nonexistent domain
    r_empty = await orchestrator.handle_citizen_message(user_id, "I want assistance for space rocket tourism")
    t_empty = next((c for c in r_empty.content if isinstance(c, TextContent)), None).text
    assert "No active government schemes matched" in t_empty or "benefit area" in t_empty.lower()

    # Query for nonexistent scheme details via card action
    fake_card_click = '{"action": "view_checklist", "scheme_id": "non_existent_fake_scheme"}'
    r_fake = await orchestrator.handle_citizen_message(user_id, fake_card_click)
    # Orchestrator handles gracefully without throwing unhandled exception
    assert r_fake is not None

