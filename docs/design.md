# Design System
## AI-Based Log Investigation Framework for Next-Generation Cyber Forensics

**Version:** 1.0
**Companion to:** PRD.md, architecture.md, rules.md, phases.md

---

## 0. Design Brief & Direction

**Subject:** A forensic evidence workspace, not a marketing product. Investigators live in this screen for hours tracing timelines, hashes, and IP trails that may end up in a legal case file. The design should feel like a **secure evidence room crossed with a control room** — precise, low-glare, built for long sessions and high-stakes accuracy — not a SaaS dashboard trying to look exciting.

**Audience:** Cyber-forensic investigators, SOC analysts, law-enforcement cybercrime units. Expert users, data-dense workflows, low tolerance for decoration that slows them down.

**The page's single job:** Let an investigator go from "raw logs uploaded" to "I trust this timeline enough to put my name on it" as fast and as legibly as possible.

**Signature element:** The **custody thread** — a continuous, dotted/stitched line (visually referencing a sealed evidence bag's tamper-tape and a "red string" investigation board at once) that physically connects every timeline event, correlation edge, and report citation back to its raw source artifact. It is the one motif that appears everywhere confidence and provenance need to be visible, and nowhere else — it is not used decoratively.

**Why not the AI-default looks:** No warm cream/terracotta (too soft/consumer for evidentiary work), no acid-green-on-black cliché, no broadsheet columns (this is an application, not an article). Instead: a **cool, desaturated slate-navy base** (control-room, not "hacker" green-on-black) with **evidence-tag amber** as the single warm accent, used exactly like a physical evidence tag would be used — sparingly, to mark something that needs attention.

---

## 1. Color System

### 1.1 Core Palette (named tokens, 6 hex values)

| Token | Hex | Role |
|---|---|---|
| `--ink-950` (Base) | `#0E1420` | App background — desaturated blue-black, "control room at night," not pure black |
| `--slate-800` (Surface) | `#1A2233` | Panels, cards, sidebars — one step up from base |
| `--slate-600` (Line) | `#33415A` | Borders, dividers, inactive strokes |
| `--fog-200` (Text-on-dark) | `#C9D2E0` | Primary body text on dark surfaces |
| `--evidence-amber` (Accent/Warn) | `#D98E33` | The one warm accent — evidence tags, "needs review," pending AI findings |
| `--trace-cyan` (Confirmed/Data) | `#4FB8C4` | Confirmed correlations, active data links, the custody thread itself |

### 1.2 Semantic / Status Colors (derived, not arbitrary)
| State | Hex | Usage |
|---|---|---|
| Critical / High-severity anomaly | `#C9483F` (muted crimson, never neon red) | Ransomware detection, critical alerts only — used rarely, so it retains weight |
| Medium severity | `--evidence-amber` `#D98E33` | Anomalies needing investigator review |
| Low / informational | `--trace-cyan` `#4FB8C4` | Confirmed, low-risk correlation |
| Success / verified integrity | `#5FA777` (muted forensic green, desaturated — not "hacker green") | Hash verified, chain of custody intact |
| Disabled / archived | `#5A6478` | Closed cases, read-only states |

### 1.3 Light Mode (secondary, for report/print contexts only)
Reports exported as PDF and any printable/court-facing view use a **light, paper-like mode** — because a dark-mode PDF is unusable evidence documentation:

| Token | Hex | Role |
|---|---|---|
| `--paper-50` | `#F7F5F0` | Report background |
| `--ink-900-print` | `#1A1A1A` | Report body text |
| `--rule-line` | `#B8B2A6` | Report table/section rules |
| Accent (print) | `#B5651D` (darker amber for print contrast) | Flags/callouts in printed reports |

This is a deliberate split: **the working dashboard is dark** (long sessions, low glare, data-density), **the exported report is light** (legibility, printability, evidentiary neutrality — a courtroom exhibit should not look like a hacker terminal).

### 1.4 Color Rules
- Amber and crimson are reserved exclusively for AI-flagged/severity states — never used for ordinary UI chrome (buttons, nav). This keeps their meaning unambiguous — if it's amber, something needs a human's attention.
- Cyan (`--trace-cyan`) is reserved for anything tied to **evidence provenance**: the custody thread, confirmed correlation edges, "verified" badges. It should never be used as a generic "brand blue."
- No gradients on data or evidence elements. Gradients are permitted only in the login/auth screen background (a single, very subtle radial vignette) — everywhere else, flat color signals trustworthiness and print-safety.

---

## 2. Typography

### 2.1 Typeface Roles
| Role | Typeface | Why |
|---|---|---|
| **Display** (case titles, section headers, report headers) | **IBM Plex Sans Condensed**, Semibold | Has an official, "case-file stamp" character — condensed width reads as documentation, not marketing, without resorting to a cliché slab-serif |
| **Body / UI** | **IBM Plex Sans**, Regular/Medium | Pairs natively with the display face (same type family, different width) — high legibility at small sizes for long dashboard sessions |
| **Data / Utility** (hashes, IPs, timestamps, file paths, log excerpts, code) | **JetBrains Mono** | Distinct monospace with clearly disambiguated characters (0/O, 1/l/I) — critical when a misread hash or IP could matter |

Using one type family (IBM Plex) across display and body, plus one dedicated mono face for data, avoids the generic "Inter everywhere" template feel while staying disciplined — the personality comes from **width and weight contrast**, not from mixing unrelated families.

### 2.2 Type Scale
| Token | Size / Line-height | Weight | Use |
|---|---|---|---|
| `display-lg` | 32px / 38px | Semibold, Condensed | Case title on case overview page |
| `display-sm` | 22px / 28px | Semibold, Condensed | Section headers (Timeline, Correlation, Anomalies) |
| `body-lg` | 16px / 24px | Regular | Primary reading text, report body |
| `body-sm` | 14px / 20px | Regular | Dashboard UI text, table cells |
| `label` | 12px / 16px | Medium, uppercase, +0.04em tracking | Field labels, status badges, eyebrows *(used only where they label real metadata — never decorative)* |
| `mono-md` | 14px / 20px | Regular | IPs, hashes, file paths inline in UI |
| `mono-sm` | 12px / 18px | Regular | Timestamps, log excerpt previews, audit trail entries |

### 2.3 Typographic Rules
- Every hash, IP address, file path, or timestamp is **always** set in `JetBrains Mono`, in every context (dashboard, tooltips, reports) — this becomes a learned visual signal: *monospace = verifiable evidentiary data*, proportional = interpretation/narrative.
- Uppercase + tracked labels (`label` token) are reserved for genuine field labels (e.g., "SOURCE IP", "SHA-256", "REVIEWED BY") — never used as generic decorative eyebrows.
- No italic. In a forensic context, italic reads as "uncertain" — instead, uncertainty (AI confidence < threshold) is communicated with the amber color token and an explicit confidence percentage, never a type style.

---

## 3. Layout

### 3.1 Grid & Density
- 12-column grid, 8px base spacing unit. Dashboard views default to **dense** mode (compact row height, minimal whitespace) — investigators are scanning volume, not being sold to. A "comfortable" density toggle is available per user preference but dense is default.
- Panels use `--slate-800` on `--ink-950`, with a single 1px `--slate-600` border — no drop shadows on dark surfaces (shadows read as "floating card" UI language borrowed from marketing sites; this tool uses flat, stacked panels like a physical case file instead).

### 3.2 Timeline Layout (Signature Component)
```
┌─────────────────────────────────────────────────────────────┐
│  CASE #4471 — Insider Exfiltration          [●] Investigating │
├─────────────────────────────────────────────────────────────┤
│  09:14  ●┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│         PC-04771  │  file "Q3_financials.xlsx" copied → USB   │
│                                                                │
│  09:17  ●┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│         MOBILE-2291 │ same file hash appears on device        │
│         └─ 94% confidence match  [view evidence]              │
│                                                                │
│  09:22  ⚠┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│         MOBILE-2291 │ file attached to email → external IP    │
└─────────────────────────────────────────────────────────────┘
```
- The dotted horizontal rule (`┄`) *is* the custody thread — rendered in `--trace-cyan` for confirmed links, `--evidence-amber` for AI-inferred/unconfirmed links, dashed opacity-stepped to literally show "how sure are we this connects."
- Each node is a filled circle (confirmed, cyan) or a warning triangle (anomaly, amber/crimson by severity) — never generic dots for everything; the marker shape itself carries meaning.

### 3.3 Correlation Graph
- Force-directed graph (D3), nodes colored by entity type (device = slate, file = fog, IP = trace-cyan, user = amber outline), edges drawn as the same custody-thread dotted stroke style as the timeline, for visual consistency between the two views of the same underlying data.

---

## 4. Motion & Animation

**Direction: motion is evidentiary, not decorative.** In a tool used to communicate serious findings (data theft, ransomware, potential crime), excess animation reads as untrustworthy. Every motion below exists to communicate *state change* or *causal connection* — nothing is ambient or purely atmospheric.

| Moment | Motion | Purpose |
|---|---|---|
| **Timeline load** | Custody thread draws itself left-to-right, ~600ms, ease-out, nodes fade/pop in sequence as the thread reaches them | Reinforces that the timeline is *reconstructed*, not just displayed — mirrors the product's actual job |
| **New correlation found** (async AI job completes) | The relevant thread segment briefly pulses from amber → cyan once confirmed, 400ms | Makes AI state transitions (unconfirmed → confirmed) legible without a modal/toast interrupting the investigator |
| **Anomaly flagged** | Severity badge does a single soft scale-in (1.0 → 1.04 → 1.0, 200ms) — no looping pulse, no continuous blink | A one-time attention cue; looping/blinking alerts cause alarm fatigue in analyst tools and are explicitly avoided |
| **Panel/route transitions** | 150ms crossfade only — no slide, no 3D transforms | Keeps navigation fast and low-distraction across long sessions |
| **Hover states** (buttons, timeline nodes, graph nodes) | 100ms color/border transition only | Immediate, precise feedback — no bounce/spring easing anywhere in the product; springs read as playful, wrong register for this tool |
| **3D usage** | **Deliberately none in the working dashboard.** The correlation graph is 2D force-directed, not a 3D node cloud. | 3D graph visualizations look impressive in demos but reduce actual readability of who's-connected-to-what, which is the one thing this tool cannot compromise on. The one place a subtle 3D-ish effect is allowed: a very slight parallax (2–3px) on the login screen's background vignette — atmosphere only, never on data. |
| **Reduced motion** | All of the above respect `prefers-reduced-motion`: thread "draws in" becomes an instant fade, pulses become instant color swaps | Accessibility floor, non-negotiable |

**Explicitly avoided:** particle effects, glassmorphism/blur-heavy panels, skeleton shimmer loaders (use a simple static placeholder + progress %), confetti/celebration animations on report export (a forensic report export is not a "success!" moment), looping ambient background animation.

---

## 5. Iconography & Data Visualization

- Icon set: **Lucide** (already available per `architecture.md` frontend libraries) — outline style, 1.5px stroke, matched to the condensed/precise type direction. No filled/glyph icons except for the two custody-thread node markers (filled circle = confirmed, filled triangle = anomaly), which are intentionally distinct from the rest of the icon language so they read as *data*, not *chrome*.
- Charts (Recharts, per `architecture.md`): flat fills only, palette drawn strictly from Section 1 tokens, gridlines in `--slate-600` at 40% opacity, no 3D bar/pie charts ever — 3D charts distort magnitude and have no place in evidentiary reporting.
- Status badges use the **evidence-tag shape**: a small rectangle with a single die-cut notch on the left edge (referencing a physical evidence tag) — this is the one custom iconographic shape in the system, used consistently for case status, artifact status, and report status, and nowhere else.

---

## 6. Component Notes

| Component | Treatment |
|---|---|
| Buttons | Flat fill (`--slate-600` default, `--trace-cyan` primary action, `--evidence-amber` only for "Review flagged finding" actions), 4px border-radius — small radius reads as precise/official, not the fully-rounded "friendly SaaS" default |
| Inputs | Flat, 1px `--slate-600` border, focus state = 2px `--trace-cyan` outline (visible keyboard focus is mandatory per accessibility floor) |
| Tables (log/event lists) | Zebra striping via 4% opacity `--fog-200` on alternate rows, monospace for all data columns, proportional font only for human-written annotations |
| Modals | Reserved for destructive/high-consequence actions only (finalize report, delete case) — everything else happens inline/in-panel, since modals interrupt an investigator's train of thought during analysis |
| Empty states | Written in the interface's voice, action-oriented per `rules.md`/writing guidance — e.g., "No logs ingested yet. Upload artifacts to begin building this case's timeline." with a direct upload action, not a generic illustration |

---

## 7. Accessibility Floor (non-negotiable)
- WCAG AA contrast minimum for all text/background pairs in both dark (dashboard) and light (report) modes — verified against the exact tokens in Section 1, not adjusted ad hoc per component.
- Visible 2px focus ring (`--trace-cyan`) on every interactive element, keyboard-navigable timeline and graph views.
- `prefers-reduced-motion` respected everywhere per Section 4.
- Color is never the only signal: every severity/status color pairing also carries a text label and/or distinct icon shape (per Section 5) so the system remains legible for color-blind users.
- Minimum touch/click target 40×40px in dense mode, 44×44px in comfortable mode.

---

## 8. Summary Token Reference

```
Base:        #0E1420
Surface:     #1A2233
Line:        #33415A
Text:        #C9D2E0
Accent:      #D98E33  (evidence-amber — review/warn)
Data/Trace:  #4FB8C4  (trace-cyan — confirmed/provenance)
Critical:    #C9483F
Verified:    #5FA777

Display:     IBM Plex Sans Condensed, Semibold
Body:        IBM Plex Sans, Regular/Medium
Data/Mono:   JetBrains Mono, Regular

Motion:      functional only — thread-draw, one-time pulse, 100–600ms, no springs, no loops, no 3D on data
Signature:   the custody thread — dotted provenance line linking every timeline node, graph edge, and report citation to its source artifact
```
