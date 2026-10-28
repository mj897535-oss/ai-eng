# SyntaxLens Requirements Traceability Matrix (RTM)

> **Document Version:** 2.0 (Phase P16 Delivery & Final Verification)  
> **Traceability Target:** SRS Sections 6–14 • 100% Verified

---

## 1. Functional Requirements (FR-01 to FR-20)

| ID | Requirement Summary | Planned Phase | Planned Tests | Status |
|---|---|---|---|---|
| **FR-01** | **Authentication & RBAC**: Secure sign-in; participants access only own data; role-based researcher and reviewer permissions. | **Phase 3** (Auth, RBAC, Audit) | `tests/api/test_auth.py`, `tests/api/test_rbac_matrix.py` | Verified (RBAC Matrix, Session & CSRF) |
| **FR-02** | **Participant Management**: Create, batch import, deactivate, view participants. Enforce unique pseudonymous IDs (e.g. `SL-2026-xxx`). | **Phase 4** (Participants & Onboarding) | `tests/api/test_participant_management.py`, `tests/api/test_csv_bulk_import.py` | Verified (Services & API) |
| **FR-03** | **Consent Handling**: Present approved consent before recording; record consent version, status, and timestamp. Append-only. | **Phase 4** (Participants & Onboarding) | `tests/api/test_consent_gating.py`, `tests/api/test_consent_withdrawal.py` | Verified (Append-Only Gating Tested) |
| **FR-04** | **Audio Capture**: Record, listen back, re-record before submission; presigned S3 upload; upload failure handling. | **Phase 6** (Audio Capture & Upload) | `tests/api/test_audio_recording.py` | Verified (Bulletproof Recorder & Storage) |
| **FR-05** | **Assessment Task**: Standardized instructions, task duration (60s), prep time (30s), topic bank, rubric version. | **Phase 5** (Versioned Config) | `tests/api/test_research_settings.py`, `tests/unit/test_topic_seed_assignment.py` | Verified (Equivalence Pairs & Seeds) |
| **FR-06** | **Transcription**: Faithful transcript preserving errors; retain timestamps; decoupled STTProvider. | **Phase 7** (Transcription Pipeline) | `tests/services/test_stt_pipeline.py`, `tests/api/test_stt_endpoints.py` | Verified (MockSTT, Verbatim Preserved, Word Counting) |
| **FR-07** | **Error Analysis**: Candidate deviations with span, correction, category, confidence, and explanation. | **Phase 8** (Assessment Engine) | `tests/services/test_error_analysis.py`, `tests/services/test_llm_mock.py` | Verified (Decoupled LLMProvider, Golden Set Tests) |
| **FR-08** | **Error Categories**: 8 categories (TNS, SVA, WO, AUX, ART, PREP, PRO, OTH). Pure metrics integration. | **Phase 8** (Assessment Engine) | `tests/research/test_metrics.py`, `tests/services/test_error_analysis.py` | Verified (Taxonomies & Golden Fixtures) |
| **FR-09** | **Uncertainty Handling**: Flag items as acceptable variation, transcription error, or needing human review. | **Phase 8** (Assessment Engine) | `tests/services/test_error_analysis.py`, `tests/services/test_llm_mock.py` | Verified (Dialect/Uncertainty Flags & Review Auto-Routing) |
| **FR-10** | **Human Review**: Reviewer can accept, reject, edit, or recategorize. Model outputs never overwritten. | **Phase 9** (Review Workflow) | `tests/services/test_review_cockpit.py`, `app/models/assessment.py` | Verified (Append-only Decisions, Derived View, Immutability) |
| **FR-11** | **Personalised Tutor**: Uses verified baseline priorities; strict server-side blinding during pre/post tests. | **Phase 10** (Tutor Engine) | `tests/services/test_tutor_ladder.py`, `app/api/v1/tutor.py` | Verified (Verified Baseline Gating, Score Isolation) |
| **FR-12** | **Feedback Sequence**: Hint ladder (L0 quote, L1 hint, L2 rule, L3 reveal); independent transfer check. | **Phase 10** (Tutor Engine) | `tests/services/test_tutor_ladder.py`, `app/services/llm/mock.py` | Verified (Hint Ladder State Machine & Transfer Check) |
| **FR-13** | **Session History**: Track start/end, active practice duration, targeted skills, hint usage, outcomes. | **Phase 11** (Practice Logging) | `tests/services/test_practice_recurrence.py`, `app/api/v1/tutor.py` | Verified (Active Timing, Idle Gaps Excluded, Technical Interruptions) |
| **FR-14** | **Recurrence Tracking**: Track error categories across sessions without double counting repeated hints for one utterance. | **Phase 11** (Practice Logging) | `tests/services/test_practice_recurrence.py`, `app/research/metrics.py` | Verified (SHA-256 Fingerprint, Zero Double-Counting Guarantee) |
| **FR-15** | **Post-Test**: Equal condition assessment, alternate topic, rubric version parity, linked to pre-test. | **Phase 12** (Post-Test & Comparative) | `tests/research/test_comparative_metrics.py`, `app/research/metrics.py` | Verified (Equivalence Group Linkage, Rubric Parity) |
| **FR-16** | **Student & Researcher Dashboard**: Cohort progress, completion funnel, intervention adherence, plain-language numbers. | **Phase 13** (Dashboards) | `tests/api/test_dashboards.py`, `apps/web/src/app/dashboard` | Verified (Cohort Funnel, Adherence, Capacity Panel) |
| **FR-17** | **Participant Drilldown**: Longitudinal timeline, event sequence, assessment verification statuses. | **Phase 13** (Dashboards) | `tests/api/test_dashboards.py`, `apps/web/src/app/admin/dashboard` | Verified (Participant Drilldown Timeline) |
| **FR-18** | **Data Export**: De-identified CSV with data dictionary and provenance metadata. | **Phase 14** (Export & Data Dict) | `tests/api/test_export.py` | Verified (Export API, Salted-Hash, Snapshots) |
| **FR-19** | **Audit Trail**: Append-only log for login, consent, audio submission, review decisions, export, deletion. | **Phase 3** (Auth, RBAC, Audit) | `tests/db/test_audit_immutability.py`, `tests/api/test_auth.py` | Verified (Triggers & Logging) |
| **FR-20** | **Configuration**: Versioned and frozen prompts, rubrics, topic pool, and scoring rules per study period. | **Phase 5** (Versioned Config) | `tests/api/test_research_settings.py`, `tests/db/test_frozen_immutability.py` | Verified (DB Triggers & Settings UI) |

---

## 2. Non-Functional Requirements (NFRs)

| ID | Requirement Summary | Planned Phase | Planned Verification Method | Status |
|---|---|---|---|---|
| **NFR-SEC-01** | **OWASP ASVS L2**: HTTPS/HSTS, CSP, secure SameSite cookies, CSRF tokens, rate limits, no raw PII in research tables. | **Phase 15** | `tests/api/test_hardening.py`, automated header tests. | Verified (ASVS L2 Baseline) |
| **NFR-SEC-02** | **Append-Only Immutability**: DB triggers prevent `UPDATE`/`DELETE` on audit logs, error candidates, reviewer decisions. | **Phase 3 / 9** | `tests/db/test_audit_immutability.py`. | Verified (Database Triggers) |
| **NFR-SEC-03** | **Storage Access Control**: S3 private buckets, short-lived presigned URLs (15m expiry), zero public access. | **Phase 6** | `tests/api/test_audio_recording.py`. | Verified (Presigned Expiry Gating) |
| **NFR-PRIV-01** | **Provider Privacy Gate**: AI providers vetted for zero-retention, training opt-out, zero names/canaries in outgoing payloads. | **Phase 15** | `tests/api/test_hardening.py`. | Verified (Privacy Gate & Canary Inspector) |
| **NFR-PRIV-02** | **Retention & Purge**: Configurable data retention; voluntary withdrawal purges audio and anonymizes identity. | **Phase 15** | `tests/api/test_hardening.py`. | Verified (Right-to-be-Forgotten Service) |
| **NFR-REL-01** | **Idempotency & Zero Dropouts**: Duplicate submissions resolved idempotently without data duplication. | **Phase 6 / 15** | `tests/api/test_audio_recording.py`, `tests/api/test_load_concurrency.py`. | Verified (Idempotency Handlers) |
| **NFR-REL-02** | **Circuit Breaker Resilience**: AI timeouts trip circuit breaker after 3 failures, gracefully degrading to queued retry. | **Phase 15** | `tests/api/test_hardening.py`. | Verified (Circuit Breaker Suite) |
| **NFR-SCAL-01** | **Cohort Scalability**: Support 120 enrolled participants with 3x headroom concurrency (360 simultaneous requests). | **Phase 16** | `tests/api/test_load_concurrency.py`. | Verified (360 Concurrent Requests) |
| **NFR-ACC-01** | **Accessibility**: WCAG 2.1 AA keyboard navigation, high contrast, ARIA landmarks, mobile 360px responsiveness. | **Phase 16** | Playwright accessibility and manual keyboard sweeps. | Verified (Full Mobile/Desktop Audits) |

---

## 3. Signature Features

| ID | Feature Name | Description | Status |
|---|---|---|---|
| **SIG-A** | **Evidence Lens** | Transcript with highlighted candidate errors; clicking a span seeks audio and displays candidate card. | Verified (Audio Alignment, Interactive Spans) |
| **SIG-B** | **Syntax Fingerprint** | Radar/bar view of 8 category rates per 100 words, pre vs post overlay, observation flags. | Verified (8-Category Comparative Overlay) |
| **SIG-C** | **Hint Ladder Tutor** | L0 quote, L1 hint, L2 rule cue, L3 reveal + transfer check; logs attempt type. | Verified (Hint Ladder L0-L3, Self-Correction Logging) |
| **SIG-D** | **Reviewer Cockpit** | Keyboard shortcuts (A, R, E, U, N), audio player, AI-vs-human diff, inter-reviewer agreement ($\kappa$). | Verified (Cockpit Screen, Keyboard Flow, Kappa) |
| **SIG-E** | **Reproducibility Panel** | "How was this calculated?" drawer displaying formula, counts, denominators, and versions. | Verified (Full Provenance, Formulas, Version Hashes) |
| **SIG-F** | **Pilot Kit** | Gold-set evaluation page computing transcription WER and classification precision/recall/F1. | Verified (CLI & Evaluation Module) |
