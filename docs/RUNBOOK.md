# SyntaxLens Operational Runbook

> **Disaster Recovery, Automated Backups, Restores, and Failure Response**  
> **Document Version:** 1.0 (Phase P15 Security & Reliability Hardening)

---

## 1. Routine Backups & Automated Snapshots

### 1.1 Database Snapshot Schedule
* **Full Daily Snapshot**: Automated nightly PostgreSQL backup stored in encrypted S3 cold storage (`s3://syntaxlens-backups/db/daily/`).
* **Continuous Archiving**: Write-Ahead Logging (WAL) archiving enabled with Point-in-Time Recovery (PITR) up to 14 days.

### 1.2 Object Storage Replication
* Speech audio recordings and frozen export snapshots in S3 use Cross-Region Replication (CRR) to a secondary geographically isolated bucket with object-level immutability (WORM / Object Lock).

---

## 2. Disaster Recovery Drill (Tested Script)

SyntaxLens includes an automated verification script that creates, cryptographically signs, and validates backup archives:

```bash
# 1. Run automated backup and cryptographic drill
python -c "
from app.services.backup import generate_backup_archive, verify_and_restore_backup
import tempfile, json

with tempfile.TemporaryDirectory() as tmp_dir:
    mock_data = {'participants': [{'id': 'p1'}], 'assessments': [{'id': 'a1'}]}
    manifest = generate_backup_archive(tmp_dir, mock_data)
    print(f'Backup created: {manifest.backup_id} (SHA-256: {manifest.archive_checksum_sha256[:12]}...)')
    
    restored = verify_and_restore_backup(f'{tmp_dir}/{manifest.backup_id}.json')
    print(f'Disaster Recovery Drill: {restored[\"restore_status\"].upper()} for tables: {restored[\"recovered_tables\"]}')
"
```

### 2.1 Database Restore Procedure
1. Halt active application containers to prevent write skew:
   ```bash
   docker-compose stop api worker
   ```
2. Verify archive checksum against the manifest:
   ```bash
   sha256sum -c backup_manifest.sha256
   ```
3. Restore database schema and rows:
   ```bash
   pg_restore --clean --if-exists -U syntaxlens_admin -d syntaxlens backup_20261028.dump
   ```
4. Verify trigger integrity:
   ```bash
   pytest apps/api/tests/db/test_audit_immutability.py
   ```
5. Restart application services:
   ```bash
   docker-compose start api worker
   ```

---

## 3. Reliability & Failure Response Procedures

### 3.1 AI Provider Degradation & Circuit Breaker Tripping
* When external STT or LLM APIs experience latency spikes or consecutive HTTP 5xx errors ($N \ge 3$), the internal **Circuit Breaker** trips from `CLOSED` to `OPEN`.
* **Behavior during OPEN state**:
  - Outgoing provider requests are paused for the recovery cool-off duration (default: 30 seconds).
  - Assessment jobs remain in `retrying` status without dropping audio.
  - User-facing UI displays: *"We received your recording. Processing is taking longer than usual and will complete automatically."*
* **Half-Open Probe**:
  - After cool-off, the circuit permits a single test call. If successful, state resets to `CLOSED`; if failing, the cool-off resets.

### 3.2 Dead-Letter Handling (`needs_attention`)
* If an assessment fails transcription or LLM analysis after 3 automated retry attempts, it transitions to the terminal `needs_attention` state.
* **Researcher Action**:
  1. Open the Reviewer Cockpit queue filtered by `status=needs_attention`.
  2. Inspect the `last_error` log field on the assessment record.
  3. If transient network error, trigger manual re-queue from the Cockpit.
  4. If bad audio format or corrupted upload, authorize a single participant retake via `/assessments/retake-auth`.

### 3.3 Duplicate Submission Prevention
* Audio presigned upload and submission endpoints enforce strict **idempotency keys** and a **single official submission rule**:
  - Repeating a submission payload returns the existing assessment record with HTTP 200 without creating a duplicate database row.
  - Subsequent submissions for the same participant and assessment type are rejected with HTTP 409 unless an authorized retake row is present.
