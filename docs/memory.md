# Project Memory / Progress Log
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Purpose:** This file is the source of truth for "where we left off." Read this FIRST at the start of every session, alongside PRD.md, architecture.md, rules.md, and phases.md. Update it BEFORE ending any session — not after, since sessions can end abruptly.

**Last updated:** [DATE] by [you / agent]

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
| Phase 0 — Setup & Foundations | ⬜ Not started / 🟨 In progress / ✅ Done | ⬜ | |
| Phase 1 — Ingestion, Parsing, Basic Search | ⬜ / 🟨 / ✅ | ⬜ | |
| Phase 2 — Storage + AI Engine Prototype | ⬜ / 🟨 / ✅ | ⬜ | |
| Phase 3 — Dashboard GUI | ⬜ Not started | — | |
| Phase 4 — Reporting & Benchmarking | ⬜ Not started | — | |
| Phase 5 — Productization (stretch) | ⬜ Not started | — | |

*(Update the checkboxes/status above as phases complete. Replace ⬜/🟨/✅ with the real current state.)*

---

## 2. Phase Exit-Criteria Checklists

### Phase 0
- [ ] Repo scaffolded per architecture.md folder structure
- [ ] docker-compose running: Postgres+TimescaleDB, Redis, Elasticsearch, MinIO, backend, frontend
- [ ] Base SQLAlchemy models: Case, Device, RawArtifact, AuditLog
- [ ] Auth working (JWT/OAuth2), 3 roles: admin, investigator, viewer
- [ ] CI pipeline passes on clean PR
- [ ] User can create a Case and see it logged in AuditLog

### Phase 1
- [ ] Upload → hash → immutable storage → RawArtifact record works
- [ ] Pluggable parser registry + format detection implemented
- [ ] Parsers working: Windows EVTX, Linux syslog, Android logcat, USB/Bluetooth artifacts, email headers, network/IP logs
- [ ] Normalization into common LogEvent schema
- [ ] Bulk write to TimescaleDB + Elasticsearch indexing
- [ ] Basic search/filter API + minimal frontend search UI
- [ ] Malformed files fail gracefully (recorded reason, no pipeline block)
- [ ] Validated against Scenario 1 sample logs (PC + Android)
- [ ] Validated against Scenario 2 sample logs (Windows system/app logs)

### Phase 2
- [ ] Entity graph builder (NetworkX) implemented
- [ ] Cross-device correlation logic implemented
- [ ] Anomaly detection prototype (isolation forest) implemented
- [ ] Ransomware timeline detector prototype implemented
- [ ] SHAP explainability attached to every AI output — spot-checked in DB
- [ ] Model versioning recorded on every AI output — spot-checked in DB
- [ ] AI runs async via Celery, confirmed non-blocking on large log sets
- [ ] AI failure degrades gracefully — raw/parsed data still viewable if AI run fails
- [ ] Validated against Scenario 1: file hash correctly correlated PC → USB/Bluetooth/email → mobile
- [ ] Validated against Scenario 2: chronologically correct timeline, download → execution → encryption

---

## 3. Currently In Progress

*(Fill this in before ending any session — what file/module is mid-work, and what the next concrete step is.)*

- **File/module:** [e.g. `backend/app/ai_engine/anomaly/isolation_forest.py`]
- **State:** [e.g. "model trains, but SHAP explanation not yet wired into API response"]
- **Next concrete step:** [e.g. "wire shap_explainer.py output into Anomaly.explanation_json field"]

---

## 4. Known Issues / Open TODOs

*(Bugs, shortcuts taken, or things intentionally deferred — so a fresh session doesn't "fix" something on purpose or re-discover the same bug.)*

- [ ] [example] Android USB/Bluetooth parser only handles the synthetic dataset's log format — needs generalizing before real-world logs
- [ ] [example] Anomaly detection thresholds are placeholder values — need tuning against ground truth once benchmarking (Phase 4) begins

---

## 5. Approved Deviations from architecture.md / rules.md

*(Anything intentionally different from the original docs, with the reason — so the agent doesn't silently "correct" it back.)*

- [example] None yet.

---

## 6. Environment / Setup Notes

*(Anything a fresh session needs to know to get the dev environment running — not covered elsewhere.)*

- Repo: [path/URL]
- Branch convention: [e.g. `phase-N-<feature>`, merged to `main` at phase completion]
- `.env` / secrets: [where they live, NOT the values themselves]
- Synthetic datasets location: `datasets/synthetic/` per architecture.md — [note any additions made]

---

## 7. Session Log

*(Optional running log — one line per session, oldest at top or newest at top, your call. Useful for spotting drift over time.)*

| Date | Phase worked on | Summary |
|---|---|---|
| [DATE] | Phase 0 | [what got done] |
| [DATE] | Phase 1 | [what got done] |
| [DATE] | Phase 2 | [what got done] |
