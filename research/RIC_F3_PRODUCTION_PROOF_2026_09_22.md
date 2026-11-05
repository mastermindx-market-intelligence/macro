# RIC F3 — Yield Momentum → Transmission → Forward Path: production proof

**Operation:** new production-proof child (MAS-245). **Not** a rewrite of F3, **not** a
revival of the terminal source child `ric-f3-yield-momentum-transmission-20260901-sol-001`,
and **not** a reopening of macro PR #6721.

| | |
|---|---|
| Macro SHA proved | `ea194c5d215c64158a828abdc676f47bb7723374` (== `origin/main` at session start) |
| `origin/main` at re-check | `c538c78eef57b810ab36ddc8c7d93ef15a5dec7f` |
| Production build id | live `macro.html` title stamp **2026-09-21**; served board asof **2026-09-18** |
| Nightly proving the path | `daily.yml` run at `edbcbf702a1a`, 2026-09-22T01:42Z, success |
| Authority | `authority=false can_score=false can_size=false can_trade=false` — verified intact end to end |

## Verdict

The merged F3 source is **correct on the real current path**. It is also **inert**: the
object it produces has no downstream reader anywhere in the product. The honest capability
state is not `BUILT_NOT_PROVEN` — it is **BUILT, PROVEN, AND UNCONSUMED**.

Two defects were found. Neither is in F3's own arithmetic.

## Phase 1 — current source identity (resolved, not inferred)

| Fact | Value | Where |
|---|---|---|
| Source owner | FRED `DGS20` | `data/fred/DGS20.parquet`, 14,475 rows |
| Canonical alias | `DGS20 -> us20y`, frozen, CCW-owned | `config.yml:308`; `engine/yield_momentum.py:16` |
| Source clock (last print) | **2026-09-18 = 5.38**; prior 2026-09-17 = 5.32 | parquet tail |
| Model clock (frame end) | **2026-09-18** (`SPY.last_valid_index()`) | `engine/inputs.py:170` |
| Producer | `build_yield_momentum(f)` | `engine/rate_inflation_transmission.py:595` |
| Consumer | reads `tx["yield_momentum"]`, copies it out | `engine/rates_inflation_command.py:1234`, `:1422` |

All five rate series stop at 2026-09-18 in this checkout, so `frame_as_of == as_of` is an
honest reflection of committed data, not a masked gap.

## Phase 2 — one real current observation through the real path

Ran `engine.inputs.build_features()` (no fixtures, no overrides) then
`engine.yield_momentum.build_yield_momentum(f)` at `ea194c5d`:

```
source_column      us20y            source_id            DGS20
level              5.38             as_of                2026-09-18
observation_origin captured_source_row                   origin_status matched_captured_alignment
velocity_bp        5d 0.0 | 22d 21.0 | 63d 42.0
endpoint_dates     5d [2026-09-11, 2026-09-18] | 22d [2026-08-19, …] | 63d [2026-06-23, …]
acceleration_bp    16.0             turn_watch           null
path_qualified     false            calculation_version  fixed_grid_origin.v2
last_observed      as_of 2026-09-18 level 5.38 | previous 2026-09-17 5.32 | change_bp 6.0
```

The deterministic result is **internally consistent and correctly dated**: 5.38 is the true
2026-09-18 print, `observation_origin` correctly says it is a captured source row (not
carried), and `last_observed` reconstructs the 09-17→09-18 +6.0bp step exactly.

### The committed artifact disagrees with it

`git show origin/main:data/transmission/latest.json`:

```
asof 2026-09-18   calculation_version: ABSENT (v1-era)
20y  level 5.32   as_of 2026-09-18   turn_watch "extreme_high_watch"
```

`5.32` is the **2026-09-17** value stamped as a 2026-09-18 observation — the pre-#7291
ffill laundering the origin-tracking work was built to stop. Same shape on 2y/5y/10y/30y.
The artifact was last committed **2026-09-19 15:12** (`weekly: deep-dive 2026-09-19`),
and #7291 merged **2026-09-20 00:24** — about nine hours later. So the served payload has
never been produced by the fixed code.

**This is a cadence gap, not an incident and not an unfixed code defect.**
`scripts/build_transmission.py` — the sole writer of `data/transmission/latest.json` — is
owned as a step by exactly ONE lane: `config/dag.yml` lane 19,
`.github/workflows/weekly.yml`, job `weekly-report`. The daily lane (lane 3, job `engine`)
and the two render lanes only *reference* it for ordering; none runs it. So the nightly was
never this artifact's owner, the 09-21 and 09-22 green nightlies were never going to
refresh it, and the last weekly simply predates the fix. Confirmed live: `snapshot(f)` on
the real frame at HEAD returns `calculation_version fixed_grid_origin.v2`, 20y `level 5.38`,
`as_of 2026-09-18`, `observation_origin captured_source_row` — the correct payload, ready
for the next weekly run.

Note for whoever reads the code next: `scripts/run_transmission_chains.py:8` calls
build_transmission part of "the nightly", which is stale wording and is what makes this
look like a nightly failure.

## Phase 3 — failure semantics on the real path

Nine cases driven off the real DGS20 series. **No source failure becomes a neutral or
supportive zero.**

| Case | status | level | carried | as_of | velocities | turn_watch |
|---|---|---|---|---|---|---|
| Normal | available | 5.38 | — | 2026-09-18 | 0.0 / 21.0 / 42.0 | null |
| Stale (carried 1d) | **stale** | **null** | 5.32 | **2026-09-17** | all null | null |
| Stale beyond ffill | **stale** | null | — | 2026-09-03 | all null | null |
| Null last value | **stale** | null | — | 2026-09-17 | all null | null |
| Missing prior history | available | 5.38 | — | 2026-09-18 | 63d **null** | null |
| Flat / near-zero move | available | 5.00 | — | 2026-09-18 | 0.0 / 0.0 / 0.0 | null |
| Future-dated source row | available | 5.38 | — | 2026-09-18 | populated | null |
| No evidence at all | available | 5.38 | — | 2026-09-18 | populated | null |
| Invalid grid | **invalid_grid** | null | — | null | all null | null |

Key results:

- **Stale does not launder.** A carried value drops `level` to null, moves it to
  `carried_level`, rolls `as_of` back to the true origin date (2026-09-17, not the grid's
  2026-09-18), nulls every velocity and acceleration, and sets
  `observation_origin="carried"`. This is precisely the behaviour the committed v1 artifact
  lacks.
- The zeros in the Flat row are a **genuinely unchanged series**, not a masked failure —
  every real failure row nulls instead.
- **Direction turn / acceleration disagreement** are representable (acceleration is
  `Δ22d(now) − Δ22d(prior)`, so it carries a sign opposite to velocity without contradiction;
  the live read is velocity +21.0bp with acceleration +16.0bp).
- Two soft spots, both disclosed rather than laundered: a **future-dated or invalid origin**
  degrades `observation_origin` to `unverified` / `origin_status=invalid_metadata` but still
  publishes levels and velocities; and `insufficient_history` never fires because
  `enough = len(measured) >= 64` counts NaN-padded grid rows rather than observations (the
  affected velocity still returns null, so no wrong number is emitted).

## Phase 4 — current product / machine view

Live, not fixtures:

| Surface | HTTP | `yield_momentum` | F3 fields |
|---|---|---|---|
| `mastermind-x.com/macro.html` (Forward Path) | 200, 606,738 B | **0** | `turn_watch\|rolldown_forming\|velocity_bp\|acceleration_bp` = **0** |
| `mastermind-x.com/transmission.html` | 200, 138,822 B | **0** | 20Y refs = 0 |
| `mastermind-x.com/macro_rates_curves.html` | 200, 376,269 B | **0** | 20Y refs = 6 |

The **Fed Path — Forward Board renders and is healthy** — "Two-sided — watch the tape",
asof 2026-09-18, hawk 3 / ease 3, legs: Rate futures, Breakevens, Oil, Inflation path,
Yield curve, Expectations, Equity risk-off, Growth cooling, Strong dollar. **None of them is
F3.** The board's "Yield curve" leg comes from `bond_health`, not `yield_momentum`
(`yield_momentum` appears exactly three times in `rates_inflation_command.py` — read,
default, copy — and never in a scored leg).

Where the chain actually ends:

```
DGS20 -> us20y -> build_yield_momentum -> data/transmission/latest.json
      -> data/rates_command/latest.json['yield_momentum'] -> (no reader)
```

- `engine/neuralweb/world_state.py:1883` `_compose_rates_command` forwards a fixed field
  list that **omits** `yield_momentum` → never reaches `world_state.json` or the RCB lobe.
- `engine/neuralweb/market_packet.py:878` `_rates_block` (live per-turn chat grounding)
  takes only `board.rate_path_row` / `inflation_row` / `risk_row` / `curve_regime_key` →
  never reaches the chat machine consumer.
- No template references it; `grep -rl yield_momentum site/` is empty.
- `observation_origin`, `path_qualified`, `carried_level`, `frame_as_of` are **write-only** —
  nothing outside `yield_momentum.py` reads any of them.

The user's real live 20Y read is owned by a **different, independent** module:
`engine/market_os/macro_workspaces/rates_curves.py` (`SERIES_US20Y, COL_US20Y = "DGS20",
"us20y"`) → `macro_rates_curves.html`. It is a level/coverage read, carries no momentum
state, and is not a duplicate F3.

## Phase 5 — cross-contract consistency

F3 was kept strictly separate from, and was **not** conflated with, #7418 rates-conditioned
Entry Radar research, macro-regime architecture #7088, tactical R1-A/B, or any forecast
probability model. Nothing downstream treats `yield_momentum` as a forecast: it is a
top-level sibling of `board` / `expectations_pressure` and feeds no `hawk_score`,
`ease_score` or `net_state`. Display/context authority is intact at every hop.

## First causal failure

**`engine/yield_momentum.py` `_series_read`** — the `path_qualified` gate:

```python
out['path_qualified'] = (all(observed) and numeric.notna().all()
                         and item['source_basis'] == 'captured_source_rows')
```

`observed` is tested against a `pd.bdate_range` weekday grid over `TURN_LOOKBACK = 1260`
rows. US Treasury CMT series do not print on US market holidays, so every holiday in the
window is ffill-carried and counts as *not observed*. Measured on the real frame: **1206
observed, 54 carried** for `us20y`. One unobserved row anywhere disqualifies the whole path,
so `path_qualified` is **False for all five series, every night**, and `turn_watch` — gated
on `enough and path_qualified` — is **structurally unreachable in production**.

Isolation (same series, only holiday prints differ):

| Input | path_qualified | turn_watch |
|---|---|---|
| Real DGS20 on the real weekday grid | False | **null** |
| Same series reindexed to print every weekday | **True** | `extreme_high_watch` |
| Real DGS20, short holiday-free window | True | null (`insufficient_history`) |

The test suite cannot see it: `tests/test_yield_momentum.py:88` asserts
`turn_watch == "rolldown_forming"` on a synthetic fixture that prints every weekday, and
**115 F3-related tests pass green at HEAD**. The committed v1 artifact still shows
`extreme_high_watch` on 4 of 5 series, so #7291 converted a firing capability into a
permanently null one, silently.

**Owning boundary:** how `observed` is computed — it cannot distinguish an *expected*
absence (market holiday, no print was ever due) from a *real* gap (a due print that is
missing). The qualification's intent is correct and must not be relaxed wholesale; the
bounded repair is the expected-vs-real absence distinction, under a fresh carrier.

The defect is currently **consequence-free**, because the field has no reader.

## Subagents

All four external lanes were commissioned and **none started** — clean refusals, no
`EFFECT_UNKNOWN`, no partial effects:

| Lane | Commission | Outcome |
|---|---|---|
| MiniMax | source→F3→RIC lineage trace | `LOCAL_SEAT_REMOTE_REQUIRED host=m2` |
| GLM | deterministic stale/null/turn probe | `GLM_DISABLED no key` |
| Cursor | adversarial attack | `LOCAL_SEAT_REMOTE_REQUIRED host=m2` |
| Grok | adversarial attack | `LANE_ADMISSION_REFUSED … host_load_at_or_above_limit` (load1 27.4, 24 cores, cap 0.667) |

Grok's refusal is the **host policy working as intended** — M2 was saturated and admission
control declined to add load. It was not overridden. Per the execution continuation law
(no worker started, lawful principal tools and custody, no conflicting owner, no
`EFFECT_UNKNOWN`), all fanout work — lineage, failure semantics, and attack vectors
V1–V6 — was executed directly instead.

## Attack vectors

| Vector | Verdict |
|---|---|
| V1 stale wrapper date laundering | **Confirmed in the committed v1 artifact**; fixed in code, pending re-bake. No *other* hop re-stamps a carried value. |
| V2 20Y source convention mismatch | Clean — `DGS20 -> us20y` percent CMT consistently in `yield_momentum.SERIES`, `macro_workspaces/build.py:139`, `rates_curves.py:240`, `corp_credit.py:79` (tenor 20.0). |
| V3 duplicated rate owner | No duplicate *momentum* owner. `rates_curves.py` is an independent *level* owner for a different surface. |
| V4 current-state vs forecast confusion | Clean — never enters a scored or forecast leg. |
| V5 old cached Forward Path | **Weakness**: `asof = max(main_asof, tx_asof)` (`rates_inflation_command.py:1401`), and only an *absent* transmission is caveated, never a *stale* one — so RIC can carry a stale `yield_momentum` under a newer `asof` with no staleness flag. Detectable (the block keeps its own `asof`), but unflagged. |
| V6 source clock vs model clock collapse | Clean **vacuously** — `frame_as_of` has no reader. |

## What must not be redone

- Do **not** rewrite F3, reopen #6721, revive the terminal source child, or re-run the
  source implementation. The deterministic source is proven correct on the real path.
- Do **not** commission further F3 *source* work to "prove" it. It is proven.
- Do **not** build a new rates dashboard to prove F3.
- Do **not** relax `path_qualified` wholesale — the qualification intent is correct.

## Next RIC action

1. **Let the next `weekly.yml` run re-bake `data/transmission/latest.json`** — it will be
   the first post-#7291 bake and clears the laundered 09-17-as-09-18 payload on its own.
   No nightly investigation is owed: the daily lane does not own this artifact. To clear it
   sooner, dispatch `weekly.yml` (standard in-flight preflight first). Correct the stale
   "runs in the nightly" comment at `scripts/run_transmission_chains.py:8`.
2. **Repair the `observed` computation under a fresh carrier** so an expected market-holiday
   absence no longer disqualifies the path, restoring `turn_watch` reachability. Add a
   production-shaped (holiday-bearing) fixture so the test suite can see the difference.
3. **Only then** wire the first consumer. The natural one already exists and is waiting:
   `engine/credit_momentum.py:1125,1805` carries an interim TLT/IEF ETF-price block
   explicitly marked *"R6: no yield_momentum.v1 yet"*.
4. Optionally flag a **stale** (not merely absent) transmission input in RIC's `caveats`.

**This proof claims no F4 or forecasting authority.** It establishes deterministic current
context only.

Records: `DSC:F3-TURN-WATCH-IS-STRUCTURALLY-UNREACHABLE-IN-PRODUCTION`,
`DSC:F3-YIELD-MOMENTUM-HAS-NO-CONSUMER`.
