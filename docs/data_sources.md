# CivicBridge Data Sources & Verification Methodology

## 1. Catalog Overview

CivicBridge maintains a curated SQLite database of **13 prominent Indian Central Government welfare and assistance schemes**, representing the primary socio-economic safety net across six critical categories:

| Category | Schemes Included | Governing Ministry / Department | Official Portal |
|---|---|---|---|
| **Agriculture & Farmer Support** | PM-KISAN | Ministry of Agriculture & Farmers Welfare | `https://pmkisan.gov.in` |
| **Pensions & Social Welfare** | PM-KMY, APY, IGNOAPS | MoAFW / LIC, PFRDA (MoF), NSAP (MoRD) | `https://maandhan.in`, `https://www.npscra.nsdl.co.in`, `https://nsap.nic.in` |
| **Healthcare Assistance** | Ayushman Bharat PM-JAY, PMMVY | National Health Authority (MoHFW), MoWCD | `https://pmjay.gov.in`, `https://pmmvy.wcd.gov.in` |
| **Housing Assistance** | PMAY-Gramin, PMAY-Urban | Ministry of Rural Development, MoHUA | `https://pmayg.nic.in`, `https://pmaymis.gov.in` |
| **Education & Scholarships** | NMMSS, Post-Matric SC Scholarship | Ministry of Education, MoSJE | `https://scholarships.gov.in` |
| **Employment & Skill Development** | PM SVANidhi, PM Vishwakarma, PMEGP | MoHUA, Ministry of MSME, KVIC | `https://pmsvanidhi.mohua.gov.in`, `https://pmvishwakarma.gov.in`, `https://kviconline.gov.in` |

---

## 2. Scheme Record Structure

Every scheme record in `data/schemes.json` and the SQLite database contains 19 structured attributes:

```json
{
  "scheme_id": "pm_kisan",
  "name": "Pradhan Mantri Kisan Samman Nidhi",
  "short_name": "PM-KISAN",
  "description": "Central sector income support scheme providing ₹6,000 per year...",
  "category": "agriculture",
  "governing_department": "Department of Agriculture and Farmers Welfare",
  "benefit_summary": "Direct income support of ₹6,000 per year in 3 instalments via DBT",
  "benefit_amount": "₹6,000 / year",
  "geographic_coverage": "All India",
  "target_residence": "all",
  "rules": [
    {
      "rule_name": "landholder_requirement",
      "description": "Must be a cultivable landholding farmer family...",
      "rule_type": "is_landholder",
      "parameters": {"required": true}
    }
  ],
  "required_documents": [
    "Aadhaar Card of the applicant",
    "Land Ownership Document (Khatauni / RoR / Patta)",
    "Aadhaar-seeded Bank Account Passbook",
    "Active Mobile Number linked to Aadhaar"
  ],
  "application_steps": [
    "Visit official portal https://pmkisan.gov.in...",
    "Click on 'New Farmer Registration'..."
  ],
  "official_portal_url": "https://pmkisan.gov.in",
  "evidence_urls": [
    "https://pmkisan.gov.in",
    "https://www.myscheme.gov.in/schemes/pm-kisan"
  ],
  "application_dates": "Open year-round on the PM-KISAN portal",
  "last_verified": "2026-03-15",
  "verification_status": "VERIFIED",
  "notes": "Institutional landholders and income tax payees excluded."
}
```

---

## 3. Official Source Whitelist & Verification

CivicBridge enforces strict verification criteria to ensure information fidelity:

1. **Approved Domain Whitelist**:
   - `*.gov.in` (Official National and State Government Portals)
   - `*.nic.in` (National Informatics Centre Infrastructure)
   - `myscheme.gov.in` (National e-Governance Division Unified Platform)
   - Authorized national financial/pension intermediaries: `maandhan.in`, `npscra.nsdl.co.in`, `kviconline.gov.in`

2. **Transport Security**:
   - All links must use secure `https://` encryption.

3. **Freshness Window**:
   - Every scheme record records a `last_verified` date.
   - The Verification Specialist flags any record older than 365 days as potentially stale.

4. **Zero Hallucination Policy**:
   - The system queries only verified database records.
   - Rules are strictly evaluated against known facts. If citizen information is absent, the rule status is explicitly marked `UNKNOWN` rather than guessing.
