"""Applicant profile schemas and extraction logic."""

from __future__ import annotations

import re
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class ApplicantProfile(BaseModel):
    """Structured representation of citizen attributes needed for scheme and internship eligibility."""

    state: Optional[str] = Field(None, description="State or Union Territory of residence")
    residence: Optional[Literal["rural", "urban", "semi-urban"]] = Field(
        None, description="Type of living area: rural, urban, semi-urban"
    )
    age: Optional[int] = Field(None, ge=0, le=125, description="Applicant age in years")
    occupation: Optional[str] = Field(
        None,
        description="Applicant occupation: farmer, student, street_vendor, artisan, unorganized_worker, salaried, unemployed, other",
    )
    annual_income: Optional[float] = Field(
        None, ge=0, description="Annual family income in Indian Rupees (INR)"
    )
    education_level: Optional[str] = Field(
        None,
        description="Highest completed level: none, class_8_pass, class_10_pass, class_12_pass, graduate, post_graduate",
    )
    gender: Optional[Literal["male", "female", "transgender", "other"]] = Field(
        None, description="Gender of the applicant"
    )
    caste_category: Optional[Literal["General", "SC", "ST", "OBC", "EWS"]] = Field(
        None, description="Caste / social reservation category"
    )
    is_landholder: Optional[bool] = Field(
        None, description="Whether the applicant or family owns cultivable agricultural land"
    )
    landholding_ha: Optional[float] = Field(
        None, ge=0, description="Size of agricultural landholding in hectares (if applicable)"
    )
    is_taxpayer: Optional[bool] = Field(
        None, description="Whether the applicant or family member paid income tax in last assessment year"
    )
    is_bpl: Optional[bool] = Field(
        None, description="Whether holding a Below Poverty Line (BPL) / Antyodaya ration card"
    )
    is_pregnant_or_lactating: Optional[bool] = Field(
        None, description="Maternity condition relevant for maternal welfare schemes"
    )
    category_interest: Optional[str] = Field(
        None,
        description="Benefit category: agriculture, healthcare, housing, education, pensions, employment, internship",
    )
    opportunity_interest: Literal["schemes", "internships", "both"] = Field(
        "both",
        description="Target opportunity type: schemes, internships, or both",
    )
    field_of_study: Optional[str] = Field(
        None,
        description="Academic discipline: computer_science, engineering, public_policy, economics, commerce, agriculture, science, arts, law, general",
    )
    skills: List[str] = Field(
        default_factory=list,
        description="Declared skills such as python, data_analysis, gis, research, excel, web_development",
    )
    current_degree_status: Optional[Literal["pursuing", "completed", "fresh_graduate"]] = Field(
        None, description="Degree completion status"
    )
    marks_percentage: Optional[float] = Field(
        None, ge=0, le=100, description="Academic marks percentage (e.g. 85.0 for 85%)"
    )

    def summary_dict(self) -> dict:
        """Return non-null profile attributes for display and logging."""
        return {k: v for k, v in self.model_dump().items() if v is not None}

    def has_sufficient_info_for_search(self) -> bool:
        """Check if profile has enough detail to identify relevant schemes or internships."""
        return bool(
            self.category_interest
            or self.occupation
            or self.age
            or self.residence
            or self.state
            or self.education_level
            or self.opportunity_interest in ("internships", "schemes", "both")
        )

    def missing_fields_for_category(self) -> list[str]:
        """Return critical fields that would refine eligibility based on domain."""
        missing = []
        if not self.category_interest and not self.occupation and self.opportunity_interest == "schemes":
            missing.append("benefit interest (e.g. farming, education, housing, healthcare, pension, employment)")
        if self.category_interest in ("agriculture", "farming") or self.occupation == "farmer":
            if self.is_landholder is None:
                missing.append("whether you own agricultural land")
            if self.age is None:
                missing.append("your age")
        elif (self.category_interest == "education" or self.occupation == "student") and self.opportunity_interest == "schemes":
            if self.annual_income is None:
                missing.append("family annual income")
            if self.education_level is None:
                missing.append("current or completed education level")
        elif self.category_interest == "housing":
            if self.residence is None:
                missing.append("rural or urban residence")
            if self.annual_income is None:
                missing.append("annual family income")
        elif self.category_interest in ("pensions", "social welfare"):
            if self.age is None:
                missing.append("your age")
            if self.occupation is None:
                missing.append("occupation or employment sector")
        elif self.category_interest in ("employment", "skill development", "business"):
            if self.occupation is None:
                missing.append("current occupation (e.g. street vendor, artisan, unorganized worker)")
        return missing


# Known Indian states and UTs for parsing
INDIAN_STATES = [
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa",
    "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala",
    "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland",
    "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
    "uttar pradesh", "uttarakhand", "west bengal", "delhi", "jammu and kashmir",
    "ladakh", "puducherry", "chandigarh", "dadra and nagar haveli and daman and diu"
]


def extract_profile_from_text(text: str, existing_profile: Optional[ApplicantProfile] = None) -> ApplicantProfile:
    """Extract applicant attributes from citizen natural language text.
    
    Preserves existing information while updating newly discovered fields.
    """
    profile = existing_profile.model_copy() if existing_profile else ApplicantProfile()
    lower = text.lower()

    # 1. Opportunity Type & Intent
    has_internship = any(w in lower for w in ["internship", "intern", "trainee", "apprenticeship"])
    has_scheme = any(w in lower for w in [
        "scheme", "scholarship", "financial assistance", "assistance", "benefit",
        "fund", "grant", "subsidy", "welfare", "pension", "loan"
    ])
    if has_internship and has_scheme:
        profile.opportunity_interest = "both"
    elif has_internship:
        profile.opportunity_interest = "internships"
    elif has_scheme:
        profile.opportunity_interest = "schemes"

    # 2. Category of Interest
    if has_internship and not has_scheme:
        profile.category_interest = "internship"
    elif any(w in lower for w in ["farmer", "kisan", "crop", "agriculture", "farming", "landholder"]):
        profile.category_interest = "agriculture"
        if profile.occupation is None:
            profile.occupation = "farmer"
    elif any(w in lower for w in ["scholarship", "student", "study", "college", "school", "education"]):
        profile.category_interest = "education"
        if profile.occupation is None:
            profile.occupation = "student"
    elif any(w in lower for w in ["house", "housing", "pucca makan", "awas", "home loan", "shelter"]):
        profile.category_interest = "housing"
    elif any(w in lower for w in ["health", "hospital", "ayushman", "medical", "treatment", "illness", "doctor"]):
        profile.category_interest = "healthcare"
    elif any(w in lower for w in ["pension", "old age", "elderly", "senior citizen", "retire"]):
        profile.category_interest = "pensions"
    elif any(w in lower for w in ["street vendor", "thela", "hawker", "rehri", "artisan", "vishwakarma", "loan", "startup", "skill", "employment", "business", "small business"]):
        profile.category_interest = "employment"

    # 3. Specific occupations
    if any(w in lower for w in ["street vendor", "vendor", "hawker", "rehri", "thelawala"]):
        profile.occupation = "street_vendor"
        profile.residence = profile.residence or "urban"
    elif any(w in lower for w in ["artisan", "craftsperson", "carpenter", "blacksmith", "goldsmith", "potter", "sculptor", "tailor", "cobbler"]):
        profile.occupation = "artisan"
    elif any(w in lower for w in ["farmer", "kisan", "cultivator", "peasant"]):
        profile.occupation = "farmer"
    elif any(w in lower for w in ["student", "studying", "undergraduate", "postgraduate", "scholar"]):
        profile.occupation = "student"
    elif any(w in lower for w in ["unorganized", "daily wage", "laborer", "labourer", "construction worker", "maid", "driver"]):
        profile.occupation = "unorganized_worker"

    # 4. Residence
    if any(w in lower for w in ["village", "rural", "gaon", "dehat", "gramin", "gram"]):
        profile.residence = "rural"
    elif any(w in lower for w in ["city", "urban", "town", "metro", "municipal"]):
        profile.residence = "urban"

    # 5. State
    for state in INDIAN_STATES:
        if state in lower:
            profile.state = state.title()
            break
    # Common abbreviations
    if not profile.state:
        if re.search(r"\bup\b", lower):
            profile.state = "Uttar Pradesh"
        elif re.search(r"\bmp\b", lower):
            profile.state = "Madhya Pradesh"
        elif re.search(r"\bmh\b", lower):
            profile.state = "Maharashtra"
        elif re.search(r"\btn\b", lower):
            profile.state = "Tamil Nadu"
        elif re.search(r"\brj\b", lower):
            profile.state = "Rajasthan"

    # 6. Age
    age_match = re.search(r"\b(?:i am|age is|age|aged|am)\s*([0-9]{1,2})\s*(?:years|yrs|year)?\s*(?:old)?\b", lower)
    if age_match:
        try:
            val = int(age_match.group(1))
            if 0 < val <= 120:
                profile.age = val
        except ValueError:
            pass
    elif not profile.age:
        alt_match = re.search(r"\b([0-9]{1,2})\s*(?:years old|yrs old|year old)\b", lower)
        if alt_match:
            try:
                val = int(alt_match.group(1))
                if 0 < val <= 120:
                    profile.age = val
            except ValueError:
                pass

    # 7. Annual Income
    income_match = re.search(r"(?:income|earning|salary)(?:\s*(?:is|around|of|upto|less than|under)?\s*)?(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]+)?)\s*(lakh|lac|lpa|thousand|k)?", lower)
    if income_match:
        val = float(income_match.group(1))
        unit = income_match.group(2)
        if unit in ("lakh", "lac", "lpa"):
            profile.annual_income = val * 100000.0
        elif unit in ("thousand", "k"):
            profile.annual_income = val * 1000.0
        else:
            profile.annual_income = val
    else:
        lakh_match = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:lakh|lac|lpa)\b", lower)
        if lakh_match and ("income" in lower or "earn" in lower or "salary" in lower or "family" in lower):
            profile.annual_income = float(lakh_match.group(1)) * 100000.0

    # 8. Education Level & Field of Study
    if any(w in lower for w in ["post graduate", "pg", "masters", "msc", "mcom", "ma", "mtech", "mba", "m.e"]):
        profile.education_level = "post_graduate"
    elif any(w in lower for w in ["graduate", "degree", "graduation", "bsc", "bcom", "ba", "btech", "b.tech", "college", "bca", "bba"]):
        profile.education_level = "graduate"
    elif any(w in lower for w in ["12th", "12 pass", "class 12", "intermediate", "higher secondary"]):
        profile.education_level = "class_12_pass"
    elif any(w in lower for w in ["10th", "10 pass", "class 10", "matric", "high school", "secondary"]):
        profile.education_level = "class_10_pass"
    elif any(w in lower for w in ["8th", "8 pass", "class 8", "middle school"]):
        profile.education_level = "class_8_pass"

    # Field of Study
    if any(w in lower for w in ["computer science", "cs", "information technology", "it", "software"]):
        profile.field_of_study = "computer_science"
    elif any(w in lower for w in ["engineering", "btech", "b.tech", "b.e", "mechanical", "electrical", "civil"]):
        profile.field_of_study = "engineering"
    elif any(w in lower for w in ["public policy", "governance", "policy", "political science"]):
        profile.field_of_study = "public_policy"
    elif any(w in lower for w in ["economics", "economy", "econometrics"]):
        profile.field_of_study = "economics"
    elif any(w in lower for w in ["commerce", "bcom", "b.com", "accounting", "finance"]):
        profile.field_of_study = "commerce"
    elif any(w in lower for w in ["agriculture", "bsc agri", "agricultural"]):
        profile.field_of_study = "agriculture"
    elif any(w in lower for w in ["law", "llb", "legal"]):
        profile.field_of_study = "law"

    # Degree status
    if any(w in lower for w in ["pursuing", "enrolled", "studying in", "2nd year", "second year", "3rd year", "final year", "in college", "student"]):
        profile.current_degree_status = "pursuing"
    elif any(w in lower for w in ["graduated", "completed", "passed out", "fresh graduate", "recent graduate"]):
        profile.current_degree_status = "fresh_graduate"

    # Marks Percentage
    marks_match = re.search(r"\b([0-9]{2}(?:\.[0-9]+)?)\s*(?:%|percent|percentage)\b", lower)
    if marks_match:
        try:
            p_val = float(marks_match.group(1))
            if 30.0 <= p_val <= 100.0:
                profile.marks_percentage = p_val
        except ValueError:
            pass

    # Skills extraction
    skills_map = {
        "python": "python",
        "data analysis": "data_analysis",
        "data analytics": "data_analysis",
        "gis": "gis",
        "remote sensing": "gis",
        "sql": "sql",
        "excel": "excel",
        "research": "research",
        "policy analysis": "policy_analysis",
        "web development": "web_development",
        "machine learning": "machine_learning",
        "ai": "machine_learning",
        "urban planning": "urban_planning",
    }
    for phrase, skill_key in skills_map.items():
        if re.search(rf"\b{re.escape(phrase)}\b", lower):
            if skill_key not in profile.skills:
                profile.skills.append(skill_key)

    # 9. Caste Category
    if re.search(r"\b(sc|scheduled caste)\b", lower):
        profile.caste_category = "SC"
    elif re.search(r"\b(st|scheduled tribe)\b", lower):
        profile.caste_category = "ST"
    elif re.search(r"\b(obc|other backward class)\b", lower):
        profile.caste_category = "OBC"
    elif re.search(r"\b(ews|economically weaker section)\b", lower):
        profile.caste_category = "EWS"
    elif re.search(r"\b(general category|general caste|unreserved)\b", lower):
        profile.caste_category = "General"

    # 10. Landholding
    if any(w in lower for w in ["own land", "have land", "landowner", "landholder", "have farm", "my land"]):
        profile.is_landholder = True
    elif any(w in lower for w in ["landless", "no land", "don't own land", "tenant farmer", "sharecropper"]):
        profile.is_landholder = False

    land_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:hectare|ha|acres?)\b", lower)
    if land_match:
        val = float(land_match.group(1))
        if "acre" in lower:
            profile.landholding_ha = round(val * 0.404686, 2)
        else:
            profile.landholding_ha = val
        profile.is_landholder = True

    # 11. Gender & Maternity
    if any(w in lower for w in ["pregnant", "pregnancy", "expecting mother", "lactating"]):
        profile.gender = "female"
        profile.is_pregnant_or_lactating = True
    elif any(w in lower for w in ["female", "woman", "girl", "mother", "daughter", "lady"]):
        profile.gender = "female"
    elif any(w in lower for w in ["male", "man", "boy", "son", "gentleman"]):
        profile.gender = "male"

    # 12. BPL / Ration Card
    if any(w in lower for w in ["bpl", "below poverty line", "antyodaya", "aay card", "bpl card"]):
        profile.is_bpl = True

    # 13. Income Tax Payer
    if any(w in lower for w in ["pay tax", "income tax payer", "pay income tax", "taxpayer"]):
        profile.is_taxpayer = True
    elif any(w in lower for w in ["don't pay tax", "non taxpayer", "no income tax"]):
        profile.is_taxpayer = False

    return profile
