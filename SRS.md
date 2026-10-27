**SOFTWARE REQUIREMENTS SPECIFICATION**

**AI-Powered Spoken English Assessment ****&**** Personalised Learning App**

Developer handover document
Prepared for a PhD research project on syntactic deviations in spoken English
Target cohort: 120 participants (proposed; final protocol to be confirmed)
Version 1.0 | 27 October 2026

# 1. Purpose of this document

This document describes the proposed application, user journeys, features, data requirements, AI prompt behaviour, research metrics, security requirements and acceptance criteria. It is intended to help a software developer estimate, design, build and test the application.

Research basis: the supplied PhD proposal, “The Use of Artificial Intelligence Tools to Overcome Syntactic Deviations in Spoken English by Indian Speakers.” The proposal describes a pre-test/post-test approach using recorded spontaneous speech, AI-assisted practice, syntactic error classification and comparison of outcomes. The current request specifies a target of 120 users. This report treats 120 as the intended cohort, but the researcher and supervisor must confirm the final approved protocol.

# 2. Product overview

Build a responsive web application that allows participants to record spoken English, receive a baseline syntactic assessment, practise conversational English with an AI tutor tailored to their baseline results, and complete a post-test. A separate researcher dashboard should manage participants and compare assessment results.

| **User role** | **Purpose** | **Permissions** |
| --- | --- | --- |
| Participant / Student | Complete profile, pre-test, practice sessions and post-test; view own progress. | Own profile and learning records only. |
| Researcher / Administrator | Manage participants, review recordings/transcripts/errors, monitor participation, export research data. | Access based on approved research role; audit sensitive actions. |
| Independent Reviewer (optional) | Review uncertain transcripts or error classifications and annotate the result. | Only assigned records; cannot silently overwrite original AI output. |

# 3. Scope and boundaries

## Included in the first version (MVP)

Secure login and unique participant ID for up to 120 enrolled participants.

Participant profile fields requested in the research proposal/email.

Audio recording or upload for a standardised pre-test and post-test.

Speech-to-text transcription with timestamps where supported.

Candidate syntactic error detection, categorisation, correction suggestion and confidence/review flag.

AI conversational tutor that uses pre-test findings to personalise practice.

Practice session logging, recurring-error tracking and learner progress dashboard.

Researcher dashboard, review workflow and CSV export.

Basic group comparison and pre/post metrics using consistent calculation rules.

## Not included unless separately approved

A guarantee that AI will detect every grammatical error correctly.

Automated claims that a learner has permanently mastered a grammar structure.

Accent scoring, pronunciation scoring, vocabulary scoring or general English-proficiency certification.

Native iOS/Android apps; the recommended MVP is a responsive web app.

Public leaderboards or sharing students’ scores with other participants.

A final statistical analysis plan or ethics approval; these must be confirmed by the research team.

# 4. Main user workflow

Researcher creates/imports participant records and assigns a unique research ID.

Participant signs in, reviews the consent information and completes required profile fields.

Participant completes the pre-test: a standardised spontaneous speaking task, typically around one minute, under the approved protocol.

System stores the audio securely, creates a transcript, and generates candidate syntactic deviations using a fixed rubric version.

Uncertain cases are flagged for researcher/reviewer verification. Original AI output and reviewer decisions are both retained.

AI tutor uses verified pre-test priorities to conduct personalised conversations and exercises.

Each practice session logs duration, target grammar categories, feedback, hint use, attempts and independent corrections.

Participant completes the post-test using comparable conditions and a different topic of similar difficulty.

System compares pre-test and post-test error rates and category-level results, and the researcher exports anonymised data.

# 5. Participant profile and onboarding

| **Field** | **Required?** | **Notes** |
| --- | --- | --- |
| Participant ID | Yes | Unique pseudonymous research identifier; use as the primary research key. |
| Name | Protocol-dependent | Collect only if needed. Prefer separating identifying details from research records. |
| Age | Yes, if approved | Use age or age band according to the approved consent/protocol. |
| Mother tongue | Yes | Allow self-description; do not infer from location. |
| Medium of school education | Yes | For example, English, Marathi, Hindi, other. |
| Country / State / City | Yes, if approved | Collect only the geographic granularity justified by the study. |
| Consent status and timestamp | Yes | Record the approved consent version and date/time. |
| Study group | Researcher-managed | Control/comparison or AI-intervention group; hidden from participants if required by protocol. |

# 6. Functional requirements

| **ID** | **Requirement** |
| --- | --- |
| FR-01 Authentication | Participants must sign in securely. The system must restrict each participant to their own data and provide role-based researcher access. |
| FR-02 Participant management | Researchers can create, import, deactivate and view participant records. Duplicate IDs must be rejected. |
| FR-03 Consent | The app must present approved consent information before recording and store consent version, status and timestamp. |
| FR-04 Audio capture | Participants can record, listen back, re-record before submission, and submit audio. Show recording status and upload failures clearly. |
| FR-05 Assessment task | The researcher can configure standardised instructions, task duration, topic pool, permitted preparation time and rubric version. |
| FR-06 Transcription | Store a faithful transcript. Preserve original wording; do not silently fix grammar. Keep timestamps if the transcription service supports them. |
| FR-07 Error analysis | Produce candidate errors with original span, proposed correction, category, explanation, confidence and timestamp/span reference when possible. |
| FR-08 Error categories | At minimum support tense/aspect, subject–verb agreement, word order, auxiliary usage, articles, prepositions, pronouns and other/uncertain. |
| FR-09 Uncertainty handling | Allow an item to be marked uncertain, transcription-related, acceptable variation or requiring human review. Do not force an error label when evidence is insufficient. |
| FR-10 Human review | Reviewer can accept, reject, edit or recategorise a candidate. Preserve AI output, reviewer decision, reviewer ID and timestamps. |
| FR-11 Personalised tutor | The tutor uses approved pre-test findings to select conversational topics and practice targets. It should not show assessment feedback during a blinded pre-test/post-test. |
| FR-12 Feedback sequence | Tutor quotes the relevant phrase, gives a hint, invites self-correction, explains if needed, then asks for a new independent example. |
| FR-13 Session history | Record session start/end, active practice duration, skills targeted, attempts, hint level, outcomes and technical interruptions. |
| FR-14 Recurrence tracking | Track error categories and patterns across sessions without counting repeated references to the same single utterance as separate independent errors. |
| FR-15 Post-test | Run the same assessment workflow as pre-test with equivalent instructions/rubric and comparable task difficulty. |
| FR-16 Progress dashboard | Show practice history, category trends, pre/post rates and explanations of metrics. Mark all incomplete or unreviewed results. |
| FR-17 Research dashboard | Show enrolment, assessment completion, group allocation, missing data, intervention adherence and aggregated results. |
| FR-18 Export | Export de-identified participant-level assessment records and category counts to CSV. Keep a data dictionary for all columns. |
| FR-19 Audit trail | Record important events such as login, consent, audio submission, reviewer edits, export and record deletion. |
| FR-20 Configuration | Prompts, error rubric and scoring rules must be versioned and frozen for each study/assessment period. |

# 7. Assessment and error analysis rules

The assessment engine must be separate from the conversational tutor. Assessment results should be based on a fixed rubric and stored evidence, not on the tutor's informal impression of progress.

## Recommended error record fields

| **Field** | **Description** |
| --- | --- |
| assessment_id / participant_id | Links each finding to a specific participant and assessment. |
| audio_reference | Secure storage key; never a public URL. |
| transcript_span / timestamps | Original text and, where available, the corresponding audio location. |
| candidate_error | Exact phrase or construction under review. |
| suggested_correction | Proposed grammatical alternative. |
| category_code | TNS, SVA, WO, AUX, ART, PREP, PRO, OTH or an agreed expanded taxonomy. |
| explanation | Short explanation of the syntactic rule. |
| confidence / review_status | Model confidence or calibrated score if available; pending, accepted, rejected or edited. |
| reviewer_annotation | Human-reviewed classification and reason, kept separately from original model output. |
| rubric_version / model_version | Versions used to produce the assessment. |

## Core calculations

Error rate per 100 words = (number of assessable syntactic errors ÷ total words) × 100.

Absolute error-rate reduction = pre-test error rate − post-test error rate.

Relative reduction (%) = ((pre-test rate − post-test rate) ÷ pre-test rate) × 100, only when the pre-test rate is greater than zero.

Use the same word-counting, error-counting and coding rules at both time points. Specify how multiple errors in one sentence are counted. Report raw error counts and word totals as well as rates. If the pre-test rate is zero, relative reduction is undefined and should be shown as N/A.

A category not observed in a short post-test recording does not prove that the learner has permanently overcome it. Report 'not observed in this sample' where appropriate. A percentage reduction is descriptive and alone does not establish that AI caused the change.

# 8. Standardised AI prompt behaviour

## A. Pre-test prompt

Role: neutral spoken-English syntax assessor.

Collect the approved participant metadata and present the approved speaking task.

Do not teach, correct, hint or reveal errors during the assessment.

Transcribe faithfully and label candidate deviations with category, evidence, confidence and review status.

Flag unclear audio and acceptable language variation; do not guess.

## B. AI integration / tutor prompt

Role: supportive conversational tutor focused on syntactic accuracy.

Inputs: participant ID, verified pre-test summary, priority categories, previous practice history and learning objectives.

Use natural conversation and target one or two priority structures at a time.

Allow the learner to finish speaking, then provide a hint and opportunity for self-correction before giving the answer.

Ask for a new example to check transfer; log independent correction versus hint-assisted correction.

Do not alter official assessment scores. Avoid treating accent, pronunciation, vocabulary or acceptable regional usage as syntax errors.

## C. Post-test prompt

Assess the new recording independently using the same rubric and transcription conventions.

Do not coach during the post-test.

After scoring, compare against the original baseline and report rates, counts and category-level changes.

Keep baseline records immutable and preserve any reviewer corrections as separate annotations.

Do not claim permanent mastery or causal impact from one pre/post comparison alone.

# 9. Suggested screens

| **Screen** | **Main elements** |
| --- | --- |
| Login | Participant/researcher sign-in, password reset and privacy notice. |
| Consent & profile | Approved consent, participant ID and required demographic fields. |
| Student home | Pre-test status, next task, practice button, recent activity and progress. |
| Pre-test / Post-test | Instructions, topic/task, audio recorder, playback, submit and status. |
| Assessment report | Transcript, highlighted candidate errors, categories, corrections and uncertainty/review labels. Participant visibility controlled by protocol. |
| AI tutor | Conversation interface, microphone/text input, hint/correction cards and new-sentence practice. |
| Progress | Practice minutes, session history, repeated-error patterns and category trends. |
| Research dashboard | Cohort overview, group filters, completion status, review queue, aggregate comparisons and exports. |
| Research settings | Rubric versions, prompt versions, topic bank, roles and retention configuration. |

# 10. Suggested data model

| **Entity/table** | **Key fields (illustrative)** |
| --- | --- |
| users | id, login identifier, password hash/identity provider ID, role, active status, created_at |
| participants | participant_id, protected identity fields if required, age/age band, mother_tongue, school_medium, country, state, city, group_id, consent_id |
| consents | consent_id, participant_id, consent_version, status, timestamp, withdrawal timestamp |
| assessments | assessment_id, participant_id, type (pre/post), task_id, rubric_version, audio_key, transcript, word_count, status, model_version, timestamps |
| error_annotations | annotation_id, assessment_id, text span, timestamps, category, correction, explanation, confidence, AI status, reviewer decision |
| practice_sessions | session_id, participant_id, start/end, active_duration, tutor_prompt_version, session status |
| practice_events | event_id, session_id, target_category, learner phrase, feedback, hint level, correction outcome, reviewed status |
| tasks_topics | task_id, prompt text, difficulty/metadata, assessment version, topic assignment |
| audit_logs | actor_id, action, record type/ID, timestamp, outcome |
| model_prompt_versions | version_id, prompt type, prompt text, approved date, change notes |

The developer may refine the schema. Use stable IDs and foreign keys. Keep identifying information separate from de-identified research exports. Store audio in private object storage and keep only a storage key in the database.

# 11. Technology recommendation

| **Layer** | **Suggested option** | **Reason** |
| --- | --- | --- |
| Frontend | React / Next.js responsive web app | Works across desktop and mobile browsers; supports student and researcher portals. |
| Backend API | Python FastAPI or Django | Python ecosystem supports data processing and AI integration. |
| Database | PostgreSQL | Relational participant, assessment and event records. |
| Audio storage | Private object storage with encryption | Avoid storing large audio blobs or exposing recordings publicly. |
| Speech-to-text | Select a service after a pilot benchmark | Test Indian English speech, noise handling, timestamps, privacy and cost before selection. |
| AI tutor / analysis | An API-based language model with structured JSON output | Supports conversation, candidate error classification and explanations; outputs still require validation. |
| Charts | A standard web chart library | Visualise category trends and pre/post results. |
| Exports | CSV first; XLSX optional | Compatible with common research and statistical workflows. |

Do not hard-code one AI vendor into the business logic. Wrap speech and language-model services behind interfaces so the developer can switch providers if accuracy, privacy, pricing or availability requires it.

# 12. Non-functional requirements

Security: HTTPS, secure authentication, role-based access, least-privilege permissions and encrypted storage.

Privacy: collect only approved data; show consent and withdrawal process; set retention/deletion rules with the university.

Research integrity: immutable original AI outputs, versioned rubrics/prompts, auditable reviewer changes and reproducible calculations.

Reliability: clear retry handling for failed uploads/API calls; prevent duplicate submissions when users retry.

Accessibility: usable on mobile and desktop, readable text, keyboard navigation and clear recording instructions.

Performance: display upload/transcription/analysis states; do not leave the user unsure whether a recording was submitted.

Scalability: design for 120 participants plus researcher accounts, with capacity headroom and cost monitoring.

Data export: de-identify exports by default; restrict exports containing direct identifiers or raw audio.

# 13. Privacy, ethics and research safeguards

Obtain the required institutional ethics approval and informed consent before collecting research recordings.

Explain how audio, transcripts, demographic information and AI-provider processing will be used.

Do not send names or unnecessary personal identifiers to an AI provider; use participant IDs wherever practical.

Verify provider data-retention, model-training, processing-location and contractual terms before choosing a service.

Provide a defined retention and deletion process, including withdrawal handling, subject to the approved protocol.

Restrict researcher access and log access to recordings and exports.

Treat automated classifications as candidate annotations, not infallible facts; human-review a sample to estimate accuracy.

Do not use participant data for unrelated model training or product purposes without appropriate approval and consent.

# 14. Acceptance criteria / definition of done

A participant can log in and access only their own records.

A consented participant can complete and submit a pre-test recording and see its status.

The system stores the original audio, faithful transcript, word count and rubric/model versions.

Each candidate error has a category, evidence, proposed correction and review status; uncertain cases can be flagged.

The researcher can review, accept, reject or amend a candidate without erasing the original model result.

The tutor uses baseline priorities and logs sessions, target skills, hints and correction outcomes.

The post-test can be linked to the same participant's pre-test and uses the approved rubric version.

The dashboard calculates error rates and changes from stored counts and denominators using documented formulas.

CSV export includes a data dictionary and is de-identified by default.

Access control, consent handling, audit logging, backup and deletion/retention workflows are tested.

A pilot is completed before all 120 participants are enrolled; transcript and error-classification quality is reviewed by the research team.

# 15. Suggested pilot and quality checks

Before cohort-wide use, run a small pilot approved by the research team. Include a range of speech styles and recording conditions representative of the intended participants. Human reviewers should compare a sample of transcripts and syntactic classifications against the audio. Measure transcription quality, error-classification precision/recall or agreement where feasible, time per assessment, API failures and cost per participant. Fix systematic problems before locking the workflow for the main study.

# 16. Questions the researcher must confirm before development

Final sample size and group allocation: the supplied proposal contains differing sample-size descriptions; the current target is 120, but the approved protocol must govern.

Whether the study includes a control/comparison group and what that group does.

Intervention duration and expected daily practice time.

Whether assessment topics are randomly assigned from an approved topic bank and what preparation time is allowed.

Exact coding manual, rules for counting multiple errors and whether all findings require human review.

Whether participants can see pre-test feedback immediately or only after the intervention begins.

What personal data are necessary, who can access it, and how long audio will be retained.

Which speech-to-text and language-model providers are permitted by institutional ethics/privacy requirements.

Which statistical analysis and outcome measures the supervisor approves.

# 17. Deliverables expected from the developer

Working responsive web application with participant and researcher roles.

Source code repository and setup/deployment instructions.

Database schema and migrations.

API documentation and environment configuration template (no secrets committed).

Versioned pre-test, tutor and post-test prompt configuration.

Researcher dashboard and de-identified CSV export.

Automated tests for access control, calculations and assessment workflow.

Deployment guide, backup/restore plan, error logging and basic administrator guide.

Pilot test report covering accuracy, known limitations, cost and unresolved issues.

# Appendix A — Example interaction

Student says: “He go to college every day.”

| **Stage** | **Expected system behaviour** |
| --- | --- |
| Transcription | Store the spoken wording faithfully: “He go to college every day.” |
| Candidate classification | Subject–verb agreement candidate; suggested correction: “He goes to college every day.” |
| Tutor hint | “For he/she/it in the simple present, what ending do we usually add to the verb?” |
| Self-correction | Record the student's attempt and whether it was independent or hint-assisted. |
| Transfer check | Ask for a new sentence, e.g. about what a friend does every morning. |
| Research record | Log category, attempt, hint level and outcome. Do not change the formal pre/post score from this practice event. |

# Appendix B — Source and assumptions

Source document reviewed: “Ph.D. Research Proposal — The Use of Artificial Intelligence Tools to Overcome Syntactic Deviations in Spoken English by Indian Speakers,” supplied in this conversation. The proposal describes recorded JAM-style pre/post speaking tasks, AI-supported practice, syntactic error categories and pre/post error-rate comparison. The target of 120 participants and the software features in this report reflect the current product request and implementation recommendations; they should not be mistaken for already approved amendments to the PhD protocol.

AI Spoken English App — Developer Requirements | Page