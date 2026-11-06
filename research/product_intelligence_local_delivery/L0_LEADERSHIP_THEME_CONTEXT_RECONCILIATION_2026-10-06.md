# L0 leadership / theme context reconciliation (read-only)

**MAIN_PIN:** `892157418ec6b8664d3a0d4ead12011826fc82b4` (`git rev-parse origin/main` after `git fetch origin main`, 2026-10-06).  
**Mastermind overlay pin:** `d1a8e672464d9a90dfe5b3608e071f8a730f3c95` (Mastermind PR #1258).  
**Lane:** read-only; no producer runs, no held-PR checkouts, no Terminal writes.

---

## C0 — #8470 retained-history reader consumer honesty

**Question:** Does the strict reader on macro PR #8470 (head `1537636f53cc24184a16e7a044f066d7e43f2ac4`) ever hand a consumer a replayed or backfilled row **indistinguishable** from retained history?

**Answer:** **Not when the consumer reads the reader’s `mode` field.** On head `1537636f`, `read_ledger_history()` (`engine/rotation_events.py:1176`) assigns each selected row `RECONSTRUCTED_REPLAY` only when `row.get("replayed") is True`, otherwise `RETAINED_LEDGER_UNMARKED` (`engine/rotation_events.py:1415-1418` @ `1537636f`). The reader does **not** call `backfill_leg_names()` (`engine/rotation_events.py:1493` @ `1537636f`); legacy name backfill remains a separate helper used on the nightly `closed_recent` path on main (`engine/rotation_events.py:1402-1403` @ `89215741`). **Residual risk:** ledger rows that are replay-sourced but lack `replayed: true` are classified as `RETAINED_LEDGER_UNMARKED`, not as natural first-seen history—the API still exposes `mode`, but source mis-labeling can mis-bucket. A consumer that drops `mode` and treats all rows as equally “historical” would be dishonest; that is outside the reader contract covered by `tests/test_rotation_events.py::test_read_ledger_history_preserves_native_rows_and_modes` @ `1537636f`.

---

## Q1 — GMI return consumption

### MERGED on `origin/main` (squash SHA + capability)

| PR | Squash SHA | Capability (one line) |
|---|---|---|
| #8485 | `fd2552813811` | `engine/theme_graph/rights_use.py` — per-use capture verdict for selection-cohort internal capture (fail-closed registry snapshot). |
| #8487 | `625d0c71714d` | Independent GMI completion-ruler audit (read-only report). |
| #8488 | `192a46de8be8` | D2E pre-acceptance census on main+#8432 composition (read-only; depends on held D2C/D2D for full acceptance). |
| #8489 | `c0f4a83ce974` | Agent OS / WS-GMI continuation handoff + wave state records. |
| #8490 | `d8f08cffd319` | Wave F Terminal/R2/site consumer census for ThemeState and CTE (read-only). |
| #8493 | `601f87f39924` | Agent OS follow-up + heal main ci-pack-2 readiness exemplar. |
| #8494 | `6fa88a734f88` | Agent OS: Wave F merge recorded; head placeholder hygiene. |

Sources: `research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md:17-28`, `agentos/workstreams/WS-GMI-THEME-GRAPH.md:121-171`.

### HELD (authority + release condition, quoted)

| PR | Head @ read | Holding authority / release (quoted or paraphrased from carrier) |
|---|---|---|
| #8417 | `91bf29070910` | **Sol** — handoff: “**Sol HOLD** — PARKED … Sol release ruling is the next act” (`research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md:20`). Seat comment `IC_kwDOS4LjIs8AAAABZirReg` (2026-10-06): “**HOLD-RELEASED** — Sol release ruling for WS:GMI-THEME-GRAPH D1 / PR #8417” (release posted; PR still **OPEN** unmerged at read time). |
| #8486 | `2e2bcd75ca62` | **PARKED by inheritance** on #8417 — “nothing until #8417 releases; ci-authority FAIL is structural `unsupported_base_ref`” (`research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md:21`). |
| #8455 | `4b38f2501a32` | **Draft / HOLD-FOR-REVIEW. No auto-merge.** (`gh pr view 8455` body). Handoff: “**Sol HOLD** — PARKED” (`research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md:17`). |
| #8432 | `54d17ebcb1c1` | **Sol HOLD** — “never ready/arm/merge” (`research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md:22`). Body: “**latest-base integration checks and action-time release remain pending**. No main merge or runtime activation is claimed.” |
| #8435 | `7429a3e5f6da` | Same Sol hold pattern as #8432 (`research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md:23`). Body: “**expected-head release and protected readback**” required before release. |

### Consumable contract / reader functions on `MAIN_PIN` vs held-only

**May consume today on `89215741` (path:line):**

- `engine/theme_context.py:589` `compute_theme_context`, `:891` `read_context` — `theme_context.v1` producer/consumer (`research/theme_graph/WAVE_F_TERMINAL_R2_CONSUMER_CENSUS_2026-10-05.md:20-21` cites CTE chain).
- `engine/company_theme_exposure/views.py:259` `build_bundle`, `:190` `build_exposures`, `:340` `load_company_generation` — `company_theme_exposure.v1` (+ embedded theme_state receipt per census).
- `scripts/build_company_theme_exposure.py:25` `main` — nightly builder (`.github/workflows/company-intelligence.yml` per census).
- `engine/theme_graph/rights_use.py:140` `current_use_verdict`, `:286` `capture_capability` — merged #8485.
- `engine/theme_graph/store.py:258+` `read_nodes`, `read_edges`, `read_capability`, etc. — graph store readers.
- `engine/us_board_rank.py:2208` `load_theme_context` — basket/theme chip consumer.
- `engine/rotation_events.py:1085` `closed_recent` — tail closure strip only; **no** `read_ledger_history` on main (`rg '^def read_ledger_history' engine/rotation_events.py` @ `89215741` → **no matches**).

**Exist only on held heads — do not consume:**

- `read_ledger_history` — #8470 `1537636f` only (`engine/rotation_events.py:1176` @ `1537636f`).
- `engine/theme_graph/selection_cohort_reads.py` and W3C publication seams — #8486 / #8417 stack (`WS-GMI-THEME-GRAPH.md:141-150`; `rg 'selection_cohort_reads' engine/` @ `89215741` → absent).
- D2C/D2D ontology/PIT vintage readers — #8432 / #8435 heads only.

---

## Q2 — #8470 reader review

**Artifact base:** merge-base `9a2f00a560ab93257a19f35cc62b4c287500a958` … head `1537636f` — `engine/rotation_events.py` +362 lines, `tests/test_rotation_events.py` +227 (`git diff --stat`).

**Public entrypoints on head `1537636f`:** `read_ledger_history` (`engine/rotation_events.py:1176`); helpers `_history_iso_date` (:1121), `_history_leg_key` (:1133), `_history_invalid` (:1143). Pre-existing public API unchanged in diff (e.g. `closed_recent` :1085, `backfill_leg_names` :1493).

**`gh pr checks 8470` (once, 2026-10-06):** all binding packs **pass** except **`ci-authority/codex/merge-queue-pilot` FAIL** (standing inactive context per packet law — excluded). Quoted line: `ci-authority/codex/merge-queue-pilot	fail	0	https://github.com/mastermindx-market-intelligence/macro/runs/111648533997`.

### Adversarial matrix

| Case | Verdict | Evidence |
|---|---|---|
| (a) Replay vs retained-unmarked | **HANDLED** | `row_mode` assignment `engine/rotation_events.py:1415-1418` @ `1537636f`; `tests/test_rotation_events.py::test_read_ledger_history_preserves_native_rows_and_modes` @ `1537636f`. |
| (b) Malformed row before retention boundary | **HANDLED** | Fail-closed `_history_invalid` (:1143+); `test_read_ledger_history_malformed_before_cutoff_fails_closed`, `test_read_ledger_history_through_stops_before_future_rows` @ `1537636f`. |
| (c) Backfill attempt | **HANDLED** (reader refuses) | `read_ledger_history` does not invoke `backfill_leg_names`; `test_read_ledger_history_does_not_mutate_source_bytes` @ `1537636f`. Separate `backfill_leg_names` still exists for other call paths. |
| (d) Missing / undefined `through` boundary | **HANDLED** | `through=None` reads full ledger with typed empty/missing (`test_read_ledger_history_missing_and_empty_are_typed`); invalid `through` rejected (`test_read_ledger_history_rejects_invalid_query_arguments`) @ `1537636f`. |
| (e) Duplicate publication of one row | **HANDLED** | `test_read_ledger_history_duplicate_lifecycle_rows_are_not_deduplicated` @ `1537636f`. |
| (f) Clock skew (`ts` vs observation date) | **UNKNOWN** | Reader preserves both `observation_date` and `recorded_at` on each row (`engine/rotation_events.py:1434-1438` @ `1537636f`) but **no** test named for skew discrimination (`rg -i skew tests/test_rotation_events.py` @ `1537636f` → no matches). |
| (g) Other acceptance gaps | See L-A…L-G below. | |
| L-A (multi-clock GMI read-at-use) | **OUT OF SCOPE / UNHANDLED** | Rotation ledger reader; GMI clocks live in `rights_use` / cohort stack (#8486 held). Mastermind `05_ACCEPTANCE_AND_RED_TEAM.md:64` (pin `d1a8e672`). |
| L-B (later membership at earlier cutoff) | **OUT OF SCOPE / UNHANDLED** | Not this reader’s contract. `05_ACCEPTANCE_AND_RED_TEAM.md:66`. |
| L-C (retained-unmarked + malformed boundary) | **HANDLED** | Overlaps (a)(b); `05_ACCEPTANCE_AND_RED_TEAM.md:68`. |
| L-D (AUC ties / invalid obs) | **N/A** | Leadership perception metrics — Mastermind #1194 / macro #8412 lane, not #8470. `05_ACCEPTANCE_AND_RED_TEAM.md:70`. |
| L-E (duplicate residual window / PIT beta) | **N/A** | Theme-relative research (package S), not rotation JSONL reader. `05_ACCEPTANCE_AND_RED_TEAM.md:72`. |
| L-F (category errors: daily as intraday, AUC as probability) | **N/A** at reader | Product/UI law; reader exposes typed modes only. `05_ACCEPTANCE_AND_RED_TEAM.md:74`. |
| L-G (halted/stale symbol strength) | **N/A** | Intraday/session study registration. `05_ACCEPTANCE_AND_RED_TEAM.md:76`. |

**Path disjointness:** #8470 files: `engine/rotation_events.py`, `tests/test_rotation_events.py`. Shared with macro #8412: **`tests/test_rotation_events.py` only** (#8412 also touches `engine/subsector_rotation_alerts.py`, `scripts/build_rotation_events.py`). **No** shared paths with Mastermind #1194 (`scripts/validate_perception.py`, `tests/test_validate_perception_metrics.py`).

---

## Q3 — Company / theme consumer surface (L3 attach)

**Terminal route (read-only census):** `terminal/app/api/company-theme-context/[symbol]/route.ts:9-10` @ Terminal `origin/master` `e17622b1a05fc8891e44bc3bac2d2a178c1820d7` resolves `companyThemeExposure` from R2 (`research/theme_graph/WAVE_F_TERMINAL_R2_CONSUMER_CENSUS_2026-10-05.md:62-63`).

**Macro producer chain on MAIN_PIN:**

- `scripts/build_company_theme_exposure.py:25` → `engine/company_theme_exposure/views.py:259` `build_bundle` → R2 publish (`census` above).
- `engine/theme_context.py:589` `compute_theme_context` → artifacts `site/basketdata/theme_context.json` / `theme_context_cn.json` (`git ls-tree -r origin/main --name-only site/ | rg theme_context`).
- Theme graph store under `data/theme_graph/` (read via `engine/theme_graph/store.py`).

**Leadership-oriented artifacts on main (site ls-tree):** e.g. `site/marketdata/index_leadership.json`, `site/leaderradar/radar.json`, `site/flowleaders/leaders.json`, `site/marketdata/rotation_events.json` (grep `leadership` in `engine/` returned 30+ modules; display wiring examples: `templates/sector_central.html.j2:2113+` `theme_context.leadership`, `templates/us_stocks_v2.html.j2:41-42`).

**Plausible leadership attach points (macro, for L3):**

1. **Per-ticker theme + theme_state receipt** — extend CTE bundle consumer path (`engine/company_theme_exposure/views.py:32-65` `_theme_state_receipt` @ `89215741`) rather than a parallel publisher.
2. **Basket / sector glance leadership** — `engine/theme_context.py` leadership block consumed in `templates/sector_central.html.j2:2196+` (MLC W1/W2 display law).
3. **Rotation history honesty** — after #8470 merges, `read_ledger_history` beside existing `site/marketdata/rotation_events.json` consumers (`MEGACAP_LEADERSHIP_COHERENCE_MASTERPLAN_BY_FABLE.md:10-11` MLC-R1 consume `rotation_events.jsonl` / RC).

**Masterplan / prereg constraints:** MLC-R1 consume-not-rebuild (`research/MEGACAP_LEADERSHIP_COHERENCE_MASTERPLAN_BY_FABLE.md:10-11`); display-tier first MLC-R2 (`:11`); S-MLC-1 accrual gates authority not display (`research/S_MLC_1_LEADERSHIP_CONTINUATION_PREREG.md:13-15`); V3.8 axis separation Action ≠ Trend Leadership (`research/STOCK_DASHBOARD_V38_ACTION_LEADERSHIP_ARCHITECTURE.md:75-84`).

---

## Q4 — Terminal #796 collision

| Field | Value |
|---|---|
| Title | `fix(terminal): age verified company theme context at serve and display` |
| State | OPEN, **DRAFT** |
| Head | `0dfb1d8f73f82ebd83a5f57918ed4d0cdf5cec1b` |
| TERMINAL_PIN | `e17622b1a05fc8891e44bc3bac2d2a178c1820d7` (`git rev-parse origin/master` in clone `/home/longr/lanes/tmp/mi-l0-terminal`) |

**Terminal grep** (`rg` under `terminal/app`, `terminal/components`, `terminal/lib`):  
`terminal/app/api/company-theme-context/[symbol]/route.ts`, `terminal/lib/companyThemeExposure.ts`, `terminal/components/fin/CompanyThemeContextCard.tsx`, tests under `terminal/lib/__tests__/`.

**#796 changed `.ts/.tsx` product files:** **one** — `docs/verification/.../playwright-direct.config.ts` only; remainder verification docs/assets. **No collision** with macro Q3 attach paths; **low collision** with Terminal CTE UI route (evidence bundle lane, not the BFF route body on current head).

---

## Q5 — Return carriers (last comment binding L)

| Carrier | Last comment ID | Timestamp (UTC) | Author | Binding text (excerpt) |
|---|---|---|---|---|
| GMI #8324 | `IC_kwDOS4LjIs8AAAABZisRiQ` | 2026-10-06T04:01:30Z | mastermindx-2 | “## SOL RELEASE EDGE — gate #1 advanced … **#8417 HOLD RELEASED** …” |
| Leadership Mastermind #1194 | `IC_kwDOTotz3c8AAAABZQLrWQ` | 2026-10-05T06:58:30Z | MastermindX1 | “W4 scientific disposition refresh — qualified RC history narrows H1–H12 … **MISSION_COMPLETE: false**” |
| Macro #8412 | `IC_kwDOS4LjIs8AAAABZOT9Nw` | 2026-10-05T03:41:02Z | MastermindX1 | “independent exact-head semantic review remains the **only source-release blocker** on this Draft/HOLD carrier.” |
| Macro #8470 | `IC_kwDOS4LjIs8AAAABZQaulA` | 2026-10-05T07:18:04Z | MastermindX1 | “**DRAFT / HOLD-FOR-INDEPENDENT-REVIEW** … binding hosted W2 proof” (PR body: independent review before merge). |

---

## Gaps and refusals

- **(f) clock skew:** no dedicated test; consumer must compare `observation_date` vs `recorded_at` without a spec test.
- **L-A, L-B:** not in #8470 reader scope; blocked on held GMI cohort/read-at-use (#8486 / #8417).
- **#8470** not on `main`; leadership rotation honesty consumer cannot ship from main alone.
- **Wave F UNKNOWN:** no Terminal consumer for v2/cohort (`research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md:26`, `WS-GMI-THEME-GRAPH.md:170-171`).
- **Terminal clone:** initial `git fetch origin main` failed (`fatal: couldn't find remote ref main`); used **`origin/master`** instead for TERMINAL_PIN.
- **Checks:** this lane does not claim CI green on the new PR; #8470 checks quoted above for the held reader only.
