# SyntaxLens Open Research & Protocol Questions

In accordance with Rule 1 (SRS Fidelity), any ambiguity, protocol dependency, or specification gap is catalogued here alongside the conservative engineering decision implemented in the system. All decisions are designed to protect research integrity without prematurely narrowing future protocol choices.

---

## 1. Participant Cohort and Group Allocation (SRS §16.1, §16.2)
* **Question**: The PhD proposal mentions various sample sizes; the SRS specifies an intended cohort of 120. Is the allocation 1:1 between AI-intervention and control (e.g., 60/60), or observational single-cohort? What does the control group experience?
* **Conservative Choice**: The system enforces a configurable cohort model with an initial target of 120 participants. Group assignment supports `INTERVENTION` (AI Tutor enabled) and `CONTROL` (standard practice or assessment-only mode). Allocation is hidden server-side from participants during pre- and post-tests to preserve experimental blinding.
* **Status**: Conservative default implemented in schema (`research.study_group`); researcher can toggle or assign groups without code changes.

---

## 2. Counting Multiple Errors in a Single Utterance (SRS §7, §16.5)
* **Question**: When a single sentence or clause contains multiple syntactic deviations (e.g., *"Yesterday he go to college and buy fruits"* contains two tense deviations), how are they aggregated in the denominator?
* **Conservative Choice**:
  - Each non-overlapping candidate span is recorded as an independent error record.
  - The denominator is strictly the total word count of the transcript computed by a deterministic whitespace/token boundary algorithm.
  - Rate is computed strictly as $(N_{\text{errors}} / N_{\text{words}}) \times 100$.
  - Repeated mentions of the same utterance in feedback loops do not increment the error count (enforced per FR-14).
* **Status**: Implemented in `backend/app/research/metrics.py`.

---

## 3. Pre-Test Feedback Blinding (SRS §6 FR-11, §16.6)
* **Question**: Should participants see their pre-test error report immediately after recording, or only after the entire study/intervention is finished?
* **Conservative Choice**: Absolute server-side blinding. During pre-test and post-test active windows, endpoints returning participant view models filter out `candidate_errors`, `category_code`, and scoring metrics. Only recording confirmation status and word count are returned to the participant. The full report is accessible only to the researcher until the researcher explicitly unblinds the participant.
* **Status**: Enforced in API response schemas and repository queries.

---

## 4. Personally Identifiable Information (PII) Separation (SRS §5, §16.7)
* **Question**: How strictly must participant identity (name, email) be segregated from research transcripts and syntactic findings?
* **Conservative Choice**: Complete database schema isolation.
  - Schema `identity`: contains `users` (credentials, email, hashed password, role).
  - Schema `research`: contains `participants` (keyed by pseudonymous UUID `research_id`, demographic fields, group), `assessments`, `error_annotations`, and `practice_sessions`.
  - Research records store *zero* direct PII (no email, no real names). AI providers only ever receive anonymous session tokens and transcript text.
* **Status**: Implemented in database migrations.

---

## 5. Definition of Undefined Relative Reduction (SRS §7)
* **Question**: When a participant has 0 baseline errors in pre-test, what should relative reduction display?
* **Conservative Choice**: Formula states: $\text{Relative Reduction} = \frac{\text{Pre} - \text{Post}}{\text{Pre}} \times 100$. When $\text{Pre} = 0$, relative reduction is mathematically undefined. The pure metrics module returns `None` (`null` in JSON), and the UI renders `"N/A (zero baseline)"` with an informational tooltip explaining that division by zero is avoided.
* **Status**: Implemented in `backend/app/research/metrics.py` with 100% test coverage.

---

## 6. Retention and Right to Withdraw (SRS §13, §16.7)
* **Question**: If a participant withdraws consent, how is their data handled given that research audit logs and assessments are append-only?
* **Conservative Choice**: A consent record can transition to `WITHDRAWN` with a timestamp. The participant's record is marked `is_withdrawn = true`, instantly excluding all their assessments from research exports, dashboard analytics, and cohort statistics. Raw research data is retained in a locked state for research auditability according to institutional ethics guidelines.
* **Status**: Implemented in consent state machine and export filter logic.
