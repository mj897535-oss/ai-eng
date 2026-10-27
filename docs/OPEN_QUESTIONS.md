# SyntaxLens Open Research & Protocol Questions

In accordance with Rule 1 (SRS Fidelity), every ambiguity, protocol dependency, and specification gap identified in SRS Section 16 and during architectural design is catalogued here alongside the engineering default implemented in the system.

---

## 1. Final Sample Size & Group Allocation (SRS §16.1, §16.2)
* **SRS Context**: The PhD proposal contains differing sample-size descriptions; the developer document specifies an intended target of 120 participants. Whether there is an active control group or observational single-cohort is to be confirmed.
* **Conservative Default**:
  - The application is hard-parameterized to support a cohort ceiling of 120 active participants (configurable via environment variable `MAX_COHORT_SIZE`).
  - The schema supports two groups: `INTERVENTION` (AI Tutor enabled) and `CONTROL` (self-practice / assessment-only mode).
  - Allocation is assigned by the researcher upon onboarding and is **blinded from participants** in student-facing API responses.
* **Status**: Implemented in schema (`research.study_group`); researcher can toggle or assign groups without code modifications.

---

## 2. Control Group Intervention Workflow (SRS §16.2)
* **SRS Context**: What does the control/comparison group experience between pre-test and post-test? Do they receive standard text reading, unassisted conversation, or no practice?
* **Conservative Default**:
  - If a participant belongs to `CONTROL`, the "Start Practice" button navigates to an unguided spontaneous reading/recording practice module without AI Hint Ladder corrections, preserving time-on-task parity without delivering syntactic scaffolding.
* **Status**: Awaiting researcher confirmation; control UI module structured as a placeholder flag.

---

## 3. Intervention Duration & Practice Adherence Targets (SRS §16.3)
* **SRS Context**: What is the required intervention duration (e.g., 2 weeks vs 4 weeks) and daily practice goal (e.g., 10 minutes vs 20 minutes)?
* **Conservative Default**:
  - The system tracks `active_duration_seconds` per session. Default benchmark targets are set to 15 minutes per session, 5 sessions per week, over 3 weeks (total target: 225 active minutes).
  - The Researcher Dashboard reports raw active minutes and adherence percentages against this benchmark without locking out participants who practice more or less.
* **Status**: Parameterized in `research.practice_sessions`.

---

## 4. Assessment Topic Pool, Randomization & Preparation Time (SRS §16.4)
* **SRS Context**: Are topics assigned deterministically, randomly from a pool, or chosen by the learner? What preparation time is enforced?
* **Conservative Default**:
  - Random assignment without replacement from a validated pool of JAM (Just-A-Minute) spontaneous speech topics calibrated to CEFR B1.
  - Standardized countdown: Exactly **30 seconds preparation time** (microphone locked), followed by **60 seconds speaking time** with automatic recording stop.
  - Pre-test and post-test draw from distinct, difficulty-paired topic sub-banks (e.g. Pre: "A Memorable Journey", Post: "A Memorable Event") to prevent memorized transfer.
* **Status**: Implemented in `research.assessment_tasks`.

---

## 5. Coding Manual, Overlapping Errors & Single-Utterance Counting (SRS §7, §16.5)
* **SRS Context**: When a sentence contains multiple syntactic errors (e.g. *"Yesterday he go to market"* contains both Tense and SVA), how are they counted?
* **Conservative Default**:
  - Each distinct non-overlapping character span is recorded as an independent error record.
  - The denominator is strictly the total word count of the faithful transcript computed by deterministic tokenization (`app/research/metrics.py::count_words`).
  - Error rate is $(N_{\text{errors}} / N_{\text{words}}) \times 100$.
  - In practice sessions (FR-14), successive hints for the same utterance share an `utterance_fingerprint` to prevent double-counting.
* **Status**: Fully implemented and unit-tested in `app/research/metrics.py`.

---

## 6. Pre-Test Feedback Blinding Timing (SRS §6 FR-11, §16.6)
* **SRS Context**: May participants view their pre-test error report immediately, or only after the post-test and research intervention conclude?
* **Conservative Default**:
  - **Strict Server-Side Blinding**: During active pre-test and intervention periods, the participant API returns only recording confirmation and word count. Candidate error spans, categories, explanations, and scores are scrubbed server-side.
  - Full reports are accessible to researchers and reviewers immediately, and unlocked for participants only upon explicit researcher unblinding after post-test completion.
* **Status**: Enforced in API response schemas and query filters.

---

## 7. PII Scope, Access Roles & Audio Retention Window (SRS §13, §16.7)
* **SRS Context**: What personal data is justifiable, who can access raw audio, and how long will voice recordings be retained?
* **Conservative Default**:
  - Full name and email reside exclusively in `identity.users`.
  - Research records (`research.participants`) store only pseudonymous code (`SL-2026-xxx`), age, mother tongue (L1), school medium, and location.
  - Raw audio is accessible only via short-lived (15 min) signed URLs to authenticated researchers and assigned reviewers.
  - Retention default: Audio keys are flagged for archival/deletion 12 months post-study completion, subject to university ethics confirmation.
* **Status**: Implemented in database schema and storage adapter.

---

## 8. Permitted Cloud Providers vs Local On-Premise Execution (SRS §13, §16.8)
* **SRS Context**: Which commercial STT and LLM providers are approved under institutional data-privacy guidelines?
* **Conservative Default**:
  - The system defaults to `STT_PROVIDER=mock` and `LLM_PROVIDER=mock`, allowing the entire application, database, and test suite to run on-premise with zero external data egress.
  - Provider adapters for Deepgram/Whisper and OpenAI/Anthropic are isolated behind interfaces with strict PII scrubbing if cloud providers are approved.
* **Status**: Mock providers fully tested; cloud adapters sit behind abstract classes.

---

## 9. Approved Statistical Analysis Plan & Outcome Metrics (SRS §7, §16.9)
* **SRS Context**: What statistical tests and outcome measures will the supervisor accept for the final thesis?
* **Conservative Default**:
  - The pure metrics engine computes raw counts, denominators, error rate per 100 words, absolute reduction, and relative reduction.
  - In accordance with SRS §7, when pre-test error rate is 0, relative reduction is reported as `None` / `"N/A (zero baseline)"` to prevent division-by-zero distortion.
  - All dashboard and export outputs append the approved scientific disclaimer: *"Descriptive change observed in speech samples. Absence of an error structure does not prove permanent acquisition or causal impact."*
* **Status**: Verified in `app/research/metrics.py`.

---

## 10. Acceptable Language Variation vs Syntactic Deviations (Indian English)
* **SRS Context**: Certain syntactic constructions in Indian English (e.g. stative verbs in progressive aspect: *"I am understanding the concept"*, or topicalization: *"In Mumbai, I stayed"*) may be considered acceptable regional usage rather than errors.
* **Conservative Default**:
  - The scoring rubric includes category `OTH` (Other / Uncertain / Variation) and an `is_acceptable_variation` flag.
  - The AI model is explicitly prompted NOT to mark regional dialect features as errors. Uncertain candidates are routed to the Reviewer Cockpit for human verification.
* **Status**: Prompt guidelines and rubric schema support variation tagging.

---

## 11. Right to Withdraw Data Handling (SRS §13)
* **SRS Context**: If a participant withdraws consent mid-study, how is their append-only research data handled?
* **Conservative Default**:
  - A new consent row with `status = 'withdrawn'` is appended to `research.consents`.
  - The participant is flagged `is_withdrawn = true` in `research.participants`.
  - All subsequent research exports, dashboard aggregations, and pilot analytics instantly filter out the withdrawn participant's data. Historical audit records remain intact for compliance verification.
* **Status**: Implemented in schema and export filter design.

---

## 12. Inter-Reviewer Disagreement Resolution Protocol (SRS §10, FR-10)
* **SRS Context**: When multiple reviewers evaluate the same candidate error and disagree (e.g. one accepts, one rejects), how is consensus established?
* **Conservative Default**:
  - Reviewer decisions are stored as individual rows. If two reviewers disagree, the item remains flagged as `DISPUTED` in the Reviewer Cockpit.
  - A Lead Researcher / Admin account must cast an authoritative consensus decision before the record is marked as verified for tutor priority injection.
* **Status**: Implemented in reviewer workflow schema.
