# SyntaxLens Requirements Traceability Matrix (RTM)

This document tracks the mapping between the Software Requirements Specification (`docs/SRS.md`), architectural components, implementation files, and automated test suites.

## 1. Functional Requirements (FR-01 to FR-20)

| ID | Title & SRS Summary | Backend / DB Implementation | Frontend Implementation | Automated Tests |
|---|---|---|---|---|
| **FR-01** | **Authentication & RBAC**: Restrict participants to own data; researcher role isolation. | `app/api/auth.py`, `app/models/identity.py`, `app/core/security.py` | `src/app/(auth)/login/page.tsx`, `src/lib/auth.ts` | `tests/api/test_auth.py`, `tests/api/test_rbac.py` |
| **FR-02** | **Participant Management**: Create, import, deactivate, enforce unique IDs. | `app/api/participants.py`, `app/models/research.py` | `src/app/researcher/participants/page.tsx` | `tests/api/test_participants.py` |
| **FR-03** | **Consent Handling**: Display approved consent before recording; record version, status, timestamp. | `app/api/consent.py`, `app/models/consent.py` (Append-Only) | `src/app/(student)/consent/page.tsx` | `tests/api/test_consent.py`, `tests/db/test_immutability.py` |
| **FR-04** | **Audio Capture**: Record, playback, re-record before submission; presigned S3 storage keys. | `app/api/audio.py`, `app/services/storage.py` | `src/components/audio/AudioRecorder.tsx` | `tests/api/test_audio.py` |
| **FR-05** | **Assessment Task**: Configure standardized instructions, duration, topic pool, rubric version. | `app/models/assessment_task.py`, `app/api/tasks.py` | `src/app/(student)/assessment/page.tsx` | `tests/api/test_tasks.py` |
| **FR-06** | **Transcription**: Faithful transcription; preserve wording; capture timestamps; STTProvider. | `app/services/stt/`, `app/models/assessment.py` | `src/components/assessment/TranscriptView.tsx` | `tests/services/test_stt.py` |
| **FR-07** | **Error Analysis**: Detect candidate errors with span, correction, category, confidence, explanation. | `app/services/llm/`, `app/models/error_annotation.py` | `src/components/evidence/EvidenceLens.tsx` | `tests/services/test_error_analysis.py` |
| **FR-08** | **Error Categories**: Tense/aspect, SVA, word order, auxiliary, articles, prepositions, pronouns, other. | `app/schemas/categories.py`, `app/models/error_annotation.py` | `src/components/metrics/CategoryPill.tsx` | `tests/unit/test_categories.py` |
| **FR-09** | **Uncertainty Handling**: Flag acceptable variation, transcription error, or pending human review. | `app/models/error_annotation.py`, `app/schemas/review.py` | `src/components/reviewer/UncertaintyTag.tsx` | `tests/unit/test_uncertainty.py` |
| **FR-10** | **Human Review**: Accept/reject/edit candidate without overwriting original AI output. | `app/models/reviewer_decision.py`, `app/api/reviews.py` | `src/app/researcher/review/page.tsx` (Reviewer Cockpit) | `tests/api/test_reviews.py`, `tests/db/test_immutability.py` |
| **FR-11** | **Personalized Tutor**: Baseline priorities drive conversation; blinded pre/post tests. | `app/services/tutor/`, `app/api/tutor.py` | `src/app/(student)/tutor/page.tsx` | `tests/services/test_tutor.py`, `tests/api/test_blinding.py` |
| **FR-12** | **Feedback Sequence**: L0 quote, L1 hint, L2 rule cue, L3 reveal; independent transfer check. | `app/services/tutor/ladder.py` | `src/components/tutor/HintLadder.tsx` | `tests/services/test_hint_ladder.py` |
| **FR-13** | **Session History**: Track start/end, active duration, targeted skills, hint usage, outcomes. | `app/models/practice.py`, `app/api/practice.py` | `src/app/(student)/progress/page.tsx` | `tests/api/test_practice.py` |
| **FR-14** | **Recurrence Tracking**: Track error recurrence without double counting single utterance references. | `app/research/metrics.py`, `app/services/recurrence.py` | `src/components/progress/RecurrenceChart.tsx` | `tests/research/test_metrics.py` |
| **FR-15** | **Post-Test**: Equal condition assessment, alternate topic, rubric version parity. | `app/api/assessments.py`, `app/services/assessment.py` | `src/app/(student)/assessment/post/page.tsx` | `tests/api/test_post_test.py` |
| **FR-16** | **Progress Dashboard**: Category trends, pre/post rates, metric explanations, unreviewed warnings. | `app/api/dashboard.py`, `app/research/metrics.py` | `src/app/(student)/dashboard/page.tsx` | `tests/api/test_student_dashboard.py` |
| **FR-17** | **Research Dashboard**: Enrolment, adherence, completion, group filter, cohort comparison. | `app/api/research_dashboard.py` | `src/app/researcher/dashboard/page.tsx` | `tests/api/test_research_dashboard.py` |
| **FR-18** | **Data Export**: De-identified CSV with data dictionary and provenance metadata. | `app/api/export.py`, `app/services/export.py` | `src/app/researcher/export/page.tsx` | `tests/api/test_export.py` |
| **FR-19** | **Audit Trail**: Append-only log for login, consent, audio, reviewer edits, export, deletion. | `app/models/audit.py`, `app/core/audit.py` | `src/app/researcher/audit/page.tsx` | `tests/db/test_audit_immutability.py` |
| **FR-20** | **Configuration**: Versioned and frozen prompts, rubrics, topic pool, and scoring rules. | `app/models/configuration.py`, `app/api/config.py` | `src/app/researcher/config/page.tsx` | `tests/api/test_config.py` |

---

## 2. Signature Features

| Feature | Description | Implementation Path | Test Suite |
|---|---|---|---|
| **A. Evidence Lens** | Transcript with interactive candidate error spans, audio timeline seek, candidate card (phrase, correction, category, confidence). | `src/components/evidence/EvidenceLens.tsx`, `app/api/assessments.py` | `tests/e2e/evidence_lens.spec.ts` |
| **B. Syntax Fingerprint** | Radar/bar view of 8 category error rates per 100 words, pre vs post overlay, low-count warning, "not observed in this sample" hatching. | `src/components/metrics/SyntaxFingerprint.tsx`, `app/research/metrics.py` | `tests/research/test_metrics.py`, `tests/e2e/syntax_fingerprint.spec.ts` |
| **C. Hint Ladder Tutor** | L0 quote phrase, L1 hint question, L2 rule cue, L3 reveal. Log attempt type (independent, hint-assisted, revealed) + transfer check. | `app/services/tutor/ladder.py`, `src/components/tutor/HintLadder.tsx` | `tests/services/test_hint_ladder.py`, `tests/e2e/tutor_ladder.spec.ts` |
| **D. Reviewer Cockpit** | Audio + transcript + candidate queue, keyboard shortcuts (A, R, E, U, N), AI-vs-human diff, inter-reviewer agreement stats. | `src/app/researcher/review/page.tsx`, `app/api/reviews.py` | `tests/api/test_reviews.py`, `tests/e2e/reviewer_cockpit.spec.ts` |
| **E. Reproducibility Panel** | "How was this calculated?" drawer displaying formula, counts, denominators, rubric, prompt, model versions. | `src/components/metrics/ReproducibilityDrawer.tsx` | `tests/research/test_metrics.py` |
| **F. Pilot Kit** | Gold-set evaluation page: transcription WER, error classification precision/recall/agreement, time and cost per assessment. | `app/services/pilot/`, `src/app/researcher/pilot/page.tsx` | `tests/services/test_pilot.py` |

---

## 3. Non-Functional & Acceptance Criteria

| Area | Requirement | Enforcement Mechanism |
|---|---|---|
| **Append-Only DB** | AI outputs, transcripts, baselines, consents, audit logs cannot be updated or deleted. | PostgreSQL database triggers raising `RAISE EXCEPTION` on `UPDATE` or `DELETE`. Proved by `tests/db/test_immutability.py`. |
| **Pure Metrics** | All error rates, reductions, and statistics calculated by one pure Python module. UI never implements formulas. | `backend/app/research/metrics.py` with 100% unit test coverage. |
| **Server-Side Blinding**| No candidate feedback or error scores returned to student during active pre/post tests. | Response serializers check study phase and role before including error details. |
| **Zero-API Key Execution** | System must run fully with zero external API keys. | Mock deterministic STT (`MockSTTProvider`) and LLM (`MockLLMProvider`) enabled by default or flag. |
| **Security & Privacy** | ASVS L2 baseline: Argon2id, httpOnly/SameSite cookies, CSRF, rate-limiting, CSP, S3 presigned URLs, no PII to LLM. | FastApi middleware, separate `identity` / `research` Postgres schemas, presigned S3 URLs. |
| **Accessibility & UX** | WCAG 2.2 AA compliant, 360px+ responsive, dark/light mode, keyboard navigability, B1 CEFR plain copy. | Tailwind CSS, Radix UI primitives, automated axe-core accessibility checks in Playwright. |
