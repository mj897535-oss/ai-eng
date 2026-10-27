# SyntaxLens Phased Implementation Plan

This implementation plan details the 16 ordered phases required to build, test, and verify SyntaxLens against `docs/SRS.md` and research integrity guidelines.

---

## Phase 2: Foundations, Environment & CI Pipeline

* **Goal**: Establish continuous integration, containerized multi-service orchestration, quality gates (ruff, mypy strict, tsc strict, pytest), and automated testing pipelines.
* **Tasks**:
  1. Validate `docker-compose.yml` for local service bringing up (PostgreSQL 16, MinIO, Redis, Backend, Worker, Frontend).
  2. Implement GitHub Actions / local CI workflow checking `ruff check`, `mypy --strict`, Next.js `tsc --noEmit`, and `pytest`.
  3. Configure MinIO bucket auto-provisioning container (`syntaxlens-audio`) with private access policies.
  4. Implement database migration verification scripts testing forward and rollback operations.
* **Tests**:
  - `tests/db/test_migrations.py`: Test migration up and down cycles.
  - `tests/test_ci.py`: Verification that all lint and typecheck scripts exit with code 0.
* **Done Criteria**:
  - Single command `docker compose up` starts all 6 containers with healthchecks green.
  - CI pipeline executes ruff, mypy strict, tsc strict, and pytest with 100% pass rate.

---

## Phase 3: Authentication, RBAC & Audit Trail (FR-01, FR-19)

* **Goal**: Implement secure, role-based authentication using Argon2id, httpOnly cookies, CSRF protection, and append-only audit logging.
* **Tasks**:
  1. Build `identity.users` authentication service (Argon2id password hashing, JWT generation, secure cookie handling).
  2. Implement RBAC middleware with distinct roles: `student`, `researcher`, `reviewer`, `admin`.
  3. Build FastAPI authentication endpoints: `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me`.
  4. Implement append-only research audit logging decorator recording actor ID, action, resource, IP, and timestamp.
  5. Build Next.js login screen with WCAG 2.2 AA compliant form controls, visible error alerts, and remember-me.
* **Tests**:
  - `tests/api/test_auth.py`: Login success, bad password rejection, lockout after 5 failed attempts.
  - `tests/api/test_rbac.py`: Student cannot access researcher endpoints; reviewer cannot alter user roles.
  - `tests/api/test_audit.py`: Verify authentication events write to `identity.identity_audit_logs`.
* **Done Criteria**:
  - User can sign in, receive secure httpOnly session cookies, and be redirected by role.
  - Audit log captures all login and access events.
  - Zero PII leaked in token payloads.

---

## Phase 4: Participants, Consent, Profile & Batch Import (FR-02, FR-03)

* **Goal**: Implement participant management, demographic onboarding, append-only consent signing, and researcher CSV batch import.
* **Tasks**:
  1. Build participant registration and demographic profile API (`/api/v1/participants/profile`).
  2. Implement consent presentation and signing API (`/api/v1/consent/sign`, `/api/v1/consent/withdraw`).
  3. Build researcher batch participant CSV import endpoint enforcing unique `research_code` generation (`SL-2026-xxx`).
  4. Build student onboarding UI (informed consent disclosure, demographic form: L1, medium of schooling, age).
  5. Build researcher participant management view with filter by study group and withdrawal status.
* **Tests**:
  - `tests/api/test_participants.py`: Duplicate research code rejection, demographic validation.
  - `tests/api/test_consent.py`: Append-only consent verification, withdrawal status toggle.
  - `tests/unit/test_csv_import.py`: Valid and malformed CSV import handling.
* **Done Criteria**:
  - Participants can sign consent, complete demographic onboarding, and receive a pseudonymous research ID.
  - Researcher can upload a 120-participant CSV and allocate study groups (`intervention` vs `control`).

---

## Phase 5: Versioned Configuration (Rubric, Prompts, Topic Bank) (FR-05, FR-20)

* **Goal**: Implement researcher configuration management to freeze rubrics, prompts, and standardized speaking tasks per study period.
* **Tasks**:
  1. Build configuration API for rubrics, prompts, and task topics (`/api/v1/config/...`).
  2. Implement database freezing enforcement (records flagged `is_frozen = true` reject updates).
  3. Seed validated JAM speaking topics with 30s prep and 60s speaking duration.
  4. Build researcher configuration view showing active rubric version, prompt templates, and topic pool.
* **Tests**:
  - `tests/api/test_config.py`: Verify frozen rubric cannot be mutated.
  - `tests/unit/test_topic_allocation.py`: Test random topic assignment without replacement.
* **Done Criteria**:
  - Rubric (`v1.0-jam-phd`) and prompts (`v1.0-tutor-ladder`) are versioned and locked in the database.
  - Researcher dashboard verifies all active configuration hashes.

---

## Phase 6: Audio Capture & Secure Upload Pipeline (FR-04)

* **Goal**: Build accessible, robust in-browser audio recording with re-recording, playback, and presigned private S3 upload.
* **Tasks**:
  1. Build accessible `AudioRecorder` React component using MediaRecorder API with audio level meter and countdown timers (30s prep, 60s speaking).
  2. Implement presigned S3 upload URL generation endpoint (`/api/v1/audio/upload-url`) with checksum validation.
  3. Implement upload confirmation and retry mechanism for mobile network interruptions.
  4. Ensure audio files are stored in private bucket with short-lived (15 min) access URLs.
* **Tests**:
  - `tests/api/test_audio.py`: Presigned URL generation, key format validation, size limit checks.
  - `tests/e2e/test_audio_recording.spec.ts`: Playwright recording simulation, playback review, and submission.
* **Done Criteria**:
  - Participant can record 60 seconds of spontaneous speech, listen back, re-record, and submit.
  - Audio binary resides securely in private object storage; storage key is stored in database.

---

## Phase 7: Speech-to-Text Transcription Pipeline (FR-06)

* **Goal**: Implement background transcription worker using the decoupled `STTProvider` interface with word-level timestamps.
* **Tasks**:
  1. Connect background worker (Redis + RQ) to audio processing queue.
  2. Implement `STTProvider` integration with deterministic `MockSTTProvider` and real adapter support (Whisper / Deepgram).
  3. Implement faithful verbatim transcript storage: preserve grammar deviations, capture word-level start/end timestamps.
  4. Expose processing status endpoint (`/api/v1/assessments/{id}/status`) returning `QUEUED`, `TRANSCRIBING`, `COMPLETED`, or `FAILED`.
* **Tests**:
  - `tests/services/test_stt.py`: Verbatim preservation test, timestamp alignment test.
  - `tests/worker/test_transcription_job.py`: Job retry on transient failure, idempotent execution.
* **Done Criteria**:
  - Audio submission automatically triggers transcription job.
  - Faithful transcript with word timestamps is stored in `research.assessments`.

---

## Phase 8: Assessment Engine & Error Categorization (FR-07, FR-08, FR-09)

* **Goal**: Implement automated candidate syntactic deviation detection, taxonomy classification (8 categories), and confidence scoring.
* **Tasks**:
  1. Implement `LLMProvider` analysis worker generating candidate errors adhering to `research.error_annotations`.
  2. Map findings to the 8 standard categories: `TNS`, `SVA`, `WO`, `AUX`, `ART`, `PREP`, `PRO`, `OTH`.
  3. Implement uncertainty tagging (`is_acceptable_variation`, `unclear_audio`, `requires_review`).
  4. Implement **Evidence Lens** backend data provider returning character spans, timestamps, and explanations.
  5. Enforce **Server-Side Blinding**: Participant endpoints return 0 error details during pre-test active phase.
* **Tests**:
  - `tests/services/test_error_analysis.py`: Validate 8 categories detection on standard benchmark utterances.
  - `tests/api/test_blinding.py`: Assert that student API requests during active assessment return zero error spans or scores.
* **Done Criteria**:
  - Candidate errors appended to `research.error_annotations` with confidence and timestamps.
  - Server-side blinding strictly prevents participant feedback leakage.

---

## Phase 9: Human Review Workflow & Reviewer Cockpit (FR-10, Signature Feature D)

* **Goal**: Build the Reviewer Cockpit allowing independent linguists to verify, accept, reject, or edit candidate errors without mutating AI data.
* **Tasks**:
  1. Build Reviewer API (`/api/v1/reviews/queue`, `/api/v1/reviews/decide`).
  2. Implement `research.reviewer_decisions` child row creation referencing `annotation_id`.
  3. Build **Reviewer Cockpit** web UI:
     - Audio player synced to transcript spans.
     - Candidate error queue with keyboard shortcuts (`A` accept, `R` reject, `E` edit, `U` uncertain, `N` next).
     - AI-vs-human diff view.
     - Live inter-reviewer agreement statistics (Cohen's Kappa).
* **Tests**:
  - `tests/api/test_reviews.py`: Review decision recording, verification that AI output is unchanged.
  - `tests/e2e/test_reviewer_cockpit.spec.ts`: Keyboard shortcut execution and decision persistence.
* **Done Criteria**:
  - Reviewer can audit 10 candidate errors in under 3 minutes using keyboard shortcuts.
  - Original AI records remain untouched in the database.

---

## Phase 10: AI Conversational Tutor & Hint Ladder (FR-11, FR-12, Signature Feature C)

* **Goal**: Implement the pedagogical tutor utilizing verified pre-test priorities and 4-step Hint Ladder scaffolding.
* **Tasks**:
  1. Build Tutor API (`/api/v1/tutor/turn`, `/api/v1/tutor/session/start`).
  2. Implement Hint Ladder state machine:
     - **L0**: Quote the exact student phrase.
     - **L1**: Ask a targeted hint question.
     - **L2**: State the grammatical rule cue.
     - **L3**: Reveal the natural form + require transfer sentence.
  3. Prevent tutor from accessing or altering official assessment scores.
  4. Build accessible student Chat / Speaking Tutor interface with hint cards and audio playback.
* **Tests**:
  - `tests/services/test_hint_ladder.py`: Step progression from L0 through L3.
  - `tests/api/test_tutor_isolation.py`: Prove tutor execution cannot write to `research.assessments`.
* **Done Criteria**:
  - Student conducts interactive conversation addressing verified priority errors.
  - Hint Ladder provides structured support without premature answer leakage.

---

## Phase 11: Practice Logging & Recurrence Tracking (FR-13, FR-14)

* **Goal**: Log granular tutoring events and track error recurrence across sessions without double-counting repeated hints.
* **Tasks**:
  1. Implement `practice_events` logger tracking feedback level, attempt type (`independent`, `hint_assisted`, `revealed`), and transfer outcome.
  2. Implement `utterance_fingerprint` generation and `parent_event_id` linking to satisfy FR-14 de-duplication.
  3. Build student Progress page showing active practice minutes, sessions completed, and targeted structures.
* **Tests**:
  - `tests/api/test_practice_logging.py`: Event persistence and attempt classification.
  - `tests/research/test_recurrence.py`: Prove that 3 hints for 1 sentence count as 1 error event.
* **Done Criteria**:
  - Longitudinal practice logs stored with precise durations and attempt categories.
  - Single utterances receiving multiple hints are de-duplicated in recurrence reporting.

---

## Phase 12: Post-Test Assessment & Pure Metrics Engine (FR-15, SRS §7)

* **Goal**: Execute post-test assessment under identical rubric conditions and run the Pure Metrics Engine for comparative research reporting.
* **Tasks**:
  1. Build Post-Test workflow with difficulty-matched alternate JAM topic.
  2. Implement comparative assessment pipeline linking participant pre-test to post-test.
  3. Integrate `app/research/metrics.py`:
     - Calculate pre-test and post-test error rates per 100 words.
     - Calculate absolute error-rate reduction.
     - Calculate relative reduction with strict zero-baseline protection (`None` / `"N/A"`).
     - Attach mandatory scientific disclaimer.
* **Tests**:
  - `tests/api/test_comparative_pipeline.py`: Pre-to-post calculation consistency.
  - `tests/research/test_metrics.py`: 100% pure unit test coverage for comparative rules.
* **Done Criteria**:
  - Post-test scored identically to pre-test.
  - Pre vs Post comparison metrics generated purely by backend module without floating-point artifacts.

---

## Phase 13: Student & Researcher Dashboards (FR-16, FR-17, Signature Features B & E)

* **Goal**: Deliver intuitive, accessible dashboards for students (progress & feedback) and researchers (cohort adherence & comparisons).
* **Tasks**:
  1. Build **Syntax Fingerprint** component (radar and bar charts showing 8 category error rates per 100 words with "not observed in this sample" hatching).
  2. Build **Reproducibility Panel** ("How was this calculated?" drawer displaying formula, counts, denominators, and prompt/rubric hashes).
  3. Build Student Dashboard: practice history, category trends, unblinded report (if approved by protocol).
  4. Build Researcher Dashboard: 120-participant enrollment funnel, group comparison (`intervention` vs `control`), adherence metrics, unreviewed queue count.
* **Tests**:
  - `tests/api/test_dashboards.py`: Dashboard data payload verification.
  - `tests/e2e/test_dashboards.spec.ts`: Chart rendering, keyboard navigation, and drawer toggling.
* **Done Criteria**:
  - Dashboards clearly visualize category distributions without claiming permanent mastery or causation.
  - Every metric has an accessible reproducibility drawer explaining its calculation.

---

## Phase 14: De-Identified Data Export & Data Dictionary (FR-18)

* **Goal**: Implement one-click de-identified research CSV export with an integrated data dictionary for thesis statistical analysis.
* **Tasks**:
  1. Build export service generating participant-level and category-level assessment CSVs (`/api/v1/export/csv`).
  2. Enforce strict de-identification: direct identifiers (names, emails) are completely omitted; only pseudonymous `research_code` is exported.
  3. Exclude withdrawn participants (`is_withdrawn = true`).
  4. Generate automated Markdown / PDF Data Dictionary detailing every column, data type, coding rule, and denominator.
* **Tests**:
  - `tests/api/test_export.py`: Export generation, verify zero PII in CSV rows, verify data dictionary integrity.
* **Done Criteria**:
  - Researcher can download analysis-ready CSV file compatible with R / SPSS / Python.
  - Export accompanied by complete column data dictionary.

---

## Phase 15: Security, Privacy, Retention & Disaster Recovery (SRS §12, §13)

* **Goal**: Hardening application security to OWASP ASVS L2, enforcing retention/deletion rules, and validating disaster recovery backups.
* **Tasks**:
  1. Implement rate limiting on authentication and AI execution endpoints using Redis.
  2. Configure strict Content Security Policy (CSP), CORS, and cookie flags (`Secure`, `httpOnly`, `SameSite=Lax/Strict`).
  3. Implement data retention and right-to-be-forgotten administrative utility.
  4. Write automated database backup and restore validation script (`scripts/backup_restore.sh`).
* **Tests**:
  - `tests/security/test_security_headers.py`: Automated OWASP security header audit.
  - `tests/security/test_rate_limiting.py`: Request throttling verification under burst traffic.
  - `tests/security/test_backup_restore.py`: Automated dump and restore cycle verifying trigger persistence.
* **Done Criteria**:
  - OWASP ASVS L2 security baseline verified.
  - Automated database backup and restore script tested and documented.

---

## Phase 16: Pilot Kit, End-to-End QA & Documentation (SRS §14, §15, Signature Feature F)

* **Goal**: Deploy the Pilot Kit benchmarking tool, execute full end-to-end accessibility and functional test suites, and produce final thesis documentation.
* **Tasks**:
  1. Build **Pilot Kit** evaluation suite (`/researcher/pilot`):
     - Calculates transcription Word Error Rate (WER) against gold transcripts.
     - Calculates syntactic error classification Precision, Recall, and F1.
     - Computes average API latency and cost per assessment.
  2. Execute Playwright end-to-end test suite across mobile (360px) and desktop viewports.
  3. Run automated WCAG 2.2 AA accessibility audit using `@axe-core/playwright`.
  4. Finalize administrator and researcher deployment guides.
* **Tests**:
  - `tests/e2e/test_full_participant_journey.spec.ts`: Complete flow from onboarding to post-test.
  - `tests/e2e/test_accessibility_axe.spec.ts`: Zero automated WCAG 2.2 AA violations.
* **Done Criteria**:
  - Pilot Kit benchmarking validated on gold speech sample.
  - Full application ready for PhD cohort enrollment.
