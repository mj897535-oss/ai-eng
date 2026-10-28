# SyntaxLens Requirements Traceability Matrix (RTM)

This matrix maps every Functional Requirement (FR-01..FR-20), Non-Functional Requirement (SRS §12–13), Acceptance Criterion (SRS §14), and Signature Feature to its planned implementation phase, planned verification tests, and current status.

---

## 1. Functional Requirements (FR-01 to FR-20)

| ID | Requirement Summary | Planned Phase | Planned Tests | Status |
|---|---|---|---|---|
| **FR-01** | **Authentication & RBAC**: Secure sign-in; participants access only own data; role-based researcher and reviewer permissions. | **Phase 3** (Auth, RBAC, Audit) | `tests/api/test_auth.py`, `tests/api/test_rbac_matrix.py` | Verified (Phase 3 Matrix) |
| **FR-02** | **Participant Management**: Create, batch import, deactivate, view participants. Enforce unique pseudonymous IDs (e.g. `SL-2026-xxx`). | **Phase 4** (Participants & Onboarding) | `tests/api/test_participant_management.py`, `tests/api/test_csv_bulk_import.py` | Verified (Phase 4 Services & API) |
| **FR-03** | **Consent Handling**: Present approved consent before recording; record consent version, status, and timestamp. Append-only. | **Phase 4** (Participants & Onboarding) | `tests/api/test_consent_gating.py`, `tests/api/test_consent_withdrawal.py` | Verified (Append-Only Gating Tested) |
| **FR-04** | **Audio Capture**: Record, listen back, re-record before submission; presigned S3 upload; upload failure handling. | **Phase 6** (Audio Capture & Upload) | `tests/api/test_audio_recording.py` | Verified (Phase 6 Bulletproof Recorder) |
| **FR-05** | **Assessment Task**: Standardized instructions, task duration (60s), prep time (30s), topic bank, rubric version. | **Phase 5** (Versioned Config) | `tests/api/test_research_settings.py`, `tests/unit/test_topic_seed_assignment.py` | Verified (Phase 5 Equivalence Pairs & Seeds) |
| **FR-06** | **Transcription**: Faithful transcript preserving errors; retain timestamps; decoupled STTProvider. | **Phase 7** (Transcription Pipeline) | `tests/services/test_stt_pipeline.py`, `tests/api/test_stt_endpoints.py`, `tests/services/test_stt_mock.py` | Verified (Deterministic MockSTT, Verbatim Preserved, Pipeline & Metrics) |
| **FR-07** | **Error Analysis**: Candidate deviations with span, correction, category, confidence, and explanation. | **Phase 8** (Assessment Engine) | `tests/services/test_error_analysis.py`, `tests/services/test_llm_mock.py` | Verified (Decoupled LLMProvider, Non-LLM Post-Validation, Golden Set Tests) |
| **FR-08** | **Error Categories**: 8 categories (TNS, SVA, WO, AUX, ART, PREP, PRO, OTH). Pure metrics integration. | **Phase 8** (Assessment Engine) | `tests/research/test_metrics.py`, `tests/api/test_research_settings.py`, `tests/services/test_error_analysis.py` | Verified (Phase 5 Taxonomies & Phase 8 Golden Fixtures) |
| **FR-09** | **Uncertainty Handling**: Flag items as acceptable variation, transcription error, or needing human review. | **Phase 8** (Assessment Engine) | `tests/services/test_error_analysis.py`, `tests/services/test_llm_mock.py` | Verified (Dialect/Uncertainty Flags & Review Auto-Routing) |
| **FR-10** | **Human Review**: Reviewer can accept, reject, edit, or recategorize. Model outputs never overwritten. | **Phase 9** (Review Workflow) | `tests/services/test_review_cockpit.py`, `app/services/review.py`, `app/models/assessment.py` | Verified (Append-only Decisions, Derived View, Immutability Triggers) |
| **FR-11** | **Personalised Tutor**: Uses verified baseline priorities; strict server-side blinding during pre/post tests. | **Phase 10** (Tutor Engine) | `tests/services/test_tutor_ladder.py`, `app/services/tutor.py`, `app/api/v1/tutor.py` | Verified (Verified Baseline Gating, Zero Assessment Write Access) |
| **FR-12** | **Feedback Sequence**: Hint ladder (L0 quote, L1 hint, L2 rule, L3 reveal); independent transfer check. | **Phase 10** (Tutor Engine) | `tests/services/test_tutor_ladder.py`, `app/services/llm/mock.py` | Verified (Hint Ladder State Machine & Transfer Check Verified) |
| **FR-13** | **Session History**: Track start/end, active practice duration, targeted skills, hint usage, outcomes. | **Phase 11** (Practice Logging) | `tests/services/test_practice_recurrence.py`, `app/services/tutor.py`, `app/api/v1/tutor.py` | Verified (Active Timing, Idle Gaps Excluded, Technical Interruptions) |
| **FR-14** | **Recurrence Tracking**: Track error categories across sessions without double counting repeated hints for one utterance. | **Phase 11** (Practice Logging) | `tests/services/test_practice_recurrence.py`, `app/research/metrics.py`, `app/models/practice.py` | Verified (SHA-256 Fingerprint, Zero Double-Counting Guarantee, Pure Metrics) |
| **FR-15** | **Post-Test**: Equal condition assessment, alternate topic, rubric version parity, linked to pre-test. | **Phase 12** (Post-Test & Comparative) | `tests/research/test_comparative_metrics.py`, `app/research/metrics.py`, `app/api/v1/analysis.py` | Verified (Equivalence Group Pairing, Pure Metrics Engine, Immutability) |
| **FR-16** | **Progress Dashboard**: Category trends, pre/post rates, metric explanations, unreviewed warnings. | **Phase 13** (Dashboards) | `tests/api/test_dashboards.py`, `apps/web/src/app/dashboard/progress/page.tsx` | Verified (Student Home, Progress Screen, Plain-Language Explainer, Blinding Gating) |
| **FR-17** | **Research Dashboard**: Enrolment, completion status, group allocation, missing data, adherence, aggregates. | **Phase 13** (Dashboards) | `tests/api/test_dashboards.py`, `apps/web/src/app/admin/dashboard/page.tsx` | Verified (Cohort Funnel, Distributions via Pure Metrics, 120-Part Capacity/Cost Panel) |
| **FR-18** | **Data Export**: De-identified CSV with data dictionary and provenance metadata. | **Phase 14** (Export & Data Dict) | `tests/api/test_export.py`, `tests/unit/test_csv_generation.py` | Planned |
| **FR-19** | **Audit Trail**: Append-only log for login, consent, audio submission, review decisions, export, deletion. | **Phase 3** (Auth, RBAC, Audit) | `tests/db/test_audit_immutability.py`, `tests/api/test_auth.py`, `tests/api/test_rbac_matrix.py` | Verified (Triggers & Logging) |
| **FR-20** | **Configuration**: Versioned and frozen prompts, rubrics, topic pool, and scoring rules per study period. | **Phase 5** (Versioned Config) | `tests/api/test_research_settings.py`, `tests/db/test_frozen_immutability.py` | Verified (Phase 5 DB Triggers & Settings UI) |

---

## 2. Non-Functional Requirements (SRS §12–13)

| ID | Category & Requirement Summary | Planned Phase | Planned Tests | Status |
|---|---|---|---|---|
| **NFR-SEC-01** | **Transport & Header Security**: HTTPS, OWASP ASVS L2 security headers (CSP, HSTS, X-Frame-Options DENY, nosniff). | **Phase 15** (Security & Retention) | `tests/api/test_health.py::test_security_headers_present` | Verified (Phase 1 Baseline) |
| **NFR-SEC-02** | **Credential Storage**: Argon2id password hashing, secure session management, httpOnly+SameSite cookies. | **Phase 3** (Auth, RBAC, Audit) | `tests/api/test_auth.py`, `app/core/security.py`, `app/core/session.py` | Verified (Phase 3 Baseline) |
| **NFR-SEC-03** | **Audio Storage Protection**: Private S3 bucket, no public URLs, short-lived (15 min) presigned URLs. | **Phase 6** (Audio Capture & Upload) | `tests/api/test_audio_recording.py` | Verified (Phase 6 Storage & Gated Access) |
| **NFR-PRIV-01** | **PII & Research Isolation**: Dual-schema architecture (`identity` vs `research`). No PII transmitted to STT or LLM. | **Phase 15** (Security & Retention) | `tests/services/test_sanitizer.py`, `tests/db/test_schema_isolation.py` | Verified in Schema & DB Migrations |
| **NFR-PRIV-02** | **Right to Withdraw**: Protocol-compliant consent withdrawal setting `is_withdrawn = true` and excluding from exports. | **Phase 4** (Participants & Onboarding) | `tests/api/test_consent_withdrawal.py` | Verified (Phase 4 Workflow) |
| **NFR-RES-01** | **Append-Only Research Records**: Database triggers block `UPDATE` and `DELETE` on research tables. | **Phase 1 / Phase 2** | `tests/db/test_immutability.py` (4 tests) | Verified (DB Triggers Tested) |
| **NFR-RES-02** | **Pure Calculation Module**: Single source of truth for all metrics. UI never calculates formulas. | **Phase 1 / Phase 12** | `tests/research/test_metrics.py` (18 unit tests) | Verified (100% pure unit tests) |
| **NFR-REL-01** | **Upload & Submission Idempotency**: Idempotency keys prevent duplicate assessments or sessions on retries. | **Phase 6** (Audio Capture & Upload) | `tests/api/test_audio_recording.py` | Verified (Phase 6 Idempotency Engine) |
| **NFR-REL-02** | **Zero-API Key Testability**: Complete test suite and local development run without external API keys. | **Phase 2** (Foundations & CI) | `tests/services/test_stt_mock.py`, `test_llm_mock.py` | Verified (Deterministic Mocks) |
| **NFR-ACC-01** | **Accessibility (WCAG 2.2 AA)**: Keyboard navigable, skip links, visible focus, 360px+ responsive, dark/light mode. | **Phase 16** (QA & Pilot Kit) | `tests/e2e/accessibility.spec.ts` (axe-core) | Planned (Layout baseline in P1) |
| **NFR-PERF-01** | **Transparent Pipeline Status**: Clear user-visible feedback for upload, transcription, and analysis states. | **Phase 6 / Phase 8** | `tests/e2e/test_status_polling.spec.ts` | Planned |
| **NFR-SCAL-01** | **Cohort Scalability**: Support 120 enrolled participants with concurrent recording and tutoring. | **Phase 16** (QA & Pilot Kit) | `tests/load/test_concurrent_sessions.py` | Planned |

---

## 3. Acceptance Criteria (§14 Definition of Done)

| ID | Acceptance Criterion (§14) | Planned Phase | Planned Verification Method | Status |
|---|---|---|---|---|
| **AC-01** | Participant signs in and accesses only their own records. | **Phase 3** | Integration test checking cross-user data access rejection. | Verified (`test_rbac_matrix.py`) |
| **AC-02** | Consented participant submits pre-test recording and tracks status. | **Phase 6** | `tests/api/test_audio_recording.py` | Verified (Phase 6 Pre/Post Screens & Polling) |
| **AC-03** | System stores original audio, faithful transcript, word count, versions. | **Phase 7** | `tests/services/test_stt_pipeline.py`, `tests/api/test_stt_endpoints.py` | Verified (Audio key, Verbatim Transcript, Word-Count Rule, Immutability Trigger) |
| **AC-04** | Each candidate error has category, evidence, correction, review status. | **Phase 8** | `tests/services/test_error_analysis.py`, Pydantic Schema & PostValidationLayer | Verified (Schema Adherence, Exact Span Offsets, Immutability) |
| **AC-05** | Researcher reviews, accepts, rejects, edits without erasing AI data. | **Phase 9** | `tests/services/test_review_cockpit.py`, `app/services/review.py` | Verified (Append-only Decision Rows, Derived View, Immutability) |
| **AC-06** | Tutor uses baseline priorities and logs sessions, hints, outcomes. | **Phase 10 & 11** | `tests/services/test_tutor_ladder.py`, `tests/services/test_practice_recurrence.py` | Verified (Priority Personalization, Hint Ladder, Active Timing & Recurrence) |
| **AC-07** | Post-test links to same participant's pre-test under approved rubric. | **Phase 12** | `tests/research/test_comparative_metrics.py` | Verified (Equivalence group linkage, rubric parity, immutable baseline) |
| **AC-08** | Dashboard calculates error rates and reductions via pure module. | **Phase 13** | Unit test verifying dashboard returns pure module outputs. | Verified (`tests/api/test_dashboards.py`, Zero Drift Guarantee) |
| **AC-09** | CSV export includes data dictionary and is de-identified by default. | **Phase 14** | Test verifying CSV output contains zero names/emails and has data dictionary. | Planned |
| **AC-10** | Access control, consent handling, audit logging, retention tested. | **Phase 15** | Comprehensive security and retention test suite. | Partially Verified (Access & Audit in P3) |
| **AC-11** | Pilot completed before 120 enrollment; WER and accuracy reviewed. | **Phase 16** | Pilot Kit benchmark evaluation execution. | Pure metrics ready |

---

## 4. Signature Features

| ID | Feature Name | Description | Planned Phase | Planned Verification Tests | Status |
|---|---|---|---|---|---|
| **SIG-A** | **Evidence Lens** | Transcript with highlighted candidate errors; clicking a span seeks audio and displays candidate card. | **Phase 8 & 9** | `tests/services/test_error_analysis.py`, `EvidenceLens.tsx`, `AssessmentReportPage` | Verified (Audio Alignment, Interactive Spans, Candidate Card, Participant Gating) |
| **SIG-B** | **Syntax Fingerprint** | Radar/bar view of 8 category rates per 100 words, pre vs post overlay, with "not observed in this sample" hatching. | **Phase 12 & 13** | `tests/research/test_comparative_metrics.py`, `apps/web/src/app/assessment/[id]/comparative/page.tsx` | Verified (8-Category Comparative Overlay & Observation Labels) |
| **SIG-C** | **Hint Ladder Tutor** | L0 quote, L1 hint, L2 rule cue, L3 reveal + transfer check; logs attempt type. | **Phase 10** | `tests/services/test_tutor_ladder.py`, `TutorChat.tsx`, `app/api/v1/tutor.py` | Verified (Hint Ladder L0-L3, Self-Correction Logging, Appendix A E2E) |
| **SIG-D** | **Reviewer Cockpit** | Keyboard shortcuts (A, R, E, U, N), audio player, AI-vs-human diff, inter-reviewer agreement ($\kappa$). | **Phase 9** | `tests/services/test_review_cockpit.py`, `ReviewerCockpit.tsx`, `app/api/v1/reviews.py` | Verified (Cockpit Screen, Keyboard Flow, Kappa Calculation, Audit Trail) |
| **SIG-E** | **Reproducibility Panel** | "How was this calculated?" drawer displaying formula, counts, denominators, and versions. | **Phase 12 & 13** | `tests/research/test_comparative_metrics.py`, `apps/web/src/app/assessment/[id]/comparative/page.tsx` | Verified (Full Provenance, Formulas, Effective Sets, Version Hashes) |
| **SIG-F** | **Pilot Kit** | Gold-set evaluation page computing transcription WER and classification precision/recall/F1. | **Phase 16** | `tests/research/test_metrics.py`, `tests/services/test_pilot.py` | Metrics Verified |
