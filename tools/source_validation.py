"""Source validation and citation verification tool."""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from typing import Optional

from schemas.scheme import Scheme
from schemas.results import VerificationCheckResult

# Approved official government domains and verified national welfare portals
OFFICIAL_DOMAINS = (
    ".gov.in",
    ".nic.in",
    "myscheme.gov.in",
    "maandhan.in",
    "npscra.nsdl.co.in",
    "kviconline.gov.in",
)


class SourceValidationTool:
    """Validates citations, portal URLs, and verification freshness of schemes."""

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL syntax."""
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    @staticmethod
    def is_official_domain(url: str) -> bool:
        """Check if URL host belongs to recognized official government domains."""
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            return any(host.endswith(dom) or host == dom for dom in OFFICIAL_DOMAINS)
        except Exception:
            return False

    @staticmethod
    def is_secure_url(url: str) -> bool:
        """Verify URL uses secure HTTPS transport."""
        try:
            parsed = urlparse(url)
            return parsed.scheme.lower() == "https"
        except Exception:
            return False

    @classmethod
    def verify_scheme_sources(
        cls, scheme: Scheme, max_age_days: int = 365
    ) -> VerificationCheckResult:
        """Check that a scheme has valid, secure, and official source links, and is not stale."""
        findings: list[str] = []
        is_valid = True

        portal_url = scheme.official_portal_url
        if not cls.is_valid_url(portal_url):
            is_valid = False
            findings.append(f"Official portal URL '{portal_url}' is invalid or missing.")
        else:
            if not cls.is_secure_url(portal_url):
                findings.append(f"Official portal URL '{portal_url}' does not use HTTPS.")
            if not cls.is_official_domain(portal_url):
                findings.append(f"Official portal URL '{portal_url}' is not a recognised .gov.in/.nic.in domain.")
            else:
                findings.append(f"Official portal verified: {portal_url}")

        # Check evidence citations
        if not scheme.evidence_urls:
            findings.append("No secondary evidence citations provided.")
        else:
            for ev_url in scheme.evidence_urls:
                if not cls.is_valid_url(ev_url):
                    findings.append(f"Malformed evidence URL: {ev_url}")
                elif not cls.is_official_domain(ev_url):
                    findings.append(f"Evidence citation '{ev_url}' is not from an official domain.")

        # Check verification recency
        is_stale = False
        try:
            verified_date = datetime.strptime(scheme.last_verified, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            age_days = (today - verified_date).days
            if age_days > max_age_days:
                is_stale = True
                findings.append(f"Record last verified {age_days} days ago (exceeds {max_age_days} days threshold).")
            else:
                findings.append(f"Source verified {age_days} days ago (within freshness window).")
        except Exception:
            is_stale = True
            findings.append("Invalid or unparseable last_verified date format.")

        has_official = any(cls.is_official_domain(u) for u in [portal_url] + scheme.evidence_urls)

        return VerificationCheckResult(
            scheme_id=scheme.scheme_id,
            is_valid=is_valid and has_official,
            has_official_source=has_official,
            is_secure_https=cls.is_secure_url(portal_url),
            is_stale=is_stale,
            last_verified=scheme.last_verified,
            findings=findings,
        )
