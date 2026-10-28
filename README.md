# SyntaxLens Research Platform

> **Research-Grade Spoken English Syntactic Assessment and Pedagogical Tutoring System**  
> Evaluates AI-guided syntactic scaffolding for adult spoken English learners in randomized controlled trial (RCT) environments.

---

## 🌟 Key Features & Signature Capabilities

* **Evidence Lens (Signature Feature A)**: Interactive transcript aligned with speech audio waveforms. Click candidate error spans to seek audio playback and view side-by-side linguistic classifications.
* **Syntax Fingerprint (Signature Feature B)**: Comparative radar and distribution overlays showing pre-test vs. post-test syntactic error rates per 100 words across 8 standardized categories.
* **Hint Ladder AI Tutor (Signature Feature C)**: Conversational tutoring utilizing a 4-tier scaffolding ladder (L0 quote &rarr; L1 guiding question &rarr; L2 rule cue &rarr; L3 model reveal + transfer prompt).
* **Reviewer Cockpit (Signature Feature D)**: High-speed, keyboard-driven interface (`A`, `R`, `E`, `U`, `N`) for human annotators to verify AI candidates. Models outputs are immutable; reviewer decisions are stored append-only.
* **Reproducibility Panel (Signature Feature E)**: Complete audit trail drawer displaying exact calculation formulas, word counts, denominators, and frozen prompt/rubric hashes.
* **Pilot Kit (Signature Feature F)**: Golden-standard evaluation engine computing transcription Word Error Rate (WER), category-level Precision/Recall/F1, and inter-rater agreement ($\kappa$).

---

## 🏗️ Architecture & Privacy Safeguards

SyntaxLens is built with strict privacy-by-design principles adhering to **OWASP ASVS Level 2** and institutional research ethics (IRB) mandates:

* **Schema Isolation**: Participant PII (names, emails) is stored in the `identity` schema, completely segregated from speech transcripts and assessments in the `research` schema.
* **Append-Only Database Triggers**: Database-level triggers abort any `UPDATE` or `DELETE` statements on audit logs, error annotations, and reviewer decisions.
* **Provider Privacy Gate**: AI providers are strictly gated on zero-retention enterprise agreements and verified training opt-outs. Outgoing payloads are actively scanned for PII and canary strings.
* **Zero Schema Drift**: Research datasets and data dictionaries (`DATA_DICTIONARY.csv`) are derived programmatically from the exact same typed schema descriptors.

---

## 🚀 Quickstart & Local Development

### 1. Backend Setup (FastAPI & Python 3.11+)
```bash
# Clone repository
git clone https://github.com/syntaxlens/syntaxlens.git
cd syntaxlens

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate

# Install dependencies
pip install -r apps/api/requirements.txt

# Run backend tests (100% passing, 210 tests)
pytest apps/api/tests/ -v

# Start development API server
uvicorn apps.api.app.main:app --reload --port 8000
```

### 2. Frontend Setup (Next.js 14 & Tailwind CSS)
```bash
cd apps/web

# Install dependencies
npm install

# Run TypeScript typechecking
npm run typecheck

# Start development web server
npm run dev
```

---

## 📖 Comprehensive Documentation Links

* [Acceptance Report & Verification Matrix](docs/ACCEPTANCE_REPORT.md) — Complete SRS §14 acceptance criteria verification (100% pass rate).
* [Requirements Traceability Matrix](docs/TRACEABILITY.md) — Full mapping of FR-01 through FR-20, NFRs, and Signature Features.
* [Security Architecture & STRIDE Threat Model](docs/SECURITY.md) — Threat model, defense-in-depth, and encryption controls.
* [Research Privacy & Data Flows](docs/PRIVACY.md) — Data classification, retention periods, and right-to-be-forgotten protocols.
* [Operational Runbook](docs/RUNBOOK.md) — Disaster recovery, backup manifests, and circuit-breaker handling.
* [Deployment & Setup Guide](docs/DEPLOYMENT_GUIDE.md) — Docker Compose production deployment and database migrations.
* [User Guides](docs/USER_GUIDES.md) — Participant, Reviewer Cockpit, and Researcher instructions.
* [Pilot Kit Evaluation Report](docs/PILOT_REPORT.md) — Gold standard evaluation benchmarking report (Markdown & CSV).

---

## 📄 License & Attribution

Developed for doctoral and institutional academic research in spoken English applied linguistics. Licensed under the Apache License 2.0.
