# SyntaxLens Comprehensive User Guides

> **Documentation Version:** 1.0 (Phase P16 Delivery)  
> **Target Audiences:** Participants (Learners), Researchers, and Expert Reviewers

---

# Part 1: Participant User Guide

Welcome to SyntaxLens! SyntaxLens is an intelligent research platform designed to help you practice and improve your spoken English syntax (grammar, word order, and sentence structures) in a supportive, conversational environment.

## 1. Onboarding & Informed Consent
1. Navigate to the SyntaxLens application URL in your web browser.
2. Sign in with the research credentials provided by your study coordinator.
3. Carefully review the **Informed Consent Form**. This explains how your voice recordings are used, your right to withdraw at any time, and how your privacy is protected.
4. Click **Accept & Continue** to complete your enrollment.

## 2. Taking the Pre-Test Assessment
1. From your **Student Home**, click **Start Pre-Test Assessment**.
2. Read the prompt topic displayed on the screen (you have 30 seconds of preparation time).
3. Click the **Record** button and speak naturally for 60 seconds.
4. When finished, you may listen back to your recording. If satisfied, click **Submit Recording**.
5. Your recording will be processed by our faithful transcription and syntactic assessment system. During the pre-test study window, your results remain blinded to maintain scientific fairness.

## 3. Conversational Tutoring with the Hint Ladder
If you are allocated to the tutoring group:
1. Click **Start Practice Session** from your dashboard.
2. The AI Tutor will open with a friendly conversational prompt focused on your target grammatical structures (e.g., past tense verbs or subject-verb agreement).
3. Speak or type your response. If a sentence has a syntactic deviation, the tutor guides you using the **Hint Ladder**:
   - **Level 0 (Echo Quote)**: Quotes your exact phrase so you can notice the error yourself.
   - **Level 1 (Guiding Question)**: Asks a targeted question to prompt your self-correction.
   - **Level 2 (Rule Cue)**: Gives a concise grammatical rule explanation.
   - **Level 3 (Reveal & Transfer)**: Models the correct phrasing and asks you to generate a brand new sentence to test your understanding.
4. Practice sessions automatically pause if you are inactive for more than 60 seconds.

## 4. Post-Test & Comparative Progress
1. At the end of the 3-week study period, complete the **Post-Test Assessment** (a 1-minute recording on a comparable topic).
2. Once verified by your researcher, view your **Syntax Fingerprint** to see your error rate reduction per 100 words across all 8 grammatical categories!

---

# Part 2: Reviewer Cockpit Guide

The Reviewer Cockpit is a high-efficiency interface for human annotators to verify AI-generated candidate syntactic deviations.

## 1. Navigating the Review Queue
1. Sign in with your Reviewer account and open `/admin/reviews`.
2. Filter candidate assessments by status (`unreviewed`, `in_review`, `verified`), error category (`TNS`, `SVA`, etc.), or participant group.
3. Click on any candidate to launch the **Reviewer Cockpit**.

## 2. Cockpit Layout & Controls
* **Top Bar**: Displays assessment metadata, word count, recording duration, and current verification status.
* **Waveform Audio Player**: Interactive playback; click anywhere on the waveform or transcript to seek directly to that spoken timestamp.
* **Side-by-Side Panel**:
  - **Left (AI Output)**: Exact character span, error category, candidate deviation, and AI explanation.
  - **Right (Reviewer Decision)**: Editable fields for your authoritative determination.

## 3. Keyboard Shortcuts
For rapid, ergonomic adjudication, use the following single-key shortcuts:
* `A` — **Accept** candidate as valid syntactic deviation.
* `R` — **Reject** candidate (false positive).
* `E` — **Edit** candidate (correct span boundaries, category code, or explanation).
* `U` — **Mark Uncertain** / Transcription Related (audio disfluency).
* `N` — **Mark Acceptable Variation** (acceptable Indian English dialect).

Every decision is saved as an **append-only** record. The original AI output is never overwritten.

---

# Part 3: Researcher & Administrator Guide

The Researcher Dashboard provides high-level cohort management, versioned research configuration, and cryptographic dataset exports.

## 1. Cohort & Adherence Monitoring
* Open `/admin/dashboard` to view the enrollment funnel (`invited -> consented -> pre-test -> practising -> post-test`).
* Inspect aggregate pre/post comparative statistics across intervention and control groups, computed strictly via the pure metrics module.
* Click on any participant to view their longitudinal event timeline and error recurrence patterns.

## 2. Research Configuration & Freezing
* Open `/admin/config` to manage rubrics, prompt versions, and equivalence task groups.
* **Freezing Protocol**: Once a study period begins, click **Freeze Rubric** or **Freeze Prompt**. Frozen configurations cannot be modified or deleted, guaranteeing scientific reproducibility.

## 3. De-Identified Data Export
* Open `/admin/export` to generate server-side research datasets.
* Select format (CSV or XLSX) and optional **Salted HMAC Participant Re-Keying**.
* Download includes the accompanying **Data Dictionary** (`DATA_DICTIONARY.csv`), derived from the exact same schema definition with 100% column parity.
* Elevated exports (with direct identifiers) require `RESEARCHER_ADMIN` credentials, an explicit IRB justification reason, and the `X-Confirm-Elevated: true` header.
