# 🇮🇳 CivicBridge AI — Indian Government Benefits Navigator

[![Fetch.ai uAgents](https://img.shields.io/badge/Fetch.ai-uAgents_v0.26-blue)](https://github.com/fetchai/uAgents)
[![Agent Chat Protocol](https://img.shields.io/badge/ACP-v0.3.0-green)](https://github.com/fetchai/uAgents)
[![ASI:One Compatible](https://img.shields.io/badge/ASI:One-Dynamic_UI-orange)](https://asi1.ai/)
[![Test Suite](https://img.shields.io/badge/Tests-24%2F24_Passing-brightgreen)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**CivicBridge** is an autonomous AI agent built on Fetch.ai uAgents, the Agent Chat Protocol (ACP v0.3.0), and ASI:One that helps Indian citizens discover, assess eligibility for, and navigate central government welfare and financial assistance schemes.

CivicBridge operates deterministically against verified government data, provides actionable personalized document checklists, renders native ASI:One interactive cards, and guarantees citizen privacy by strictly forbidding collection of Aadhaar numbers or passwords.

---

## 📌 Problem Statement

India operates over hundreds of central and state welfare initiatives designed to support farmers, students, senior citizens, unorganized workers, and urban entrepreneurs. However, millions of eligible citizens miss out because:
1. **Information Asymmetry**: Scheme rules, income limits, and landholding caps are buried across fragmented gazettes and departmental websites.
2. **Ambiguous Eligibility**: Citizens frequently apply for programs they are ineligible for, or avoid applying due to confusing criteria.
3. **Complex Procedures**: Required certificates (caste, income, land records) vary significantly by scheme, leading to frequent rejections.
4. **Privacy & Fraud Concerns**: Fraudulent intermediary sites often solicit sensitive Aadhaar or bank credentials.

**CivicBridge solves this** by acting as a zero-friction, privacy-respecting navigator accessible through decentralized chat interfaces like ASI:One.

---

## 🎯 Target Users

- **Farmers & Cultivators**: Seeking income support (PM-KISAN), solar irrigation, and old-age pensions (PM-KMY).
- **Students & Scholars**: Seeking pre-matric and post-matric merit-cum-means scholarships.
- **Low-Income Families**: Needing health insurance cover (Ayushman Bharat PM-JAY) and pucca housing (PMAY-G / PMAY-U).
- **Senior Citizens & Unorganized Workers**: Requiring guaranteed monthly pensions (APY, IGNOAPS).
- **Street Vendors & Artisans**: Seeking collateral-free micro-credit loans (PM SVANidhi, PM Vishwakarma, PMEGP).

---

## 🚀 Key Features

- **Agent Chat Protocol (ACP v0.3.0) Native**: Connects directly to Agentverse mailboxes and ASI:One conversational chats.
- **ASI:One Dynamic UI & Cards**: Generates rich Element-Tree cards (`section`, `list`, `badge`, `button`, `action.selection`) with direct click-to-drilldown actions.
- **Deterministic Eligibility Logic**: Age bounds, income ceilings, land sizes, and caste criteria are evaluated using deterministic Python logic—never LLM hallucinations.
- **4 Specialist Architecture**: Scheme Discovery, Deterministic Eligibility, Verification Auditor, and Application Planner.
- **Strict Citation Verification**: All source links are audited against official `.gov.in` and `.nic.in` domains.
- **Zero Sensitive Data Ingestion**: Rejects Aadhaar numbers and bank credentials, ensuring privacy.
- **Actionable Application Roadmaps**: Generates tailored document checklists and numbered application instructions.

---

## 🏗️ Architecture

```
                                  [ Citizen in ASI:One ]
                                            │
                                            ▼  Agent Chat Protocol (ACP v0.3.0)
                             ┌──────────────────────────────┐
                             │   CivicBridge uAgent Core    │
                             └──────────────┬───────────────┘
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │   Multi-Agent Orchestrator   │
                             └──────┬───┬──────┬──────┬─────┘
                                    │   │      │      │
            ┌───────────────────────┘   │      │      └──────────────────────────┐
            ▼                           ▼      ▼                                 ▼
┌───────────────────────┐    ┌─────────────┐ ┌───────────────────┐    ┌─────────────────────┐
│ 1. Scheme Discovery   │    │ 2. Rules &  │ │ 3. Verification   │    │ 4. Application      │
│    Specialist         │    │ Eligibility │ │    Specialist     │    │    Planner          │
└───────────┬───────────┘    └──────┬──────┘ └─────────┬─────────┘    └──────────┬──────────┘
            │                       │                  │                         │
            ▼                       ▼                  ▼                         ▼
  [ SQLite Repository ]     [ Deterministic ]  [ .gov.in Domain & ]      [ Personalized Doc ]
  [ 13 Curated Schemes]     [ Math Evaluator]  [ Freshness Audit  ]      [ Checklist Engine ]
```

---

## 📦 Benefit Categories & Verified Schemes Catalog

CivicBridge includes 13 thoroughly verified schemes in `data/schemes.json` across 6 initial benefit categories:

1. **Agriculture & Farmer Support**:
   - `PM-KISAN`: Pradhan Mantri Kisan Samman Nidhi (₹6,000/yr DBT)
2. **Pensions & Social Welfare**:
   - `PM-KMY`: Pradhan Mantri Kisan Maan-Dhan Yojana (₹3,000/mo pension)
   - `APY`: Atal Pension Yojana (₹1,000 - ₹5,000/mo guaranteed pension)
   - `IGNOAPS`: Indira Gandhi National Old Age Pension Scheme
3. **Healthcare Assistance**:
   - `PM-JAY`: Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (₹5 Lakh cover/family)
   - `PMMVY`: Pradhan Mantri Matru Vandana Yojana (Maternity cash transfer)
4. **Housing Assistance**:
   - `PMAY-G`: Pradhan Mantri Awaas Yojana - Gramin (₹1.20 - ₹1.30 Lakh grant)
   - `PMAY-U`: Pradhan Mantri Awas Yojana - Urban (Up to ₹2.50 Lakh subsidy)
5. **Education & Scholarships**:
   - `NMMSS`: National Means-cum-Merit Scholarship (₹12,000/yr for Class 9-12)
   - `Post-Matric SC`: Post Matric Scholarship for Scheduled Caste Students
6. **Employment & Skill Development**:
   - `PM-SVANidhi`: Micro-credit loan for Street Vendors (₹10,000 - ₹50,000 at 7% subsidy)
   - `PM-Vishwakarma`: Toolkit grant (₹15,000) and credit (up to ₹3 Lakh at 5%) for artisans
   - `PMEGP`: Prime Minister's Employment Generation Programme (15%-35% margin subsidy)

---

## 💻 Tech Stack

- **Framework**: Python 3.10+, [Fetch.ai uAgents](https://github.com/fetchai/uAgents) (`>=0.26.1`), `uagents-core` (`>=0.4.12`)
- **Messaging Protocol**: Agent Chat Protocol (ACP v0.3.0) with element-tree dynamic cards
- **Data Layer**: SQLite 3 with repository pattern & seed loader
- **Validation**: Pydantic v2
- **Testing**: Pytest & Pytest-Asyncio

---

## ⚙️ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/kushagra4798/civicbridge_ai.git
cd civicbridge_ai
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```
Edit `.env` if you wish to customize port, seed phrase, or add an Agentverse mailbox key:
```env
AGENT_NAME="CivicBridge Navigator"
AGENT_SEED_PHRASE="civicbridge-navigator-secret-seed-2026"
AGENT_PORT=8000
AGENT_MAILBOX_KEY=""  # Fill in when deploying to Agentverse
DATABASE_PATH="database/civicbridge.db"
LOG_LEVEL="INFO"
```

### 5. Seed Database
```bash
python database/seed.py
```
*Output: `Successfully seeded 13 official schemes into database`.*

---

## 🧪 Running Tests

The test suite validates scheme discovery, deterministic condition evaluation, source validation, edge cases, and end-to-end multi-turn conversations:

```bash
python -m pytest -v
```

**Test Suite Coverage (24/24 passing)**:
- `tests/test_discovery.py`: Category filtering, urban/rural residence filtering, empty search fallbacks, scheme ID retrieval.
- `tests/test_eligibility.py`: Deterministic evaluation of age, residence, occupation, income ceiling, caste reservation, landholding, taxpayer disqualification, and overall eligibility aggregation.
- `tests/test_verification.py`: Official domain whitelist (`.gov.in`, `.nic.in`), secure HTTPS, stale record detection (>365 days), batch auditing.
- `tests/test_end_to_end.py`: Full simulated journeys for Farmer, Student, and Street Vendor personas, multi-step card button clicks, and sensitive Aadhaar number rejection.

---

## 🏃 Local Execution & Interactive Demo

To test CivicBridge locally in your terminal simulating the full ACP and ASI:One conversation flow:

```bash
python demo_cli.py
```

Try typing:
- *"I am a 32 years old farmer in Uttar Pradesh with 1.2 hectares of land"*
- *"PM-KISAN"*
- *"I am an SC college student in Maharashtra with 1.8 Lakh income"*
- *"I am an urban street vendor in Delhi"*

---

## 🌐 Agentverse Deployment & ASI:One Integration

### Step 1: Obtain Agentverse Mailbox Key
1. Navigate to [Agentverse](https://agentverse.ai/) and sign in.
2. Go to **My Agents** and click **Create Agent** (or run locally with a Mailbox).
3. Under **Agent Settings** -> **Mailbox**, retrieve your Mailbox Key.
4. Add the key to `.env`:
   ```env
   AGENT_MAILBOX_KEY="your-mailbox-key-here"
   ```

### Step 2: Run the Agent
```bash
python agent/main.py
```
On startup, the console displays your deterministic agent address:
```
==================================================================
🇮🇳 CivicBridge Benefits Navigator Agent Started
Agent Name: CivicBridge Navigator
Agent Address: agent1qdtanumvgyvj8ucrjcuwwm3czj6dznpakfs90lrv4afy6lqwqx04wmy63gs
Database: database/civicbridge.db (13 schemes loaded)
Agentverse Mailbox: Enabled
==================================================================
```

### Step 3: Discover & Test in ASI:One
1. Visit [ASI:One](https://asi1.ai/) and start a new conversation.
2. In the recipient field, enter your agent's address or search for **`CivicBridge Navigator`**.
3. Send a message such as: *"I am a small farmer in UP with 1 hectare of land"*
4. Experience the structured eligibility assessment and interactive cards directly in the ASI:One chat UI!

---

## 📋 Live Links & Artifacts

- **GitHub Repository**: [https://github.com/kushagra4798/civicbridge_ai](https://github.com/kushagra4798/civicbridge_ai)
- **Agentverse Profile**: `https://agentverse.ai/agents/details/agent1qdtanumvgyvj8ucrjcuwwm3czj6dznpakfs90lrv4afy6lqwqx04wmy63gs` *(pending public registry sync)*
- **ASI:One Shared Chat**: `https://asi1.ai/chat/civicbridge-demo` *(available upon live session creation)*

---

## ⚠️ Known Limitations

1. **Curated Seed Coverage**: CivicBridge covers 13 major national welfare schemes across 6 domains. It does not yet claim exhaustive coverage of all 500+ state-specific departmental schemes.
2. **Advisory Scope**: CivicBridge provides advisory guidance based on official public gazettes. It does not submit biometric e-KYC or sanction financial disbursements on behalf of ministries.
3. **Card Interaction Fallback**: In chat clients that do not yet support Agentverse dynamic element-tree cards, the agent automatically falls back to full GitHub-flavored markdown with identical fidelity.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
