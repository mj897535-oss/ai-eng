# SyntaxLens Security Architecture & Threat Model (STRIDE)

> **Document Version:** 1.0 (Phase P15 Security Hardening)  
> **Classification:** Institutional Research Security & Privacy Specification  
> **Compliance Target:** OWASP ASVS Level 2, HIPAA Security Rule (Administrative/Technical Safeguards), GDPR / Right to be Forgotten

---

## 1. Executive Summary

SyntaxLens is an academic research platform evaluating AI-guided syntactic scaffolding for spoken English learners. Because the platform records, transcribes, and analyzes participant speech, it handles sensitive behavioral and biometric-adjacent data. This document outlines the institutional threat model, cryptographic boundaries, defensive controls, and operational guardrails.

---

## 2. STRIDE Threat Model

| STRIDE Category | Threat Description | Attack Vector / Asset | Mitigating Control & Verification |
|---|---|---|---|
| **Spoofing** | Adversary attempts to authenticate as a participant, reviewer, or administrator. | Session tokens, password reset endpoints, JWT/Cookie handling. | HttpOnly, SameSite=Lax/Strict session cookies; CSRF double-submit token verification; timing-safe password hash verification via `argon2id` / `bcrypt`; lockout after 5 consecutive failed attempts. |
| **Tampering** | Malicious alteration of baseline assessments, transcripts, rubric versions, or audit logs. | PostgreSQL `research` and `identity` schemas; S3 speech audio objects. | Append-only database triggers preventing `UPDATE` or `DELETE` on `audit_logs`, `error_annotations`, `reviewer_decisions`, and frozen rubrics; S3 object versioning with write-once access roles. |
| **Repudiation** | Researcher or reviewer denies taking an action (e.g., overriding AI candidate or accessing raw audio). | Reviewer Cockpit sign-off; participant data export. | `research.audit_logs` records `(actor_id, role, action, record_type, record_id, outcome, ip_hash, user_agent, timestamp)` for every single access, review decision, or export event. Immutable via DB triggers. |
| **Information Disclosure** | Leakage of participant identity (names, emails) joined with non-standard syntactic deviations or raw speech audio. | Research export CSVs; third-party AI provider requests; S3 bucket. | Schema isolation: `identity.users` has zero foreign keys to transcripts. AI requests contain zero names or canary tokens. S3 bucket blocks public access; audio access requires short-lived presigned URLs (15 min expiry). Salted HMAC re-keying on export. |
| **Denial of Service** | Flooding the audio ingestion or LLM assessment pipeline to exhaust research compute credits. | `/assessments/pre/submit`, `/tutor/turn`. | Strict rate-limiting (30 requests/minute per IP/user); circuit breakers with exponential backoff on STT/LLM pipelines; idempotent submission keys preventing double processing. |
| **Elevation of Privilege** | Participant attempting to access Reviewer Cockpit, Research Settings, or unmasked exports. | API authorization middleware; `/admin/*` routes. | Strict hierarchical RBAC (`PARTICIPANT`, `REVIEWER`, `RESEARCHER_ADMIN`). Elevated exports require `RESEARCHER_ADMIN` + explicit IRB reason + `X-Confirm-Elevated: true` confirmation header. |

---

## 3. Cryptographic & Operational Architecture

```mermaid
flowchart TD
    Client["Participant / Researcher Client"] -->|HTTPS + HSTS + CSP| APIGateway["FastAPI Gateway (TLS 1.3)"]
    
    subgraph Boundary["Institutional Security Boundary"]
        APIGateway -->|RBAC & Rate Limit| Auth["Session & CSRF Validator"]
        Auth --> IdentityDB[("identity.users (Isolated PII)")]
        Auth --> ResearchDB[("research.* (Append-Only Assessments)")]
        
        APIGateway -->|Presigned PUT (15m)| S3["Private Storage (AES-256 SSE)"]
        
        APIGateway --> Gate["Provider Privacy Gate"]
        Gate -->|Canary Inspection: No PII| AIProvider["Enterprise AI Provider (Zero-Retention)"]
    end
```

### 3.1 Network & Transport Hardening
* **HSTS**: `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` enforced on all responses.
* **Content Security Policy (CSP)**: `default-src 'self'; script-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';`.
* **Framing & MIME Protection**: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
* **Cookie Protection**: `HttpOnly`, `SameSite=Lax`, and `Secure` (in production).

### 3.2 Storage Encryption at Rest
* **Database**: PostgreSQL encrypted at rest using LUKS / AWS KMS EBS volume encryption.
* **Audio Storage**: S3/MinIO bucket configured with Server-Side Encryption (`AES256` or `aws:kms`). Public bucket policies and ACLs are disabled at the cloud root.

### 3.3 Least-Privilege Database Roles
* **`app_rw` Role**: Granted `SELECT`, `INSERT` on research tables; granted `UPDATE` only on mutable participant status flags.
* **Append-Only Triggers**: Database triggers explicitly abort any `UPDATE` or `DELETE` statement against `research.audit_logs`, `research.error_annotations`, and `research.reviewer_decisions`.
