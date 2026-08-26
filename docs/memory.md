# Project Memory / Progress Log
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Purpose:** This file is the source of truth for "where we left off." Read this FIRST at the start of every session, alongside PRD.md, architecture.md, rules.md, and phases.md. Update it BEFORE ending any session — not after, since sessions can end abruptly.

**Last updated:** 2026-08-26 (session 4) by agent

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
| Phase 0 — Setup & Foundations | 🟨 Nearly done | 🟨 | Runtime-verified 2026-08-26: stack boots, migrations apply, auth works, case-create writes AuditLog. CI workflow `.github/workflows/ci.yml` EXISTS (3 jobs: backend-lint, backend-test, frontend-lint) but has NEVER RUN — triggers on `main` branch while repo is `master`; no remote configured. Branch name must be fixed before CI can execute. |
| Phase 1 — Ingestion, Parsing, Basic Search | 🟨 Code-complete | ⬜ | Pipeline fully wired (upload→hash→store→parse→normalize→ES via Celery), 6 parsers registered, search API + UI exist — but **never exercised end-to-end with real log files** |
| Phase 2 — Storage + AI Engine Prototype | 🟨 Code-complete | ⬜ | All AI components implemented and import cleanly; **never run against actual ingested data** |
| Phase 3 — Dashboard GUI | 🟨 In Progress | ⬜ | NextAuth ✅ runtime-verified; React Query ✅ all pages migrated (049ab75); TS clean. Remaining: Zod, design tokens, timeline/correlation fixes, RBAC UI, root layout |
| Phase 4 — Reporting & Benchmarking | ⬜ Not started | — | |
| Phase 5 — Productization (stretch) | ⬜ Not started | — | |

**Legend:** ✅ verified by execution · 🟨 partially verified / code-complete · ⬜ not verified

---

## 2. Phase Exit-Criteria Checklists

### Phase 0 🟨 (runtime-verified 2026-08-26 unless noted)
- [x] Repo scaffolded per architecture.md folder structure
- [x] docker-compose running: Postgres+TimescaleDB, Redis, Elasticsearch, MinIO, backend — VERIFIED live (all containers healthy; note: compose `frontend` service unused in dev, see §5)
- [x] Base SQLAlchemy models: Case, Device, RawArtifact, AuditLog, User, CaseInvestigator, LogEvent, Entity, CorrelationEdge, Anomaly — VERIFIED: all 3 migrations apply cleanly → 13 tables
- [x] Auth working (JWT/OAuth2), 3 roles: admin, investigator, viewer — VERIFIED: register 201 + login 200 + NextAuth session with role
- [x] CI pipeline (GitHub Actions) configured — **FILE EXISTS** (`.github/workflows/ci.yml`, 73 lines, 3 jobs: backend-lint/ruff, backend-test/pytest, frontend-lint/npm+typecheck). **BUT NEVER EXECUTED:** workflow triggers on `push`/`pull_request` to `main`, repo branch is `master`. No remote configured. Must rename branch to `main` (or fix workflow triggers) + push to GitHub before CI can run. Config exists; execution unverified.
- [x] User can create a Case and see it logged in AuditLog — VERIFIED: `case_created` row present in audit_logs after API case creation

### Phase 1 🟨 — items below are CODE-COMPLETE only (imports clean, never run end-to-end)
- [x] Upload → hash → immutable storage → RawArtifact record works (logs.py POST /{case_id}/logs) *(code-complete)*
- [x] Pluggable parser registry + format detection implemented (registry.py)
- [x] Parsers working: Windows EVTX, Linux syslog, Android logcat, USB/Bluetooth artifacts, email headers, network/IP logs
- [x] Normalization into common LogEvent schema (normalizer.py)
- [x] Bulk write to TimescaleDB + Elasticsearch indexing (search_index.py)
- [x] Basic search/filter API + minimal frontend search UI (routes/search.py, search-filters component)
- [x] Malformed files fail gracefully (ArtifactStatus.PARSE_FAILED with reason, no pipeline block)
- [ ] Validated against Scenario 1 sample logs — NOT YET TESTED with live data
- [ ] Validated against Scenario 2 sample logs — NOT YET TESTED with live data

### Phase 2 🟨 — items below are CODE-COMPLETE only (never run against real ingested data)
- [x] Entity graph builder (NetworkX) implemented (entity_graph.py) *(code-complete)*
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
- [x] NextAuth.js code wired — SessionProvider in providers.tsx, [...nextauth] route, lib/auth.ts hooks, localStorage token handling removed (commits 98b7e94, ef9c4a2). ✅ RUNTIME-VERIFIED 2026-08-26: real HTTP login flow against live backend — session cookie issued, /api/auth/session returns user+role+id+accessToken, authenticated GET /cases renders 200. NEXTAUTH_URL + NEXTAUTH_SECRET pinned in untracked frontend/.env.local (warnings gone; prod needs a real secret)
- [x] React Query provider wired — QueryClientProvider in providers.tsx (commit 8b0b00c), now used by every data page (see next item)
- [x] React Query page migration — DONE (commit 049ab75). All 6 data pages (cases list, case detail, timeline, correlation, anomalies, search) use useQuery/useMutation; zero raw useEffect+fetch data fetching remains in app/**. Auth pages intentionally left on signIn()/direct flow. Verified: tsc clean + authenticated smoke test of all routes → 200
- [x] 8 pre-existing TypeScript errors — FIXED (commit 5ccdee3): tsconfig target es5→ES2017 (Set iteration), explicit D3 selection generics in correlation-graph. `npx tsc --noEmit` is now clean
- [x] Zod wired — runtime validation on ALL API responses (commit 7ab8861): 9 schemas in lib/api-client.ts, types inferred via z.infer, request<T> parses through optional schema, tsc clean
- [x] Design-token CSS/Tailwind config — DONE (§1.1/§1.2/§1.3 colors, §2.1 fonts, §2.2 type scale)
- [ ] NOT YET: Custody thread (dotted connecting lines) in timeline per design.md §3.2
- [ ] NOT YET: Circle vs triangle markers by type per design.md §3.2
- [ ] NOT YET: Correct entity colors in correlation graph per design.md §3.3
- [ ] NOT YET: RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3
- [ ] NOT YET: Real root layout with sidebar, nav, auth wrapper

---

## 3. Currently In Progress

- **Module:** Phase 3 — FIX NOW item **D14(e): Timeline fix** (next up)
- **State:** D1(a) NextAuth runtime-verified. D2(b) React Query page migration complete. D3(c) Zod DONE (7ab8861). D9(d) Design tokens DONE — all §1.1/§1.2/§1.3 colors, §2.1 fonts, §2.2 type scale. TS clean; `npx tsc --noEmit` clean.
- **Next concrete step:** D14(e) Fix timeline component — add custody thread (dotted connecting line, cyan=confirmed/amber=inferred), circle vs triangle markers by type per design.md §3.2.

---

## 4. Known Issues / Open TODOs

### Critical — Must Fix Before Any Frontend Work
- [ ] **No git repo existed** — NOW FIXED (git init + initial commit done 2026-08-25)
- [ ] **memory.md was blank** — NOW FIXED (populated with real state)

### FIX NOW List (authoritative, commit after each)
- [x] **D1(a):** Wire NextAuth.js properly — DONE + RUNTIME-VERIFIED 2026-08-26: real login against live backend, session cookie issued, /api/auth/session returns user+role+id+accessToken, /cases renders authenticated. Dev secret pinned in .env.local.
- [x] **D2(b):** Wire React Query — DONE (049ab75): provider (8b0b00c) + all data pages migrated to useQuery/useMutation. Smoke-tested authenticated on all routes.
- [x] **D3(c):** Wire Zod — DONE (`7ab8861`): 9 Zod schemas (Case, Device, Artifact, LogEvent, Anomaly, CorrelationEdge, Entity, SearchResponse, User) in lib/api-client.ts. All API methods pass schema to request<T> which parses on every response. Types inferred from schemas (no duplicate interfaces). tsc clean. **Note:** commit message says `feat(a)` — typo, should be `feat(D3c)`. Cannot rewrite; this note prevents confusion when scanning git log.
- [x] **D9(d):** Build design-token CSS/Tailwind config — DONE (`a82a8a1`): all §1.1/§1.2/§1.3 colors, §2.1 fonts, §2.2 type scale in tailwind.config.js + globals.css. **Note:** commit message says `feat(a)` — same typo pattern as 7ab8861.
- [ ] **D14(e):** Fix timeline component — custody thread (dotted connecting line, cyan=confirmed/amber=inferred), circle vs triangle markers by type per design.md §3.2.
- [ ] **D15(f):** Fix correlation graph — dotted custody-thread edge style, correct entity colors per design.md §3.3.
- [ ] **D16(g):** Add RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3.
- [ ] **D17(h):** Build real root layout — sidebar with case name, nav, auth wrapper.

### Process Lessons
- **LESSON (2026-08-26): Phases 0-2 were marked "✅ Done" but had NEVER actually been run.** First live boot of the backend required 5 root-cause fixes (reserved `metadata` attr, wrong registry import path, enum name/value mismatch, duplicate CREATE TYPE from ignored `create_type` kwarg, passlib/bcrypt breakage). Rule going forward: **mark an item verified only when it has actually been executed** — code existing on disk is not verification. Distinguish "code complete" from "runtime verified" in every checklist.

### Load-Bearing Environment Facts (do not remove without re-testing)
- [ ] Backend Docker image REQUIRES `g++` (not just gcc) — shap 0.44.1 builds from source on python:3.12-slim. Removing it breaks `docker compose build backend`.
- [ ] `bcrypt==4.0.1` is PINNED — passlib 1.7.4 is incompatible with bcrypt>=4.1 at runtime (registration/login 500s). Do not bump bcrypt without replacing passlib.
- [ ] Dev DB has a working seeded-by-hand user for manual testing: **username `testuser`, password `TestPass123!`, role investigator, email test@example.com** (created via POST /api/auth/register). NextAuth login flow verified against this account 2026-08-26.

### Other Open Issues
- [ ] **CI workflow exists but has never run** — `.github/workflows/ci.yml` present (3 jobs), but triggers on `main` while repo branch is `master`; no remote. Must rename branch or fix triggers + push before CI executes. Config verified on disk; execution status unknown.
- [ ] `next build` (production build) NOT yet run — tsc is clean so it should pass, but unverified. Run before relying on it.
- [x] node_modules NOT installed in frontend — FIXED 2026-08-26 (`npm install` done; package-lock.json committed). Typecheck/lint now possible locally
- [x] 8 TS errors blocking `next build` — FIXED (5ccdee3), tsc clean
- [x] NextAuth env vars NEXTAUTH_URL + NEXTAUTH_SECRET — set in untracked frontend/.env.local (dev value); prod deploy still needs a real secret
- [ ] Scenario 1 & 2 validation not yet performed (synthetic datasets exist in datasets/synthetic/) — blocks honest Phase 1/2 completion. **Also covers Zod schema validation:** all 9 Zod schemas pass against live backend but only verified against empty/near-empty responses (one case, no devices/artifacts/events/anomalies/correlations). Full validation against populated anomaly, correlation, and log-event data should happen when ingesting Scenario 1 & 2 datasets — schemas may need `.nullable()` / optional adjustments once real data shapes appear.
- [ ] NL query backend has empty __init__.py — Claude API integration not implemented
- [ ] Reporting module has empty __init__.py — PDF/CSV/JSON export not implemented
- [ ] Tests exist but not verified against running services
- [ ] Process note: prior session ended without updating memory.md — items (a)+(b-partial) sat unlogged until session 2 reconciled it. Reminder stands: update this file BEFORE ending every session.

---

## 5. Approved Deviations from architecture.md / rules.md

- **Dev frontend runs on host (`npm run dev`, :3000), not via compose `frontend` service.** Reason: hot-reload iteration speed; avoids rebuilding the Docker image on every change. The compose service remains available for prod-like verification later. Consequence: port 3000 must stay free when starting the full compose stack.
- No other deviations. Entity model attribute renamed to `entity_metadata` (DB column still `metadata`) and enum `values_callable` additions preserve the architecture-defined schema exactly — implementation fixes, not deviations.

---

## 6. Environment / Setup Notes

- Repo: `C:\Users\adity\OneDrive\Desktop\Project\Cyber Forensics Platform`
- Branch: `master`
- `.env` / secrets: `.env.example` exists at root — actual `.env` not tracked (per .gitignore); frontend `.env.local` (untracked) contains NEXT_PUBLIC_API_URL, NEXTAUTH_URL, NEXTAUTH_SECRET (dev-only value)
- Synthetic datasets location: `datasets/synthetic/` — 5 files for Scenario 1 & 2
- Git: initialized 2026-08-25; session-3 commits: `e4a8052` (backend runtime fixes), `5ccdee3` (TS fixes), `049ab75` (React Query migration); session-4 commits: `bc7d3d9` (memory sync), `7ab8861` (Zod wiring)
- Branch convention: still `master`, no feature branches used yet
- frontend node_modules installed as of 2026-08-26 — typecheck via `npx tsc --noEmit`
- Full docker stack boots and works end-to-end (postgres/redis/es/minio/backend); run migrations with `docker compose exec -e PYTHONPATH=/app backend alembic upgrade head`
- Frontend dev server runs on :3000 (`npm run dev`); compose `frontend` service NOT used in dev (see §5 deviation)

---

## 7. Session Log

| Date | Phase worked on | Summary |
|---|---|---|
| 2026-08-25 | Setup / Phase 0-3 | Audited full codebase state vs memory.md. Found memory.md blank, no git repo. Initialized git, created .gitignore, made initial commit. Verified Phase 1 ingestion pipeline fully wired (upload→hash→store→parse→normalize→ES). Populated memory.md with real state. Established FIX NOW list (items a–h) for Phase 3 frontend fixes. |
| 2026-08-25 (session 2) | Phase 3 | Resume/cleanup session. memory.md was stale: item (a) NextAuth had been completed & committed (98b7e94, ef9c4a2) but never logged — flagged mismatch, verified artifacts on disk ([...nextauth] route, lib/auth.ts), marked done-with-caveat (not runtime-verified; node_modules absent). Committed half-finished D2(b) React Query provider (8b0b00c) — pages still raw useEffect+fetch. Synced all sections; next step = migrate pages to useQuery/useMutation per §3. No new features built this session. |
| 2026-08-26 (session 3) | Phase 0-3 verification + fixes | First-ever live run of the whole stack. npm install done; found+fixed 5 backend root causes (bcrypt pin, g++ in Dockerfile, reserved metadata attr, wrong registry import, postgresql.ENUM create_type + env.py DATABASE_URL_SYNC) → commit e4a8052. LESSON: Phases 0-2 were "done" but never run. NextAuth runtime-verified with real login (testuser). Fixed 8 TS errors incl. sa.Enum/tsconfig findings → 5ccdee3. D2(b) complete: all 6 data pages migrated to React Query, smoke-tested authenticated → 049ab75. Pinned NEXTAUTH_SECRET in .env.local to stop recompile-induced auth flakiness. Wrap-up verification pass: audit logging CONFIRMED at runtime (user_registered/user_login/case_created rows); discovered CI workflow never existed → Phase 0 item unchecked, Phase 0/1/2 status downgraded to honest 🟨 code-complete/verified states. Next: D3(c) Zod, then CI workflow + Scenario validation to close Phases 0-2 honestly. |
| 2026-08-26 (session 4) | Phase 0-3 corrections + Zod + tokens | Cross-checked memory.md vs repo: found 2 stale claims (CI exists but never ran; design tokens partial). Updated memory.md (commit bc7d3d9). Wired Zod in api-client.ts: 9 schemas, all API methods parse responses, types inferred → commit 7ab8861. Zod live-tested 9/9 endpoints against running backend (empty responses). D9(d) design tokens complete: added disabled color, light-mode tokens (§1.3), type scale (§2.2) to tailwind.config.js + globals.css. |
