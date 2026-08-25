# Architecture Document
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Version:** 1.0
**Companion to:** PRD.md

---

## 1. Tech Stack

### 1.1 Frontend
| Component | Choice | Why |
|---|---|---|
| Framework | **Next.js (React) + TypeScript** | SSR for dashboards, good ecosystem, fast dev |
| UI Kit | **Tailwind CSS + shadcn/ui** | Rapid, consistent, accessible components |
| Timeline / Graph viz | **D3.js** (custom timeline & correlation graph) + **Recharts** (simple charts) | Fine-grained control needed for forensic timelines |
| State management | **React Query** (server state) + **Zustand** (UI state) | Simple, avoids Redux boilerplate |
| Auth (client) | **NextAuth.js** | RBAC-friendly session handling |

### 1.2 Backend
| Component | Choice | Why |
|---|---|---|
| API framework | **Python + FastAPI** | Async, strong typing, best ecosystem for ML integration |
| Task queue / workers | **Celery + Redis** (broker) | Async ingestion/parsing/ML jobs off the request path |
| Auth & RBAC | **FastAPI + OAuth2/JWT**, roles: admin / investigator / viewer | Case-level access control |
| API Gateway (optional, prod) | **NGINX / Kong** | Rate limiting, TLS termination |

### 1.3 Data Layer
| Store | Choice | Purpose |
|---|---|---|
| Normalized event store | **PostgreSQL + TimescaleDB extension** | Time-series-optimized queries over normalized log events |
| Full-text / fast search | **Elasticsearch (or OpenSearch)** | Free-text search across large log volumes, filtering |
| Raw immutable evidence store | **Object storage (S3-compatible / MinIO)**, write-once + SHA-256 checksums | Preserves original logs for chain-of-custody |
| Cache | **Redis** | Query caching, Celery broker, session store |
| Metadata / audit DB | **PostgreSQL** (same instance, separate schema) | Case metadata, users, audit trail, chain-of-custody log |

### 1.4 AI / ML Layer
| Component | Choice | Purpose |
|---|---|---|
| Classical ML | **scikit-learn, XGBoost** | Anomaly detection (isolation forest, one-class SVM), classification of event types |
| Correlation engine | **NetworkX** (graph modeling) | Model entities (device, user, file, IP) as a graph; find correlated paths across devices |
| Explainability | **SHAP** | Per-alert feature attribution shown to investigators |
| NL query (optional) | **Anthropic Claude API** (via `/v1/messages`), function-calling to structured DB query layer — never free-text SQL generation directly | Natural-language investigator queries, grounded in retrieved events only |
| Model serving | **FastAPI microservice** (internal), or batch via Celery workers | Keeps ML compute isolated from the main API |

### 1.5 Log Parsing
| Source | Parser approach |
|---|---|
| Windows Event Logs (EVTX) | `python-evtx` / `Chainsaw`-style rule parsing |
| Linux syslog | Standard syslog parser (regex + `rsyslog` format support) |
| Android (logcat, app/USB/Bluetooth transfer artifacts) | Custom parsers per artifact type (logcat grammar, `usbfs`/`btsnoop` logs) |
| Email headers/logs | `email` (Python stdlib) header parser |
| Network / ISP / firewall logs | CSV/JSON generic parser + IP/GeoIP enrichment (`MaxMind GeoLite2`) |
| Extensibility | All parsers implement a common `BaseParser` interface → **pluggable parser registry** |

### 1.6 Infrastructure / DevOps
| Component | Choice |
|---|---|
| Containerization | **Docker** + **docker-compose** (dev), **Kubernetes** (prod) |
| CI/CD | **GitHub Actions** |
| Secrets | **HashiCorp Vault** or cloud KMS |
| Monitoring | **Prometheus + Grafana**, **Loki** for app logs (not to be confused with forensic case logs) |
| Deployment targets | Cloud (AWS/Azure/GCP) with an on-prem/air-gapped deployment option for law-enforcement use |

---

## 2. App Flow

### 2.1 Case Lifecycle Flow
```
1. Investigator logs in → creates a new Case
2. Uploads raw log files/artifacts (per device: PC, mobile, server, network)
3. System hashes + stores raw files in immutable evidence store (chain-of-custody entry created)
4. Ingestion workers detect format → route to correct parser
5. Parsed events normalized → written to TimescaleDB (+ indexed in Elasticsearch)
6. AI engine runs (async, Celery job):
     a. Entity graph built (users, devices, files, IPs, hashes)
     b. Cross-device correlation computed
     c. Anomaly detection scored
     d. XAI explanations attached to each finding
7. Dashboard polls/streams job status → renders:
     - Unified timeline
     - Correlation graph
     - Anomaly/alerts panel
8. Investigator filters/searches/annotates findings
9. (Optional) Investigator asks NL question → Claude API translates to structured query → grounded answer + cited events returned
10. Investigator generates report → PDF/CSV/JSON export, signed/hashed for integrity
11. All actions (upload, view, query, export) logged to audit trail
```

### 2.2 Request-Level Flow (Ingestion Example)
```
Browser (upload) 
   → POST /api/cases/{id}/logs 
   → FastAPI validates file, computes SHA-256, stores raw in S3/MinIO 
   → Creates DB record (status: "queued") 
   → Enqueues Celery task: parse_log_file(file_id)
   → Worker: detect format → run parser → normalize → bulk insert (Postgres/Timescale) + index (Elasticsearch)
   → Update DB record (status: "parsed") 
   → Enqueue Celery task: run_ai_correlation(case_id)
   → Worker: build/update entity graph, run anomaly models, attach SHAP explanations
   → Update DB record (status: "analyzed")
   → WebSocket / polling notifies frontend → dashboard refreshes
```

### 2.3 Data Model (Core Entities, simplified)
```
Case (id, name, created_by, status, created_at)
Device (id, case_id, type[pc|mobile|server|network], os, owner)
RawArtifact (id, device_id, filename, sha256, storage_path, uploaded_by, uploaded_at)
LogEvent (id, case_id, device_id, timestamp, source_type, actor, action, object, ip_address, file_hash, raw_ref)
Entity (id, case_id, type[user|device|file|ip|hash], value)
CorrelationEdge (id, case_id, entity_a_id, entity_b_id, relation_type, confidence, evidence_event_ids[])
Anomaly (id, case_id, event_ids[], score, model, explanation_json, reviewed_by)
Report (id, case_id, format, generated_by, generated_at, file_hash)
AuditLog (id, case_id, user_id, action, target, timestamp)
```

---

## 3. Folder & File Structure

```
cyber-forensics-platform/
├── frontend/
│   ├── app/                          # Next.js app router
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── cases/
│   │   │   ├── page.tsx              # case list
│   │   │   └── [caseId]/
│   │   │       ├── page.tsx          # case overview
│   │   │       ├── timeline/
│   │   │       ├── correlation/
│   │   │       ├── anomalies/
│   │   │       ├── search/
│   │   │       ├── nl-query/
│   │   │       └── reports/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── timeline/                 # D3 timeline component
│   │   ├── correlation-graph/        # D3/Cytoscape graph view
│   │   ├── anomaly-panel/
│   │   ├── search-filters/
│   │   └── ui/                       # shadcn components
│   ├── lib/
│   │   ├── api-client.ts
│   │   └── auth.ts
│   ├── hooks/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI entrypoint
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── cases.py
│   │   │   │   ├── devices.py
│   │   │   │   ├── logs.py           # upload/ingestion endpoints
│   │   │   │   ├── search.py
│   │   │   │   ├── anomalies.py
│   │   │   │   ├── nl_query.py       # LLM NL query endpoint
│   │   │   │   └── reports.py
│   │   │   └── deps.py               # auth/RBAC dependencies
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── audit.py              # audit trail / chain-of-custody logging
│   │   ├── db/
│   │   │   ├── models/               # SQLAlchemy models (Case, Device, LogEvent, etc.)
│   │   │   ├── session.py
│   │   │   └── migrations/           # Alembic
│   │   ├── ingestion/
│   │   │   ├── parsers/
│   │   │   │   ├── base.py           # BaseParser interface
│   │   │   │   ├── windows_evtx.py
│   │   │   │   ├── linux_syslog.py
│   │   │   │   ├── android_logcat.py
│   │   │   │   ├── android_usb_bt.py
│   │   │   │   ├── email_headers.py
│   │   │   │   └── network_generic.py
│   │   │   ├── registry.py           # parser format-detection + routing
│   │   │   └── normalizer.py         # maps raw → common LogEvent schema
│   │   ├── ai_engine/
│   │   │   ├── correlation/
│   │   │   │   ├── entity_graph.py   # NetworkX graph builder
│   │   │   │   └── cross_device.py   # correlation logic (Scenario 1 style)
│   │   │   ├── anomaly/
│   │   │   │   ├── isolation_forest.py
│   │   │   │   └── ransomware_timeline.py  # Scenario 2 style detection
│   │   │   ├── explainability/
│   │   │   │   └── shap_explainer.py
│   │   │   └── nl_query/
│   │   │       ├── claude_client.py
│   │   │       └── query_grounding.py     # translates NL → structured DB query
│   │   ├── reporting/
│   │   │   ├── pdf_report.py
│   │   │   ├── csv_export.py
│   │   │   └── json_export.py
│   │   ├── storage/
│   │   │   ├── object_store.py       # S3/MinIO client, hashing, immutability
│   │   │   └── search_index.py       # Elasticsearch client
│   │   └── tasks/
│   │       ├── celery_app.py
│   │       ├── ingestion_tasks.py
│   │       └── ai_tasks.py
│   ├── tests/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── infra/
│   ├── docker-compose.yml            # local dev: postgres, redis, elasticsearch, minio, api, worker, frontend
│   ├── k8s/                          # production manifests / helm charts
│   └── terraform/                    # cloud infra as code (optional)
│
├── datasets/
│   └── synthetic/                    # synthetic PoC datasets for Scenario 1 & 2
│
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   └── api-spec.yaml                 # OpenAPI spec
│
└── README.md
```

---

## 4. Key Architectural Decisions

| Decision | Rationale |
|---|---|
| **Separate raw evidence store from queryable DB** | Raw logs stay immutable (hashed, write-once) for evidentiary integrity; normalized DB is the fast query surface. Deleting/reindexing the query layer never touches evidence. |
| **Async pipeline (Celery)** | Log ingestion + ML correlation can be slow (large files); must not block the API or UI. |
| **Pluggable parser registry** | New log/device formats (future IoT sources, new OS versions) can be added as isolated modules without touching core ingestion logic. |
| **Graph-based correlation (NetworkX)** | Cross-device correlation (file → USB → email → mobile) is naturally a graph-traversal problem, not a simple join. |
| **XAI required on every AI output** | Investigators/courts need to know *why* something was flagged — SHAP attached to every anomaly/correlation. |
| **LLM only queries, never asserts facts directly** | NL query layer must translate to structured queries against real stored events and cite them — avoids hallucinated "facts" in a forensic context. |
| **Audit log on every action** | Required for chain-of-custody; who accessed/exported what, and when. |
| **Cloud + on-prem deployment options** | Law enforcement / government use cases may require air-gapped, on-prem deployment; architecture avoids hard cloud-only dependencies (MinIO instead of AWS-S3-only, self-hostable Elasticsearch, etc.). |

---

## 5. Mapping to Delivery Phases (from PRD)

| Phase | Architecture components involved |
|---|---|
| **Phase 1** | `ingestion/parsers/*`, `ingestion/registry.py`, `normalizer.py`, basic `search.py` API |
| **Phase 2** | `db/models`, TimescaleDB + Elasticsearch wiring, `ai_engine/anomaly/*` prototype |
| **Phase 3** | `frontend/components/timeline`, `correlation-graph`, full dashboard routes |
| **Phase 4** | `reporting/*` (PDF/CSV/JSON), benchmarking harness against `datasets/synthetic` |

---

## 6. Security & Chain-of-Custody Notes
- All raw artifacts hashed (SHA-256) on upload; hash stored alongside metadata and re-verified on every export.
- Every read/write/export action recorded in `AuditLog` with user, timestamp, and target.
- RBAC enforced at API layer: `viewer` (read-only), `investigator` (upload/query/report), `admin` (user/case management).
- Encryption in transit (TLS) and at rest (DB + object storage encryption).
- Report exports are hashed/signed so any post-export tampering is detectable.
