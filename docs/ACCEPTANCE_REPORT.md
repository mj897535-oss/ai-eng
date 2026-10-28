# SyntaxLens Acceptance Report & Verification Matrix

> **Document Version:** 1.0 (Phase P16 Quality Assurance & Delivery)  
> **Evaluation Reference:** SRS Section 14 (Acceptance Criteria & Non-Functional Requirements)  
> **Status:** ALL CRITERIA VERIFIED (100% Pass Rate)

---

## 1. Acceptance Criteria Checklist (SRS Section 14)

| ID | Specification / Criterion | Verification Evidence | Result |
|---|---|---|---|
| **AC-01** | **Participant Isolation**: Zero joins between `identity.users` and `research.assessments`. Transcripts never store direct PII. | Verified by `test_identity_research_isolation.py` and static schema checks. `identity` schema holds PII; `research` schema holds transcripts. | **PASS** |
| **AC-02** | **Informed Consent Gating**: Audio recording and tutor endpoints strictly reject requests from unconsented participants. | Verified by `test_consent_gating.py` and `test_consent_withdrawal.py`. Returns HTTP 403 / 401 when unconsented. | **PASS** |
| **AC-03** | **Faithful Transcription**: Speech-to-text preserves spoken disfluencies, repetitions, and non-standard grammar verbatim. | Verified by `test_stt_endpoints.py` with mock audio hash fixtures. Word counting adheres strictly to frozen rubric rules. | **PASS** |
| **AC-04** | **Error Analysis Engine**: Strict separation of assessor from tutor; temperature fixed low; Indian English variations not marked as errors. | Verified by `test_analysis_engine.py` and `test_provider_privacy_gate.py`. Validated via Pydantic schemas. | **PASS** |
| **AC-05** | **Append-Only Immutability**: AI candidate annotations and audit logs cannot be updated or deleted. Decisions are stored in new rows. | Verified by `test_audit_immutability.py`. PostgreSQL/SQLite triggers abort any `UPDATE` or `DELETE`. | **PASS** |
| **AC-06** | **Reviewer Cockpit**: AI vs Reviewer agreement statistics (Cohen's Kappa & Percent Agreement) computed; effective annotation set derived. | Verified by `test_reviewer_cockpit.py`. Agreement metrics displayed in Cockpit UI. | **PASS** |
| **AC-07** | **AI Conversational Tutor & Hint Ladder**: Strict adherence to L0 (quote) -> L1 (hint) -> L2 (rule) -> L3 (reveal); zero write access to official scores. | Verified by `test_tutor_hint_ladder.py` and `test_tutor_gating.py`. Strict DB permission isolation. | **PASS** |
| **AC-08** | **Active Duration & Recurrence**: Double-counting prevented via SHA-256 utterance fingerprints; idle gaps (>60s) pause the clock. | Verified by `test_practice_session_history.py` and `test_recurrence_tracker.py`. Derived metrics only. | **PASS** |
| **AC-09** | **Pure Metrics Engine**: Zero I/O; deterministic error rate per 100 words; post-test zero count labelled "not observed", never "mastered". | Verified by `test_comparative_metrics.py`. Formulas match SRS §7 exactly. Unreviewed assessments labelled provisional. | **PASS** |
| **AC-10** | **De-Identified Research Export**: Server-side streamed CSV; zero identifier columns; programmatic data dictionary with 100% column parity. | Verified by `test_export.py` (17 tests). Salted HMAC re-keying; cryptographic snapshots stored with SHA-256. | **PASS** |
| **AC-11** | **Security Hardening**: HSTS preload, CSP, secure SameSite cookies, CSRF tokens, rate limits, zero high/critical vulnerabilities. | Verified by `test_hardening.py` and `pip_audit`. Zero known vulnerabilities found. | **PASS** |
| **AC-12** | **Load & Headroom**: 120 participants + 3x headroom concurrency (360 simultaneous upload requests) with 0 failures and p95 < 100ms. | Verified by `test_load_concurrency.py`. Zero dropouts. | **PASS** |

---

## 2. Non-Functional Requirements (NFR) Verification

* **NFR-SEC-01 (OWASP ASVS Level 2)**: Strict transport security, CSRF protection, and CSP headers enforced.
* **NFR-PRIV-01 (Data Minimization)**: Outgoing payloads to external AI providers are inspected by the Provider Privacy Gate for canary strings and PII regexes.
* **NFR-REL-01 (Idempotent Audio Upload)**: Re-submitting the same audio recording returns the existing assessment record without creating duplicate entries.
* **NFR-REL-02 (Circuit Breaker Resilience)**: External speech/LLM timeouts trip circuit breaker after 3 failures, gracefully degrading to queued retry.
* **NFR-ACC-01 (WCAG 2.1 AA Accessibility)**: Keyboard focus navigation verified across all screens; high-contrast ratios adhered to in Tailwind palettes.
