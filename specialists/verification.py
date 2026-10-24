"""Verification Specialist validating scheme evidence, citations, and eligibility assertions."""

from __future__ import annotations

import logging
from typing import List, Optional

from schemas.scheme import Scheme
from schemas.results import SchemeEvaluation, VerificationCheckResult
from tools.source_validation import SourceValidationTool

logger = logging.getLogger(__name__)


class VerificationSpecialist:
    """Specialist responsible for fact-checking evidence and validating eligibility logic."""

    def __init__(self, validator: Optional[SourceValidationTool] = None) -> None:
        self.validator = validator or SourceValidationTool()

    def verify_sources(self, scheme: Scheme) -> VerificationCheckResult:
        """Run official domain, HTTPS, and freshness verification on a scheme."""
        return self.validator.verify_scheme_sources(scheme)

    def verify_and_annotate(
        self, scheme: Scheme, evaluation: SchemeEvaluation
    ) -> SchemeEvaluation:
        """Audit an evaluation against the scheme's verified citations and annotate warnings."""
        check = self.verify_sources(scheme)

        # Integrity Check: Ensure evaluation logic was strictly respected
        if evaluation.unmet_conditions and evaluation.overall_status != "NOT_ELIGIBLE":
            evaluation.overall_status = "NOT_ELIGIBLE"
            evaluation.source_warning = "Corrected: Unmet condition detected; cannot be marked eligible."

        warnings = []
        if not check.has_official_source:
            warnings.append("Caution: Official .gov.in source citation is missing or unverified.")
        if not check.is_secure_https:
            warnings.append("Notice: Portal link does not use encrypted HTTPS.")
        if check.is_stale:
            warnings.append(f"Caution: Record verified over 365 days ago ({scheme.last_verified}).")

        if warnings:
            evaluation.source_warning = " ".join(warnings)
            if not check.has_official_source:
                evaluation.verification_status = "UNVERIFIED"

        return evaluation

    def audit_batch(
        self, schemes: List[Scheme], evaluations: List[SchemeEvaluation]
    ) -> List[SchemeEvaluation]:
        """Audit a batch of candidate schemes and evaluations."""
        scheme_map = {s.scheme_id: s for s in schemes}
        audited: List[SchemeEvaluation] = []

        for eval_item in evaluations:
            scheme = scheme_map.get(eval_item.scheme_id)
            if scheme:
                audited.append(self.verify_and_annotate(scheme, eval_item))
            else:
                eval_item.source_warning = "Caution: Scheme not found in official catalog."
                eval_item.verification_status = "UNVERIFIED"
                audited.append(eval_item)

        return audited
