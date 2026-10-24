# 🇮🇳 CivicBridge AI — Indian Government Benefits & Opportunity Navigator

[![Fetch.ai uAgents](https://img.shields.io/badge/Fetch.ai-uAgents_v0.26-blue)](https://github.com/fetchai/uAgents)
[![Agent Chat Protocol](https://img.shields.io/badge/ACP-v0.3.0-green)](https://github.com/fetchai/uAgents)
[![ASI:One Compatible](https://img.shields.io/badge/ASI:One-Dynamic_UI-orange)](https://asi1.ai/)
[![Test Suite](https://img.shields.io/badge/Tests-41%2F41_Passing-brightgreen)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**CivicBridge** is an autonomous AI agent built on Fetch.ai uAgents, the Agent Chat Protocol (ACP v0.3.0), and ASI:One that serves as an intelligent government benefits and opportunity navigator for India.

CivicBridge helps citizens answer three essential questions within a single conversational workflow:
1. **What government schemes or internship opportunities do I qualify for now?**
2. **Which eligibility requirements are missing, unmet, or unresolved?**
3. **What legitimate, evidence-backed actions can I take to become eligible for additional high-impact opportunities in the future?**

Our primary differentiator is the **Eligibility Growth Planner** — connecting verified public norms to concrete next steps (certificates, official registrations, recognized courses, or qualification milestones) rather than merely cataloging schemes.

---

## 📌 Problem Statement

India operates hundreds of central welfare initiatives and official internship programs designed to support farmers, students, youth, senior citizens, unorganized workers, and urban entrepreneurs. However, millions miss out because:
1. **Information Asymmetry**: Scheme criteria, income limits, and landholding caps are buried across fragmented gazettes and departmental websites.
2. **Ambiguous Eligibility**: Citizens frequently apply for programs they are ineligible for, or avoid applying due to confusing criteria.
3. **Internship Navigation Gap**: Government internships (e.g., PM Internship Scheme, NITI Aayog, Digital India) are hosted across different portals with varied eligibility and stipend rules.
4. **Dead-End Responses**: Conventional tools inform users they are "ineligible" without providing actionable pathways to overcome remediable gaps.
5. **Privacy & Fraud Risks**: Fraudulent intermediary websites often solicit sensitive Aadhaar or bank credentials under the guise of application processing.

**CivicBridge solves this** by acting as a zero-friction, privacy-respecting navigator accessible through decentralized chat interfaces like ASI:One.

---

## 🎯 Target Users

- **Students & Graduates**: Discovering national merit scholarships and paid government internships (PMIS, NITI Aayog, Digital India, TULIP, RBI).
- **Farmers & Cultivators**: Seeking income support (PM-KISAN), solar irrigation, and old-age pensions (PM-KMY).
- **Low-Income Families**: Needing health insurance cover (Ayushman Bharat PM-JAY) and pucca housing (PMAY-G / PMAY-U).
- **Senior Citizens & Unorganized Workers**: Requiring guaranteed monthly pensions (APY, IGNOAPS).
- **Street Vendors & Artisans**: Seeking collateral-free micro-credit loans (PM SVANidhi, PM Vishwakarma, PMEGP).

---

## 🚀 Core Capabilities

### Capability A — Government Scheme Discovery
- Curated coverage across 6 core welfare domains: Education, Housing, Healthcare, Pensions, Agriculture, and Employment.
- Multilateral matching on state, rural/urban residence, age, occupation, caste, landholding, and income.
- Targeted follow-up queries when missing criteria could materially affect eligibility.

### Capability B — Government Internship Discovery
- Covers high-impact official internship initiatives:
  - **PM Internship Scheme (PMIS)**: 1.25 Crore youth target, ₹5,000/mo stipend + ₹6,000 grant via Ministry of Corporate Affairs (`pminternship.mca.gov.in`).
  - **NITI Aayog Internship Scheme**: Policy research & governance (`niti.gov.in`).
  - **Digital India Internship (MeitY)**: Electronics, IT, and software governance (`meity.gov.in`).
  - **TULIP Internship**: The Urban Learning Internship Program with Smart Cities & ULBs (`internship.aicte-india.org`).
  - **RBI Summer Placement Scheme**: Central banking & economics with ₹45,000/mo stipend (`rbi.org.in`).
- Distinguishes government-hosted programs from private-sector listings on public portals.
- Matches by field of study, degree status (pursuing vs completed), required skills, and work mode.

### Capability C — Eligibility Growth Planner (Key Differentiator)
- Evaluates user profile against published scheme and internship criteria.
- Classifies gaps into 6 structured categories:
  - `missing_document`: Remediable certificates (Caste, Income, Land Records / RoR).
  - `missing_registration`: Mandatory portal registrations (National Scholarship Portal, PMIS, e-Shram).
  - `missing_skill`: Practical competencies (Python, Web Development, Data Analysis) mapped to recognized public learning portals like [SWAYAM](https://swayam.gov.in/).
  - `missing_qualification`: Educational benchmarks (degree completion, minimum marks percentage).
  - `experience_requirement`: Prior exposure or internship prerequisites.
  - `unmet_fixed_condition`: Statutory legal limits (age limits, taxpayer exclusions) strictly identified as non-actionable fixed boundaries.
- **High-Leverage Actions**: Prioritizes single concrete steps that simultaneously unlock multiple target schemes or internships.
- **Truth in Advertising**: Labels skills improvements as `"improves_preparedness"` and documents as `"satisfies_prerequisite"` — **never** guaranteeing selection or sanction.

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
│ 1. Scheme Discovery   │    │ 2. Rules &  │ │ 3. Verification   │    │ 4. Application &    │
│    Specialist         │    │ Eligibility │ │    Specialist     │    │    Growth Planner   │
└───────────┬───────────┘    └──────┬──────┘ └─────────┬─────────┘    └──────────┬──────────┘
            │                       │                  │                         │
            ▼                       ▼                  ▼                         ▼
  [ SQLite Repository ]     [ Deterministic ]  [ .gov.in Domain & ]      [ Actionable Roadmaps ]
  [ 18 Curated Records]     [ Math Evaluator]  [ Freshness Audit  ]      [ Growth Plan Engine  ]
```

### Specialist Breakdown

1. **Orchestrator (`agent/orchestrator.py`)**: Manages multi-turn citizen sessions, privacy filtering (scrubbing Aadhaar/bank numbers), card button click actions, and synthesis of Scheme + Internship + Growth Plan results.
2. **Scheme Discovery Specialist (`specialists/discovery.py`)**: Multi-channel search over SQLite repository for welfare schemes and official internships with progressive query relaxation.
3. **Eligibility Specialist (`specialists/eligibility.py`)**: Evaluates 17 deterministic rule types using strict Python logic (`MET`, `NOT_MET`, `UNKNOWN`). Never treats missing data as eligible.
4. **Verification Specialist (`specialists/verification.py`)**: Audits official `.gov.in`/`.nic.in` domains, HTTPS security, and flags stale records older than 365 days.
5. **Application & Growth Planner (`specialists/application_planner.py`)**: Generates personalized document checklists, step-by-step instructions, and constructs the Eligibility Growth Plan.

---

## 📦 Verified Catalog (18 Opportunities)

CivicBridge contains **18 thoroughly verified opportunities** in `data/schemes.json`:

### Welfare Schemes (13)
1. **PM-KISAN**: Pradhan Mantri Kisan Samman Nidhi (₹6,000/yr DBT) — `pmkisan.gov.in`
2. **PM-KMY**: PM Kisan Maan-Dhan Yojana (₹3,000/mo pension) — `maandhan.in`
3. **APY**: Atal Pension Yojana (₹1,000 - ₹5,000/mo guaranteed pension) — `npscra.nsdl.co.in`
4. **IGNOAPS**: Indira Gandhi National Old Age Pension Scheme — `nsap.nic.in`
5. **PM-JAY**: Ayushman Bharat PM Jan Arogya Yojana (₹5 Lakh cover/family) — `pmjay.gov.in`
6. **PMMVY**: Pradhan Mantri Matru Vandana Yojana (Maternity cash transfer) — `pmmvy.wcd.gov.in`
7. **PMAY-G**: Pradhan Mantri Awaas Yojana - Gramin (₹1.20 - ₹1.30 Lakh grant) — `pmayg.nic.in`
8. **PMAY-U**: Pradhan Mantri Awas Yojana - Urban (Up to ₹2.50 Lakh subsidy) — `pmaymis.gov.in`
9. **NMMSS**: National Means-cum-Merit Scholarship (₹12,000/yr) — `scholarships.gov.in`
10. **Post-Matric SC**: Post Matric Scholarship for SC Students — `scholarships.gov.in`
11. **PM-SVANidhi**: Micro-credit for Street Vendors (₹10k - ₹50k, 7% subsidy) — `pmsvanidhi.mohua.gov.in`
12. **PM-Vishwakarma**: Toolkit grant (₹15k) & credit (up to ₹3 Lakh at 5%) — `pmvishwakarma.gov.in`
13. **PMEGP**: Prime Minister's Employment Generation Programme (15%-35% subsidy) — `kviconline.gov.in`

### Official Government Internships (5)
14. **PMIS**: Prime Minister's Internship Scheme in Top Companies (₹5,000/mo + ₹6,000 grant) — `pminternship.mca.gov.in`
15. **NITI-Internship**: NITI Aayog Internship Scheme (Unpaid policy & governance) — `niti.gov.in`
16. **Digital-India-Internship**: Digital India Internship Scheme by MeitY (₹10,000/mo) — `meity.gov.in`
17. **TULIP**: The Urban Learning Internship Program (MoHUA & AICTE) — `internship.aicte-india.org`
18. **RBI-Internship**: RBI Summer Placement Scheme (₹45,000/mo) — `rbi.org.in`

---

## 💻 Tech Stack

- **Framework**: Python 3.10+, [Fetch.ai uAgents](https://github.com/fetchai/uAgents) (`>=0.26.1`), `uagents-core` (`>=0.4.12`)
- **Messaging Protocol**: Agent Chat Protocol (ACP v0.3.0) with element-tree dynamic cards
- **Data Layer**: SQLite 3 with repository pattern & seed loader
- **Validation**: Pydantic v2
- **Testing**: Pytest & Pytest-Asyncio (33 tests, 100% pass rate)

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
AGENT_MAILBOX_KEY=""  # Fill in when deploying to Agentverse Mailbox
DATABASE_PATH="database/civicbridge.db"
LOG_LEVEL="INFO"
```

### 5. Seed Database
```bash
python database/seed.py
```
*Output: `Successfully seeded 18 official schemes & internships into database`.*

---

## 🧪 Running Tests

The test suite validates scheme discovery, internship matching, deterministic rule evaluation, growth planning, citation verification, edge cases, and end-to-end multi-turn journeys:

```bash
python -m pytest -v
```

**Test Suite Coverage (41/41 passing in <2s)**:
- `tests/test_acp_handler.py` (8 tests): ACP protocol message handling, StartSessionContent extraction, session state reset & isolation, error resilience, and distinct prompt-response flows.
- `tests/test_discovery.py` (6 tests): Category filtering, urban/rural residence filtering, empty search fallbacks, scheme ID retrieval.
- `tests/test_internships.py` (5 tests): Internship discovery, host type classification (Govt vs Portal), stipend retrieval, work mode, and field of study filtering.
- `tests/test_growth_planner.py` (3 tests): Gap category classification, high-leverage action identification, statutory fixed condition handling.
- `tests/test_eligibility.py` (8 tests): Deterministic evaluation of age, residence, occupation, income ceiling, caste reservation, landholding, taxpayer disqualification, and aggregate eligibility.
- `tests/test_verification.py` (4 tests): Official domain whitelist (`.gov.in`, `.nic.in`), secure HTTPS, stale record detection (>365 days), batch auditing.
- `tests/test_end_to_end.py` (7 tests): Full journeys for Farmer, Student, Street Vendor, Representative Rajasthan Student Growth Journey, multi-step card button clicks, and sensitive Aadhaar number rejection.

---

## 🏃 Local Execution & Interactive Demo

To test CivicBridge locally simulating the full ACP and ASI:One conversation flow:

```bash
python demo_cli.py
```

Try typing:
- *"I'm a student from Rajasthan. I'm looking for government financial assistance and internships. Based on my profile, what can I apply for now, and what should I work on to become eligible for more opportunities?"*
- *"PMIS"*
- *"I am a 32 years old farmer in Uttar Pradesh with 1.2 hectares of land"*
- *"I am an SC college student in Maharashtra with 1.8 Lakh income"*

---

## 🌐 Agentverse Deployment & ASI:One Integration

### Step 1: Obtain Agentverse Mailbox Key
1. Navigate to [Agentverse](https://agentverse.ai/) and sign in.
2. Go to **My Agents** and click **Create Agent** (or create a local Agent with Mailbox).
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
Database: database/civicbridge.db (18 schemes loaded)
Agentverse Mailbox: Enabled
==================================================================
```

### Step 3: Discover & Test in ASI:One
1. Visit [ASI:One](https://asi1.ai/) and start a new conversation.
2. In the recipient field, enter your agent's address or search for **`CivicBridge Navigator`**.
3. Send a message such as: *"I am a student from Rajasthan looking for financial assistance and internships"*
4. Experience the structured eligibility assessment, dynamic cards, and actionable growth plan directly in ASI:One!

---

## ⚠️ Known Limitations

1. **Curated Seed Coverage**: CivicBridge covers 18 major national welfare programs and flagship internships. It does not yet claim exhaustive coverage of all 500+ state-specific departmental schemes.
2. **Advisory Scope**: CivicBridge provides advisory guidance based on official public gazettes. It does not submit biometric e-KYC or sanction disbursements on behalf of ministries.
3. **Card Interaction Fallback**: In chat clients that do not yet support Agentverse dynamic element-tree cards, the agent automatically falls back to full GitHub-flavored markdown with identical fidelity.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
