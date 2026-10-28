# SyntaxLens Render Cloud Deployment Guide

This guide describes how to deploy the entire SyntaxLens platform to **Render** using the included Infrastructure-as-Code Blueprint (`render.yaml`).

---

## 1. Architecture Overview on Render

The Render deployment consists of four coordinated components defined in [`render.yaml`](../render.yaml):

| Service Name | Type | Plan | Description |
|---|---|---|---|
| **`syntaxlens-db`** | PostgreSQL 16 | Starter / Free | Managed database with `identity` and `research` schemas and append-only immutability triggers. |
| **`syntaxlens-redis`** | Redis | Starter / Free | Fast in-memory session store and rate-limiting cache. |
| **`syntaxlens-api`** | Web Service (Docker / FastAPI) | Starter / Free | Python 3.12 FastAPI backend serving `/api/v1` with dynamic `$PORT` binding, auto-migrations, and seed. |
| **`syntaxlens-web`** | Web Service (Docker / Next.js) | Starter / Free | Node.js 20 Next.js 14 App Router frontend serving the participant and researcher dashboards. |

---

## 2. 1-Click Blueprint Deployment (Step-by-Step)

### Step 1: Connect Your GitHub Repository
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. In the top navigation, click **New +** and select **Blueprint**.
3. Connect your GitHub account (if not already connected) and select the repository:
   ```
   https://github.com/mj897535-oss/ai-eng
   ```
4. Choose the `main` or `master` branch.

### Step 2: Review Blueprint Resources
Render will automatically parse [`render.yaml`](../render.yaml) and display the four resources to be created:
- `syntaxlens-db` (Database)
- `syntaxlens-redis` (Redis)
- `syntaxlens-api` (API Service)
- `syntaxlens-web` (Web Service)

### Step 3: Click Apply
Click the **Apply** button. Render will begin building and deploying all components concurrently in dependency order.

---

## 3. Automated Database Migrations & Initial Data Seeding

During the startup of `syntaxlens-api`, the entrypoint script [`apps/api/start.sh`](../apps/api/start.sh) runs automatically:
1. **Alembic Migrations**: Runs `alembic upgrade head` to create all tables and database triggers in the `identity` and `research` schemas.
2. **Initial Seed Script**: Runs `python -m app.seed` to initialize:
   - Frozen PhD Spoken English Syntax Rubric `v1.0-jam-phd` (8 categories: TNS, SVA, WO, AUX, ART, PREP, PRO, OTH).
   - Standard Prompt Versions (`v1.0-jam-pre`, `v1.0-tutor-ladder`, `v1.0-jam-post`).
   - Standard 1-minute assessment topic bank.
   - Initial research test accounts.

### Pre-Configured Test Accounts (From `app.seed`)

| Role | Email | Password |
|---|---|---|
| **Researcher Admin** | `researcher@syntaxlens.edu` | `SyntaxLens@2026!` |
| **Reviewer** | `reviewer@syntaxlens.edu` | `SyntaxLens@2026!` |
| **Student Participant** | `student1@syntaxlens.edu` | `SyntaxLens@2026!` |

*(Researchers can invite new participants or create new users at any time via the Researcher Dashboard).*

---

## 4. Verification and Health Checks

Once deployed, verify that the services are online:

1. **API Health Check**:
   ```bash
   curl https://<YOUR_API_NAME>.onrender.com/api/v1/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "SyntaxLens Backend API",
     "environment": "production",
     "rubric_version": "v1.0-jam-phd",
     "prompt_version": "v1.0-tutor-ladder",
     "stt_provider": "mock",
     "llm_provider": "mock"
   }
   ```

2. **API Readiness Check** (verifies live DB connection):
   ```bash
   curl https://<YOUR_API_NAME>.onrender.com/api/v1/ready
   ```
   Expected response:
   ```json
   {
     "status": "ready",
     "database": "connected",
     "storage": "configured"
   }
   ```

3. **Frontend Dashboard**:
   Open `https://<YOUR_WEB_NAME>.onrender.com` in your browser. You can immediately log in using the seed accounts above.

---

## 5. Live AI Providers (Optional)

By default, the platform uses deterministic, reproducible research mock engines (`STT_PROVIDER=mock`, `LLM_PROVIDER=mock`). To enable live AI models on Render:

In your `syntaxlens-api` Environment Settings on Render:
- `LLM_PROVIDER`: `gemini`
- `GEMINI_API_KEY`: `<YOUR_GEMINI_API_KEY>`
- `LLM_MODEL`: `gemini-1.5-pro` (or `gemini-1.5-flash`)
- `STT_PROVIDER`: `mock` (or your preferred STT service)

The platform will automatically gate requests through the **Provider Privacy Gate** (Phase P15) to ensure zero participant PII leaves the platform.
