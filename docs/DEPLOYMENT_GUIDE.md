# SyntaxLens Deployment & Operations Guide

> **Production Setup, Docker Compose, Database Migrations, and Backup Plans**  
> **Document Version:** 1.0 (Phase P16 Quality Assurance & Delivery)

---

## 1. Prerequisites & Architecture Overview

* **Operating System**: Linux (Ubuntu 22.04 LTS recommended), macOS, or Windows WSL2
* **Runtimes**: Python 3.11+, Node.js 18+ LTS, Docker & Docker Compose
* **Databases**: PostgreSQL 15+ with `identity` and `research` schemas, Redis 7+
* **Storage**: AWS S3 or MinIO S3-compatible private object storage

---

## 2. Environment Configuration (`.env`)

Copy `.env.example` to `.env` in both `apps/api` and `apps/web`:

```bash
cp .env.example .env
```

### Key Environment Variables (`apps/api/.env`)
```ini
# Environment
ENVIRONMENT=production
DEBUG=False
API_PREFIX=/api/v1
CORS_ORIGINS=["https://syntaxlens.edu"]

# Database & Cache
DATABASE_URL=postgresql+asyncpg://syntaxlens_app:secure_password@postgres:5432/syntaxlens
DATABASE_URL_SYNC=postgresql+psycopg2://syntaxlens_app:secure_password@postgres:5432/syntaxlens
REDIS_URL=redis://redis:6379/0

# Storage (S3 / MinIO)
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_BUCKET_NAME=syntaxlens-private-audio
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_REGION=us-east-1
S3_USE_SSL=True
S3_PRESIGNED_EXPIRATION_SECONDS=900

# Security & Cookies
SECRET_KEY=generate_with_openssl_rand_hex_32
COOKIE_SECURE=True
COOKIE_SAMESITE=lax

# AI Providers
STT_PROVIDER=whisper
LLM_PROVIDER=gemini
```

---

## 3. Database Initialization & Schema Migrations

### 3.1 Initialize Schemas and Immutability Triggers
Run the schema setup script against PostgreSQL:

```bash
psql -U postgres -d syntaxlens -f scripts/init_db.sql
```

### 3.2 Run Alembic Migrations
```bash
cd apps/api
alembic upgrade head
```

### 3.3 Verify Append-Only Database Triggers
Confirm that database triggers abort any unauthorized `UPDATE` or `DELETE` on research tables:
```bash
pytest tests/db/test_audit_immutability.py
```

---

## 4. Docker Deployment

Launch all services using Docker Compose:

```bash
docker-compose up -d --build
```

### Services Started:
* `postgres`: PostgreSQL 15 database container.
* `redis`: Ephemeral session store and rate-limiting cache.
* `minio`: S3-compatible private object storage.
* `api`: FastAPI asynchronous backend service (port 8000).
* `web`: Next.js 14 frontend web application (port 3000).

---

## 5. Automated Backup & Disaster Recovery Plan

### 5.1 Nightly Database Backups
A scheduled cron job takes daily PostgreSQL backups and uploads them to encrypted cold storage:
```bash
0 2 * * * pg_dump -U syntaxlens_admin -Fc syntaxlens | aws s3 cp - s3://syntaxlens-backups/db/$(date +\%Y\%m\%d).dump --sse AES256
```

### 5.2 Disaster Recovery Verification Drill
Execute the automated restore test:
```bash
python -c "
from app.services.backup import generate_backup_archive, verify_and_restore_backup
import tempfile

with tempfile.TemporaryDirectory() as tmp_dir:
    data = {'test': [{'val': 1}]}
    manifest = generate_backup_archive(tmp_dir, data)
    print(f'Backup verified: {manifest.backup_id} (SHA-256: {manifest.archive_checksum_sha256[:12]}...)')
    res = verify_and_restore_backup(f'{tmp_dir}/{manifest.backup_id}.json')
    print(f'Restore Drill: {res[\"restore_status\"].upper()}')
"
```
