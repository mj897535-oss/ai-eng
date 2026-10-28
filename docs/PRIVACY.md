# SyntaxLens Research Privacy Specification

> **Data Classification, Flow Inventory, Retention Periods, and Right-to-be-Forgotten**  
> **Document Version:** 1.0 (Phase P15 Security & Privacy Hardening)

---

## 1. Data Classification Inventory

| Data Class | Example Elements | Storage Location | Sensitivity | Retention Period | De-Identification Rule |
|---|---|---|---|---|---|
| **Direct PII** | Full name, email address, password hash, IP hash. | `identity.users`, `identity.identity_audit_logs` | Highly Confidential | Purged immediately upon participant withdrawal or study close + 30 days. | Isolated in `identity` schema; never joined directly with transcripts or error rows. |
| **Biometric / Speech Audio** | Raw audio recordings (`.webm`, `.opus`, `.mp4`). | Private S3 Bucket (`audio/{code}/*`) | Confidential | Deleted upon study completion or participant withdrawal. | Storage keys use random suffix pseudonyms. Expire presigned URLs in 15 minutes. |
| **Faithful Transcripts** | Verbatim transcript text, word timestamps, disfluencies. | `research.assessments.transcript`, `words_json` | Research Confidential | Preserved for research validation unless participant requests complete scrub. | Associated exclusively with pseudonymous `research_code` (e.g. `SL-2026-0042`). |
| **Syntactic Annotations** | Error category (`TNS`, `SVA`, etc.), char offsets, reviewer decisions. | `research.error_annotations`, `reviewer_decisions` | Research Data | Retained permanently in anonymized research dataset for open science. | Fully de-identified. All public exports replace codes with salted HMAC hashes. |
| **Audit Logs** | Actor ID, role, action, record ID, timestamp, outcome. | `research.audit_logs` | Institutional Record | 7 years (IRB compliance mandate). | Append-only. Contains zero speech transcripts or audio content. |

---

## 2. Privacy-by-Design Data Flows

```mermaid
sequenceDiagram
    autonumber
    actor Participant as Participant
    participant App as SyntaxLens Web & API
    participant PrivateS3 as S3 Private Bucket
    participant Gate as Provider Privacy Gate
    participant STT_LLM as Approved AI Provider

    Participant->>App: Authenticates & provides informed consent
    App->>PrivateS3: Requests short-lived presigned PUT URL (15m expiry)
    PrivateS3-->>App: Signed URL with AES-256 header
    App-->>Participant: Uploads speech directly to storage (no server intermediary)
    
    App->>Gate: Evaluates outgoing payload for canary strings & PII
    Note over Gate: Rejects if provider unapproved or training opt-out unconfirmed
    Gate->>STT_LLM: Transcribes & evaluates syntax (Zero-Data-Retention tier)
    STT_LLM-->>App: Returns candidate error annotations
    App-->>Participant: Displays tutor hints or blinded assessment status
```

---

## 3. Provider Privacy Gate Requirements

1. **Mandatory Administrative Whitelist**: Only providers explicitly vetted and approved in the database privacy registry can receive participant audio or transcripts.
2. **Zero Data Retention Guarantee**: Commercial AI provider contracts must enforce zero-retention (ephemeral memory only).
3. **Model Training Opt-Out**: No speech transcripts, learner turns, or error annotations may be used by the foundation model vendor for model training or tuning.
4. **Jurisdictional Data Residency**: AI processing regions must match institutional IRB jurisdiction (e.g., US-only or EU-only regions).
5. **Automated Canary Testing**: Outgoing requests undergo regex PII scrubbing and canary token inspection. If a participant name or direct identifier is detected, the request is immediately halted and an alert is triggered.

---

## 4. Withdrawal & Right to be Forgotten Protocol

When a participant exercises their voluntary right to withdraw:
1. **Immediate Ingestion Halt**: All future audio recordings, assessment tasks, and tutor sessions are immediately locked.
2. **Audio Purge**: Raw audio files associated with the participant are deleted from the private S3 bucket.
3. **Identity Scrubbing**: In `identity.users`, the participant's name is replaced with `Withdrawn Participant [UUID]` and the email is scrambled (`withdrawn_[hash]@redacted.syntaxlens.local`).
4. **De-Identified Aggregate Preservation**: To maintain the integrity of peer-reviewed statistical power calculations, de-identified error counts may be retained where consented by the protocol; otherwise, transcript text is overwritten with `[PURGED_ON_WITHDRAWAL]`.
5. **Cryptographic Audit Row**: The purge action is logged to `research.audit_logs` with the executing actor ID and deletion counts.
