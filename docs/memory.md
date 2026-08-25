# Project Memory / Progress Log
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Purpose:** This file is the source of truth for "where we left off." Read this FIRST at the start of every session, alongside PRD.md, architecture.md, rules.md, and phases.md. Update it BEFORE ending any session — not after, since sessions can end abruptly.

**Last updated:** 2026-08-25 (session 2) by agent

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
| Phase 3 — Dashboard GUI | 🟨 In Progress | ⬜ | FIX NOW: (a) NextAuth done (not runtime-verified), (b) React Query provider only, pages not migrated — see checklist |
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
- [x] NextAuth.js code wired — SessionProvider in providers.tsx, [...nextauth] route, lib/auth.ts hooks, localStorage token handling removed (commits 98b7e94, ef9c4a2). ⚠️ Code exists only — NOT runtime-verified (no login flow tested; node_modules not installed, so not even typecheck-verified)
- [ ] NextAuth runtime verification — actual login against running backend
- [x] React Query provider wired — QueryClientProvider in providers.tsx (commit 8b0b00c). ⚠️ Provider only — NOT typecheck-verified (node_modules absent), no page uses it yet
- [ ] React Query page migration — ALL data fetching still raw useEffect+fetch; zero useQuery/useMutation usages (grep-verified 2026-08-25 session 2)
- [ ] NOT YET: Zod wired (in package.json but zero imports/usage — grep-verified)
- [ ] NOT YET: Design-token CSS/Tailwind config from design.md §1-2
- [ ] NOT YET: Custody thread (dotted connecting lines) in timeline per design.md §3.2
- [ ] NOT YET: Circle vs triangle markers by type per design.md §3.2
- [ ] NOT YET: Correct entity colors in correlation graph per design.md §3.3
- [ ] NOT YET: RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3
- [ ] NOT YET: Real root layout with sidebar, nav, auth wrapper

---

## 3. Currently In Progress

- **Module:** Phase 3 frontend — FIX NOW item **D2(b): React Query** (mid-work)
- **State:** `QueryClientProvider` wired into `frontend/components/providers.tsx` inside SessionProvider (commit 8b0b00c). Pages untouched: every page under `frontend/app/**` still fetches via raw useEffect+fetch; zero useQuery/useMutation imports anywhere (grep-verified). Typed API helpers live in `frontend/lib/api-client.ts` (still plain fetch wrappers).
- **Next concrete step:** Migrate data fetching to useQuery/useMutation — start with cases list (`app/cases/page.tsx`) and case detail (`app/cases/[caseId]/page.tsx`), then timeline/correlation/anomalies/search pages. Keep fetchers centralized in lib/api-client.ts. Commit when pages compile (`npm install` first — node_modules currently absent, so nothing typechecks locally yet).

---

## 4. Known Issues / Open TODOs

### Critical — Must Fix Before Any Frontend Work
- [ ] **No git repo existed** — NOW FIXED (git init + initial commit done 2026-08-25)
- [ ] **memory.md was blank** — NOW FIXED (populated with real state)

### FIX NOW List (authoritative, commit after each)
- [x] **D1(a):** Wire NextAuth.js properly — DONE (commits 98b7e94, ef9c4a2). ⚠️ Not runtime-verified: login flow untested, deps not installed. Verification tracked as its own Phase 3 checklist item.
- [ ] **D2(b):** Wire React Query — IN PROGRESS: provider committed (8b0b00c); page migration to useQuery/useMutation pending (see §3 for exact next step).
- [ ] **D3(c):** Wire Zod — runtime validation on API responses.
- [ ] **D9(d):** Build design-token CSS/Tailwind config from design.md §1-2 (colors, typography). Prerequisite for fixing timeline.
- [ ] **D14(e):** Fix timeline component — custody thread (dotted connecting line, cyan=confirmed/amber=inferred), circle vs triangle markers by type per design.md §3.2.
- [ ] **D15(f):** Fix correlation graph — dotted custody-thread edge style, correct entity colors per design.md §3.3.
- [ ] **D16(g):** Add RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3.
- [ ] **D17(h):** Build real root layout — sidebar with case name, nav, auth wrapper.

### Other Open Issues
- [ ] node_modules NOT installed in frontend — nothing typechecks/builds locally; run `npm install` before verifying any frontend work
- [ ] Scenario 1 & 2 validation not yet performed (synthetic datasets exist in datasets/synthetic/)
- [ ] NL query backend has empty __init__.py — Claude API integration not implemented
- [ ] Reporting module has empty __init__.py — PDF/CSV/JSON export not implemented
- [ ] Tests exist but not verified against running services
- [ ] Process note: prior session ended without updating memory.md — items (a)+(b-partial) sat unlogged until session 2 reconciled it. Reminder stands: update this file BEFORE ending every session.

---

## 5. Approved Deviations from architecture.md / rules.md

- None yet.

---

## 6. Environment / Setup Notes

- Repo: `C:\Users\adity\OneDrive\Desktop\Project\Cyber Forensics Platform`
- Branch: `master`
- `.env` / secrets: `.env.example` exists at root — actual `.env` not tracked (per .gitignore)
- Synthetic datasets location: `datasets/synthetic/` — 5 files for Scenario 1 & 2
- Git: initialized 2026-08-25, initial commit `46814cf`; latest as of session 2: `ef9c4a2` (a), `8b0b00c` (b partial)
- Branch convention: still `master`, no feature branches used yet
- frontend/node_modules NOT installed — no local typecheck/lint possible until `npm install`

---

## 7. Session Log

| Date | Phase worked on | Summary |
|---|---|---|
| 2026-08-25 | Setup / Phase 0-3 | Audited full codebase state vs memory.md. Found memory.md blank, no git repo. Initialized git, created .gitignore, made initial commit. Verified Phase 1 ingestion pipeline fully wired (upload→hash→store→parse→normalize→ES). Populated memory.md with real state. Established FIX NOW list (items a–h) for Phase 3 frontend fixes. |
| 2026-08-25 (session 2) | Phase 3 | Resume/cleanup session. memory.md was stale: item (a) NextAuth had been completed & committed (98b7e94, ef9c4a2) but never logged — flagged mismatch, verified artifacts on disk ([...nextauth] route, lib/auth.ts), marked done-with-caveat (not runtime-verified; node_modules absent). Committed half-finished D2(b) React Query provider (8b0b00c) — pages still raw useEffect+fetch. Synced all sections; next step = migrate pages to useQuery/useMutation per §3. No new features built this session. |
