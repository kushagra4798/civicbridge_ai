"""Tests for Verification Specialist and SourceValidationTool."""

import pytest
from schemas.scheme import Scheme, EligibilityRule
from schemas.results import SchemeEvaluation
from tools.source_validation import SourceValidationTool
from specialists.verification import VerificationSpecialist


def test_source_validation_official_domains():
    tool = SourceValidationTool()

    assert tool.is_official_domain("https://pmkisan.gov.in") is True
    assert tool.is_official_domain("https://scholarships.gov.in/portal") is True
    assert tool.is_official_domain("https://nsap.nic.in") is True
    assert tool.is_official_domain("https://www.myscheme.gov.in/schemes/pm-kisan") is True
    assert tool.is_official_domain("https://maandhan.in") is True

    # Untrusted / Third-party domains
    assert tool.is_official_domain("https://fake-government-schemes.com") is False
    assert tool.is_official_domain("https://blogspot.com/pmkisan") is False
    assert tool.is_official_domain("http://unverified-portal.org") is False


def test_source_validation_https_security():
    tool = SourceValidationTool()
    assert tool.is_secure_url("https://pmkisan.gov.in") is True
    assert tool.is_secure_url("http://insecure.gov.in") is False


def test_scheme_source_verification_stale_and_fresh():
    tool = SourceValidationTool()

    # Fresh verified scheme
    fresh_scheme = Scheme(
        scheme_id="fresh_test",
        name="Fresh Scheme",
        short_name="FRESH",
        description="Freshly verified scheme",
        category="agriculture",
        governing_department="Dept of Agriculture",
        benefit_summary="Assistance",
        official_portal_url="https://agricoop.gov.in",
        evidence_urls=["https://pmkisan.gov.in"],
        last_verified="2026-03-01",
    )
    fresh_res = tool.verify_scheme_sources(fresh_scheme)
    assert fresh_res.is_valid is True
    assert fresh_res.has_official_source is True
    assert fresh_res.is_stale is False

    # Stale scheme (> 365 days old)
    stale_scheme = Scheme(
        scheme_id="stale_test",
        name="Stale Scheme",
        short_name="STALE",
        description="Outdated verification",
        category="agriculture",
        governing_department="Dept",
        benefit_summary="Assistance",
        official_portal_url="https://agricoop.gov.in",
        last_verified="2024-01-01",
    )
    stale_res = tool.verify_scheme_sources(stale_scheme)
    assert stale_res.is_stale is True


def test_verification_specialist_audit_batch():
    specialist = VerificationSpecialist()

    scheme = Scheme(
        scheme_id="pmkisan_test",
        name="PM Kisan",
        short_name="PM-KISAN",
        description="Farmer support",
        category="agriculture",
        governing_department="MoA",
        benefit_summary="₹6,000 / year",
        official_portal_url="https://pmkisan.gov.in",
        evidence_urls=["https://myscheme.gov.in"],
        last_verified="2026-03-01",
    )

    evaluation = SchemeEvaluation(
        scheme_id="pmkisan_test",
        scheme_name="PM Kisan",
        short_name="PM-KISAN",
        category="agriculture",
        overall_status="ELIGIBLE",
        met_conditions=["Farmer landholder verified"],
        benefit_summary="₹6,000 / year",
        geographic_coverage="All India",
        official_portal_url="https://pmkisan.gov.in",
        application_dates="Year-round",
        last_verified="2026-03-01",
        verification_status="VERIFIED",
    )

    audited = specialist.audit_batch([scheme], [evaluation])
    assert len(audited) == 1
    assert audited[0].verification_status == "VERIFIED"
    assert audited[0].source_warning is None
