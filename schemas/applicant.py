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
        description="Highest completed or current level: none, class_8_pass, class_10_pass, class_12_pass, undergraduate, graduate, post_graduate",
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
    field_sources: dict[str, str] = Field(
        default_factory=dict,
        description="Source tracking for profile attributes: 'explicitly_supplied', 'reliably_established', or 'unknown'"
    )

    def get_source(self, field_name: str) -> str:
        """Return the establishment source of a specific field."""
        return self.field_sources.get(field_name, "unknown")

    def summary_dict(self) -> dict:
        """Return non-null profile attributes for display and logging."""
        data = {k: v for k, v in self.model_dump().items() if v is not None and k != "field_sources"}
        return data

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


def extract_profile_from_text(
    text: str,
    existing_profile: Optional[ApplicantProfile] = None,
    is_follow_up: bool = False,
) -> ApplicantProfile:
    """Extract applicant attributes from natural language text.
    
    If is_follow_up is True and an existing_profile is supplied, compatible attributes
    from the current conversation are preserved while newly supplied details are updated.
    If is_follow_up is False, a clean profile is created without inheriting stale facts.
    """
    lower = text.lower()

    # Step 1: Initialize profile based on follow-up context
    if is_follow_up and existing_profile:
        profile = existing_profile.model_copy()
        # Mark all inherited non-null fields as reliably established in current conversation
        for k, v in profile.model_dump().items():
            if v is not None and k != "field_sources":
                if k not in profile.field_sources:
                    profile.field_sources[k] = "reliably_established"
    else:
        profile = ApplicantProfile()

    # Step 2: Opportunity Type & Intent
    has_internship = bool(re.search(r"\b(?:internship|internships|intern|interns|trainee|apprenticeship)\b", lower))
    has_scheme = bool(re.search(
        r"\b(?:scheme|schemes|scholarship|scholarships|financial assistance|assistance|benefit|benefits|fund|grant|subsidy|welfare|pension|pensions|loan|loans)\b",
        lower
    ))
    if has_internship and has_scheme:
        profile.opportunity_interest = "both"
        profile.field_sources["opportunity_interest"] = "explicitly_supplied"
    elif has_internship:
        profile.opportunity_interest = "internships"
        profile.field_sources["opportunity_interest"] = "explicitly_supplied"
    elif has_scheme:
        profile.opportunity_interest = "schemes"
        profile.field_sources["opportunity_interest"] = "explicitly_supplied"

    # Step 3: Category of Interest
    if has_internship and not has_scheme:
        profile.category_interest = "internship"
        profile.field_sources["category_interest"] = "explicitly_supplied"
    elif re.search(r"\b(?:farmer|farmers|kisan|crop|crops|agriculture|farming|cultivator|cultivators)\b", lower):
        profile.category_interest = "agriculture"
        profile.field_sources["category_interest"] = "explicitly_supplied"
        if profile.occupation is None:
            profile.occupation = "farmer"
            profile.field_sources["occupation"] = "explicitly_supplied"
    elif re.search(r"\b(?:scholarship|scholarships|student|students|study|studying|college|school|education)\b", lower):
        profile.category_interest = "education"
        profile.field_sources["category_interest"] = "explicitly_supplied"
        if profile.occupation is None:
            profile.occupation = "student"
            profile.field_sources["occupation"] = "explicitly_supplied"
    elif re.search(r"\b(?:house|housing|pucca\s+makan|awas|home\s+loan|shelter)\b", lower):
        profile.category_interest = "housing"
        profile.field_sources["category_interest"] = "explicitly_supplied"
    elif re.search(r"\b(?:health|hospital|ayushman|medical|treatment|illness|doctor)\b", lower):
        profile.category_interest = "healthcare"
        profile.field_sources["category_interest"] = "explicitly_supplied"
    elif re.search(r"\b(?:pension|pensions|old\s+age|elderly|senior\s+citizen|retirement)\b", lower):
        profile.category_interest = "pensions"
        profile.field_sources["category_interest"] = "explicitly_supplied"
    elif re.search(r"\b(?:street\s+vendor|thela|hawker|rehri|artisan|vishwakarma|loan|startup|skill|employment|small\s+business)\b", lower):
        profile.category_interest = "employment"
        profile.field_sources["category_interest"] = "explicitly_supplied"

    # Step 4: Specific Occupations (Strict word boundaries)
    if re.search(r"\b(?:street\s+vendor|vendor|hawker|rehri|thelawala)\b", lower):
        profile.occupation = "street_vendor"
        profile.residence = profile.residence or "urban"
        profile.field_sources["occupation"] = "explicitly_supplied"
    elif re.search(r"\b(?:artisan|craftsperson|carpenter|blacksmith|goldsmith|potter|sculptor|tailor|cobbler)\b", lower):
        profile.occupation = "artisan"
        profile.field_sources["occupation"] = "explicitly_supplied"
    elif re.search(r"\b(?:farmer|farmers|kisan|cultivator|cultivators|peasant)\b", lower):
        profile.occupation = "farmer"
        profile.field_sources["occupation"] = "explicitly_supplied"
    elif re.search(r"\b(?:student|students|studying|undergraduate|postgraduate|scholar|college\s+student|currently\s+in\s+[1-4]|in\s+[1-4](?:st|nd|rd|th)\s+year|in\s+2nd\s+year|in\s+3rd\s+year|in\s+1st\s+year|in\s+4th\s+year)\b", lower):
        profile.occupation = "student"
        profile.field_sources["occupation"] = "explicitly_supplied"
    elif re.search(r"\b(?:unorganized|daily\s+wage|laborer|labourer|construction\s+worker|maid|driver)\b", lower):
        profile.occupation = "unorganized_worker"
        profile.field_sources["occupation"] = "explicitly_supplied"

    # If occupation shifted during follow-up, remove incompatible old fields
    if is_follow_up and existing_profile and existing_profile.occupation != profile.occupation:
        if profile.occupation == "farmer":
            profile.field_of_study = None
            profile.field_sources.pop("field_of_study", None)
            profile.current_degree_status = None
            profile.field_sources.pop("current_degree_status", None)
            profile.marks_percentage = None
            profile.field_sources.pop("marks_percentage", None)
        elif profile.occupation == "student":
            profile.is_landholder = None
            profile.field_sources.pop("is_landholder", None)
            profile.landholding_ha = None
            profile.field_sources.pop("landholding_ha", None)

    # Step 5: Residence (Rural / Urban)
    if re.search(r"\b(?:village|rural|gaon|dehat|gramin|gram)\b", lower):
        profile.residence = "rural"
        profile.field_sources["residence"] = "explicitly_supplied"
    elif re.search(r"\b(?:city|urban|town|metro|municipal)\b", lower):
        profile.residence = "urban"
        profile.field_sources["residence"] = "explicitly_supplied"

    # Step 6: State / Union Territory (Strict boundaries; no accidental 'up' preposition match)
    for state in INDIAN_STATES:
        if re.search(r"\b" + re.escape(state) + r"\b", lower):
            profile.state = state.title()
            profile.field_sources["state"] = "explicitly_supplied"
            break

    if not profile.state or profile.get_source("state") != "explicitly_supplied":
        if re.search(r"\b(?:in\s+up|from\s+up|of\s+up|uttar\s+pradesh|u\.p\.)\b", lower) or re.search(r"\bup\s+(?:state|govt|government|board|citizen|resident|domicile)\b", lower):
            profile.state = "Uttar Pradesh"
            profile.field_sources["state"] = "explicitly_supplied"
        elif re.search(r"\b(?:in\s+mp|from\s+mp|of\s+mp|madhya\s+pradesh|m\.p\.)\b", lower) or re.search(r"\bmp\s+(?:state|govt|government|board|citizen|resident)\b", lower):
            profile.state = "Madhya Pradesh"
            profile.field_sources["state"] = "explicitly_supplied"
        elif re.search(r"\b(?:in\s+mh|from\s+mh|of\s+mh|maharashtra)\b", lower) or re.search(r"\bmh\s+(?:state|govt|government|board|citizen|resident)\b", lower):
            profile.state = "Maharashtra"
            profile.field_sources["state"] = "explicitly_supplied"
        elif re.search(r"\b(?:in\s+tn|from\s+tn|of\s+tn|tamil\s+nadu)\b", lower) or re.search(r"\btn\s+(?:state|govt|government|board|citizen|resident)\b", lower):
            profile.state = "Tamil Nadu"
            profile.field_sources["state"] = "explicitly_supplied"
        elif re.search(r"\b(?:in\s+rj|from\s+rj|of\s+rj|rajasthan)\b", lower) or re.search(r"\brj\s+(?:state|govt|government|board|citizen|resident)\b", lower):
            profile.state = "Rajasthan"
            profile.field_sources["state"] = "explicitly_supplied"

    # Step 7: Age (Strict pattern avoiding class 10/12 false positives)
    age_match = re.search(r"\b(?:i am|age is|age|aged|am)\s+([0-9]{1,2})\s*[-–\s]*(?:years?|yrs?)?\s*[-–\s]*old\b", lower)
    if not age_match:
        age_match = re.search(r"\b([0-9]{1,2})\s*[-–\s]*(?:years?|yrs?)\s*[-–\s]*old\b", lower)
    if not age_match:
        age_match = re.search(r"\b(?:age is|age of|aged)\s+([0-9]{1,2})\b", lower)
    if not age_match:
        age_match = re.search(r"\b(?:i am|am)\s+([0-9]{1,2})\s*(?:,|\band\b|\blive\b|\bstudying\b|\bstudent\b|\bfarmer\b|\byears?\b|\byrs?\b)", lower)

    if age_match:
        try:
            val = int(age_match.group(1))
            if 1 <= val <= 120:
                profile.age = val
                profile.field_sources["age"] = "explicitly_supplied"
        except ValueError:
            pass

    # Step 8: Annual Income (Handles colons, commas e.g. ₹2,40,000, 2.4 lakh, 2.4 LPA, Rs. 2,40,000)
    income_match = re.search(
        r"(?:family\s+)?(?:annual\s+)?(?:income|earning|salary)\s*[:=–-]?\s*(?:is|around|of|upto|less than|under)?\s*(?:rs\.?|inr|₹)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(lakh|lac|lpa|crore|thousand|k)?",
        lower,
    )
    if income_match:
        raw_num = income_match.group(1).replace(",", "").strip()
        unit = income_match.group(2)
        try:
            val = float(raw_num)
            if unit in ("lakh", "lac", "lpa"):
                profile.annual_income = val * 100000.0
            elif unit == "crore":
                profile.annual_income = val * 10000000.0
            elif unit in ("thousand", "k"):
                profile.annual_income = val * 1000.0
            else:
                profile.annual_income = val
            profile.field_sources["annual_income"] = "explicitly_supplied"
        except ValueError:
            pass
    else:
        # Fallback 1: e.g. "₹2,40,000" or "Rs. 2,40,000" with income context
        standalone_curr = re.search(r"\b(?:rs\.?|inr|₹)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(lakh|lac|lpa|thousand|k)?\b", lower)
        if standalone_curr and any(w in lower for w in ["income", "earn", "salary", "family", "annual", "rupees", "p.a", "per year"]):
            raw_num = standalone_curr.group(1).replace(",", "").strip()
            unit = standalone_curr.group(2)
            try:
                val = float(raw_num)
                if unit in ("lakh", "lac", "lpa"):
                    profile.annual_income = val * 100000.0
                elif unit in ("thousand", "k"):
                    profile.annual_income = val * 1000.0
                else:
                    profile.annual_income = val
                profile.field_sources["annual_income"] = "explicitly_supplied"
            except ValueError:
                pass
        else:
            # Fallback 2: "2.4 lakh" with income context
            lakh_match = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:lakh|lac|lpa)\b", lower)
            if lakh_match and any(w in lower for w in ["income", "earn", "salary", "family", "rupees"]):
                profile.annual_income = float(lakh_match.group(1)) * 100000.0
                profile.field_sources["annual_income"] = "explicitly_supplied"

    # Step 9: Education Level (Strict word boundaries, Roman numerals Class VIII/X/XII, B.Sc./B.Tech)
    if re.search(r"\b(?:post\s+graduate|post-graduate|masters|msc|m\.sc|mcom|m\.com|mtech|m\.tech|mba|m\.a)\b", lower):
        profile.education_level = "post_graduate"
        profile.field_sources["education_level"] = "explicitly_supplied"
    elif re.search(r"\b(?:currently\s+in\s+)?(?:2nd|second|3rd|third|final|1st|first)\s+year\b", lower) and re.search(r"\b(?:b\.?sc|b\.?tech|b\.?e|bca|bba|b\.?com|b\.?a|undergraduate|college|degree)\b", lower):
        profile.education_level = "undergraduate"
        profile.current_degree_status = "pursuing"
        profile.field_sources["education_level"] = "explicitly_supplied"
        profile.field_sources["current_degree_status"] = "explicitly_supplied"
        if not profile.occupation:
            profile.occupation = "student"
            profile.field_sources["occupation"] = "explicitly_supplied"
    elif re.search(r"\b(?:undergraduate|pursuing\s+graduation|college\s+student|enrolled\s+in\s+college)\b", lower):
        profile.education_level = "undergraduate"
        profile.current_degree_status = "pursuing"
        profile.field_sources["education_level"] = "explicitly_supplied"
        profile.field_sources["current_degree_status"] = "explicitly_supplied"
    elif re.search(r"\b(?:completed\s+graduation|graduated|passed\s+degree|bachelor\s+degree\s+holder)\b", lower):
        profile.education_level = "graduate"
        profile.field_sources["education_level"] = "explicitly_supplied"
    elif re.search(r"\b(?:b\.?sc|bsc|bcom|b\.com|btech|b\.tech|b\.e|bca|bba|college|university)\b", lower):
        if "pursuing" in lower or "studying" in lower or "student" in lower or "year" in lower:
            profile.education_level = "undergraduate"
            profile.current_degree_status = profile.current_degree_status or "pursuing"
        else:
            profile.education_level = "undergraduate"
        profile.field_sources["education_level"] = "explicitly_supplied"
    elif re.search(r"\b(?:12th|12\s+pass|class\s+12|class\s+xii|intermediate|higher\s+secondary)\b", lower):
        profile.education_level = "class_12_pass"
        profile.field_sources["education_level"] = "explicitly_supplied"
    elif re.search(r"\b(?:10th|10\s+pass|class\s+10|class\s+x|matric|high\s+school|secondary)\b", lower):
        profile.education_level = "class_10_pass"
        profile.field_sources["education_level"] = "explicitly_supplied"
    elif re.search(r"\b(?:8th|8\s+pass|class\s+8|class\s+viii|middle\s+school)\b", lower):
        profile.education_level = "class_8_pass"
        profile.field_sources["education_level"] = "explicitly_supplied"

    # Step 10: Field of Study (Academic disciplines; never match 'it' inside 'benefits', 'credit', etc.)
    if re.search(r"\b(?:computer\s+science|information\s+technology|software\s+engineering|software\s+development)\b", lower) or re.search(r"\b(?:b\.?tech|degree|study|studying|major|diploma)\s+(?:in\s+)?(?:cs|it)\b", lower):
        profile.field_of_study = "computer_science"
        profile.field_sources["field_of_study"] = "explicitly_supplied"
    elif re.search(r"\b(?:b\.?sc|bsc|bachelor\s+of\s+science|physics|chemistry|mathematics|math|biology|botany|zoology)\b", lower):
        profile.field_of_study = "science"
        profile.field_sources["field_of_study"] = "explicitly_supplied"
    elif re.search(r"\b(?:mechanical|electrical|civil|aerospace|chemical)\s+engineering\b", lower) or re.search(r"\b(?:engineering|b\.?tech|b\.?e)\b", lower):
        profile.field_of_study = "engineering"
        profile.field_sources["field_of_study"] = "explicitly_supplied"
    elif re.search(r"\b(?:public\s+policy|governance|political\s+science)\b", lower):
        profile.field_of_study = "public_policy"
        profile.field_sources["field_of_study"] = "explicitly_supplied"
    elif re.search(r"\b(?:economics|econometrics|b\.?a\.?\s+economics|m\.?a\.?\s+economics)\b", lower):
        profile.field_of_study = "economics"
        profile.field_sources["field_of_study"] = "explicitly_supplied"
    elif re.search(r"\b(?:commerce|b\.?com|accounting|chartered\s+accountan(?:cy|t))\b", lower):
        profile.field_of_study = "commerce"
        profile.field_sources["field_of_study"] = "explicitly_supplied"
    elif re.search(r"\b(?:bsc\s+agri(?:culture)?|agricultural\s+science|agronomy|degree\s+in\s+agriculture)\b", lower):
        profile.field_of_study = "agriculture"
        profile.field_sources["field_of_study"] = "explicitly_supplied"
    elif re.search(r"\b(?:ll\.?b|b\.?a\.?\s+ll\.?b|law\s+degree|legal\s+studies)\b", lower):
        profile.field_of_study = "law"
        profile.field_sources["field_of_study"] = "explicitly_supplied"

    # Step 11: Degree Status
    if re.search(r"\b(?:pursuing|enrolled|studying\s+in|2nd\s+year|second\s+year|3rd\s+year|final\s+year)\b", lower):
        profile.current_degree_status = "pursuing"
        profile.field_sources["current_degree_status"] = "explicitly_supplied"
    elif re.search(r"\b(?:graduated|completed\s+degree|passed\s+out|fresh\s+graduate|recent\s+graduate)\b", lower):
        profile.current_degree_status = "fresh_graduate"
        profile.field_sources["current_degree_status"] = "explicitly_supplied"

    # Step 12: Marks Percentage (Strictly self-attributed; never fabricate from requirement statements or unprovided notices)
    has_unprovided_marks_signal = bool(re.search(
        r"\b(?:haven't|have\s+not|didn't|did\s+not|not)\s+(?:told|shared|given|provided|mentioned)\s+(?:you\s+)?(?:my\s+)?(?:marks|score|percentage|grades?)\b",
        lower,
    ) or re.search(r"\bwithout\s+(?:knowing\s+)?(?:my\s+)?(?:marks|score|percentage)\b", lower))

    is_requirement_statement = bool(re.search(
        r"\b(?:requires?|requiring|cutoff|cut-off|eligibility|criteria|minimum|need|needs|condition)\s*(?:of|is|at\s+least|min)?\s*[0-9]{2}(?:\.[0-9]+)?\s*(?:%|percent|percentage)\b",
        lower,
    ))

    if not has_unprovided_marks_signal and not is_requirement_statement:
        marks_patterns = [
            r"(?:my\s+)?(?:marks|score|percentage)\s*(?:is|are|of|around|:|=)?\s*([0-9]{2}(?:\.[0-9]+)?)\s*(?:%|percent|percentage)?",
            r"(?:i\s+)?(?:have\s+)?(?:scored|got|secured|achieved|with)\s+([0-9]{2}(?:\.[0-9]+)?)\s*(?:%|percent|percentage)",
            r"\b([0-9]{2}(?:\.[0-9]+)?)\s*(?:%|percent|percentage)\s*(?:marks|score|in\s+12|in\s+10|in\s+class|in\s+college|aggregate)\b",
        ]
        for p in marks_patterns:
            m = re.search(p, lower)
            if m:
                try:
                    p_val = float(m.group(1))
                    if 30.0 <= p_val <= 100.0:
                        profile.marks_percentage = p_val
                        profile.field_sources["marks_percentage"] = "explicitly_supplied"
                        break
                except ValueError:
                    pass

    # Step 13: Skills extraction (Strict word boundaries)
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
        "urban planning": "urban_planning",
    }
    for phrase, skill_key in skills_map.items():
        if re.search(rf"\b{re.escape(phrase)}\b", lower):
            if skill_key not in profile.skills:
                profile.skills.append(skill_key)
                profile.field_sources["skills"] = "explicitly_supplied"

    # Step 14: Caste Category (Strict word boundaries, never match B.Sc. / M.Sc.)
    if re.search(r"(?<![bm]\.)(?<![bm])\b(?:sc|scheduled\s+caste)\b(?!\.)", lower):
        profile.caste_category = "SC"
        profile.field_sources["caste_category"] = "explicitly_supplied"
    elif re.search(r"\b(st|scheduled tribe)\b", lower):
        profile.caste_category = "ST"
        profile.field_sources["caste_category"] = "explicitly_supplied"
    elif re.search(r"\b(obc|other backward class)\b", lower):
        profile.caste_category = "OBC"
        profile.field_sources["caste_category"] = "explicitly_supplied"
    elif re.search(r"\b(ews|economically weaker section)\b", lower):
        profile.caste_category = "EWS"
        profile.field_sources["caste_category"] = "explicitly_supplied"
    elif re.search(r"\b(general category|general caste|unreserved)\b", lower):
        profile.caste_category = "General"
        profile.field_sources["caste_category"] = "explicitly_supplied"

    # Step 15: Landholding
    land_match = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:hectares?|ha|acres?)\b", lower)
    if land_match:
        val = float(land_match.group(1))
        if "acre" in lower:
            profile.landholding_ha = round(val * 0.404686, 2)
        else:
            profile.landholding_ha = val
        profile.is_landholder = True
        profile.field_sources["landholding_ha"] = "explicitly_supplied"
        profile.field_sources["is_landholder"] = "explicitly_supplied"
    elif re.search(r"\b(?:own\s+land|have\s+land|landowner|landholder|have\s+farm|my\s+land|own\s+farm)\b", lower):
        profile.is_landholder = True
        profile.field_sources["is_landholder"] = "explicitly_supplied"
    elif re.search(r"\b(?:landless|no\s+land|don't\s+own\s+land|tenant\s+farmer|sharecropper)\b", lower):
        profile.is_landholder = False
        profile.field_sources["is_landholder"] = "explicitly_supplied"

    # Step 16: Gender & Maternity
    if re.search(r"\b(?:pregnant|pregnancy|expecting\s+mother|lactating)\b", lower):
        profile.gender = "female"
        profile.is_pregnant_or_lactating = True
        profile.field_sources["gender"] = "explicitly_supplied"
        profile.field_sources["is_pregnant_or_lactating"] = "explicitly_supplied"
    elif re.search(r"\b(?:female|woman|girl|mother|daughter|lady)\b", lower):
        profile.gender = "female"
        profile.field_sources["gender"] = "explicitly_supplied"
    elif re.search(r"\b(?:male|man|boy|son|gentleman)\b", lower):
        profile.gender = "male"
        profile.field_sources["gender"] = "explicitly_supplied"

    # Step 17: BPL / Ration Card
    if re.search(r"\b(?:bpl|below\s+poverty\s+line|antyodaya|aay\s+card|bpl\s+card)\b", lower):
        profile.is_bpl = True
        profile.field_sources["is_bpl"] = "explicitly_supplied"

    # Step 18: Income Tax Payer
    if re.search(r"\b(?:pay\s+tax|income\s+tax\s+payer|pay\s+income\s+tax|taxpayer)\b", lower):
        profile.is_taxpayer = True
        profile.field_sources["is_taxpayer"] = "explicitly_supplied"
    elif re.search(r"\b(?:don't\s+pay\s+tax|non\s+taxpayer|no\s+income\s+tax)\b", lower):
        profile.is_taxpayer = False
        profile.field_sources["is_taxpayer"] = "explicitly_supplied"

    return profile
