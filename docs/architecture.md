# CivicBridge Architecture & Design Specification

## 1. Overview

**CivicBridge** is an autonomous AI-agent system designed for Indian citizens to navigate complex government welfare programs and official internships, evaluate eligibility deterministically, and generate personalized Eligibility Growth Plans and application roadmaps.

Built on **Fetch.ai uAgents**, the **Agent Chat Protocol (ACP v0.3.0)**, and **ASI:One**, CivicBridge delivers an interactive, conversational advisory workflow directly within decentralized chat interfaces without requiring any custom third-party frontend.

---

## 2. Multi-Specialist Component Architecture

CivicBridge uses a modular, specialist-driven architecture coordinated inside a single high-performance agent runtime:

```mermaid
flowchart TD
    User["Citizen / ASI:One User"] <-->|"Agent Chat Protocol (ACP v0.3.0)\nText & Dynamic UI Cards"| Agent["CivicBridge Agent (uAgent)"]
    
    subgraph Agent Runtime
        Agent <--> Orchestrator["Orchestrator Component"]
        
        Orchestrator -->|"1. Extract & Search"| Discovery["Scheme & Internship Discovery Specialist"]
        Orchestrator -->|"2. Deterministic Rules"| Eligibility["Eligibility Specialist (17 Rule Types)"]
        Orchestrator -->|"3. Source & Logic Audit"| Verification["Verification Specialist"]
        Orchestrator -->|"4. Personalized Roadmaps & Growth"| Planner["Application & Growth Planning Specialist"]
        
        Discovery <-->|"Query Catalog"| Repo["Scheme Repository (SQLite)"]
        Discovery <--> SearchTool["Multi-Channel Search Tool"]
        Eligibility <--> RulesTool["Deterministic Rules Engine"]
        Verification <--> SourceTool["Source & Citation Validator"]
        Planner <--> GrowthEngine["Eligibility Growth Engine"]
    end
```

### Specialist Breakdown & Responsibilities

1. **Orchestrator (`agent/orchestrator.py`)**
   - Ingests inbound ACP `ChatMessage` blocks and card button actions (`MetadataContent`).
   - Maintains conversational session state (`UserSession`) per citizen.
   - Parses applicant attributes (state, residence, age, occupation, education level, field of study, skills, caste, landholding, income) while enforcing privacy safeguards (explicitly scrubbing Aadhaar/bank numbers).
   - Coordinates specialist calls in sequence and handles partial data, missing criteria, or edge-case inputs gracefully.
   - Synthesizes Schemes, Internships, and Eligibility Growth Plans into a unified response with ASI:One interactive element-tree cards.

2. **Scheme & Internship Discovery Specialist (`specialists/discovery.py`)**
   - Connects to the local SQLite repository via `SchemeSearchTool`.
   - Supports two coordinated discovery channels:
     - **Welfare Schemes**: Filtered by category, urban/rural residence, state coverage, and livelihood.
     - **Government Internships**: Filtered by field of study, qualification status, and location.
   - Relaxes filters progressively if strict matching yields no candidates.

3. **Eligibility Specialist (`specialists/eligibility.py`)**
   - Evaluates explicit, structured criteria using deterministic Python comparison logic (`tools/eligibility_rules.py`).
   - Supports 17 deterministic rule types:
     - `age_range`, `residence`, `occupation`, `income_limit`, `caste`, `landholding_max`
     - `education_min`, `field_of_study`, `skills`, `marks_minimum`, `degree_status`
     - `disqualification`, `gender`, `maternity`, `bpl_required`, `fixed_condition`
   - Produces structured results for every rule with status:
     - `MET`: Condition verified by provided profile data.
     - `NOT_MET`: Condition violated by provided profile data.
     - `UNKNOWN`: Information missing from profile; never assumed to be eligible.
   - Computes overall category: `ELIGIBLE`, `LIKELY_ELIGIBLE`, `POTENTIALLY_ELIGIBLE`, or `NOT_ELIGIBLE`.

4. **Verification Specialist (`specialists/verification.py`)**
   - Checks that all candidate schemes and internships reference authorized `.gov.in`, `.nic.in`, or approved official portal domains.
   - Validates secure HTTPS transport and flags unencrypted links.
   - Validates verification freshness against a 365-day threshold to flag stale records.
   - Audits eligibility outputs against structured rules to ensure integrity.

5. **Application & Growth Planning Specialist (`specialists/application_planner.py`)**
   - **Application Roadmap**: Generates tailored document checklists (customizing certificates based on citizen caste, landholding, or income), step-by-step application instructions, and official portal URLs.
   - **Eligibility Growth Planner**: Connects published requirements to concrete next steps:
     - Classifies gaps into 6 categories: `missing_document`, `missing_registration`, `missing_skill`, `missing_qualification`, `experience_requirement`, `unmet_fixed_condition`.
     - Identifies **High-Leverage Actions** that unlock multiple target opportunities simultaneously.
     - Associates recognized portals (e.g., [SWAYAM](https://swayam.gov.in/), [NSP](https://scholarships.gov.in/)) for skill and registration completion.
     - Delineates statutory boundaries as non-negotiable (`satisfaction_guarantee="fixed_ineligible"`).

---

## 3. Protocol & Messaging Flow

```mermaid
sequenceDiagram
    autonumber
    actor Citizen as Citizen (ASI:One)
    participant Agent as CivicBridge Agent
    participant Orch as Orchestrator
    participant DB as SQLite DB

    Citizen->>Agent: ChatMessage (text: "I am a student from Rajasthan looking for internships and aid")
    Agent->>Citizen: ChatAcknowledgement (receipt)
    Agent->>Orch: handle_citizen_message()
    Orch->>DB: Search matching schemes & internships
    DB-->>Orch: Candidates (NMMSS, Post-Matric SC, PMIS, Digital India, TULIP)
    Orch->>Orch: Evaluate deterministic rules (MET, NOT_MET, UNKNOWN)
    Orch->>Orch: Audit citations & freshness (.gov.in check)
    Orch->>Orch: Generate Eligibility Growth Plan (High-leverage gaps)
    Orch-->>Agent: ChatMessage with Unified Markdown + Dynamic UI Card
    Agent->>Citizen: ChatMessage (Delivered to ASI:One)
    
    Citizen->>Agent: Card Button Tap / Text: "PMIS"
    Agent->>Orch: handle_citizen_message("PMIS")
    Orch->>Orch: Generate personalized checklist & steps for PMIS
    Orch-->>Agent: ChatMessage with Roadmap Markdown + Detail Card
    Agent->>Citizen: ChatMessage (Delivered to ASI:One)
```

---

## 4. ASI:One Dynamic UI Integration

CivicBridge conforms to the official **Agentverse Element-Tree Specification**:
- **Protocol Header**: Transmitted as a `MetadataContent` block alongside markdown `TextContent`.
- **Card Payload Schema**:
  ```json
  {
    "card_protocol_version": "1",
    "requires_card_interaction": "true",
    "card_kind": "custom",
    "card_payload": "{\"root\": {\"type\": \"section\", \"title\": \"...\", \"children\": [...]}}"
  }
  ```
- **Supported Visual Components**: `section`, `list`, `badge`, `button`, `action.selection` with direct click-to-drilldown actions.
- **Dual Compatibility**: Because every message includes both markdown `TextContent` and element-tree `MetadataContent`, the agent functions seamlessly in standard terminal ACP clients, web chat, and rich ASI:One card carousels.

---

## 5. Security & Privacy Guardrails

1. **No Sensitive Identifiers**: CivicBridge never asks for, records, or stores Aadhaar numbers, PAN numbers, bank account numbers, or passwords.
2. **Deterministic Evaluation**: Calculations (age boundaries, income caps, landholding ceilings, marks percentages) use strict arithmetic in Python rather than relying on LLM guesses.
3. **Official Citation Whitelist**: Sources are checked against approved `.gov.in` and `.nic.in` domains.
4. **Advisory Disclaimer**: All output explicitly reminds citizens that assessments are informational and official sanction rests exclusively with government authorities.
5. **Ethical Boundaries in Growth Planning**:
   - Skills courses improve preparedness (`improves_preparedness`), never guaranteeing selection.
   - Statutory criteria (age ceilings, taxpayer exclusions) are never represented as solvable through courses or documents.
