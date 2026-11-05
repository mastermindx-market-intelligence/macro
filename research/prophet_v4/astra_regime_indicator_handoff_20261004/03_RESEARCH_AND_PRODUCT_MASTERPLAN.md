# 03 — Research and product master plan (Prophet regime × indicator × timeframe × theme)

**Author:** Fable seat, Claude Code session `f273dd7d-5dfb-4725-b26d-3de277637b11`, operation key `prophet-astra-ceo-fable-20261004-001`.
**Status:** PLAN FROZEN for wave 1 (2026-10-04). Evidence class of every result in this program is labelled per §6; nothing here is a live Prophet change.
**Authority:** Chairman transferred the Astra CEO assignment (`00_ASTRA_CEO_ASSIGNMENT.md`) to Fable orchestration on 2026-10-04 ("complete it end to end … under Fable orchestration at max throttle"). Inside that scope this seat decides; it does not re-ask Sol for in-scope matters. Outside it (production Prophet mutation, Phase-22, incumbent V4 PRs, TOI/Temporal-Grain carriers, GMI theme graph) the existing owners decide and this program only supplies evidence.

This chapter is the integrated master plan whose earlier upload was blocked. It was authored fresh by the receiving seat from the accepted chapters 00/01/02, the deep-research program (09), Sol's parallel program on #8303, and the TOI recommissioning packet on #8332. It does not retry, rename or route around the blocked upload; it replaces the missing chapter with the receiver's own plan.

---

## 0. Exit gate (what "complete" means for this program)

The program is complete when ALL of the following are true and verified against `origin/main`:

1. Chapters 03/04/05 exist, are merged, and a cold stranger can resume the program from 05 alone.
2. Wave-1 experiments A1, B1, C1, C2, F1 (§5) have each produced a committed result packet (`results/<LANE>/RESULT.md` + `result.json` + code + input/code hashes) that an independent adversarial review has judged ACCEPT, with every pre-declared falsifier answered either way.
3. The central hypothesis (§5.4, C2) has a pre-declared verdict: SUPPORTED / NOT SUPPORTED / INSUFFICIENT SUPPORT — at evidence level ≤ 3 (§6) — and a written product implication (§7) conditional on that verdict.
4. Wave-2 (D theme restriction, E family×regime tournament, Phase-22 continuity) is either executed to the same standard or explicitly parked with a named blocker and owner.
5. Agent OS records (DEC/DSC/handoff) are merged and `python3 scripts/agentos.py validate` passes.
6. Product handoff: a consumable conditioning table and management-rule proposal delivered to the Prophet V4 / Mastermind owners as evidence, with the acceptance ladder rung honestly stated (never above `MERGED` for research artifacts; `PRODUCTION_PROOF` only if an owner ships and proves a consumer).

Not in the exit gate: changing any live rank, gate, sizing, calendar, publisher or Phase-22 population. Those are owner acts.

## 1. Mission restated

Improve Prophet across regimes, technical families, timeframes and themes with true, reproducible evidence that Mastermind and Prophet can consume. Preserve the large-winner tail while reducing avoidable severe failures. One Prophet platform with separately evaluated strategies; regime is a conditioning variable, never a universal score. No indicator, regime label, theme restriction, threshold, timeframe or model earns authority from narrative plausibility.

## 2. Evidence consumed and DO_NOT_REDO (binding unless materially invalidated)

| Source | Finding | Program consequence |
|---|---|---|
| 01 §audit, engine/canon.py:417 | Incumbent cascade is RSI14 → MACD(14/60/5) on RSI + StochRSI 14/3/3, `adjust=False` recursive EMA, SMA-seeded Wilder RMA | Every experiment uses `engine.canon.rsi_macd` verbatim for identity; a fresh reimplementation is only a parity check |
| engine/session_anchor.py, era `abs-session-2026-08-06` | Absolute-session anchor exists; 2D/3D bars bucket by session position | Phase offsets are defined relative to this anchor; phase 0 = production |
| 01 §broad regime null | 57,642 signals / 763 months, regime main effect .95pp | No family-by-regime main-effect study is re-run; wave 2 E is an INTERACTION tournament only |
| 01 §RS threshold | .75–.85 band not validated; ≥.85 vs middle +6.05pp continuation failure p=.0139 | Not re-run; RS tercile may appear as a covariate only |
| 01 §1.5-ATR gate | NO-GO (288 paired months, all intervals include zero) | Not re-run; extension gates are not a wave-1 variable |
| #8303 PILOT_FINDINGS / KERNEL_FACTORIAL (Sol) | 2,730 + 2,681 ETF events QQQ/IWM/SOXX 2007–2025; 3D-vs-1D regime interaction intervals include zero for both price-MACD and RSI-MACD; longer-kernel RSI effect flips sign across eras; half-life of span-60 on 3D ≈ 62 sessions vs span-26 ≈ 27 | ETF pilot is DO_NOT_REDO. Wave 1 moves to a STOCK panel (the pilot's own next step) and separates grain from memory explicitly (§5.2) |
| #8303 CALENDAR_PHASE_FINDINGS | Omitted 2007-01-02 closure shifts every 2D/3D bucket; owner migration obligation | Lanes use the current reference calendar as-is and record its hash; no calendar edit |
| #8303 README | 0/60 leading-slice changes under absolute grid; frozen-window oracle 42/60 — do not blanket re-anchor | Honoured |
| Phase-22 prereg (2026-09-19) | LIVE_FORWARD, C2_1D_TURN@1 conditioned on same-cut C4 2D StochRSI turn; floors fixed; NOT STARTED | Untouched. This program never reads Phase-22 outcomes and never edits its population |
| Phase-21 | 209 episodes / 8 dates / 181 tickers = development evidence | Cited as development evidence only |
| WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE + #8332 (Sol, 2026-10-03) | TOI recommissioning has its own CEO start prompt; carriers #7107 (W1) / #7094 (W2-0); "do not create replacement census/implementation carriers" | TOI W1/W2-0 are OUT OF SCOPE for this program; this program consumes a future accepted W2-0 clock contract if it lands, else uses the US session clock from `engine.session_anchor` |
| WS:TEMPORAL-GRAIN-INTELLIGENCE (#6803 W1A, V2-M HOLD) | G/A/K/D decomposition; V2-M waits on TOI W2-0 | Decomposition adopted as the experimental vocabulary; no V2-M work here |
| WS:PROPHET-US-V4-RECOVERY, carrier #6805, incumbents #7581/#7180/#7572 | Production Prophet US owners | Never seized; results are delivered to them as evidence |
| regime_v2_pit.parquet (`flag_rotation_persistence`, `pit_class`) | An incumbent PIT regime store already carries a rotation-persistence flag | C1 constructs a continuous rotation variable and REPORTS agreement with the incumbent flag; it never replaces it |

## 3. Architectural decisions (frozen)

- **D1 — Experimental unit and clock.** Session = US exchange session from the SPY reference index; absolute-session positions from `engine.session_anchor.session_positions`; n-day bars from `engine.bar_derive` buckets with explicit phase `p ∈ {0..n−1}` (bucket = (position + p) // n). A signal on an n-day bar is known at the close of the bar's last session; entry is the NEXT session close. No intra-bar knowledge, ever.
- **D2 — Grain vs memory separation (Temporal Grain G/A/K/D).** Every multi-day result is paired with its matched-elapsed-memory 1D control (`alpha_new = 1 − (1 − alpha)^(d_new/d_old)` applied to every exponential smoother in the cascade, Wilder RMA included) and its same-grain alternative-kernel control. A "timeframe effect" that disappears under matched memory is reported as a memory effect.
- **D3 — Phase robustness.** All valid phases are computed; results report cross-phase dispersion; the winning phase is never selected after outcomes.
- **D4 — Regime = conditioning variables, pre-declared, PIT-constructed.** Rotation speed (leadership persistence), breadth, real-rate impulse, incumbent quad/transition state. Labels are built from inputs strictly before the signal date, using expanding-window terciles so no future distribution leaks.
- **D5 — Dependency-aware inference.** Entry-month cluster bootstrap (1,000 draws, seed 20261004) for every interval; honest-N = distinct months / distinct names / events / eras per cell; cells below floor are reported as INSUFFICIENT SUPPORT, never dropped silently.
- **D6 — Decision rules pre-declared.** Each experiment carries its falsifier and verdict rule before any outcome is computed (§5). A null is a result.
- **D7 — One writer.** Lanes compute and write result files under their own `results/<LANE>/` directory; only the seat commits. Lanes never run git write commands, never touch `data/`, never touch engine code.
- **D8 — Nothing promotes.** Evidence level ≤ 3 (§6). Product changes are proposals to owners.

## 4. Wave plan

| Wave | Content | Exit |
|---|---|---|
| **W1 (this plan)** | A1 baseline/clock census · C1 rotation-state variable · B1 stock-panel phase & matched-memory event panel + confirmation pairs · C2 decisive rotation × confirmation-cost interaction · F1 entry-vs-management hazard on the served ledger · adversarial review of each | All five result packets ACCEPT; C2 verdict written; 03/04/05 + results merged |
| **W2** | D theme-restriction (needs PIT theme membership — census first against GMI theme graph #7870 outputs) · E family × regime INTERACTION tournament on the B1 panel (trend, momentum, compression, participation, RS, structure) with the same controls · Phase-22 continuity note (no outcome read) · product conditioning-table spec | Each either ACCEPT or PARKED with named blocker |
| **W3** | Delivery to owners: conditioning table + management-rule proposal to V4 owners (#6805), hazard findings to the Prophet management law owner, clock findings to Temporal Grain; Agent OS handoff | Owner acknowledgement recorded; ladder rung stated honestly |

## 5. Frozen wave-1 experimental designs

Common conventions for all lanes: repository root on the compute host `~/lanes/repos/macro`; results under `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/<LANE>/`; price stores are FINAL-VINTAGE and the universes are SURVIVOR-SELECTED (current membership) — every RESULT.md states this in its first paragraph; warm-up exclusion = first 400 SESSIONS of each series regardless of grain; cost = 0.20pp round-trip charged once; returns are log returns; SPY excess = asset log return − SPY log return over the same sessions.

### 5.1 A1 — Baseline and clock truth (Priority A)

Question: are we measuring Prophet correctly, and what is the served definition today?
Deliverables: (a) served Prophet US definition from code with `file:line` receipts — indicator stack, grains, anchor era, universe filters, rank families (`us_prophet_v1..v3`, `conviction`, `confluence`, `bottoming-alignment`), lanes; (b) era/version map from `git log` of `engine/canon.py`, `engine/session_anchor.py`, `engine/bar_derive.py`, `engine/mtf_upturn.py`, `engine/us_board_rank.py` (dates constants or anchoring changed); (c) ledger denominators: `data/prophet/ledger.jsonl` rows by signal month × outcome; `data/us_board_ledger/retro_grades.parquet` rows by as_of month × rank_by × lane × horizon with `ret` coverage; (d) data inventory: first/last date, row count, columns, sha256 for every store named in §5.2–5.5 plus `regime_v2_pit` `pit_class` share by year; (e) parity: `engine.canon.rsi_macd` on SPY 1D vs an independent Pine-formula reimplementation — max |diff| after 400 sessions, and first-cross-date agreement; `engine.bar_derive.derive_3d_ohlcv` vs manual bucketing from `session_positions` — bar-boundary mismatch count at phase 0.
Falsifier: inability to reproduce signal identity (parity max |diff| > 1e-6 after warm-up, or any bar-boundary mismatch). If it fires, B1/C2 are blocked until explained.
Evidence level: 1 (mechanical reproducibility).

### 5.2 B1 — Stock-panel phase and matched-memory event panel (Priority B)

Universe: `data/baskets/ohlcv/*.parquet` (2,812 names, 2014-01-02 → 2026-10-02, OHLCV; current basket membership — survivor-selected); exclude names with < 800 sessions. SPY from `data/yahoo/SPY.parquet` is the clock and benchmark.
Variants (bullish event = RSI-MACD line crosses above its signal on bar close; `engine.canon.rsi_macd`, constants 14/14/60/5):
1. `1D` native;
2. `2D.p0`, `2D.p1` native 2-session bars, phases 0/1;
3. `3D.p0`, `3D.p1`, `3D.p2` native 3-session bars, phases 0/1/2;
4. `1D.M2`, `1D.M3` — 1D grain with every smoother's alpha transformed to match 2D / 3D elapsed memory (`alpha_new = 1 − (1 − alpha)^k`, **k = 1/2, 1/3** — amended 2026-10-04 per `DEC:B1-MEMORY-FACTOR-DIRECTION`; the frozen text said k = 2, 3, which SHORTENS memory; RSI RMA alpha = 1/14 transformed likewise);
5. `3D.K1` — 3D grain with every alpha transformed to 1D memory (**`k = 3`** — amended 2026-10-04, was `k = 1/3`), phase 0 only.
Outcomes per event: entry = next session close after the bar closes; SPY-excess at H5/H10/H21; close-based MFE/MAE over 21 sessions; sessions-to-MFE.
Confirmation pairs: for each `1D` event, the first `2D.p` and `3D.p` event (each phase) within 10 sessions after it → `delay_sessions`, `confirmation_cost_pct` (confirmation entry / 1D entry − 1), `mfe21_consumed_frac` (fraction of the 1D event's 21-session MFE already realised at the confirmation entry); `no_confirmation` flag if none within 10 sessions.
Statistics: per variant N, months, names, mean excess H10/H21 (cost-adjusted) with month-cluster bootstrap 95% CI, hit rate, median MFE/MAE. Phase dispersion: range of mean excess across phases and pairwise Jaccard of event-date sets; "phase-fragile" if the cross-phase range exceeds the pooled CI width. Grain-vs-memory contrasts: Δ(3D.p − 1D), Δ(3D.p − 1D.M3) [grain at matched memory], Δ(1D.M3 − 1D) [memory at fixed grain], Δ(3D.K1 − 3D.p0). Era split 2014–2019 / 2020–2026.
Verdict rule (pre-declared): a 3D grain effect exists only if Δ(3D.p − 1D.M3) has the same sign with a CI excluding zero in BOTH eras and in ≥ 2 of 3 phases. Otherwise the observed 3D-vs-1D difference is attributed to memory and/or phase.
Outputs: `events_panel.parquet`, `confirmation_pairs.parquet`, `result.json`, `RESULT.md`, code + tests, hashes.
Evidence level: 2 (descriptive association), survivor-selected, final-vintage.

### 5.3 C1 — Rotation / leadership state variable (Priority C primitive)

Inputs: SPDR sectors XLK XLE XLF XLV XLI XLY XLP XLU XLB (1998-12 →), XLRE (2015-10 →), XLC (2018-06 →); SPY; RSP (2003-05 →); `data/fred/DFII10.parquet` (2003-01 →); `data/regime/regime_v2_pit.parquet`.
Daily construction at date t using closes ≤ t only: sector 21-session log return minus SPY; cross-sectional rank among sectors available at t; **leadership persistence** `LP_t` = Spearman correlation of sector rank vectors at t and t−21; **leader retention** = share of the top-3 set at t−21 still top-3 at t; rotation speed = 1 − LP; **breadth spread** = RSP − SPY 21-session return (NaN before 2003-05); **participation share** = fraction of sectors beating SPY over 21 sessions; **real-rate impulse** = 21-session change in DFII10 (NaN before 2003). Terciles: expanding-window terciles over all dates ≤ t with ≥ 3 years of history (PIT-safe). Labels are shifted one session before use by any event lane.
Agreement: Cohen's kappa and a contingency table between `rotation_tercile == fast` and `regime_v2_pit.flag_rotation_persistence` (and `transition_state`), by era; `pit_class` carried.
Positive controls (descriptive, pre-declared): (a) LP must be persistent itself — AR(1) of LP at a 21-session lag > 0.5; (b) known fast-rotation windows (2020-11-09 → 2020-12-31 vaccine rotation; 2021-02-01 → 2021-03-31 reflation chop) must show a LOWER mean LP than known persistent-leadership windows (2022-01-03 → 2022-06-30 energy leadership; 2023-03-01 → 2023-06-30 mega-cap tech leadership). A variable failing either control is reported BROKEN and C2/F1 report their rotation-conditioned cells as INSUFFICIENT SUPPORT.
Outputs: `rotation_state_daily.parquet` (date, LP, retention, rotation_tercile, breadth_spread, breadth_tercile, participation_share, dfii_impulse, dfii_tercile, n_sectors), `result.json`, `RESULT.md`, code + tests, hashes.
Evidence level: 1–2.

### 5.4 C2 — The decisive interaction: rotation speed × confirmation cost (Priority C)

Hypothesis (from the Chairman's mechanism, 09 §3): narrow breadth + fast leadership turnover → shorter follow-through → the cost of waiting for slow (2D/3D) confirmation rises as leadership persistence falls.
Inputs: B1 `events_panel.parquet` + `confirmation_pairs.parquet`; C1 `rotation_state_daily.parquet` joined at the 1D signal date minus one session.
Primary statistic (pre-declared): `DiD(p) = [E(excess_H10 | 3D.p-confirmed entries) − E(excess_H10 | 1D entries)]_fast − [same]_persistent`, computed per phase p and pooled with equal phase weight; repeat for 2D.p vs 1D. Secondary: confirmation-cost curve = mean `mfe21_consumed_frac` at 2D/3D confirmation by rotation tercile; false starts avoided = share of 1D events with excess_H10 < −2pp that received no 3D confirmation, by tercile; large winners excluded = share of 1D events with excess_H21 > +10pp that never received 3D confirmation, by tercile. Second axis: breadth tercile (report only).
Inference: entry-month cluster bootstrap (1,000 draws, seed 20261004); floors per cell: ≥ 24 distinct months, ≥ 100 distinct names, ≥ 300 events, both eras represented; below floor → INSUFFICIENT SUPPORT for that cell.
Verdict rule (pre-declared): SUPPORTED iff pooled DiD < 0 with 95% CI excluding zero, the same sign in both eras, and in ≥ 2 of 3 phases, AND the confirmation-cost curve rises monotonically from persistent → fast. NOT SUPPORTED iff the pooled CI includes zero with adequate support. INSUFFICIENT SUPPORT otherwise. Either way the result is recorded.
Outputs: `result.json`, `RESULT.md` (with the cell table, honest-N, era and phase tables), code + tests, hashes.
Evidence level: 2 (descriptive association; not OOS decision usefulness — that is wave 2 with purged validation).

### 5.5 F1 — Entry vs management decomposition on the served ledger (Priority F)

Inputs: `data/us_board_ledger/retro_grades.parquet` (13,563 rows; as_of 2026-06-15 → 2026-09-17; horizons 5/10/21; rank_by families; lanes) and `data/prophet/ledger.jsonl` (≈300 closed episodes since 2026-03; schema `prophet.ledger/v1`, see `research/PROPHET_LEDGER_SCHEMA.md`); C1 `rotation_state_daily.parquet` joined at as_of.
Episode = (ticker, as_of, rank_by) with lane ∈ {buy, leaders}; path = excess_spy at H5/H10/H21 and `mae_close_excess_spy`. Competing outcomes by H21: SEVERE (excess_spy ≤ −7pp or MAE ≤ −7pp), TARGET (excess_spy ≥ +7pp), NEITHER.
Decomposition: (i) entry-state model — logistic regression of SEVERE on entry-state covariates (rotation tercile, breadth tercile, dfii tercile, `quad`, `vol_regime`, `off_high`, `band`, `archetype`, rank_by, sector) with purged out-of-sample AUC by as_of-week blocks; (ii) path model — discrete-time hazard of first SEVERE by horizon bucket (≤5, 6–10, 11–21) conditional on survival; (iii) attribution split — share of SEVERE episodes that were non-negative at H10 (deterioration after a good start) vs negative at H5 and never positive (immediate failure); (iv) same split by rotation tercile at entry.
Inference: as_of-week cluster bootstrap; honest-N (as_of dates ≈ 95 across 3 months; name count) stated up front — this is SMALL-N descriptive evidence.
Verdict rule (pre-declared): MANAGEMENT lever indicated if OOS AUC ≤ 0.55 and > 50% of SEVERE episodes were non-negative at H10; SELECTION lever indicated if OOS AUC ≥ 0.65 and > 50% were immediate failures; otherwise MIXED. Prophet ledger (`ledger.jsonl`) is reported as a second, smaller denominator with the same split by outcome class.
Outputs: `result.json`, `RESULT.md`, code + tests, hashes.
Evidence level: 2, small-N.

## 6. Evaluation contract

Evidence levels: 1 mechanical reproducibility · 2 descriptive association · 3 out-of-sample decision usefulness (purged, pre-registered) · 4 production acceptance. Evidence classes: final-vintage / source-vintage (as-observed) / live-forward. Wave 1 is level ≤ 2, final-vintage, survivor-selected. Nothing in wave 1 may be described as validated, promoted or live. The word "validated" is CI-guarded in user-facing text. Multiplicity: the number of contrasts per lane is reported; no adjustment is claimed; one primary statistic per lane is pre-declared. Honest-N appears in every cell table. Reviewers are instructed to REFUTE.

## 7. Product implication map (conditional; owner-gated)

| C2 verdict | B1 verdict | Proposal delivered to owners |
|---|---|---|
| SUPPORTED | grain effect real | Regime-conditioned confirmation grain: in persistent-leadership states keep the slow confirmation (2D/3D) for Prophet admission; in fast-rotation states admit on 1D with tighter management; delivered as a conditioning TABLE (state → recommended confirmation grain + expected cost/protection) for the V4 owners to evaluate under Phase-22 discipline — never a router inside this program |
| SUPPORTED | memory, not grain | Same conditioning, but implemented as kernel memory on the 1D grain (matched-memory variants), avoiding phase fragility |
| NOT SUPPORTED | any | No timeframe conditioning proposal; the September 2026 narrative is recorded as not supported at this evidence level; attention moves to F1's lever |
| INSUFFICIENT | any | Named data/support gap and the exact lane that closes it |

F1 feeds the management law: a MANAGEMENT verdict proposes hazard-based exit/review rules by signal age; a SELECTION verdict proposes entry-state screens to the ranker owners. Both are proposals with evidence level stated.

## 8. Pre-mortem (tripwires carried into packets)

1. A lane silently selects the best phase or threshold after outcomes → packets forbid it; reviewers check the code path ordering and that thresholds are expanding-window or constants.
2. Survivorship inflates every mean → stated in every RESULT first paragraph; reviewers refuse packets that omit it.
3. Grain and memory confounded (the #8303 lesson) → B1 variants 4–5 are mandatory; C2 reads B1's matched-memory contrasts before interpreting any 3D effect.
4. Same-day stock rows treated as independent → month-cluster bootstrap and honest-N are NOT DONE UNLESS items.
5. Compute host disk (mini2 at 98%) → outputs capped at 300 MB per lane, nothing written under `data/`; the seat rsyncs results back and the lane deletes nothing.
6. Lane runs git on the shared checkout → forbidden in every packet; the seat is the only committer.
7. PIT leak through regime labels → C1 shifts labels by one session and uses expanding terciles; C2 joins at t−1.
8. Small-N over-reading in F1 → verdict rules pre-declared; AUC floors; descriptive wording.
