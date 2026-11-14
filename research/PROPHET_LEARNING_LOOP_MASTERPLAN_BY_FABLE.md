# Prophet Learning Loop — postmortem forensics, exit-policy measurement, ledger continuity (masterplan by Fable)

Date: 2026-08-02 · Status: CHARTERED — operator-directed (2026-08-02 session, second directive:
"analyze BOTH our winners and losers… reverse engineer the exact root mistakes… build the
infrastructure for this to be regularly done… let your winners run and cut your losers short…
optimize for longer term capital returns… China track record wiped 7/30 — get our history back").
Program id: `prophet_learning_loop`. Sibling: `research/PROPHET_BOARD_PRIORITY_ENGINE_MASTERPLAN_BY_FABLE.md`
(same session, same PR). Evidence anchors: `engine/track_scoring.py` (#3664 three rules),
`research/US_BOARD_MEASUREMENT.md`, memory `backtest-horizon-swing-2-4-weeks` (horizon-ladder
STANDING rule), memory `us-board-definition-change-2026-06-25` (era-pooling trap).

---

## §0 ACCEPTANCE GATES (binding)

- **G1 — Postmortem engine produces root-cause rows for the operator's loser cohort.** Running
  `python -m scripts.prophet_postmortem` over the committed ledgers yields, for each of
  OLN 07-21 / AMKR 07-17 / IPGP 07-15 / STAA 07-15 / PSKY 07-01 / FN 07-21 / CDNS 07-09 /
  IPGP 07-10 / UNIT 07-21 / HL 07-01 / BG 07-17 (the 2026-07-31 track-record worst rows): a
  deterministic failure taxonomy, entry-time context (theme/sector state AT ENTRY from git
  history of `data/baskets/latest.json` + sector stage artifacts), visible-at-entry flags, and
  an anomalous-vs-systemic aggregation. A fixture test pins ≥ the IPGP double-admission
  detection — same ticker re-admitted ≤ 10 sessions after a prior episode that REALIZED a
  ≥ 8% loss (`prior_episode_loss`). That is the leg IPGP actually fires on, and it is
  HINDSIGHT: the first position was +3.04% green on the night the board bought the name
  back. The sibling leg `open_drawdown_at_readmit` (prior position already ≥ 8% under
  water AT the re-admission) is the buildable one and fires 0 times on the 2026-07-31
  window; both are costed, separately labelled, in the veto table.
- **G2 — Taxonomy is deterministic.** Every classification is a feature-threshold rule
  (documented in-module); no LLM anywhere in the classification path (A7: LLMs never originate
  signals). Multi-label allowed; every label carries its trigger values.
- **G3 — Exit-policy horse race is date-blocked and decomposed.** Same-entry-cohort comparison
  on matured US episodes: fixed H=10 (incumbent) vs H=21 vs trailing-stop family (ATR-k) vs
  target/stop (Prophet plan geometry), reporting per policy: expectancy, win rate, avg
  win/loss, MAE/MFE capture, and the **winners-kept vs losers-cut decomposition** (how much of
  the policy delta comes from extending winners vs truncating losers). Date-blocked CIs
  (engine/track_scoring date_block_ci or equivalent); overlapping-window caveat printed.
  Verdict language: DESCRIPTIVE ONLY — "policy X shows…", no "validated", no product change.
- **G4 — Track-scoring core untouched.** The three #3664 rules (forced verdict, symmetric
  maturity, date-blocked CIs) stay intact in `engine/track_scoring.py`; the horse race is a
  SEPARATE study reading the same episodes. The public track record's headline stays the
  incumbent rule until any change passes promotion.
- **G5 — CN ledger continuity restored.** `cn_track_ledger.json` (or a sibling artifact)
  carries the PRIOR-definition record (2026-06-30..07-29 cohort, ~1,082 board.parquet rows)
  graded under the same scoring core, clearly labeled as the previous board definition, NEVER
  pooled with the cn_prophet_v2 record (era-pooling trap, memory `us-board-definition-change`).
  The China dialog shows both: "current definition (accruing since 07-30)" + "previous
  definition (Jun 30 – Jul 29)". History visible again; honesty preserved.
- **G6 — The loop is institutionalized.** A recurring review protocol exists as a checked-in
  doc (`docs/PROPHET_POSTMORTEM_PROTOCOL.md`): when it runs (weekly + after any ≥3-loser
  cluster), what the artifact provides, what a Fable session does with it (adjudicate systemic
  vs anomalous; register candidate fixes via prereg; NEVER hot-patch score weights from one
  week's losers), and where verdicts are recorded. The admin surface points at the artifact.
- **G7 — No new authority claims.** Everything here is measurement/display tier. Any gate/veto
  born from forensics (e.g. "sector-headwind demotion") is registered as a candidate with its
  own prereg — explicitly NOT shipped in this program.

## §1 The reconciliation (fixed-horizon record vs "let winners run")

Two different jobs, two instruments — never one blended number:
1. **The track record** measures SIGNAL QUALITY: comparable, forced-verdict, fixed-H episodes
   (H=10 empirical; H=5 showed no edge). It must stay policy-free so eras and desks compare.
   It grows a **horizon LADDER** (10/21 now, 63 as records mature — descriptive columns beside
   the verdict horizon, per the standing ladder rule) so "does the edge extend?" becomes a
   printed fact instead of a debate.
2. **The exit-policy horse race (G3)** measures TRADE MANAGEMENT: on identical entries, what a
   holder-with-rules captures. This is where "let winners run / cut losers short" is tested —
   including the operator's hypothesis that impulse moves sometimes extend for months when a
   sector enters a larger bull move (the trailing-stop family is exactly the instrument that
   captures those without predicting them).
3. **Longer-term pick quality** enters selection only through evidence: the ladder + postmortem
   cohorts (e.g. theme-tailwind at entry vs 63d outcome) feed candidate features into the
   promotion pipeline (pick-lab books / preregs), never directly into live weights.

## §2 Postmortem engine design (`scripts/prophet_postmortem.py` + `engine/postmortem.py`)

- **Inputs:** `data/us_board_ledger/retro_grades.parquet` + `snapshots.jsonl` (entry rows,
  matured outcomes), closes caches (path context), git history of `data/baskets/latest.json`
  (theme state at entry date — 31 commits available), sector stage from the entry-date board
  row itself (spotlight/sector fields), signal fields captured in snapshots.
- **Per-episode output row:** ticker, entry_date, horizon, excess/abs return, MAE/MFE, and:
  - `entry_context`: theme id + reco + label + bull_days AT ENTRY; sector spotlight stage;
    extension state; tier; alpha; conviction band; days_since_signal.
  - `failure_labels` (matured losers ≤ −8% abs or ≤ −5% excess): each with trigger values —
    `sector_headwind` (theme/sector reco ∈ {avoid, trim} at entry — VISIBLE-AT-ENTRY),
    `bought_extended` (ext evidence at entry), `thesis_break` (base-broken flag date from
    hold-state history when reconstructable; else close crossed entry-row stop level),
    `gap_event` (≥8% single-session gap against the position — earnings/news class),
    `market_beta` (excess loss < 40% of absolute loss — the tape, not the pick),
    `re_admission` (same ticker re-admitted ≤10 sessions after a prior episode that was
    already ≥8% under water — `open_drawdown_at_readmit`, BUILDABLE — or that realized a
    ≥8% loss — `prior_episode_loss`, HINDSIGHT, the IPGP case),
    `idiosyncratic` (none of the above fired).
  - `visible_at_entry`: bool per label (could the engine have known?). A label whose legs
    disagree is NOT visible-at-entry as a label — `re_admission` is excluded on exactly
    that ground — and is costed one row per leg instead, each stamped `buildable` or
    `hindsight_upper_bound`. The per-ROW flag stays leg-specific.
- **Aggregations artifact** (`data/prophet_postmortem/summary.json` + a rendered
  `reports/prophet_postmortem_<asof>.md`): label frequencies, loss contribution per label,
  cohort splits (headwind-at-entry vs tailwind-at-entry loss rates + the SYMMETRIC winners
  split — what a headwind veto would have cost in missed winners: the operator's "don't weed
  out real winners" requirement is a first-class column, not a footnote), repeat-offender
  table, systemic-vs-anomalous read (label concentration across independent dates).
- **Admin surface:** the existing rudimentary admin Prophet panel gains a link/table reading
  summary.json (smallest possible admin change; the artifact is the product).
- **Winners get the same treatment** (≥ +8%): what did the big winners share at entry? Same
  labels, opposite sign — the learning loop reads both tails.

## §3 CN continuity design (G5)

`build_china_library.emit_cn_track_ledger` currently filters episodes to the live
`board_definition` (cn_prophet_v2 → 15 stamped rows → record reset on 07-30). Change: grade
the full parquet in TWO cohorts split on definition stamp (null/legacy = "cn_standout_v1
(pre-2026-07-30)"), emit `prior_record` block alongside the current one (same scorer, same
rules, separate n/summary), template renders both with era labels. Parquet is untouched
(append-only store; verified intact 2026-08-02: 1,097 rows, 06-30..07-31).

## §4 Build lanes (this session; new files — no collision with the priority-engine lanes)

- **M1 (builder/Opus):** §2 postmortem engine + §3 CN emitter continuity + G6 protocol doc +
  tests (fixture: the 11-loser cohort; IPGP re-admission pin; era-split emit).
- **M2 (builder/Opus):** G3 exit-policy horse race script + report + ladder columns where
  maturity allows; touches NO shipping engine besides reading; report committed.
- CN dialog template half of G5 → folded into the CN board UI lane (same file ownership).

## §5 What this program does NOT do

No score-weight changes from forensics findings; no new vetoes; no pooling of eras; no
"validated" language; no LLM classification; no admin rebuild (link + table only); no HK/CA
extension yet. Each candidate fix graduating from the loop gets its own prereg + verdict.

---

## 2026-11-12 on-demand review — re-admission hindsight cluster (2026-07-31 artifact)

**Adjudication: DESCRIPTIVE ONLY; no live veto, score change, or validated edge.**
Source of truth: data/prophet_postmortem/summary.json (as_of 2026-07-31,
blob be2a3bf09566037636492611b81188626dd7bfb1), its companion
reports/prophet_postmortem_2026-07-31.md and the standing protocol
docs/PROPHET_POSTMORTEM_PROTOCOL.md. This is a review of that historical
window, **not** a fresh November backtest or current-production acceptance.

### Observation and what it does NOT prove

- There were 808 buy-board episodes across 24 board dates, 610 matured across
  18 dates, 194 in flight and 4 unscored. Matured cohorts: 132 losers,
  91 winners, 387 neutral. Fixed H=10, hypothetical next-session-close fills,
  no simulated stop; board appearances are **not executed trades**.
- The re_admission:prior_episode_loss **HINDSIGHT** row flagged 8 matured
  episodes across **7 distinct entry dates**: DCH (2026-06-18, -15.91%),
  ADNT (06-22, -9.61%), SONO (06-22, -2.40%, **neutral**),
  HWKN (06-24, -19.18%), P (07-06, -5.02%), CVSA (07-09, -11.50%),
  IPGP (07-15, -17.86%) and ODFL (07-21, -7.45%).
  Seven meet the combined loser gate (absolute <= -8% **or** SPY-excess
  <= -5%), none the winner gate. The displayed **+86.53pp** is arithmetic
  saved over the **seven loser tails only**, not a portfolio return: it
  excludes SONO's -2.40% neutral outcome, sizing, overlap and trade costs.
  Do not interpret this as executable alpha.
- Earlier position's mark **on the re-admission date**: DCH -4.54%,
  ADNT -4.63%, SONO -3.50%, HWKN +2.05%, P +0.76%, CVSA +1.36%,
  IPGP +3.04%, ODFL +1.31%. The prior episodes' 10-session outcomes
  were not resolved on their respective re-admission dates.
  The buildable sibling, re_admission:open_drawdown_at_readmit, fired
  **0/610**. An empty executable-signal sample cannot establish veto value.
- All 87 matured episodes with a recent prior averaged +0.86% (19 losers,
  11 winners), versus +1.29% for 523 other matured episodes (113 losers,
  80 winners). This unadjusted -0.43pp difference is exploratory and
  cannot isolate repeat-admission causality. A same-entry-date cluster
  bootstrap (12,000 exploratory resamples of 18 matured board dates)
  gave approximate 95% bounds **[-1.73, +0.90]pp**, including zero;
  this is NOT a promotion-grade confidence interval.
- Four of eight July flagged re-admissions had sector_basket.reco=avoid;
  earlier June cases lacked comparable recorded sector recommendation.
  Across **all** repeat-admission rows with avoid/trim sector status
  there were **13** episodes, four losers, **two winners**, seven neutral.
  A blanket veto would discard winners and requires symmetric evaluation.
- None of the eight carried entry_plan.status=buy_now: two buy_soon;
  six hold, wait_pullback, await_confluence or bounce_wait. The study
  measures buy-board appearances and simulated forced entries, not
  whether actual execution-eligible trades violated a gate.

### Hypothesis, falsifiers and owned next actions

**Unproven hypothesis:** a ticker may remain on or reappear on the board
while its sector thesis or entry readiness weakens. The four July cases
motivate investigation, not a conclusion about cause or a trading rule.

1. **Refresh evidence:** establish the latest actual ledger and artifact
   vintage, run the existing read-only/dry-run integrity/postmortem paths
   where applicable and separate authentically stamped board-definition
   eras. The Observatory displays a **July 31 historical artifact**;
   the weekly review protocol does not prove that this artifact refreshed.
2. **Verify PIT feature availability:** a re-admission candidate must use
   only prior membership, price marks and sector/entry state available
   by the decision clock. Audit scripts/prophet_postmortem.py::_mark_at:
   searchsorted with side="left" might select a later close if the board
   date is missing from the price index. Test exact-date/as-of behavior.
   This is an **audit question**, NOT a finding that these eight leaked.
3. **Test the right unit:** distinguish repeated board membership, explicit
   actionable admissions and executed positions. Compare eligible
   episodes with unflagged cases within each genuine board-definition
   era, date-blocked and out-of-sample, pricing losers, winners **and
   neutral return exposure**. Pre-register thresholds before any new
   confirmatory data, not after reading these eight rows.
4. **Clarify the observatory:** admin/prophet.py::_learning_loop already
   forwards variant, leg and visible_at_entry. Ensure the UI visibly
   labels the +86.53pp row "HINDSIGHT ONLY — NOT ACTIONABLE", distinguishes
   the separate buildable 0/610 row, and shows artifact vintage and
   the hypothetical board-signal measurement basis. Verify real-browser
   display if a later UI correction is made.

**Verdict:** a recurring retrospective cluster worth PIT investigation,
**not a measured buildable rule**. No changes here to classification,
scoring, weights, live gates or execution. Normal G6 accrual,
pre-registration and symmetric evidence requirements stay in force.
