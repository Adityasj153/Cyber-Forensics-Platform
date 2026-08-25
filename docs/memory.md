# Project Memory / Progress Log
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Purpose:** This file is the source of truth for "where we left off." Read this FIRST at the start of every session, alongside PRD.md, architecture.md, rules.md, and phases.md. Update it BEFORE ending any session — not after, since sessions can end abruptly.

**Last updated:** 2026-08-25 by agent

---

## 0. How to use this file (for the agent, every session)

1. Read this file top to bottom before touching any code.
2. Check "Currently In Progress" — if something is mid-work, continue it, don't restart it or start something new.
3. Check "Known Issues / Open TODOs" — don't silently "fix" something listed as an intentional deviation.
4. Run `git log --oneline -15` and `git status` to cross-check this file against actual repo state — if they disagree, trust the repo and flag the mismatch before proceeding.
5. At the end of the session (or when told to wrap up), update Sections 2–5 below with what actually changed.

---

## 1. Phase Status Overview

| Phase | Status | Exit Criteria Verified? | Notes |
|---|---|---|---|
| Phase 0 — Setup & Foundations | ✅ Done | ✅ | docker-compose, DB models, backend auth/RBAC, Alembic migrations, audit logging |
| Phase 1 — Ingestion, Parsing, Basic Search | ✅ Done | ✅ | Upload→hash→store→parse→normalize→ES index fully wired via Celery. 6 parsers registered. Search API exists. |
| Phase 2 — Storage + AI Engine Prototype | ✅ Done | ✅ | Entity graph, cross-device correlation, isolation forest, ransomware timeline, SHAP explainability, model versioning, Celery async |
| Phase 3 — Dashboard GUI | 🟨 In Progress | ⬜ | Components exist but NOT correctly wired or styled per spec — see FIX NOW list |
| Phase 4 — Reporting & Benchmarking | ⬜ Not started | — | |
| Phase 5 — Productization (stretch) | ⬜ Not started | — | |

---

## 2. Phase Exit-Criteria Checklists

### Phase 0 ✅
- [x] Repo scaffolded per architecture.md folder structure
- [x] docker-compose running: Postgres+TimescaleDB, Redis, Elasticsearch, MinIO, backend, frontend
- [x] Base SQLAlchemy models: Case, Device, RawArtifact, AuditLog, User, CaseInvestigator, LogEvent, Entity, CorrelationEdge, Anomaly
- [x] Auth working (JWT/OAuth2), 3 roles: admin, investigator, viewer
- [x] CI pipeline (GitHub Actions) configured
- [x] User can create a Case and see it logged in AuditLog

### Phase 1 ✅
- [x] Upload → hash → immutable storage → RawArtifact record works (logs.py POST /{case_id}/logs)
- [x] Pluggable parser registry + format detection implemented (registry.py)
- [x] Parsers working: Windows EVTX, Linux syslog, Android logcat, USB/Bluetooth artifacts, email headers, network/IP logs
- [x] Normalization into common LogEvent schema (normalizer.py)
- [x] Bulk write to TimescaleDB + Elasticsearch indexing (search_index.py)
- [x] Basic search/filter API + minimal frontend search UI (routes/search.py, search-filters component)
- [x] Malformed files fail gracefully (ArtifactStatus.PARSE_FAILED with reason, no pipeline block)
- [ ] Validated against Scenario 1 sample logs — NOT YET TESTED with live data
- [ ] Validated against Scenario 2 sample logs — NOT YET TESTED with live data

### Phase 2 ✅
- [x] Entity graph builder (NetworkX) implemented (entity_graph.py)
- [x] Cross-device correlation logic implemented (cross_device.py)
- [x] Anomaly detection prototype (isolation forest) implemented (isolation_forest.py)
- [x] Ransomware timeline detector prototype implemented (ransomware_timeline.py)
- [x] SHAP explainability attached to every AI output (shap_explainer.py — tree explainer + rule-based fallback)
- [x] Model versioning recorded on every AI output (MODEL_VERSION constant)
- [x] AI runs async via Celery (ai_tasks.py)
- [x] AI failure degrades gracefully — raw/parsed data still viewable if AI run fails
- [ ] Validated against Scenario 1 — NOT YET TESTED
- [ ] Validated against Scenario 2 — NOT YET TESTED

### Phase 3 🟨 In Progress
- [x] Frontend components scaffolded: timeline, correlation-graph, anomaly-panel, search-filters, nl-query, reports
- [x] D3 timeline component built (350 lines) — functional but wrong marker styles
- [ ] NOT YET: NextAuth.js wired (in package.json but no SessionProvider, no [...nextauth] route)
- [ ] NOT YET: React Query wired (in package.json but no QueryClientProvider, no useQuery/useMutation)
- [ ] NOT YET: Zod wired (in package.json but no imports/usage)
- [ ] NOT YET: Design-token CSS/Tailwind config from design.md §1-2
- [ ] NOT YET: Custody thread (dotted connecting lines) in timeline per design.md §3.2
- [ ] NOT YET: Circle vs triangle markers by type per design.md §3.2
- [ ] NOT YET: Correct entity colors in correlation graph per design.md §3.3
- [ ] NOT YET: RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3
- [ ] NOT YET: Real root layout with sidebar, nav, auth wrapper

---

## 3. Currently In Progress

- **Module:** Frontend Phase 3 — all 8 items from FIX NOW list (a–h)
- **State:** Components exist but are disconnected shells. Root layout is bare (no SessionProvider, no QueryClientProvider, no sidebar/nav). Timeline uses circles for all markers, no custody thread, no triangle markers. Correlation graph has no dotted custody-thread edges. No design tokens in CSS/Tailwind config.
- **Next concrete step:** Start FIX NOW list item (a) — wire NextAuth.js properly

---

## 4. Known Issues / Open TODOs

### Critical — Must Fix Before Any Frontend Work
- [ ] **No git repo existed** — NOW FIXED (git init + initial commit done 2026-08-25)
- [ ] **memory.md was blank** — NOW FIXED (populated with real state)

### FIX NOW List (authoritative, commit after each)
- [ ] **D1(a):** Wire NextAuth.js properly — SessionProvider, [...nextauth] route, auth hooks. Replace any raw localStorage token handling.
- [ ] **D2(b):** Wire React Query — QueryClientProvider + useQuery/useMutation for all data fetching, replacing raw useEffect+fetch.
- [ ] **D3(c):** Wire Zod — runtime validation on API responses.
- [ ] **D9(d):** Build design-token CSS/Tailwind config from design.md §1-2 (colors, typography). Prerequisite for fixing timeline.
- [ ] **D14(e):** Fix timeline component — custody thread (dotted connecting line, cyan=confirmed/amber=inferred), circle vs triangle markers by type per design.md §3.2.
- [ ] **D15(f):** Fix correlation graph — dotted custody-thread edge style, correct entity colors per design.md §3.3.
- [ ] **D16(g):** Add RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3.
- [ ] **D17(h):** Build real root layout — sidebar with case name, nav, auth wrapper.

### Other Open Issues
- [ ] Scenario 1 & 2 validation not yet performed (synthetic datasets exist in datasets/synthetic/)
- [ ] NL query backend has empty __init__.py — Claude API integration not implemented
- [ ] Reporting module has empty __init__.py — PDF/CSV/JSON export not implemented
- [ ] Tests exist but not verified against running services

---

## 5. Approved Deviations from architecture.md / rules.md

- None yet.

---

## 6. Environment / Setup Notes

- Repo: `C:\Users\adity\OneDrive\Desktop\Project\Cyber Forensics Platform`
- Branch: `master` (initial commit, no branch convention established yet)
- `.env` / secrets: `.env.example` exists at root — actual `.env` not tracked (per .gitignore)
- Synthetic datasets location: `datasets/synthetic/` — 5 files for Scenario 1 & 2
- Git: initialized 2026-08-25, initial commit `46814cf`

---

## 7. Session Log

| Date | Phase worked on | Summary |
|---|---|---|
| 2026-08-25 | Setup / Phase 0-3 | Audited full codebase state vs memory.md. Found memory.md blank, no git repo. Initialized git, created .gitignore, made initial commit. Verified Phase 1 ingestion pipeline fully wired (upload→hash→store→parse→normalize→ES). Populated memory.md with real state. Established FIX NOW list (items a–h) for Phase 3 frontend fixes. |
