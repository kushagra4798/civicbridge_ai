# CivicBridge Live Demo & Presentation Script

This script provides a step-by-step walkthrough to demonstrate the **CivicBridge Benefits & Opportunity Navigator** agent on Fetch.ai uAgents, Agent Chat Protocol (ACP v0.3.0), and ASI:One.

---

## Preparation

Ensure your environment is set up and the database is seeded:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed database (18 verified opportunities)
python database/seed.py

# 3. Launch interactive CLI demo
python demo_cli.py
```

*(Alternatively, run the agent with `python agent/main.py` and message it via ACP / ASI:One).*

---

## 🌟 Flagship Demo: Representative Rajasthan Student Opportunity & Growth Journey

### Context
A college student from Rajasthan seeking both government financial assistance and internships, asking what they can apply for now and what concrete steps they should take to become eligible for more opportunities in the future.

### Turn 1: Citizen Query
> **Input:**
> *"I'm a student from Rajasthan. I'm looking for government financial assistance and internships. Based on my profile, what can I apply for now, and what should I work on to become eligible for more opportunities?"*

### Expected Agent Output
The agent delivers an integrated, structured assessment containing three coordinated sections:

1. **Profile Recognition**:
   - `State: Rajasthan · Occupation: Student · Opportunity Interest: Schemes & Internships`

2. **Opportunities Assessment**:
   - **Government Schemes**:
     - `NMMSS (National Means-cum-Merit Scholarship)` — Evaluated against schooling/income norms.
     - `Post-Matric Scholarship for SC Students` — Highlighted with income and caste prerequisites.
   - **Government Internships**:
     - `PMIS (Prime Minister's Internship Scheme)` — ₹5,000/mo stipend + ₹6,000 grant (MCA portal).
     - `Digital India Internship Scheme` — ₹10,000/mo stipend (MeitY).
     - `TULIP Internship` — Urban learning program with ULBs (AICTE portal).

3. **Eligibility Growth Plan (Differentiator)**:
   - **High-Leverage Actions**:
     - 🚀 *Complete National Scholarship Portal (NSP) One-Time Registration (OTR)* → Unlocks multiple central and state scholarships (`scholarships.gov.in`).
     - 🚀 *Enroll in Foundation Course on SWAYAM / NPTEL* → Strengthens academic preparedness for technical internships (`swayam.gov.in`).
   - **Actionable Gap Classification**:
     - `Missing Registration`: e-KYC on PM Internship Portal (`pminternship.mca.gov.in`).
     - `Missing Document`: Income Certificate (<₹2.5 Lakh) and Caste Certificate if applicable.
   - **Fixed Boundaries Notice**:
     - Clearly delineates age caps (e.g. PMIS 21–24 years) as statutory non-negotiable legal limits (`fixed_ineligible`), preventing false hopes.

4. **Dynamic UI Card**:
   - Renders interactive Element-Tree card with `View Roadmap (PMIS)` and `View Roadmap (NMMSS)` action buttons.

---

### Turn 2: Citizen Drills Down into PMIS
> **Input:**
> *"PMIS"* *(or tap "View Roadmap" button on card)*

### Expected Agent Output
The agent immediately returns the **Personalized Application Roadmap**:
- **Opportunity**: `Prime Minister's Internship Scheme in Top Companies (PMIS)`
- **Host**: `Public / Private Sector Portal (Ministry of Corporate Affairs)`
- **Stipend**: `₹5,000 / month + ₹6,000 one-time grant`
- **Official Application Portal**: `https://pminternship.mca.gov.in`
- **Tailored Document Checklist**:
  - `Aadhaar Card (linked to active mobile number)`
  - `Educational Certificates (Class 10 / 12 / ITI / Diploma / Degree)`
  - `Self-declaration of not engaged in full-time employment`
- **Step-by-Step Application Steps**:
  1. Visit the official MCA PM Internship portal at `https://pminternship.mca.gov.in`.
  2. Complete candidate registration and Aadhaar-based e-KYC.
  3. Complete applicant profile including academic qualifications and location preferences.
  4. Browse published vacancies in top 500 partner companies.
  5. Submit up to 5 internship preferences per application cycle.
- **Verification Notice**: Verified against official `.gov.in` sources; reminders on DBT NPCI bank linking.

---

## Scenario 2: Small Farmer in Uttar Pradesh

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
- Renders **ASI:One Interactive Card** with "View Roadmap" button.

### Step 2: Citizen Drills Down
> **Input:**
> *"PM-KISAN"*

### Expected Agent Output
- **Personalized Document Checklist**:
  - `Land Ownership Document (Khatauni / RoR / Patta) (showing current holding of ~1.2 hectares)`
  - `Aadhaar Card of the applicant`
  - `Aadhaar-seeded Bank Account Passbook for DBT`
- **Application Instructions**: Clear steps on `https://pmkisan.gov.in` under New Farmer Registration.

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
