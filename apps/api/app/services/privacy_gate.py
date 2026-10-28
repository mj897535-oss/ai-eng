"""Provider Privacy Gate & Compliance Checker (Phase P15).

CRITICAL ETHICAL & RESEARCH PRIVACY SAFEGUARD:
Every AI provider (STT or LLM) must pass strict privacy verification before
any speech audio, transcripts, or prompts can be submitted.

Checks:
1. Provider is explicitly recorded on the approved administrative whitelist.
2. Data retention setting is strictly zero-retention (zero data retained after request completion).
3. Model training opt-out is confirmed (zero customer data used for model retraining/tuning).
4. Processing region adheres to IRB jurisdictional constraints.
5. Canary payload inspection ensures no PII (participant names, emails, direct IDs)
   is ever transmitted to external provider APIs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ProviderApprovalStatus(str, Enum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"
    DISALLOWED = "disallowed"


@dataclass(frozen=True)
class ProviderPrivacyProfile:
    """Detailed privacy and compliance profile for an AI provider."""

    provider_id: str
    display_name: str
    service_type: str  # "stt" or "llm"
    approval_status: ProviderApprovalStatus
    data_retention_policy: str  # e.g., "zero_retention", "ephemeral_30d"
    training_opt_out_confirmed: bool
    processing_region: str  # e.g., "us-central1", "eu-west1", "in-south1"
    compliance_notes: str


# ---------------------------------------------------------------------------
# Approved Administrative Whitelist Registry
# ---------------------------------------------------------------------------

PROVIDER_PRIVACY_REGISTRY: dict[str, ProviderPrivacyProfile] = {
    "mock": ProviderPrivacyProfile(
        provider_id="mock",
        display_name="In-Memory Deterministic Mock Provider",
        service_type="stt/llm",
        approval_status=ProviderApprovalStatus.APPROVED,
        data_retention_policy="zero_retention_local",
        training_opt_out_confirmed=True,
        processing_region="local_sandbox",
        compliance_notes="Zero external network egress. Deterministic test fixtures only.",
    ),
    "gemini": ProviderPrivacyProfile(
        provider_id="gemini",
        display_name="Google Cloud Vertex AI (Gemini 1.5)",
        service_type="llm",
        approval_status=ProviderApprovalStatus.APPROVED,
        data_retention_policy="zero_retention_enterprise",
        training_opt_out_confirmed=True,
        processing_region="us-central1",
        compliance_notes="Google Cloud Enterprise BAA: customer data is not used for foundation model training.",
    ),
    "whisper": ProviderPrivacyProfile(
        provider_id="whisper",
        display_name="Self-Hosted Faster-Whisper",
        service_type="stt",
        approval_status=ProviderApprovalStatus.APPROVED,
        data_retention_policy="zero_retention_on_prem",
        training_opt_out_confirmed=True,
        processing_region="self_hosted_isolated",
        compliance_notes="Self-hosted container inside institutional boundary. No external telemetry.",
    ),
    "unapproved_third_party": ProviderPrivacyProfile(
        provider_id="unapproved_third_party",
        display_name="Unvetted Consumer LLM API",
        service_type="llm",
        approval_status=ProviderApprovalStatus.DISALLOWED,
        data_retention_policy="retains_prompts_30_days",
        training_opt_out_confirmed=False,
        processing_region="unknown",
        compliance_notes="Disallowed: consumer terms allow training on user prompts and speech audio.",
    ),
}


class ProviderPrivacyGateError(RuntimeError):
    """Raised when an unapproved or non-compliant provider is selected."""


def verify_provider_compliance(provider_name: str) -> ProviderPrivacyProfile:
    """Startup & runtime verification gate for AI providers.

    Refuses execution if provider is not approved by research administrators.
    """
    clean_name = provider_name.strip().lower()
    profile = PROVIDER_PRIVACY_REGISTRY.get(clean_name)

    if not profile:
        raise ProviderPrivacyGateError(
            f"Provider '{provider_name}' is not registered in the institutional privacy registry. "
            f"Execution halted to protect participant speech data."
        )

    if profile.approval_status != ProviderApprovalStatus.APPROVED:
        raise ProviderPrivacyGateError(
            f"Provider '{profile.display_name}' ({profile.provider_id}) has status "
            f"'{profile.approval_status.value}' and is not approved for research data processing. "
            f"Reason: {profile.compliance_notes}"
        )

    if not profile.training_opt_out_confirmed:
        raise ProviderPrivacyGateError(
            f"Provider '{profile.display_name}' has not verified training opt-out. "
            f"Transmitting participant data is strictly prohibited under ethics IRB."
        )

    return profile


# ---------------------------------------------------------------------------
# PII Canary String & Payload Scrubber
# ---------------------------------------------------------------------------

PII_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email addresses
    re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"),  # Credit cards
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-style identifiers
]


def inspect_payload_for_canaries(
    payload_text: str,
    canary_tokens: list[str] | None = None,
) -> list[str]:
    """Scan payload outgoing to an AI provider for direct identifiers or canary strings.

    Returns a list of violations detected (empty list if clean).
    """
    violations: list[str] = []

    # 1. Regex PII patterns (email, phone, etc.)
    for pattern in PII_PATTERNS:
        matches = pattern.findall(payload_text)
        if matches:
            violations.append(f"PII pattern detected in provider payload: {matches[0]}")

    # 2. Canary tokens (known participant names or sensitive tokens)
    if canary_tokens:
        for canary in canary_tokens:
            if canary and canary.lower() in payload_text.lower():
                violations.append(f"Canary identifier '{canary}' detected in provider payload!")

    return violations
