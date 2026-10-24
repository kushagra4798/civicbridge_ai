# CivicBridge Data Sources & Verification Methodology

## 1. Catalog Overview

CivicBridge maintains a curated SQLite database of **18 prominent Indian Central Government welfare schemes and official internship programs**, representing vital socio-economic safety nets and career development pathways:

### Welfare Schemes (13)

| Category | Scheme | Governing Ministry / Department | Official Portal | Key Benefit |
|---|---|---|---|---|
| **Agriculture & Farmer Support** | PM-KISAN | Ministry of Agriculture & Farmers Welfare | `https://pmkisan.gov.in` | ₹6,000/yr DBT direct income support |
| **Pensions & Social Welfare** | PM-KMY | MoAFW & Life Insurance Corporation (LIC) | `https://maandhan.in` | ₹3,000/mo guaranteed contributory pension |
| **Pensions & Social Welfare** | APY | PFRDA / Department of Financial Services | `https://www.npscra.nsdl.co.in` | ₹1,000 to ₹5,000/mo guaranteed pension |
| **Pensions & Social Welfare** | IGNOAPS | National Social Assistance Programme (MoRD) | `https://nsap.nic.in` | Monthly pension for BPL seniors |
| **Healthcare Assistance** | Ayushman Bharat PM-JAY | National Health Authority (MoHFW) | `https://pmjay.gov.in` | ₹5 Lakh cashless health cover / family |
| **Healthcare Assistance** | PMMVY | Ministry of Women and Child Development | `https://pmmvy.wcd.gov.in` | ₹5,000 DBT maternity benefit |
| **Housing Assistance** | PMAY-Gramin | Ministry of Rural Development | `https://pmayg.nic.in` | ₹1.20 - ₹1.30 Lakh pucca house grant |
| **Housing Assistance** | PMAY-Urban | Ministry of Housing and Urban Affairs | `https://pmaymis.gov.in` | Up to ₹2.50 Lakh interest subsidy / grant |
| **Education & Scholarships** | NMMSS | Department of School Education & Literacy | `https://scholarships.gov.in` | ₹12,000/yr for Class 9-12 merit scholars |
| **Education & Scholarships** | Post-Matric SC | Ministry of Social Justice and Empowerment | `https://scholarships.gov.in` | Full tuition & maintenance allowance |
| **Employment & Skill Dev** | PM SVANidhi | Ministry of Housing and Urban Affairs | `https://pmsvanidhi.mohua.gov.in` | ₹10k - ₹50k working capital (7% subsidy) |
| **Employment & Skill Dev** | PM Vishwakarma | Ministry of MSME | `https://pmvishwakarma.gov.in` | ₹15k toolkit grant + ₹3 Lakh loan at 5% |
| **Employment & Skill Dev** | PMEGP | Ministry of MSME & KVIC | `https://kviconline.gov.in` | 15% - 35% margin money subsidy |

### Official Government Internships (5)

| Internship Program | Host Organization | Host Type | Official Application Portal | Stipend / Duration | Eligible Disciplines |
|---|---|---|---|---|---|
| **PM Internship Scheme (PMIS)** | Ministry of Corporate Affairs (MCA) | Public / Private Listed | `https://pminternship.mca.gov.in` | ₹5,000/mo + ₹6,000 grant (12 mos) | General, Commerce, Science, Arts, Engineering, Polytechnic |
| **NITI Aayog Internship Scheme** | NITI Aayog | Government Ministry / Think Tank | `https://niti.gov.in` | Unpaid (6 weeks to 6 months) | General, Public Policy, Economics, Engineering, Law |
| **Digital India Internship** | Ministry of Electronics & IT (MeitY) | Government Ministry | `https://meity.gov.in` | ₹10,000/mo (2 months) | Computer Science, IT, Electronics |
| **TULIP Internship** | MoHUA & AICTE | Government / Urban Local Bodies | `https://internship.aicte-india.org` | Performance stipend (8 wks to 1 yr) | Engineering, Urban Planning, Architecture, CS |
| **RBI Summer Placement Scheme** | Reserve Bank of India | Statutory Regulatory Body | `https://rbi.org.in` | ₹45,000/mo (3 months) | Economics, Finance, Banking, Statistics, Data Science |

---

## 2. Scheme & Internship Data Model

Every opportunity record in `data/schemes.json` and the SQLite database contains structured attributes:

```json
{
  "scheme_id": "pmis_internship",
  "opportunity_type": "internship",
  "name": "Prime Minister's Internship Scheme in Top Companies",
  "short_name": "PMIS",
  "description": "Flagship national internship scheme targeting 1.25 Crore youth...",
  "category": "employment",
  "governing_department": "Ministry of Corporate Affairs (MCA)",
  "host_type": "public_portal_private_sector",
  "benefit_summary": "12-month internship with ₹5,000 monthly stipend and ₹6,000 one-time grant",
  "stipend": "₹5,000 / month + ₹6,000 one-time grant",
  "duration": "12 months",
  "work_mode": "in_person",
  "geographic_coverage": "All India",
  "target_residence": "all",
  "field_of_study": ["general", "commerce", "science", "arts", "engineering", "polytechnic"],
  "required_skills": ["basic_computer_literacy"],
  "rules": [
    {
      "rule_name": "age_limit",
      "description": "Applicant must be between 21 and 24 years of age",
      "rule_type": "age_range",
      "parameters": {"min_age": 21, "max_age": 24}
    }
  ],
  "required_documents": [
    "Aadhaar Card",
    "Educational Certificates (Class 10 / 12 / ITI / Diploma / Degree)",
    "Self-declaration of not engaged in full-time employment"
  ],
  "application_steps": [
    "Register on official PM Internship portal at https://pminternship.mca.gov.in",
    "Complete e-KYC using Aadhaar and upload academic credentials"
  ],
  "official_portal_url": "https://pminternship.mca.gov.in",
  "evidence_urls": [
    "https://pminternship.mca.gov.in",
    "https://www.myscheme.gov.in/schemes/pmis"
  ],
  "application_dates": "Pilot Phase open; multiple cohort windows announced annually",
  "application_deadline": "Cohort-based",
  "last_verified": "2026-03-20",
  "verification_status": "VERIFIED"
}
```

---

## 3. Official Source Whitelist & Verification Methodology

CivicBridge enforces strict verification criteria to ensure information fidelity:

1. **Approved Domain Whitelist**:
   - `*.gov.in` (Official National and State Government Portals)
   - `*.nic.in` (National Informatics Centre Infrastructure)
   - `myscheme.gov.in` (National e-Governance Division Unified Platform)
   - `internship.aicte-india.org` (AICTE Official Internship Portal)
   - `rbi.org.in` (Reserve Bank of India Official Domain)
   - Authorized national financial/pension intermediaries: `maandhan.in`, `npscra.nsdl.co.in`, `kviconline.gov.in`

2. **Transport Security**:
   - All links must use secure `https://` encryption.

3. **Freshness Window**:
   - Every scheme record records a `last_verified` date.
   - The Verification Specialist flags any record older than 365 days as potentially stale.

4. **Zero Hallucination Policy**:
   - The system queries only verified database records.
   - Rules are strictly evaluated against known facts. If citizen information is absent, the rule status is explicitly marked `UNKNOWN` rather than guessing.
