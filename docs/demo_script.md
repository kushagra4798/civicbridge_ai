# CivicBridge Live Demo & Presentation Script

This script provides a step-by-step walkthrough to demonstrate the **CivicBridge Benefits Navigator** agent on Fetch.ai uAgents, Agent Chat Protocol (ACP), and ASI:One.

---

## Preparation

Ensure your environment is set up and the database is seeded:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed database
python database/seed.py

# 3. Launch interactive CLI demo
python demo_cli.py
```

*(Alternatively, run the agent with `python agent/main.py` and message it via ACP / ASI:One).*

---

## Scenario 1: Small Farmer in Uttar Pradesh

### Context
A 32-year-old farmer living in rural Uttar Pradesh with 1.2 hectares of land seeking agricultural assistance and old-age social security.

### Step 1: Citizen Query
> **Input:**
> *"Namaste, I am a 32 years old farmer living in a village in Uttar Pradesh. I own 1.2 hectares of cultivable land and I do not pay income tax. What government schemes can I apply for?"*

### Expected Agent Output
- Identifies **State:** Uttar Pradesh, **Residence:** Rural, **Age:** 32 yrs, **Occupation:** Farmer, **Land:** 1.2 ha.
- Returns **PM-KISAN** and **PM-KMY** with status **🟡 LIKELY ELIGIBLE** or **🟢 ELIGIBLE**.
- Displays breakdown:
  - ✅ **Met Conditions:** Landownership verified (~1.2 ha), farmer occupation verified, non-taxpayer verified.
  - 🔗 **Official Portal:** `https://pmkisan.gov.in`
- Renders **ASI:One Interactive Card** with "View Checklist" button.

### Step 2: Citizen Drills Down
> **Input:**
> *"PM-KISAN"* *(or tap "View Checklist (PM-KISAN)" on card)*

### Expected Agent Output
- **Personalized Document Checklist**:
  - `Land Ownership Document (Khatauni / RoR / Patta) (showing current holding of ~1.2 hectares)`
  - `Aadhaar Card of the applicant`
  - `Aadhaar-seeded Bank Account Passbook for DBT`
- **Application Instructions**: 5 clear steps on `https://pmkisan.gov.in` under New Farmer Registration.
- **Pre-requisites**: Reminder to ensure Aadhaar mobile linking and NPCI bank seeding.

---

## Scenario 2: SC College Student in Maharashtra

### Context
A 20-year-old student from the Scheduled Caste community studying in college in Maharashtra with family income of ₹1.8 Lakh per annum.

### Step 1: Citizen Query
> **Input:**
> *"I am a 20 year old college student in Maharashtra from SC category. My family annual income is 1.8 Lakh rupees. Are there any scholarships for me?"*

### Expected Agent Output
- Identifies **Category:** Education, **Caste:** SC, **Income:** ₹1,80,000, **Level:** College / Post-Matric.
- Matches **Post-Matric Scholarship for SC Students** with **🟢 ELIGIBLE**.
- Notes that NMMSS is for secondary school (Class 9-12), correctly ranking Post-Matric SC higher.
- Official portal: `https://scholarships.gov.in`.

### Step 2: Request Checklist
> **Input:**
> *"Post-Matric SC"*

### Expected Agent Output
- Tailored checklist highlighting:
  - `Caste Certificate (for SC category verification from Tehsildar/SDO)`
  - `Income Certificate (certifying annual family income under ₹1,80,000)`
  - `College Admission Fee Receipt and Bonafide Certificate`

---

## Scenario 3: Urban Street Vendor in Delhi

### Context
A 28-year-old street vendor running a tea/fruit stall in urban Delhi seeking working capital loan.

### Step 1: Citizen Query
> **Input:**
> *"I am a 28 years old street vendor running a fruit stall in Delhi city. I need a small working capital loan for my business."*

### Expected Agent Output
- Matches **PM-SVANidhi (PM Street Vendor's AtmaNirbhar Nidhi)** with **🟢 ELIGIBLE**.
- Explains: Collateral-free loan of ₹10,000 to ₹50,000 with 7% interest subsidy.
- Official portal: `https://pmsvanidhi.mohua.gov.in`.

### Step 2: Request Checklist
> **Input:**
> *"PM-SVANidhi"*

### Expected Agent Output
- Checklist highlighting `Certificate of Vending (CoV) / Identity Card issued by Urban Local Body (ULB) OR Letter of Recommendation (LoR)`.
- Step-by-step application via PM SVANidhi portal or nearest CSC.

---

## Scenario 4: Privacy Protection Test

### Context
User inadvertently types a 12-digit number resembling Aadhaar.

### Step 1: Citizen Query
> **Input:**
> *"My Aadhaar number is 5482 1930 8472 and I want to register."*

### Expected Agent Output
- ⚠️ **Privacy Protection Warning**:
  *"CivicBridge detected what looks like a 12-digit identification number. Please do not share Aadhaar numbers, bank account numbers, or passwords. CivicBridge evaluates eligibility using non-sensitive demographic criteria only."*
- The sensitive number is discarded immediately and never stored in the session profile or database.
