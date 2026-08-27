# Project Memory / Progress Log
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Purpose:** This file is the source of truth for "where we left off." Read this FIRST at the start of every session, alongside PRD.md, architecture.md, rules.md, and phases.md. Update it BEFORE ending any session — not after, since sessions can end abruptly.

**Last updated:** 2026-08-27 (session 7) by agent

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
| Phase 3 — Dashboard GUI | 🟨 In Progress | 🟨 | NextAuth ✅ runtime-verified. React Query ✅ all pages migrated (049ab75). TS clean. Zod ✅ (7ab8861). Design tokens ✅ (a82a8a1). Timeline ✅ (067b7c6). Correlation graph ✅ (6e5a562 + 83cbed5) — puppeteer-verified 11/11. RBAC ✅ backend API-layer RUNTIME-VERIFIED (cea2baa, 13/13 tests pass); frontend role gates code-verified (tsc clean, logic correct) but NOT browser-tested (frontend dev server failed to start — process spawn error on Windows). Remaining: root layout, browser-verify frontend role gates, Scenario 1/2 validation |
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
- [x] Custody thread (dotted connecting lines) in timeline per design.md §3.2 — DONE (067b7c6)
- [x] Circle vs triangle markers by type per design.md §3.2 — DONE (067b7c6): circle=confirmed, triangle=anomaly
- [x] Correlation graph entity colors + custody-thread edges per design.md §3.3 — DONE (6e5a562 + 83cbed5): device #33415A (slate-600), hash removed from ENTITY_COLORS (falls back to #6B8AAE), user amber-outline, dotted edges cyan/amber by confidence. Puppeteer-verified 11/11 DOM assertions (6 nodes + 5 edges). Legend auto-updates (no hash entry since removed from map).
- [x] RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3 — ✅ RUNTIME-VERIFIED (cea2baa + 9407b41). Backend: `require_case_access` dependency (ADMIN sees all, others must be assigned via CaseInvestigator — confirmed create_case inserts CaseInvestigator row at cases.py:55), self-registration locked to VIEWER role (prevents privilege escalation), 6 GET endpoints now enforce case-access check, case-update ownership check added. Frontend: `useRole()` hook + `<RoleGate>` component in `lib/rbac.tsx`, cases list/case detail/anomaly panel action buttons hidden for viewers. Test script: `scripts/test-rbac.ps1` — **13/13 API tests PASSED against live backend** (Docker rebuilt with cea2baa changes, all containers healthy). **Caveat: frontend browser verification NOT performed** — `npm run dev` failed with Win32 spawn error on Windows; RoleGate logic is code-verified (tsc clean, reads session.user.role, conditionally renders) but should be browser-tested in next session.
- [ ] NOT YET: Real root layout with sidebar, nav, auth wrapper

---

## 3. Currently In Progress

- **Module:** Phase 3 — D17(h) Root layout (next up)
- **State:** D1(a) NextAuth runtime-verified. D2(b) React Query migration complete (049ab75). D3(c) Zod DONE (7ab8861). D9(d) Design tokens DONE (a82a8a1). D14(e) Timeline DONE (067b7c6). D15(f) Correlation graph DONE (6e5a562 + 83cbed5) — puppeteer-verified 11/11. D16(g) RBAC ✅ RUNTIME-VERIFIED (cea2baa + 9407b41) — backend API-layer enforcement verified 13/13 tests pass against live backend; frontend role gates code-verified (useRole hook, RoleGate component, tsc clean) but NOT browser-tested (npm run dev failed on Windows). TS clean.
- **Next concrete step:** D17(h) — Build real root layout with sidebar (case name), navigation, auth wrapper (login/logout, role badge). Requires reading design.md for layout spec. Also: browser-verify frontend role gates (start dev server, log in as viewer, confirm buttons hidden).

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
- [x] **D14(e):** Fix timeline component — DONE (067b7c6): custody thread (dotted lines between consecutive events per device row, cyan=confirmed, amber=AI-inferred), circle markers for confirmed, triangle markers for anomalies. Mock data route (`/__mock__` caseId) for visual verification. Puppeteer-verified: 6/6 markers (3 circles + 3 triangles), 3/3 custody threads (1 cyan + 2 amber), 3 device labels, legend present.
- [x] **D15(f):** Fix correlation graph — DONE (6e5a562 + 83cbed5): custody-thread dotted edges (4,3 dasharray, cyan ≥70% / amber <70%), user amber-outline (stroke=#D98E33, fill=none), enhanced legend with edge swatches. Color deviations fixed: device corrected to #33415A (slate-600), hash removed from ENTITY_COLORS (falls back to #6B8AAE). Puppeteer-verified 11/11 DOM assertions (6 nodes + 5 edges). Legend auto-updates (no hash entry). `__mock__` route removed.
- [x] **D16(g):** Add RBAC-aware UI (viewer/investigator/admin) per phases.md Phase 3 — ✅ RUNTIME-VERIFIED (cea2baa + 9407b41). Backend: `require_case_access` dependency (ADMIN=all cases, others must be assigned via CaseInvestigator — confirmed create_case inserts CaseInvestigator row at cases.py:55), self-registration locked to VIEWER (role field removed from RegisterRequest), 6 GET endpoints now enforce case-access (logs, search, anomalies, correlations, entities), case-update ownership check added. Frontend: `useRole()` hook + `<RoleGate>` component (`lib/rbac.tsx`), cases list `+ New Case` hidden for viewers, case detail `+ Add Device` and `+ Upload File` hidden for viewers, anomaly panel Confirm/Dismiss hidden for viewers. **13/13 API tests PASSED** against live backend (Docker rebuilt, all containers healthy). **Caveat: frontend browser verification NOT performed** — `npm run dev` failed with Win32 spawn error; RoleGate logic is code-verified (tsc clean) but should be browser-tested next session.
- [ ] **D17(h):** Build real root layout — sidebar with case name, nav, auth wrapper.

### Process Lessons
- **LESSON (2026-08-26): Phases 0-2 were marked "✅ Done" but had NEVER actually been run.** First live boot of the backend required 5 root-cause fixes (reserved `metadata` attr, wrong registry import path, enum name/value mismatch, duplicate CREATE TYPE from ignored `create_type` kwarg, passlib/bcrypt breakage). Rule going forward: **mark an item verified only when it has actually been executed** — code existing on disk is not verification. Distinguish "code complete" from "runtime verified" in every checklist.
- **LESSON (2026-08-27): PowerShell 5.1 `Invoke-WebRequest` silently swallows exception response bodies.** When a non-2xx HTTP response is thrown as an exception, `$_.Exception.Response.GetResponseStream()` fails with "NonInteractive mode" error in PS 5.1 — the status code and body are lost. Fix: use `curl.exe` with `--data-binary @tempfile` for API testing scripts. The tempfile avoids PowerShell mangling double-quotes in JSON when passed via `-d`.
- **LESSON (2026-08-27): Backend Docker image is built, not volume-mounted.** Code changes to `backend/` are NOT reflected in the running container until `docker compose up -d --build backend worker` is run. Always rebuild after backend code changes before testing.

### Load-Bearing Environment Facts (do not remove without re-testing)
- [ ] Backend Docker image REQUIRES `g++` (not just gcc) — shap 0.44.1 builds from source on python:3.12-slim. Removing it breaks `docker compose build backend`.
- [ ] `bcrypt==4.0.1` is PINNED — passlib 1.7.4 is incompatible with bcrypt>=4.1 at runtime (registration/login 500s). Do not bump bcrypt without replacing passlib.
- [ ] Dev DB has a working seeded-by-hand user for manual testing: **username `testuser`, password `TestPass123!`, role investigator, email test@example.com** (created via POST /api/auth/register). NextAuth login flow verified against this account 2026-08-26.

### Other Open Issues
- [x] **D15(f) correlation graph color deviations (2):** FIXED (83cbed5). Device corrected to #33415A (slate-600 per §1.1); hash removed from ENTITY_COLORS, falls back to #6B8AAE. Puppeteer-verified 11/11.
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
- **Hash entity type in correlation graph falls back to #6B8AAE.** The design.md §3.3 spec defines 4 entity types (device, file, ip, user). Hash is an implementation addition from the backend data model (Entity entity_type includes "hash"). No spec color exists for it. Hash was removed from ENTITY_COLORS map (83cbed5) so it uses the existing code fallback #6B8AAE. This is intentional and verified.
- No other deviations. Entity model attribute renamed to `entity_metadata` (DB column still `metadata`) and enum `values_callable` additions preserve the architecture-defined schema exactly — implementation fixes, not deviations.

---

## 6. Environment / Setup Notes

- Repo: `C:\Users\adity\OneDrive\Desktop\Project\Cyber Forensics Platform`
- Branch: `master`
- `.env` / secrets: `.env.example` exists at root — actual `.env` not tracked (per .gitignore); frontend `.env.local` (untracked) contains NEXT_PUBLIC_API_URL, NEXTAUTH_URL, NEXTAUTH_SECRET (dev-only value)
- Synthetic datasets location: `datasets/synthetic/` — 5 files for Scenario 1 & 2
- Git: initialized 2026-08-25; session-3 commits: `e4a8052` (backend runtime fixes), `5ccdee3` (TS fixes), `049ab75` (React Query migration); session-4 commits: `bc7d3d9` (memory sync), `7ab8861` (Zod wiring), `a82a8a1` (design tokens), `067b7c6` (timeline fix), `6e5a562` (correlation graph fix), `0e259f5` (__mock__ removal), `2dbd73b` (memory.md update). Session-5: no code commits. Session-6: `83cbed5` (D15f color fix), `1e2f542` (memory update), `cea2baa` (D16g RBAC), `cbc4820` (memory update), `20b2a0c` (memory downgrade to code-complete). Session-7: `9407b41` (fix test-rbac.ps1 to use curl.exe), memory.md updated to reflect D16(g) runtime-verified.
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
| 2026-08-26 (session 4) | Phase 0-3 corrections + Zod + tokens + timeline | Cross-checked memory.md vs repo: found 2 stale claims (CI exists but never ran; design tokens partial). Updated memory.md (commit bc7d3d9). Wired Zod in api-client.ts: 9 schemas, all API methods parse responses, types inferred → commit 7ab8861. Zod live-tested 9/9 endpoints against running backend. D9(d) design tokens complete: added disabled color, light-mode tokens (§1.3), type scale (§2.2) → commit a82a8a1. D14(e) timeline fix: custody thread dotted lines (cyan=confirmed/amber=inferred), circle vs triangle markers, mock data route, puppeteer-verified 6/6 markers + 3/3 threads → commit 067b7c6. |
| 2026-08-26 (session 4 continued) | Phase 3 D15(f) correlation graph | Correlation graph rewrite per design.md §3.3: user amber-outline, all edges dotted custody-thread style (cyan ≥70% / amber <70%), enhanced legend with edge swatches. Puppeteer-verified: 6/6 nodes, 5/5 dotted edges, legend present → commit 6e5a562. Mock route + `__mock__` cleanup. Memory.md updated. Note: two color deviations from design.md were present in this commit but not caught until session 5 review (see below). |
| 2026-08-26 (session 5) | Phase 3 D15(f) color deviation review | No code changes. Reviewed correlation graph against design.md §3.3 and §1.1: found two color deviations — (1) device `#64748B` should be `#33415A` (slate-600 per §1.1), (2) hash `#9B7ED8` is invented purple not in any design.md palette (hash not one of §3.3's 4 spec types). Fix plan agreed: device → `#33415A`, hash → remove from ENTITY_COLORS and use existing fallback `#6B8AAE`. Must re-puppeteer after fix. memory.md updated to reflect accurate state. Next session: apply color fixes, verify, commit, then D16(g) RBAC. |
| 2026-08-27 (session 6) | Phase 3 D15(f) color fix + D16(g) RBAC code-complete | Fixed D15(f) color deviations: device corrected to #33415A (slate-600), hash removed from ENTITY_COLORS (falls back to #6B8AAE). Wrote puppeteer DOM assertion script (scripts/verify-correlation-colors.mjs), verified 11/11 pass (6 nodes + 5 edges). Committed 83cbed5. D16(g) RBAC implemented (cea2baa): backend — require_case_access dependency, self-registration locked to VIEWER, 6 GET endpoints enforce case-access, case-update ownership check. Frontend — useRole() hook, RoleGate component, action buttons hidden for viewers. Test script written (scripts/test-rbac.ps1). **D16(g) is CODE-COMPLETE ONLY — Docker was not running, no live verification performed.** Updated memory.md. Next: start Docker, run test-rbac.ps1, browser-verify viewer gates, then D17(h) root layout. |
| 2026-08-27 (session 7) | Phase 3 D16(g) RBAC runtime verification | Corrected memory.md to downgrade D16(g) from "DONE" to "code-complete, NOT runtime-verified" (commit 20b2a0c) — applying session-3 lesson about honest status. Started Docker Desktop, confirmed stack boots (5 containers healthy). Ran migrations (at head). Rebuilt backend image to pick up cea2baa code changes (`docker compose up -d --build backend worker`). First attempt to run test-rbac.ps1 failed: PowerShell 5.1 `Invoke-WebRequest` swallows exception responses (HTTP 0 for all tests). Rewrote test script to use `curl.exe` + temp files (commit 9407b41). **Re-ran: 13/13 RBAC API tests PASSED** against live backend. Confirmed: self-registration locked to VIEWER (no privilege escalation), viewer gets 403 on all write endpoints, investigator gets 403 on unassigned case endpoints. Frontend browser verification NOT performed — `npm run dev` failed with Win32 spawn error on Windows. RoleGate logic is code-verified (tsc clean, reads session.user.role, conditionally renders). Updated memory.md to reflect D16(g) as ✅ runtime-verified (backend) / code-verified (frontend). Next: D17(h) root layout + browser-verify frontend role gates. |
