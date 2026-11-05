# China Prophet: concentrated semiconductor leadership audit

Status: **BUILT_NOT_PROVEN** for the bounded display repair. Research findings are evidence-backed diagnosis, not an accepted new trading strategy. No production deployment, rank/admission/size change, historical-ledger rewrite, or order was performed.

## Commission and source custody

Chris's September 20 screenshots show semiconductors simultaneously in In Favour and Bottoming Watch, memory/packaging turning signals confined to watch, and semiconductor candidates displaced by a broad Technology quota. The desired capability is early, risk-controlled participation in concentrated leadership, not an unconditional semiconductor preference.

Protected procedure: `mastermindx-market-intelligence/Mastermind@40e7b63be296f19ef4153f59781021fb5f0e9e0d`; skillpack 1.0.1. Audited product/data: `mastermindx-market-intelligence/macro@310a23dcd3e5fb8fdb95169a489b94487b091777`. Isolated carrier: `sol/cn-act-now-coherence-20260921`. A later main observation `bb60920c4d5ff52bb80cedd2d4033f4b2facb2e2` had no drift on the four owned implementation/semantics paths.

Evidence planes must NOT be conflated:

1. Public `china_stocks.html`, fetched during this audit, contains 110 server-rendered stocktable rows and matches the screenshot's first four Technology names and candidate placement.
2. Exact-source `site/factordata/china_standouts.json`, as of 2026-09-18: 1,601 scored names; 22 featured, 14 more_actionable, 8 late_or_unfillable, 11 forming. Other lifecycle shelves account for additional displayed names. `watch` aliases must not be double-counted.
3. Exact-source `data/china_prophet_rank/candidates.parquet`, September 18 point-in-time snapshot: 1,614 names, 1,610 measured interest observations and four unavailable (`no_edge_evidence`). This is NOT the same bake as plane 2: some prices, names, universe counts and interest values differ. Use it for dated eligibility evidence, not an exact public-byte reconstruction.
4. Exact-source `site/chinabasketdata/baskets.json`, `baskets_ths.json`, and `basket_turn_cn.json` provide theme/subtheme measurements.

Authenticated public JSON routes were not read (401); the attempted public R2 standouts path returned 404. No authenticated deployment proof is implied by the Git artifact.

## Findings

### A. Intelligence ordering is actually inactive

The published artifact requests `intel_interest_then_v3_score`, but reports `effective_order_basis=cn_prophet_v3_score`, `order_mode=v3_coverage_fallback`, `intel_order_active=false`, and `fallback_reason=incomplete_intel_interest_coverage`.

`engine/china_board_rank.py` intentionally disables intelligence ordering for the entire bake when any ranked candidate lacks valid measured interest. This prevents mixed-scale ranking, but incomplete evidence makes the product fall back globally. Do not replace unknowns with zero or mix incompatible interest and legacy scores. Repair coverage and design an explicit, uniformly comparable missingness-aware ranking policy under the existing ranking owner.

### B. Featured Technology allocation is not a CPU/memory leadership list

Published artifact values (not the separate PIT interest measurements):

| Stock | Board rank | Legacy priority | Entry status | Selected narrative | Placement |
|---|---:|---:|---|---|---|
| Sunway 300136.SZ | 1 | 94.86 | bounce_wait | Consumer Electronics | Featured |
| VeriSilicon 688521.SS | 2 | 86.28 | bounce_wait | Digital Currency | Featured |
| Accelink 002281.SZ | 3 | 84.20 | bounce_wait | F5G Networks | Featured |
| Everwin 300115.SZ | 4 | 84.00 | bounce_wait | EV Charging | Featured |
| Dosilicon 688110.SS | 7 | 76.11 | bounce_wait | AI PCs | More actionable: sector_cap only |
| Eoptolink 300502.SZ | 10 | 73.81 | bounce_wait | Co-Packaged Optics | More actionable: sector_cap only |

The featured sector cap is four and total featured cap is 24. A display quota is not the same thing as a stock's entry risk or a portfolio's actual correlated exposure. Dosilicon clears incumbent featured tests before the quota binds; that does not itself prove it is a good trade. Featured is not synonymous with immediate entry: all first four Technology names have `bounce_wait` status.

### C. Important names are filtered before ranking can rescue them

The live 110-row table does not include Hygon, Loongson, Montage, GigaDevice, Longsys, Biwin, or Ingenic. The dated PIT snapshot contains them, so their absence is not evidence of missing universe coverage:

| Stock | PIT gate reason | PIT selected narrative | Live stocktable |
|---|---|---|---|
| Hygon 688041.SS | flat: sell | Quantum Tech | Absent |
| Loongson 688047.SS | flat: cut | HarmonyOS Ecosystem | Absent |
| Montage 688008.SS | flat: sell | Data Security | Absent |
| GigaDevice 603986.SS | flat: sell | Semiconductors | Absent |
| Longsys 301308.SZ | flat: sell | Endpoint Detection & Response | Absent |
| Biwin 688525.SS | flat: sell | None | Absent |
| Ingenic 300223.SZ | flat: sell | None | Absent |
| Hua Hong 688347.SS | flat: sell | Semiconductors | Ripening |
| JCET 600584.SS | flat: sell | Semiconductors | Ripening |

These rows have `extended=false` in that PIT snapshot. Broadly raising the Technology cap or changing the theme caption cannot repair upstream raw eligibility. Selected narratives are also poor primary explanations of the CPU/memory hypothesis; this is not proof that every auxiliary membership is false.

The source already contains `engine/china_continuation_watch.py`; `scripts/build_china_library.py` explicitly describes it as **SHADOW ACCRUAL, ZERO DISPLAY**, not written into `wide`/`setups`. Reuse and assess that incumbent route before proposing another parallel detector. Do not promote its research cohort into buys without evaluation.

### D. The semiconductor exclusion has two concrete gates, not merely a late-looking caption

The broad `cn_semis` basket has: five-day return +7.73%; five-day relative return +7.67%; 20-day return -1.10%; 20-day relative return +1.00%; 22.7% of 22 members above their 50-day average; RSI 53.1; relative-strength percentile 0.841; drawdown from peak -27.08%.

Its `reco=enter`, label is emerging, and clean-entry quality is 0.65, yet the clean-entry flag is false. In `engine/basket_score.clean_entry`, quality >=0.60 is insufficient: `rs_pctile >=0.75` fails `not_ext`, and breadth below 0.40 independently fails the backdrop gate. `theme_scoring.py` routes constructive themes with that false flag to add_on_pullback. The frontend incorrectly translates this catch-all into 'has run / wait for a dip'. Strong relative performance is not a sufficient measure of trade extension, but weak internal breadth is genuine contrary evidence that must not be discarded.

The two-day TURNING observation and the 480-day structural bull-age/aging texture refer to different clocks. The age texture is descriptive, not proven to cause this exclusion. A fresh rally episode needs its own causal age/reset and invalidation rules rather than inheriting the age of an older structural regime.

### E. Subtheme measurements already show stronger acceleration

The THS artifact reports five-day returns: Memory Chips +14.53%, Advanced Packaging +14.89%, 3rd-Gen Semiconductors +11.53%. Their 20-day returns are +0.43%, +3.73%, +5.19%, respectively. These are basket observations, not executable member returns or proof of a fresh bull market. Their returned `breadth` field is absent; do not fabricate healthy internal breadth.

In the Act-Now assembler, THS baskets supply naming/performance enrichment for turning observations, while the actionable theme lists come from the separate theme_intel act_now input. A TURNING/CONFIRMED subtheme is therefore not an independently evaluated early-entry route just because it appears on the board. CPU, memory products and packaging must have explicit economically grounded memberships and equal access to discovery and entry evaluation.

### F. Duplicate entities and contradictory badges are real presentation defects

Raw evidence lanes intentionally permit duplication. Theme `cn_semis` and basket `b-cn_semis` are the same canonical basket identity; the tape rider can duplicate them and copy an ENTER recommendation into Bottoming Watch. A sector ETF and a similarly named basket are not necessarily identical exposures. Never perform blanket name-based merging.

## Bounded repair delivered on this carrier

The additive `display_lanes` projection creates one card per exact canonical entity, attaches turning/cycle evidence to the primary card, retains all raw lanes and deep-copied source reads, and discloses buy/reduce disagreement without manufacturing a buy. Parent/subtheme IDs and genuinely different sector IDs remain distinct. No Prophet model, strategy, ledger, entry zone, quota or sizing code changed.

The template uses the projection, prints Entry pending instead of contradictory ENTER in the waiting lane, removes buy badges from watch cards and their hover cards, removes unsupported 'has run' assertions, and retains valid ENTER badges in Buy Now. Existing layout is preserved. Semantics documentation explains the raw/display distinction.

Tests: RED-first missing-display_lanes failure, then **196 passed** across `test_china_act_now.py`, `test_china_board_rank.py`, `test_china_board_rank_v3.py`, and `test_china_board_rank_v4.py`. New cases live in the already-wired owner test file, not a competing shared CI manifest. Real theme/tape component rendering gives one semiconductor card, watch count 27 to 26, and no horizontal overflow at 1440px or 390px. Component proof excludes sector/cycle inputs and is not a full-page deployment test. See the companion evidence folder.

## Required next model capability and acceptance

Keep a single canonical Prophet owner, with distinct evidence axes: economic exposure/thesis; market and subtheme leadership; rally episode; executable setup; portfolio risk. Narrow broad-market breadth can raise total-risk caution while strong, broadening participation inside a specific subtheme raises discovery priority. Measure turnover share and participation; do not infer literal capital migration from relative returns alone.

Reuse existing theme-graph and closed-session leadership work, plus the continuation-watch incumbent. Evaluate a momentum/ignition entry family alongside the existing reversal family. A stock should not disappear from discovery because one reversal oscillator says flat; it should show its actual entry blocker. Permit Buy Now only when a measured, strategy-specific executable setup exists. Rising price or high RS alone neither opens nor closes that permission. Keep leaders in focus through a valid rally episode; change their entry state when extended, rather than treating the theme as no longer interesting.

Research gates: point-in-time memberships and data availability; identical clocks; new-listing and corporate-action controls; costs and realistic China fillability/limit-lock/T+1 constraints; historical non-semiconductor concentrated rallies and failed rotations; regime-split walk-forward tests and ablations; prospective shadow grading in the incumbent ledger. Report delay to first actionable signal, leader coverage, false breakouts, executable forward return, adverse excursion, and missed opportunity by exact gate. Do not tune acceptance to make September 18 semiconductors win.

Sibling custody: #7526 owns semantic thesis repair/shared CI; #7455 owns closed-session leadership observations; #7508 owns returned group/member entry context; #7453 owns independent acceptance. Those descriptive deliveries are not automatically live recommendation authority. This carrier does not copy their implementations or edit their manifests.

Primary continuation: review and release this display-only carrier through exact-head CI and independent acceptance, then prove deployed bytes. In parallel, the incumbent Prophet/Theme Intelligence owners should reproduce the full-universe gate audit on a single bake and evaluate the existing continuation/leadership path before any rank/admission promotion. The overall concentrated-rally recommendation capability remains unresolved.

## Continuity record correction — 2026-09-21

The original PR's free-form Agent OS handoff failed the hosted record-schema gate. It is now recorded as `DSC:CN-PROPHET-SEMICON-LEADERSHIP-GATE-AUDIT` in `agentos/discoveries/DSC-CN-PROPHET-SEMICON-LEADERSHIP-GATE-AUDIT.md`, retaining the evidence and scoped continuation without inventing a workstream or replacing a program-wide latest handoff. No product/ranking bytes changed in this correction. See that record for exact current CI and Slack convergence blockers.
