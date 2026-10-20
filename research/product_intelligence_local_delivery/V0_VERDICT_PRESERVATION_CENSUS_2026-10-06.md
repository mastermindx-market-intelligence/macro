# V0 verdict-preservation census (Prophet V4 / Temporal Grain)

**MAIN_PIN:** `d0f14c62544daca98258cbf68a5e1e3bef54ab74` (`git rev-parse origin/main` after `git fetch origin main`, 2026-10-06).

## C0 (answer first)

**yes** — On MAIN_PIN, **INSUFFICIENT SUPPORT** is the sole **actual** C2 status in the authoritative lane record (`research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C2/RESULT.md:1,176-177`) and product law (`07_PRODUCT_CONDITIONING_TABLE_SPEC.md:57-66`). **NOT SUPPORTED** appears for C2 only as an explicitly labelled counterfactual (`RESULT.md:179`, `07:65-66`) or as **B1’s separate lane verdict** (`B1/RESULT.md:7`, `C2/RESULT.md:8`) — not as a second C2 actual status. Historical **CONFLATED** C2 r1 text is audit-only (`reviews/C2_r1/REVIEW.md:30`). **Consumers in production code:** `rg -c 'INSUFFICIENT SUPPORT|NOT SUPPORTED|SCOPED_NULL|PIT_PARTIAL' engine templates scripts app` → **0 hits** (scope: those four directories on MAIN_PIN).

---

## Q1 — Verdict inventory

| ID | Role | Path:line (MAIN_PIN) | Literal | Qualifier travel |
|---|---|---|---|---|
| **C2** | STATED | `results/C2/RESULT.md:1,176-177` | INSUFFICIENT SUPPORT | Reasons + C1 BROKEN in same doc |
| **C2** | STATED | `07_PRODUCT_CONDITIONING_TABLE_SPEC.md:57` | C2 = INSUFFICIENT SUPPORT | Display-tier + no recommendation rows |
| **C2** | CONSUMED | `07:65-66,85-86` | Counterfactual diagnostic | QUALIFIER_PRESERVED |
| **C2** | CONSUMED | `09_WAVE1_SYNTHESIS_AND_PRODUCT_IMPLICATION.md:12,19` | INSUFFICIENT + counterfactual NOT SUPPORTED | QUALIFIER_PRESERVED |
| **C2** | CONSUMED | `agentos/decisions/DEC-C1-AR1-GATE-UNCALIBRATED-SERIES-FAILS-CALIBRATED.md:16` | INSUFFICIENT SUPPORT by rule | QUALIFIER_PRESERVED |
| **B1** | STATED | `results/B1/RESULT.md:7` | NOT SUPPORTED (grain + memory) | FINAL-VINTAGE / survivor-selected in §Data class |
| **B1** | CONSUMED | `07:61-63`, `09:10,29` | NOT SUPPORTED + scope | QUALIFIER_PRESERVED |
| **F1** | STATED | `results/F1/RESULT.md:5` | MIXED | 21-NYSE embargo + small-N stated |
| **F1** | CONSUMED | `07:97-106`, `09:15,28` | MIXED + diagnostic-only AUC | QUALIFIER_PRESERVED |
| **E** | STATED | `results/E/RESULT.md:1`, `results/E/result.json:1801` | SCOPED_NULL | 10/12 above floor in answer_first |
| **E** | CONSUMED | `07:113-115`, `09:14,30` | SCOPED_NULL + no family ranking | QUALIFIER_PRESERVED |
| **D0** | STATED | `results/D0/RESULT.md:3`, `results/D0/result.json:4` | PIT_PARTIAL | Window + coverage in ANSWER FIRST |
| **D0** | CONSUMED | `07:117-119`, `09:13,31`, `DEC-D-LANE-PARKED-AS-FORWARD-STUDY` | PIT_PARTIAL + parked lane | QUALIFIER_PRESERVED |

**NOT_CONSUMED:** `engine/`, `templates/`, `scripts/`, `app/` — zero matches for all five verdict tokens (grep above).

---

## Q2 — C2 single-actual-status / counterfactual

| Consumer | Path:line | Classification |
|---|---|---|
| C2 lane record | `results/C2/RESULT.md:179` | **PRESERVED** — “COUNTERFACTUAL … not a verdict” |
| Product spec | `07_PRODUCT_CONDITIONING_TABLE_SPEC.md:65-66` | **PRESERVED** |
| Wave-1 synthesis | `09_WAVE1_SYNTHESIS_AND_PRODUCT_IMPLICATION.md:12,19` | **PRESERVED** |
| C1 decision | `DEC-C1-AR1-GATE-UNCALIBRATED-SERIES-FAILS-CALIBRATED.md:50` | **PRESERVED** — counterfactual named, not conflated with actual |
| C2 r1 review (historical) | `reviews/C2_r1/REVIEW.md:30` | **CONFLATED** — documents superseded r1 headline NOT_SUPPORTED |
| Production UI | *(none)* | **ABSENT** |

---

## Q3 — Diagnostic-to-probability leakage

| Path:line | Class | Surrounding sentence (abbrev.) |
|---|---|---|
| `07:48` | DIAGNOSTIC_ONLY | `expected_protection` … Not a candidate success probability or causal protection claim. |
| `07:105-106` | DIAGNOSTIC_ONLY | An AUC is not a calibrated chance of profit. |
| `F1/RESULT.md:5` | DIAGNOSTIC_ONLY | MIXED … product implication is descriptive only. |
| `F1/RESULT.md:170` | DIAGNOSTIC_ONLY | The verdict is descriptive; nothing is promoted here. |
| `09:28` | DIAGNOSTIC_ONLY | AUC 0.62 … descriptive chip admissible, entry screen is not. |

No `engine/` / `templates/` / `scripts/` / `app/` hit for prophet F1 AUC or C2 protection columns on MAIN_PIN.

---

## Q4 — Trend Persistence (calibrated profile / shadow field / C2 run)

| Finding | Evidence |
|---|---|
| **No macro builder** | `rg calibrated_profile\|shadow_field engine templates scripts app` → 0 hits |
| **Kill + decision** | `research/DO_NOT_REBUILD.md:133` (KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE); `agentos/decisions/DEC-TREND-PERSISTENCE-STOPS-AT-WAVE-C.md:12` (nothing built; no C2 read) |
| **WS closure** | `agentos/workstreams/WS-TREND-PERSISTENCE.md:56-57` — do not build calibrated profile / shadow field |
| **Allowed substrate only** | `collectors/sp1500_pit_sectors.py:1` — Wave C-0 PIT sectors, not profile |
| **Instrument off-repo** | `research/trend_persistence_group.py` — **absent** in macro (`docs/AGENT_OS_STATE.md` phantom-artifact); lives in Mastermind per handoff |

---

## Q5 — Browser proof status

| Q1–Q3 template consumer | Rendered site path (from `git ls-tree`) | Status |
|---|---|---|
| *(none — no template cites C2/B1/F1/E/D0 verdict literals)* | `site/prophet/index.json`, `site/prophet/board_read_sparks.json`, … | **DOCUMENT_ONLY** for all wave-1 verdicts |

Document-only assertions are not browser proof.

---

## Q6 — Integrated-answer input list (≤10)

| Verdict | Literal | Source | Qualifiers | Consume as-is? |
|---|---|---|---|---|
| C2 | INSUFFICIENT SUPPORT | `C2/RESULT.md:176` | C1 BROKEN; counterfactual separate | **Yes** (display tier) |
| B1 | NOT SUPPORTED ×3 | `B1/RESULT.md:7` | Sample + evidence level 2 | **Yes** |
| F1 | MIXED | `F1/RESULT.md:5` | 21-session embargo; 4 OOS weeks | **Yes** (diagnostic framing only) |
| E | SCOPED_NULL | `E/result.json:1801` | 10/12 above floor | **Yes** |
| D0 | PIT_PARTIAL | `D0/RESULT.md:3` | D* 2026-07-05; 25.43% min coverage | **Yes** (with parked-lane note) |
| C1 upstream | BROKEN | `C2/RESULT.md:9` | AR(1)-21 gate | **Yes** (conditions C2) |
| Product boundary | DISPLAY-TIER ONLY | `07:15-17` | No rank/size/gate | **Yes** (law) |
| C2 counterfactual | NOT SUPPORTED | `C2/RESULT.md:179` | Labelled not a verdict | **Yes** (never as actual C2) |

**Do not consume until repair:**

- C2 r1 `NOT_SUPPORTED` headline (historical only).
- F1 AUC / severe shares as probabilities or protection levers.
- D0 E* / week-40 promotion numerics (r3 record gaps per `09:13`).
- Any Trend Persistence calibrated profile or shadow field (`DNR:KILL-TREND-PERSISTENCE-*`).

---

## GAPS

1. No rendered UI consumer on MAIN_PIN — production grep zero; browser proof not available.
2. Sparse worktree: `site/` not on disk; artifact names only via `git ls-tree`.
3. Unrelated `MIXED` strings elsewhere in the repo (e.g. market_state) are out of scope for this handoff census.

## Input commits read

- Correction: `07_PRODUCT_CONDITIONING_TABLE_SPEC.md` (macro #8474 lineage).
- #8445 `62992f803f1b`, #8460 `dba78c4bd772`, #8466 `9a2f00a560ab` — lane results under `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/{B1,C1,C2,D0,E,F1}/`.
