# Engineering Rules & Guardrails
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Version:** 1.0
**Companion to:** PRD.md, architecture.md
**Purpose:** Binding rules for anyone (human or AI coding assistant) contributing to this codebase — what to use, what to avoid, and where the hard boundaries are.

---

## 1. Approved Libraries / Tools

### 1.1 Backend (Python)
| Use | For |
|---|---|
| `fastapi`, `pydantic` | API layer, request/response validation |
| `sqlalchemy`, `alembic` | ORM + migrations (never raw string-built SQL) |
| `celery`, `redis` | Async jobs (parsing, AI correlation) |
| `python-evtx`, stdlib `email`, custom regex parsers | Log parsing |
| `scikit-learn`, `xgboost` | Anomaly detection / classification |
| `networkx` | Entity/correlation graph |
| `shap` | Explainability, attached to every AI finding |
| `boto3` / MinIO SDK | Object storage (S3-compatible) |
| `elasticsearch-py` | Search indexing/queries |
| `pytest`, `pytest-asyncio` | Testing |
| `structlog` or stdlib `logging` (structured, JSON) | App logging |

### 1.2 Frontend (TypeScript)
| Use | For |
|---|---|
| Next.js, React, TypeScript | Core app |
| Tailwind CSS, shadcn/ui | Styling/components |
| D3.js | Timeline & correlation graph visualizations |
| React Query | Server-state fetching/caching |
| Zod | Runtime validation of API responses |

### 1.3 Infra
| Use | For |
|---|---|
| Docker / docker-compose / Kubernetes | Packaging & orchestration |
| GitHub Actions | CI/CD |
| Prometheus + Grafana | Metrics |
| HashiCorp Vault / cloud KMS | Secrets |

---

## 2. Libraries / Patterns to Avoid

| Avoid | Reason | Use instead |
|---|---|---|
| Raw SQL string concatenation / f-string queries | SQL injection risk, no migration tracking | SQLAlchemy ORM / parameterized queries |
| `pickle` for any data crossing a trust boundary (uploaded files, network data) | Arbitrary code execution risk | JSON / explicit schemas (Pydantic) |
| `eval()` / `exec()` anywhere in ingestion or AI pipeline | Same as above — never execute data as code | Explicit parser logic per format |
| Client-side-only auth checks | Trivially bypassed | Enforce RBAC server-side on every endpoint |
| Storing secrets/API keys in code or `.env` committed to git | Credential leakage | Vault / KMS / CI secrets store |
| Deep-learning black-box models with no explainability path (e.g., unexplained neural nets for anomaly scoring) in v1 | Forensic findings must be explainable to investigators/courts | Interpretable models (isolation forest, XGBoost + SHAP) first; deep learning only if paired with an XAI layer |
| Unvetted npm/PyPI packages with low maintenance/stars for security-critical paths (parsing, auth, crypto) | Supply-chain risk in a forensic tool | Stick to the approved list; any addition requires review |
| Mutating or "cleaning" raw uploaded log files in place | Destroys evidentiary integrity | Raw files are write-once/immutable; all processing works on copies |
| `localStorage`/`sessionStorage` for auth tokens or case data in the frontend | XSS-exposed | HttpOnly secure cookies / server session |
| Global mutable state for case data in the frontend | Cross-case data leakage risk between investigator sessions | Scope all state to case ID, fetched per-request |

---

## 3. Error Handling Rules

1. **Never silently swallow exceptions.** Every `except` block must either re-raise, log with full context (case_id, file_id, stage), or return a clear error to the caller. No bare `except: pass`.
2. **Ingestion failures are data, not crashes.** A malformed/unparseable log file must produce a recorded `RawArtifact.status = "parse_failed"` entry with an error reason — it must never take down the ingestion worker or block other files in the case.
3. **Fail closed on integrity checks.** If a SHA-256 hash mismatch is detected on a raw artifact at any point (upload, retrieval, export), halt that operation and flag the case — never proceed silently.
4. **API errors return structured, typed responses.** Use consistent error schema (`{ "error_code": ..., "message": ..., "detail": ... }`); never leak stack traces or internal paths to the frontend.
5. **AI/ML pipeline errors must degrade gracefully.** If the anomaly model or correlation engine fails on a case, the dashboard must still show ingested/parsed data — AI failure never blocks access to raw evidence.
6. **Audit every failure that touches evidence.** Failed uploads, failed exports, and integrity-check failures are logged to `AuditLog` just like successful actions.
7. **Retries only for idempotent operations.** Celery task retries are allowed for parsing/indexing (idempotent), never for operations that could duplicate evidence records.
8. **User-facing errors are actionable, not just descriptive.** E.g., "Unsupported log format: .xyz — see supported formats list" rather than a generic 500.

---

## 4. Boundaries for AI Usage

These rules apply to both (a) the AI/ML components built into the product (anomaly detection, correlation engine, NL query) and (b) any AI coding assistant used to build this codebase.

### 4.1 Product AI Boundaries (runtime)
1. **AI findings are always advisory, never authoritative.** No AI output (anomaly flag, correlation, inferred timeline) may be presented as a fact — always shown with a confidence score and marked as requiring investigator review/sign-off before it can be included in a final report.
2. **Every AI output must carry an explanation.** No anomaly score or correlation edge ships without a SHAP (or equivalent) explanation an investigator can inspect. Unexplainable outputs are not exposed in the UI.
3. **The NL-query (LLM) feature must be strictly grounded.** The LLM may only translate natural-language questions into structured queries against the normalized event store — it must never generate free-form "facts" about the case from its own knowledge. Every answer must cite the specific `LogEvent` records used.
4. **The LLM must never write directly to the evidence store.** Read-only access to query endpoints only. No LLM-initiated writes, deletes, or modifications to `LogEvent`, `RawArtifact`, or `AuditLog`.
5. **No fully automated report finalization.** Automated reporting drafts the report; a human investigator must explicitly review and approve before a report is marked "final" and exported.
6. **Model versioning is mandatory.** Every anomaly/correlation result records which model + version produced it, so findings remain reproducible and explainable months later (relevant for legal review).
7. **No AI decision may alter or delete raw evidence.** All AI processing operates on the normalized/derived layer; the immutable raw evidence store is never touched by ML/LLM components.

### 4.2 AI Coding-Assistant Boundaries (development time)
1. Any AI-assisted code touching **auth, hashing/integrity, parsing of untrusted input, or the evidence store** requires human review before merge — no auto-merge.
2. AI assistants must not introduce new third-party dependencies outside the approved list without flagging them for review (see Section 2).
3. AI-generated code must not fabricate or hardcode sample "evidence" data into non-test code paths — synthetic test data stays in `datasets/synthetic/` and `tests/`, clearly separated from production logic.
4. AI assistants should flag (not silently fix) any request that would weaken chain-of-custody guarantees, remove audit logging, or bypass RBAC — these require explicit human sign-off.
5. Prompts/config for the in-product LLM (NL query) must be version-controlled like code, with changes reviewed the same as any other logic change to the correlation/reporting pipeline.

---

## 5. Data Handling Rules
- Raw log files: **write once, never edited**, hashed on ingest, hash re-verified on export.
- PII in logs (usernames, emails, device IDs): access-controlled per case, not exposed outside authorized investigators on that case.
- Synthetic datasets used for development/testing must never be mixed with real case data in the same database/environment.
- All exports (PDF/CSV/JSON) are hashed at generation time; the hash is stored so tampering after export is detectable.

---

## 6. Testing Rules
- Every parser (Section 1.1, `ingestion/parsers/*`) must have unit tests using representative sample logs for its format.
- Every AI component (anomaly detector, correlation engine) must be tested against the synthetic datasets for **Scenario 1** (insider exfiltration) and **Scenario 2** (ransomware) with known ground truth, before being considered "done" for a phase.
- No PR touching ingestion, auth, or the evidence store merges without passing integration tests.

---

## 7. Summary Checklist (before merging any change)
- [ ] No new unapproved dependency without review
- [ ] No raw SQL, `eval`/`exec`, or `pickle` on untrusted data
- [ ] Errors logged with context, never silently swallowed
- [ ] Raw evidence store untouched/immutable
- [ ] AI outputs include confidence + explanation, marked advisory
- [ ] LLM NL-query changes are read-only and grounded in real events
- [ ] Audit log entries added for any new action touching case data
- [ ] Tests added/updated, including against synthetic Scenario 1/2 data where relevant
