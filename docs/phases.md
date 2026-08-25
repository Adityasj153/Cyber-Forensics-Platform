# Project Phases
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Version:** 1.0
**Companion to:** PRD.md, architecture.md, rules.md

This document breaks the project into sequential, buildable phases. Each phase lists its goal, scope, concrete tasks, components touched (per `architecture.md`), exit criteria, and how it's validated against the two testing scenarios (insider exfiltration, ransomware) from the problem statement.

---

## Phase 0 — Project Setup & Foundations
**Goal:** Get a working skeleton running end-to-end before any real feature work.

**Tasks:**
- Initialize repo with the folder structure from `architecture.md`
- Set up `docker-compose.yml`: Postgres+TimescaleDB, Redis, Elasticsearch, MinIO, backend, frontend
- Scaffold FastAPI app (`main.py`, health-check endpoint) and Next.js app (empty dashboard shell)
- Set up Alembic migrations, base SQLAlchemy models (`Case`, `Device`, `RawArtifact`, `AuditLog`)
- Set up auth (JWT/OAuth2) with three roles: admin, investigator, viewer
- Set up CI (GitHub Actions): lint, type-check, test on every PR
- Set up structured logging + audit-log write path
- Generate/seed initial synthetic dataset stubs for Scenario 1 and Scenario 2 in `datasets/synthetic/`

**Exit criteria:**
- A user can log in, create a Case, and see it in an empty dashboard
- CI pipeline passes on a clean PR
- Audit log records the case-creation event

---

## Phase 1 — Log Ingestion, Parsing & Aggregation (Basic Filtering/Search)
*(Maps to PRD Milestone: Phase 1)*

**Goal:** Get raw logs from multiple sources into the system, normalized, and searchable — no AI yet.

**Scope:**
- File upload → hashing → immutable storage (MinIO) → `RawArtifact` record
- Pluggable parser registry + format detection
- Parsers for: Windows EVTX, Linux syslog, Android logcat, Android USB/Bluetooth transfer artifacts, email headers, generic network/IP logs (CSV/JSON)
- Normalization into common `LogEvent` schema
- Bulk write to TimescaleDB + indexing into Elasticsearch
- Basic filtering/search API (by time range, device, event type, keyword) + minimal frontend search UI
- Ingestion status tracking (`queued` → `parsing` → `parsed` / `parse_failed`)

**Components touched:** `ingestion/*`, `db/models`, `storage/object_store.py`, `storage/search_index.py`, `api/routes/logs.py`, `api/routes/search.py`, frontend `search/` route

**Exit criteria:**
- Sample logs from Scenario 1 (PC + Android) and Scenario 2 (Windows system/app logs) can be uploaded and parsed without manual intervention
- Every uploaded file has a verifiable SHA-256 hash on record
- A user can search/filter parsed events by time, device, and keyword in the dashboard
- Malformed files fail gracefully with a recorded reason (per `rules.md` §3.2), without blocking other files

**Validation against scenarios:**
- Scenario 1: confirm file-transfer-related events (USB, Bluetooth, email) from both devices appear as normalized `LogEvent` rows
- Scenario 2: confirm system/application log entries around the ransomware timeframe are ingested and searchable

---

## Phase 2 — Secure Storage/Retrieval & AI Engine Prototype
*(Maps to PRD Milestone: Phase 2)*

**Goal:** Harden storage/retrieval, and stand up a first working version of the AI correlation & anomaly detection engine.

**Scope:**
- Performance/indexing tuning for large log volumes (time-series partitioning in TimescaleDB, ES index mapping)
- Entity graph builder (`ai_engine/correlation/entity_graph.py`) using NetworkX: model users, devices, files, IPs, hashes as nodes/edges from `LogEvent` data
- Cross-device correlation logic (`cross_device.py`) — link the same file/hash appearing across devices/channels (USB, Bluetooth, email)
- Anomaly detection prototype (`isolation_forest.py`): flag unusual transfer volumes, off-hours activity, suspicious process/file patterns
- Ransomware-specific timeline detector prototype (`ransomware_timeline.py`): trace first appearance of a malicious file/process → propagation → encryption events
- SHAP explainability wired into every anomaly/correlation output (no unexplained scores, per `rules.md` §4.1)
- Model versioning recorded on every AI output
- Async execution via Celery (`ai_tasks.py`) so AI runs don't block the API

**Components touched:** `ai_engine/*`, `tasks/ai_tasks.py`, `db/models` (add `Entity`, `CorrelationEdge`, `Anomaly`)

**Exit criteria:**
- Running the AI engine on Scenario 1 data produces a correlation edge linking the confidential file across PC → transfer channel → mobile, with a confidence score and SHAP explanation
- Running the AI engine on Scenario 2 data produces an ordered timeline of ransomware-related events (download → execution → encryption) with flagged anomalies
- AI failures degrade gracefully — raw/parsed data remains viewable even if AI run fails (per `rules.md` §3.5)

---

## Phase 3 — Graphical Representation & Full Dashboard GUI
*(Maps to PRD Milestone: Phase 3)*

**Goal:** Make the AI engine's output usable by an investigator through a full interactive dashboard.

**Scope:**
- Unified timeline visualization (D3.js) — chronological, zoomable, filterable, cross-device
- Correlation graph visualization — interactive node/edge view of entities (files, devices, IPs, users)
- Anomaly/alerts panel — severity, confidence, SHAP explanation shown per finding, with investigator review/sign-off action
- Case overview page — device summary, artifact list, ingestion status
- Advanced query builder UI (on top of Phase 1 search) — combine time range, device, IP, hash, event type
- (Optional, if in scope for this build) NL query interface: investigator asks a question in plain language → grounded structured query → answer with cited `LogEvent` records (per `rules.md` §4.1.3–4.1.4)
- RBAC-aware UI (viewer = read-only, investigator = full case actions, admin = user/case management)

**Components touched:** `frontend/components/timeline`, `correlation-graph`, `anomaly-panel`, `search-filters`, `nl-query` (optional), `api/routes/nl_query.py` (optional), `api/routes/anomalies.py`

**Exit criteria:**
- An investigator can open Scenario 1's case and visually trace the file-transfer timeline with IP addresses shown, entirely from the dashboard (matches PRD Scenario 1 requirement)
- An investigator can open Scenario 2's case and see the infection-to-encryption timeline with implicated applications/files highlighted (matches PRD Scenario 2 requirement)
- Every AI finding on screen is marked advisory with visible confidence + explanation, and requires explicit investigator review before being marked "confirmed"

---

## Phase 4 — Reporting Engine & Benchmarking
*(Maps to PRD Milestone: Phase 4)*

**Goal:** Deliver export-ready reporting and validate the whole system against defined benchmarks.

**Scope:**
- PDF report generation: case metadata, timeline, entities/IPs involved, evidence references, AI findings with confidence/explanation, investigator sign-off status
- CSV export: raw/normalized event export
- JSON export: machine-readable, structured for SIEM/SOAR ingestion
- Report integrity: hash/signature attached at export time (per `rules.md` §5)
- Human-in-the-loop finalization workflow — reports are "draft" until an investigator explicitly approves (per `rules.md` §4.1.5)
- Benchmarking harness: run the full pipeline against `datasets/synthetic/` Scenario 1 & 2 with known ground truth; measure:
  - Time from upload → completed timeline
  - Correlation precision/recall vs. ground truth
  - Anomaly detection precision/recall vs. ground truth
- Documentation pass: finalize API spec (`docs/api-spec.yaml`), deployment guide, user guide for investigators

**Components touched:** `reporting/*`, `api/routes/reports.py`, `db/models` (add `Report`), benchmarking scripts under `tests/`

**Exit criteria:**
- Full PDF/CSV/JSON export works for both scenario cases and passes hash-integrity verification
- Benchmark report published showing measured accuracy/speed against synthetic ground truth
- End-to-end walkthrough of both testing scenarios, from raw log upload to final signed-off report, works without manual intervention outside investigator review steps

---

## Phase 5 (Post-MVP / Stretch) — Productization & Ecosystem Integration
*(Not in original 4 milestones — forward-looking, from PRD's Business Case / Commercialization section)*

**Goal:** Move from working PoC to a deployable, multi-tenant product.

**Candidate scope (prioritize based on actual demand):**
- Multi-tenancy for MSSP use (case isolation per client org)
- SIEM/SOAR integration connectors (consume the JSON export format)
- On-prem/air-gapped deployment packaging for law-enforcement/government use
- Training-as-a-Service mode: guided scenarios for law enforcement academies using synthetic datasets
- Expanded parser library (additional IoT, cloud service, and mobile-OS log formats)
- Cloud-native scaling (Kubernetes autoscaling, managed Elasticsearch/Postgres)

**Exit criteria:** Defined per specific commercialization target once prioritized — not part of the core PoC scope.

---

## Phase Summary Table

| Phase | Focus | Key Output |
|---|---|---|
| 0 | Setup | Running skeleton, CI, auth, base schema |
| 1 | Ingestion & Search | Multi-source logs parsed, normalized, searchable |
| 2 | Storage + AI Prototype | Correlation graph + anomaly detection with XAI |
| 3 | Dashboard GUI | Full visual timeline, correlation graph, alerts, (optional) NL query |
| 4 | Reporting & Benchmarking | PDF/CSV/JSON export, integrity-signed, benchmarked accuracy |
| 5 (stretch) | Productization | Multi-tenant, SIEM/SOAR integration, on-prem packaging |

---

## Dependencies Between Phases
- Phase 1 must complete (normalized `LogEvent` data available) before Phase 2's AI engine has anything to correlate.
- Phase 2's `Entity`/`CorrelationEdge`/`Anomaly` models must exist before Phase 3's dashboard views can render them.
- Phase 3's investigator review/sign-off workflow must exist before Phase 4's reporting can enforce "draft until approved" (per `rules.md` §4.1.5).
- Benchmarking in Phase 4 depends on the synthetic datasets seeded in Phase 0 and used for validation throughout Phases 1–3.
