# SyntaxLens Research & Technical Risk Register

This document identifies the top 12 scientific, technical, and operational risks associated with building and deploying the SyntaxLens platform for PhD research, along with concrete engineering mitigations.

---

## Risk Summary Matrix

| Risk ID | Risk Domain | Severity | Likelihood | Mitigation Summary |
|---|---|---|---|---|
| **RSK-01** | STT Accuracy on Indian English | **High** | **High** | Pilot benchmark calibration; verbatim preservation; decoupled STT interface with local Whisper option. |
| **RSK-02** | LLM Hallucinated Errors / Over-Correction | **High** | **High** | Mandatory Reviewer Cockpit audit; prompt constraints barring style correction; confidence thresholds. |
| **RSK-03** | Server-Side Blinding Leaks | **Critical** | Medium | Server-side query sanitization stripping candidate annotations for student roles during active test periods. |
| **RSK-04** | Error Recurrence Double Counting | **High** | Medium | Utterance SHA-256 fingerprinting and `parent_event_id` linking across Hint Ladder iterations (FR-14). |
| **RSK-05** | Third-Party Provider Privacy & PII Egress | **Critical** | Low | Dual-schema database architecture; zero PII sent to AI APIs; only pseudonymous tokens forwarded. |
| **RSK-06** | Cloud API Cost & Rate Limit Overruns | Medium | Medium | Strict token capping; Redis queue throttling; deterministic mock adapters for development and testing. |
| **RSK-07** | Audio Upload Failures on Mobile Networks | **High** | **High** | In-browser blob caching in IndexedDB; chunked presigned S3 uploads; automatic exponential backoff retry. |
| **RSK-08** | Mutation of Original Baseline AI Output | **Critical** | Low | PostgreSQL append-only triggers blocking `UPDATE` and `DELETE`; reviewer decisions recorded as child rows. |
| **RSK-09** | Participant Attrition & Missing Post-Tests | **High** | **High** | Adherence monitoring dashboard; automated progress nudges; separate reporting of incomplete cases. |
| **RSK-10** | Inter-Reviewer Disagreement & Coding Drift | Medium | Medium | Reviewer Cockpit tracking Cohen's Kappa in real-time; lead researcher tie-breaking consensus role. |
| **RSK-11** | In-Browser Audio Capture Permissions | Medium | Medium | Pre-test microphone diagnostic check; visible waveform level meter; explicit fallback recording instructions. |
| **RSK-12** | Over-Claiming Acquisition or Causality | **High** | Medium | Pure metrics engine hard-coding approved scientific disclaimers; "not observed in sample" UI hatching. |

---

## Detailed Risk Profiles & Mitigation Strategies

### RSK-01: STT Accuracy Degradation on Indian English Accents
* **Impact**: Commercial STT models trained on General American or British English often mis-transcribe Indian English phonological features (e.g. retroflex consonants, syllable-timed rhythm, unaspirated plosives) or silently "auto-correct" syntactic deviations into standard English.
* **Mitigations**:
  1. STT selection sits behind the `STTProvider` interface; the platform runs a 15-participant pilot benchmark computing Word Error Rate (WER) using the Pilot Kit before cohort enrollment.
  2. Prompts instruct STT to preserve verbatim acoustic wording without applying grammatical normalization.
  3. Reviewers can flag candidate errors as `transcription_related` in the Reviewer Cockpit.

---

### RSK-02: LLM Hallucinated Errors and False Positives on Regional Usage
* **Impact**: Language models may flag acceptable Indian English idioms (e.g. topicalization: *"In Pune I was staying"*, or stative verbs in progressive aspect: *"I am understanding"*) as errors, or hallucinate non-existent syntactic violations.
* **Mitigations**:
  1. Prompts explicitly define the 8 target categories and instruct the model to flag uncertainty rather than force a classification.
  2. Category `OTH` allows marking acceptable language variation.
  3. Every automated finding is classified as a `candidate` until an independent linguist verifies it in the Reviewer Cockpit.

---

### RSK-03: Server-Side Blinding Leaks During Pre/Post Tests
* **Impact**: If candidate error details, suggested corrections, or error rates leak to the participant client during the pre-test, experimental blinding is corrupted, invalidating pre/post intervention comparisons.
* **Mitigations**:
  1. Server-side response schemas automatically prune candidate error spans, category codes, and metrics when the requesting user is a participant in an active assessment window.
  2. Automated tests (`tests/api/test_blinding.py`) assert that student tokens receive zero error fields in response payloads.

---

### RSK-04: Double Counting of Single Utterance Errors Across Hints (FR-14)
* **Impact**: If a learner struggles with a single sentence and progresses through L0, L1, and L2 hints, recording each step as an independent error would artificially inflate their error count and distort recurrence analytics.
* **Mitigations**:
  1. When an error is identified, an `utterance_fingerprint` (SHA-256 hash of normalized text) is generated.
  2. Successive hints reference the initial event's `event_id` via `parent_event_id`.
  3. The metrics engine counts distinct utterance hashes rather than raw event rows when calculating recurrence rates.

---

### RSK-05: Third-Party Provider Privacy & PII Egress Violations
* **Impact**: Forwarding participant names, emails, or biometric voice metadata to external AI providers could breach institutional ethics approvals (IRB) and privacy laws.
* **Mitigations**:
  1. Strict dual-schema architecture: `identity` (PII) is completely isolated from `research` (observations).
  2. AI providers receive strictly anonymous session tokens and speech text; direct identifiers are never sent across the trust boundary.
  3. The entire application runs natively with deterministic mock adapters without external API keys.

---

### RSK-06: Cloud API Cost and Rate Limit Overruns
* **Impact**: Spontaneous speech transcription and multi-turn conversational tutoring across 120 participants could exceed research grant budgets or trigger provider rate limits during peak usage.
* **Mitigations**:
  1. Structured JSON output format with strict `max_tokens` limits (average turn capped at 150 tokens).
  2. Background worker with Redis rate-limiting smooths outbound API calls.
  3. Cost-per-assessment tracking integrated into the Pilot Kit.

---

### RSK-07: Audio Upload Failures on Unstable Mobile Connections
* **Impact**: Participants recording on campus Wi-Fi or mobile cellular networks may experience network drops during audio upload, resulting in lost recordings and student frustration.
* **Mitigations**:
  1. Audio blobs are held in browser client storage (IndexedDB) until upload verification is confirmed by the server.
  2. Uploads use presigned direct S3 PUT requests with client-side exponential backoff retry.
  3. Submission is idempotent; re-sending the same upload token prevents duplicate database rows.

---

### RSK-08: Mutation of Original Baseline AI Output or Audit Records
* **Impact**: Accidental modification or deletion of raw model outputs, transcripts, or consent timestamps would compromise research auditability and scientific reproducibility.
* **Mitigations**:
  1. Database-enforced immutability via PostgreSQL stored procedures and triggers.
  2. Attempts to execute `UPDATE` or `DELETE` on `consents`, `assessments`, `error_annotations`, or `audit_logs` raise database-level exceptions.
  3. Automated tests prove that modification attempts fail.

---

### RSK-09: Participant Attrition & Missing Post-Test Data
* **Impact**: High drop-out rates between pre-test and post-test could reduce statistical power below the 120-participant threshold.
* **Mitigations**:
  1. Researcher Dashboard features a live adherence funnel tracking pre-test completion, weekly practice minutes, and post-test eligibility.
  2. Export pipeline clearly segregates completed per-protocol cases from intention-to-treat / incomplete cases.

---

### RSK-10: Inter-Reviewer Disagreement & Coding Drift
* **Impact**: Multiple human reviewers applying inconsistent subjective standards to syntactic error classifications could inject noise into research findings.
* **Mitigations**:
  1. Reviewer Cockpit continuously computes and displays inter-reviewer agreement statistics (Cohen's Kappa $\kappa$).
  2. Items with conflicting reviewer decisions are flagged as `DISPUTED` for Lead Researcher consensus resolution.

---

### RSK-11: Browser Audio API Compatibility & Permission Denials
* **Impact**: Incompatible audio codecs or microphone permission denials on various browser versions (Safari, Chrome, Firefox) could block recording.
* **Mitigations**:
  1. Audio recording component checks `navigator.mediaDevices.getUserMedia` availability upon page load with helpful recovery prompts.
  2. Audio recording uses standard `audio/webm;codecs=opus` with fallback to `audio/mp4` / `audio/wav`.
  3. Pre-test diagnostic step allows participants to verify playback before beginning the timed task.

---

### RSK-12: Over-Claiming Acquisition or Causality in Results Presentation
* **Impact**: Phrasing results as "student mastered subject-verb agreement" or "AI intervention caused a 40% improvement" violates scientific rigor and SRS exclusions.
* **Mitigations**:
  1. UI copy guidelines strictly enforced: terms like "mastered" or "caused" are prohibited.
  2. Charts use hatching for "not observed in this sample".
  3. Every comparative report appends the approved scientific disclaimer regarding descriptive change.
