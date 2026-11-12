# Risk Radar — world-class risk-state master plan (2026-11)

Status: **DRAFT v2 for ruling** by the Prophet programme CEO. Project lead: Risk Radar upgrade lead
(Claude session, commissioned 2026-11-12). Built on `research/risk_radar/CENSUS_2026-11-12.md`
(Macro `main` `aed66e338d`) and the **direction ruling of 2026-11-12** (Chairman, via the Prophet
CEO), recorded in §0.1. Pro inputs return to issue #11104 and are adjudicated in §11.

Phase 1 changes nothing in the engine. This document proposes; nothing in it is installed.

---

## 0. Verdict

Risk Radar is kept and upgraded, not replaced. It already has the right skeleton: typed scare
legs, a context gate, a forward log with issue receipts, and an envelope that keeps state, hazard
and policy apart. Being fitted to the modern regime (2020 onward: pandemic, a rate-hike risk-off
cycle, tariffs, wars, QE) is the design. What it lacks is **proof that its fitting procedure
works**, and **an origin for every number it ships**.

Three gaps, three fixes:

1. **The fitting procedure is unwritten and unproven.** 14 parameter groups were tuned on modern
   data by ad-hoc sweeps; 19 have no recorded origin; the shipped bands 55/68/78/88 match neither
   documented sweep (census §2). Fix: write the procedure down, then **refit it walk-forward inside
   the modern regime** (fit to end-2021, score 2022; to end-2022, score 2023; … to today) and
   report out-of-sample hit rate, lead time and false alarms beside the in-sample figures, against
   simple baselines. Every production number then comes from that procedure. → **Slice 1.**
2. **It shows the wrong thing first.** The badge is `CAUTION · 74.6/100`; caution measures below
   base (0.90×) yet is the state on 54 of 79 logged days; the workspace leads with a pullback
   percentage its own audit calls a gradient. Fix: a four-second read in words. → **Slice 2.**
3. **It has no series a consumer can join.** Fix: publish the dated walk-forward state series
   (Slice 1) and the live, versioned state series on a stated refit schedule. → **Slice 3.**

### 0.1 Direction ruling (2026-11-12), as applied here

1. Fitted to the modern regime is the design. Production Radar is fitted on all modern data
   available, on a stated schedule. In-window tuning is not disqualifying.
2. What needs proof is the **fitting procedure**, by rolling walk-forward refit inside the modern
   regime, compared with simple baselines (SPY under its 200-session average, VIX level, credit
   spread change). Out-of-sample and in-sample are reported side by side, never mixed.
3. The 19 unknown groups and the band literals get values from the written procedure.
4. A dated walk-forward state series (each date's state from parameters fitted before it) is a
   Macro artifact the research desk may use as a feature and regime label. The current fitted
   composite is still not used as a feature on 2020–2023.
5. Stress reads beyond the sample (2008, 2018) are descriptive only and gate nothing.
6. Walk-forward scoring on 2024 onward is allowed for this purpose: it is the Radar's own,
   already-seen history, labelled as such, and is not the research desk's sealed confirmation.
7. Existing limits stand (§8). Phase 1 remains plan-only.

---

## 1. The four-second read, and the depth behind it

### What a user sees first (one line, one badge)

> **RISK STATE: GUARDED** · since 3 Nov · tape not confirming — *what would change it: SPY below its 200-day average with breadth in its bottom 40%*

- **Badge** = one of four public states (§2.1), worded for action, not a score.
- **Since** = date the current state began. Users act on changes, so the age of the state is the
  second most useful fact.
- **Tape** = whether the broad market confirms (the context gate). This is confirmation, not a
  forecast (§13).
- **What would change it** = the nearest named trigger in each direction (§2.3), in plain words.

No number other than the date appears in the first read.

### The depth (second and third layers)

1. **Why**: the hot scare types in words, each marked *validated* / *watching* / *accruing*.
2. **Track record of this state**, two columns never merged: *walk-forward (out-of-sample)* and
   *in-sample*, each with n and window; thin cells say "thin". Replaces the bare probability.
3. **Forward record since the current version's freeze**: rows, loud states, graded outcomes.
4. **Full evidence**: today's workspace inspector, unchanged.

Chinese and English copy are written together; the four state words get fixed translations in the
shared glossary.

---

## 2. Target system

### 2.1 Public states (four, mapped from today's five)

> **Superseded names (2026-11-12, Principal ruling).** The Radar is a decline-confirmation state
> with no false risk-off calls; it is not a warning and not a pivot call. The public names in the
> table below, including "RISK-OFF WARNING", are withdrawn. No state is named or read as a warning
> until a signal passes the identification pass line. Names will come from the Paper design
> (designer → critic route); the table is kept only as the record of the earlier proposal.

| Public state | Means for the user | Engine state | Why |
|---|---|---|---|
| **CLEAR** | No scare type is hot. | calm, watch | Watch has no measured lift; it stays an internal flag |
| **GUARDED** | Scare(s) hot, broad tape not confirming. Watch; do not add risk on the scare's axis. | caution | Caution alone measures below base (0.90×) |
| **RISK-OFF WARNING** | Hot scare and the tape confirms (gate met). | elevated | Gated |
| **RISK-OFF** | Confirmed and broad. | risk-off | Gated, highest measured rate |

The mapping is display; the five-step engine state stays in every series. Whether the four-state
read reduces flips is measured, not assumed (Slice 1 reports flip rates for both).

### 2.2 Transition hazard (separate output)

Probability of a ≥5% SPY drawdown onset within 21 sessions, shown as a **band** (below base / near
base / above base / well above base) with the state's walk-forward rate and n beside it. The
current table is a gradient (cell calibration error 6.1 pp; the earlier walk-forward refit of the
probability failed 4 of 6 checks), so a precise number stays in the evidence layer until the new
walk-forward shows calibration. Hazard never changes the state; the state never sizes anything.

### 2.3 What would change the call

Each state publishes its triggers, computed from the same row that produced it (the existing
`_resolve_state_row` conditions, exposed with distances): **up** — gate becoming met; a second
Tier-A scare reaching watch with a validated leg armed; an eligible Tier-B escalation. **Down** —
dominant scare below the caution band; gate lapsing; trajectory `receding`.

### 2.4 Repair and re-entry

Owned by the existing recovery engine (`engine/risk_radar_recovery.py`) and its rebound ruler. A
step down from RISK-OFF needs the down-trigger to hold for a persistence window. That window is a
**parameter of the fitting procedure** (§3.2), not a hand-set constant, and its walk-forward effect
on re-entry timing (sessions from trough; re-entries followed by a new low) is reported.

---

## 3. Fitting procedure and evidence standard

### 3.1 Every number has an origin

Each constant in production carries one origin in a machine-readable definition file:

| Origin | Meaning |
|---|---|
| `fitted` | Output of the written procedure on a stated fit window (with the fit's commit and SHA) |
| `convention` | Textbook choice, deliberately not fitted (e.g. 200-session average), listed as such in the procedure |
| `structural` | A rule, not a number (e.g. "Tier B can only escalate"), fixed by design and listed |

`unknown` is not an allowed origin after Slice 1. Census today: 14 tuned-in-window, 19 unknown, 11
convention. Slice 1 assigns each of the 44 groups to `fitted`, `convention` or `structural` and
writes the reason; the band literals 55/68/78/88 become `fitted`.

### 3.2 The written procedure (to be preregistered in Slice 1 before any refit runs)

- **Tuned**: bands (watch/caution/elevated/risk-off), Tier-A leg thresholds, Tier-A and Tier-B
  weight pairs, context-gate breadth percentile, step-down persistence window, hazard-band table.
  Everything else is `convention` or `structural` with a written reason.
- **Objective** (one, declared): maximise H21 loud-state precision for ≥5% SPY drawdown onsets,
  subject to recall ≥ a stated floor and loud-state share ≤ a stated ceiling; ties broken toward
  the simpler / convention value. Alternative objectives are reported, never selected post hoc.
- **Search**: a small declared grid per parameter (coarse steps, e.g. bands in 5-point steps),
  coordinate-wise with a fixed order, with shrinkage toward the current or convention value
  (a parameter moves only if the gain clears a stated margin). The grid, order and margin are
  frozen in the preregistration.
- **Data**: modern regime from 2020-01-02 (inputs may use earlier history for trailing
  percentiles — a 504-session window needs it). Expanding fit window.
- **Leg set**: the current 16 legs, fixed. Adding or removing a leg is not part of the procedure;
  it is a new version with its own walk-forward.

### 3.3 Walk-forward refit inside the modern regime

| Fold | Fit outcomes through | Score (out-of-sample) |
|---|---|---|
| 1 | 2021-12-31 | 2022 |
| 2 | 2022-12-30 | 2023 |
| 3 | 2023-12-29 | 2024 |
| 4 | 2024-12-31 | 2025 |
| 5 | 2025-12-31 | 2026 to date |

- An embargo of 21 sessions between fit end and score start, so H21 labels cannot overlap.
- Each fold's parameters are frozen and hashed; each scored date's state comes only from the
  parameters of the fold fitted before it.
- **Reported per fold and pooled, out-of-sample beside in-sample, never mixed**: loud-state hit
  rate (precision) at H5/H10/H21; recall of ≥5%, ≥8%, ≥10% drawdowns; median lead from first
  loud state to onset; false-alarm episodes per year; loud-state share; flip rate; parameter drift
  between folds; hazard-band calibration.
- **Baselines**, scored on the same dates and labels: SPY < 200-session average; VIX ≥ 20 and ≥ 25
  (convention levels); HY OAS 21-session change in its top decile (trailing 504-session percentile);
  and the current v2 constants frozen as of today (to show what refitting adds over "keep v2").
- **Labelling**: folds 3–5 (2024 onward) are labelled "Radar's own seen history — walk-forward
  scoring, not sealed confirmation" (ruling point 6). The whole table is labelled
  development evidence of the procedure; the confirmation of any production version remains its
  forward record from its freeze date.
- **Honest limits stated in advance**: fold 1 fits on two years with few drawdown episodes; five
  folds give few independent episodes per year; results carry block-bootstrap intervals and an
  episode count, and a fold with fewer than 3 onset episodes is marked thin. PRO-RUN B/D is asked
  to attack exactly this (§11).

### 3.4 Stress beyond the sample (descriptive only)

The final-fold parameters, applied unchanged to 2007–2009 and 2018: a table of states by month,
lead to the 2008 and Q4-2018 onsets, and time in loud states. It gates nothing.

### 3.5 Production fitting schedule and versioning

- Production parameters = the procedure run on all modern data to date, **refit annually** on the
  first session after year-end close (and on an explicit dated rule change). Each refit is a new
  `definition_id` + SHA; every forward-log row carries both.
- The forward record of each version runs from its freeze date to the next refit; all stay
  published.
- The self-retuning review loop (`engine/risk_radar_review.py`, 22 proposals, 0 applied) stays
  propose-only; its proposals feed the next scheduled refit as recorded notes, never
  `calibration.json` mid-version.
- The frozen readiness bar (≥252 receipt-bearing same-version sessions, etc.) still governs any
  *promotion* claim. With annual refits a version gets ~252 sessions, so readiness is assessed per
  version at its end, and pooled across versions of the same procedure as a second read.

### 3.6 World class, in measurable terms

Graded first on the walk-forward folds (out-of-sample columns), then on each version's forward
record. † = proposal for ruling.

| Dimension | Metric | Bar |
|---|---|---|
| Point-in-time integrity | issued rows with receipt; rows revised after issue | 100%; 0 |
| Provenance | production constants with origin `fitted`/`convention`/`structural` | 100% |
| Beats baselines | walk-forward H21 loud precision vs best baseline at matched loud share | higher in ≥ 3 of 5 folds and pooled† |
| Selectivity | loud-state share of sessions | ≤ 20%† |
| False alarms | loud episodes/year without a ≥5% onset within 21 sessions | ≤ 2† |
| Lead | median sessions, first loud state → ≥8% onset | ≥ 3† |
| Recall | ≥10% drawdowns preceded by a loud state by onset | ≥ 60%† |
| Stability | public-state changes per year | ≤ 12† |
| Procedure stability | parameter drift between adjacent folds | within one grid step for ≥ 80% of parameters† |
| Re-entry | median sessions trough → step-down from RISK-OFF | ≤ 15†; ≤ 1 premature step-down/year† |
| Explanation | loud states naming scare, triggers, record | 100% |

---

## 4. Consumer contracts

### 4.1 Walk-forward state series (Slice 1 artifact)

`data/risk_radar/walkforward_state_series.json` (+ site mirror). One row per NYSE session
2022-01-03 onward: `session`, `fold`, `fold_fit_through`, `definition_sha256` of that fold,
`engine_state`, `public_state`, `gate_met`, `dominant_scare`, `label`
(`walkforward_oos` / `walkforward_seen_2024plus`). Computed only from parameters fitted before the
session. The research desk may use it as a feature and regime label (ruling point 4); the current
fitted composite may not be used as a feature on 2020–2023.

### 4.2 Live risk-state series (Slice 3)

`site/riskdata/risk_state_series.json`, one row per session, projected deterministically from the
existing forward log (the forward log stays the system of record — this is not a new event store):

| Field | Meaning |
|---|---|
| `session` / `issued_at` | session described (data through that close) / UTC first-write time |
| `definition_id`, `definition_sha256` | version that produced it |
| `pit_class` | `prospective` (receipt-bearing) / `pre_receipt` (before 2026-09-23) |
| `public_state`, `engine_state`, `engine_state_ungated`, `gate_met` | the state |
| `state_since`, `dominant_scare`, `hot_scares` | context |
| `hazard_band` | §2.2 |
| `triggers_up`, `triggers_down` | §2.3 with distances |
| `data_state` | complete / partial / degraded + missing inputs; null never means calm |

Revision rules: a prospective row is never edited; corrections are new rows with `supersedes`;
late data shows in the next session.

### 4.3 What each consumer may do

| Consumer | May | May not |
|---|---|---|
| Rotation research desk | Use the walk-forward series as a feature/regime label; use the live series from each version's freeze | Use the current fitted composite as a feature on 2020–2023; treat 2024+ walk-forward rows as its sealed confirmation |
| Prophet | Read `public_state` as an eligibility sidecar | Change rank, population, size or order |
| Shared Shell beta / Macro dashboard | Render the four-second read and depth from the series + envelope | Recompute or re-band state; show probability as odds |
| LLM explainers | Explain and de-escalate wording | Produce or alter a state, band or probability |

No series grants execution, sizing, gating or exit authority; `envelope_may_*` stay false.

---

## 5. Inputs: what carries information beyond sector and index prices

Non-price legs today: HY OAS velocity (the only era-robust leg), MOVE, real-yield change. Price-
ratio legs (bubble extension, SMH/SPY, XLU/SPY, XLY/XLP) overlap what a rotation desk already sees.
The leg set is fixed for this procedure; new inputs enter only as a new version with its own
walk-forward:

| Input | Beyond prices? | PIT history | Path |
|---|---|---|---|
| HY OAS velocity, MOVE, real yields | yes | deep | keep |
| VIX term structure | partly | deep | Tier-B |
| Put/call, dealer GEX | yes (positioning) | forward only, gaps | accruing until ≥252 rows |
| COR1M | yes | collector exists | confirmer, display-only |
| Funding / dollar liquidity (FRA-OIS, cross-currency basis, broad dollar) | yes | partial, licence-dependent | **first v-next candidate** |
| Breadth (%>200dma, new highs) | partly | yes | gate input |
| Country-ETF breadth, JPY carry | partly | yes | Tier-B |
| Macro surprise | yes | vintage issues | not before a vintage-correct source |

A pre-2020-declared leg set ("P-declared", fitted on pre-2020 outcomes) remains available as an
optional later candidate for the research desk's discovery block; it is no longer on the critical
path (the desk's treatment of touched families is recorded in its own charter).

---

## 6. Recommendations on the open PRs (recommendation only; owners decide)

| PR | Recommendation | Reason |
|---|---|---|
| #8721 "Pullback underway" in dialogs | **Keep** | Active writer (11-11); measured depth fits the depth layer; Slice 2 rebases over it |
| #10795 display-only multi-asset context | **Keep**, then absorb as a depth section | Display-only, within the envelope contract |
| #7872 episode-aware international authority | **Keep**, separate lane | International authority, not the US series |
| #7897 China probability/hazard revalidation | **Keep** (research HOLD) | Same evidence discipline; later model for an international walk-forward |
| #10489 workspace freshness/coverage | **Absorb** into Slice 2 if dormant 14 days, else keep | Overlaps the depth layer; conflicting, CI failing |
| #7040 score velocity explanation | **Supersede** by Slice 2 triggers | Dormant since 09-14 |
| #9137, #9198 dialog string escaping | **Absorb** as one credited fix | Small, correct, dormant, conflicting |
| #9548, #10389, #10740, #7875 | Keep; coordinate file order | Live writers on workspace JS/templates/review |

---

## 7. First three slices (one PR each)

### Slice 1 — Written fitting procedure + walk-forward refit + dated walk-forward series

- **Change**: (a) preregistration of the procedure (§3.2) and the fold plan (§3.3), committed and
  hash-pinned before any refit; (b) a research script that runs the procedure per fold, reusing
  `engine/risk_radar_backtest.state_series` → `_resolve_state_row` (the parity-fixed owner) so
  replay and live cannot drift; (c) results report: per-fold and pooled out-of-sample beside
  in-sample, baselines, intervals, episode counts, provenance table for all 44 groups, 2008/2018
  descriptive stress table; (d) `data/risk_radar/walkforward_state_series.json`. No change to the
  live engine, live state or forward log.
- **Proof**: prereg commit precedes results commit; a test that each fold's fitter refuses outcome
  labels after its fit-through date (feeds a later label, expects failure); a test that every
  series row's parameters come from a fold whose `fit_through` + embargo < `session`; replay parity
  test (fold parameters run through `compute()` and the backtest give identical states on fixture
  rows); report states which numbers are out-of-sample in every table header; byte check that
  `engine/risk_radar.py` and `forward_log.jsonl` are unchanged.
- **Size risk**: if over one reviewable PR, split 1a prereg + harness + tests, 1b results + series.
- **Value**: the first evidence of how the Radar would really have run through 2022, and an origin
  for every number.

### Slice 2 — The four-second read (display only)

- **Change**: card and workspace lead with public state, `since`, tape confirmation and nearest
  triggers (§1, §2); score and probability move to the depth layer; track record shows
  walk-forward and in-sample columns from Slice 1; bilingual glossary entries. No engine math.
- **Proof**: mapping is total over the five engine states; triggers equal `_resolve_state_row`
  conditions on fixture rows; `forward_log.jsonl` and `_PROB_CAL` unchanged; dual-theme desktop +
  mobile screenshots for US and China cards; existing Radar template tests pass; first visible line
  contains no number other than the date.
- **Value**: fixes what every user sees today and stops presenting caution as a warning.

### Slice 3 — Production refit on schedule + versioned live series

- **Change**: production constants replaced by the procedure's all-modern-data fit, each with its
  origin in the definition file; `definition_id` + `definition_sha256` written into every new
  forward-log row; deterministic projection to `site/riskdata/risk_state_series.json` (§4.2);
  review loop held propose-only; annual refit schedule documented; envelope source entry.
- **Proof**: zero constants with origin `unknown`; series regenerates byte-identically from the
  forward log; changing any fitted constant changes the SHA and fails a frozen-version check;
  contract schema in `contracts/` with a consumer read test that needs no engine import; scorecard
  tolerates the new fields; first nightly run on main shows the new artifact, verified from
  `origin/main`; the forward record of the new version starts at zero.
- **Value**: a production Radar whose every number has an origin, and a joinable live state.

---

## 8. What stays out

- **do_not_redo (binding)**: no universal fused risk score in authority paths; no new event store
  or forward ledger for risk episodes (both series are projections/research artifacts, the forward
  log stays the record); no Prophet rank or population mutation; no posture_decider arming and no
  LLM probability in any authoritative consumer; no automatic exits; no re-runs of pullback
  stage-1/1b; no edits to frozen preregistrations (corrections as dated addenda).
- No trading permission, sizing or execution from any state. Paper-only.
- No production change outside the scheduled, versioned refit.
- No displayed probability as calibrated odds until walk-forward calibration supports it.
- No leg added to or removed from the procedure without a new version and its own walk-forward.
- The current fitted composite is not a feature on 2020–2023 for the research desk; 2024+
  walk-forward rows are not its sealed confirmation.
- No QLedger-dependent slice while `data/qledger/claims.jsonl` sits at the GitHub size limit.
- No edits to the open PRs in §6.

## 9. Dependencies and risks

- Slice 1 depends on the stored input history (yahoo/fred/cboe/breadth stores) back to ~2018 for
  504-session percentiles; sparse checkouts must materialise them first.
- Little history: fold 1 fits on two years; few onset episodes per fold. Results may be too thin
  to rank the procedure against baselines; that outcome is reported, not tuned away.
- Slice 2 touches templates also touched by #8721, #9548, #10389: land after them or rebase.
- Slice 3 adds forward-log fields; the scorecard reader must tolerate them (test).

## 10. Not verified

Provenance of the shipped band literals (to be replaced by Slice 1); the leg-lift study scripts
(lived in `/tmp`, not in repo); why the contagion log stopped on 2026-10-16; whether the stored
input history reaches far enough back for fold 1 without gaps.

## 11. Pro inputs and adjudication

- PRO-RUN A (independent plan, chatgpt4): pending, issue #11104.
- PRO-RUN B (critique of draft v1): pending, issue #11104 — written before the ruling; points on
  the old Radar-P framing will be adjudicated against v2.
- PRO-RUN C (Extra High implementation plan, slices of v1): pending.
- PRO-RUN D (critique of v2's walk-forward design: is walk-forward refit with this little history
  informative, and what would make it more so): to be sent.
- Each point will be recorded here as accepted / rejected / deferred with the reason.

---

## 12. Scorecard, shared code and the challenger rule (ruling 2026-11-12, second)

The Chairman's bar: 43.8% against a 17.6% base is not world class. Refitting today's constants
will not reach it, so accuracy becomes a research problem with the Radar as the incumbent.
**The research desk owns discovery. This programme owns the incumbent, the scorecard and the
installation path.**

### 12.1 Scorecard (built: `engine/risk_radar_eval/scorecard.py`)

One function scores any daily alert series on identical terms:
- budget (share of days on);
- day-level precision/lift (the definition behind the 43.8% figure);
- episode level at ≥5/7/10% drawdowns and h = 3/5/10/21:
  - caught before onset;
  - caught by breach;
  - median lead;
  - alert runs split into in-episode, early-true and false alarms;
  - false alarms per year;
- h21 probability calibration (Brier skill, reliability bins).

The first in-sample reference is at `research/risk_radar/walkforward/SCORECARD_INSAMPLE_2026-11-12.md`.
Its headline: the loud Radar caught **0 of 9** ≥5% episodes before onset since 2020 (exact 90%
interval 0–28%). All 25 of
its loud runs began inside an episode already under way, so it is a confirmation signal. At a
smaller budget, HY OAS velocity alone matches its day-level precision and leads the 10% breaches
by 17 sessions against 3.

### 12.2 Shared label and input code (built: `engine/risk_radar_eval/`)

- `labels.py`: SPY total-return day-level labels and drawdown episodes. Every call requires an
  explicit `outcomes_through`. Scoring at or after 2024-01-02 is refused unless declared the
  incumbent's seen history.
- `inputs.py`: the incumbent's leg panel (the live `leading_signals()`), gate components and the
  fixed-rule baselines.
- Tests are in `tests/test_risk_radar_eval.py`.

The research desk imports these, so a challenger is scored exactly as the incumbent is.

### 12.3 Challenger rule

A candidate replaces or joins the fitted composite only if it beats the walk-forward incumbent
on the shared scorecard, at the same alert budget, through the same written fitting procedure
(folds, embargo, objective, search discipline). No candidate enters the live engine any other
way. For challengers, 2024-01-02 onward stays sealed. A pass makes the candidate eligible for a
new version (§3.5), whose own forward record then runs from its freeze. Paper-only throughout.

### 12.4 Change to slice 1

Slice 1 now also ships the scorecard and shared code (done on the branch, unmerged). The
objective in the fitting procedure moves from day-level precision to **episode recall by breach
at a fixed budget**; see `research/risk_radar/walkforward/FITTING_PROCEDURE_DRAFT.md`. This
supersedes the objective stated in §3.2.

---

## 13. Rulings of 2026-11-12 (third) applied

### 13.1 Two jobs, scored separately

- **Confirmation** is the job of the loud states (RISK-OFF WARNING, RISK-OFF). Across all 25 loud
  runs since 2020, every one began inside a drawdown already under way. The loud state says "a
  broad risk-off move is happening". It is never presented as a forecast. Slice 2's copy says
  this in words: "The tape confirms a risk-off move", not "X% chance of a pullback". The 43.8%
  day figure appears nowhere in the four-second read or its first depth layer. Its successor
  (44.8%, n=239 days, 28 runs, 9 episodes) appears only in the evidence layer, labelled
  "day-level, in-sample, overlapping days".
- **Early warning** is a second job with its own alert budget and its own scorecard row. Its
  incumbent is GUARDED (caution+): on 78% of days it is too broad to be a warning. The baseline
  it has to beat is credit-spread velocity (§13.4). Discovery of a better early-warning signal
  belongs to the research desk under the challenger rule. This programme does not run a second
  discovery effort.

### 13.2 Scorecard additions (built)

For every signal and baseline, at each depth (5/7/10%) and horizon, the scorecard
(`engine/risk_radar_eval/scorecard.py`) now reports:

- lead in sessions to the breach;
- loss avoided, as the share of each episode's peak-to-trough decline that came after the first
  alert;
- costs:
  - rebound given up (trough to recovery);
  - return given up on alert days outside episodes;
  - sessions from the trough to all-clear;
- a net figure: loss avoided minus costs, per year.

Every rate carries its episode count and an exact 90% binomial interval. With 9 cases that
interval is wide (3/9 → 0.10–0.65), and nothing narrower is quoted. The episode definition is
unchanged; pooling across sectors and markets belongs to the research desk.

In-sample finding (2020–2026, `walkforward/SCORECARD_INSAMPLE_2026-11-12.md` §3b): no series
nets positive after rebound and outside costs. The best are the Radar's risk-off state at +0.1%/yr
and HY OAS velocity at −3.0%/yr. The loud state switches off promptly at the trough, but it comes
on late and so captures about half of each decline.

### 13.3 Proposed fit objective (to be put to PRO-RUN D's adjudication)

The ruling's default: loss avoided net of cost, at a fixed budget. Proposed precisely:

- **Primary**: maximise `net_avoided_minus_cost` per year over ≥7% episodes (h = 21), at a fixed
  loud-state budget of 15% of sessions (±2 pp; configurations outside the band are infeasible).
- **Tie-breaks**, in order: median loss-avoided share, then median lead to the −7% breach, then
  fewer false alarms.
- **Reported, never optimised**: day-level precision and calibration.
- **Known weakness**: the net figure is dominated by the largest episode (2020, 2022) and by the
  rebound term. With 9 episodes it may select for "switch off fast" rather than "switch on
  early". D is asked to judge this. The alternative is a median-of-episodes objective.

### 13.4 Baseline to beat

HY OAS 21-session change in its top decile (11% budget) catches 5/9 ≥5% episodes by breach, with
a 17-session lead to the ≥10% breaches. It is the strongest single baseline. It is recorded as
**the baseline every challenger, and the refit incumbent, must beat**. It enters the engine only
through the challenger rule.

### 13.5 Elevated cell reconciled; quotes withdrawn

The September figures (elevated 30.3%, risk-off 43.8%) reproduce exactly only with the
`global_breadth` leg absent. The live configuration gives elevated 3.2% (n=31) and risk-off 44.8%
(n=239). The September elevated figure is withdrawn. See
`walkforward/ELEVATED_CELL_RECONCILIATION_2026-11-12.md`. The walk-forward series records leg
availability per date.

### 13.6 Slice 1b order

The rebuilds run in this order:

1. put/call from the CBOE daily archive
2. GEX from historical option chains
3. AI-breadth split from point-in-time constituents and the AI tag

Each rebuild records its source and its first point-in-time date.

## 14. Pro adjudication and the pivot steer (2026-11-12, fourth)

Returns on macro#11104:
- **PRO-RUN A** (independent plan, 03:06Z).
- **PRO-RUN D** (walk-forward attack, 03:14Z, pinned to 558638d05e).
- **PRO-RUN B** (critique, 03:17Z; it reviewed v1, v2 and §13).
- **PRO-RUN C** (optional Extra High implementation plan) was **not sent**: the operator failed on
  model capacity while setting effort, with no send attempted. It is dropped, not resent.

### 14.1 Chairman steer: pivots are the goal

The primary read is now the pivot scorecard (`engine/risk_radar_eval/pivots.py`;
`walkforward/PIVOT_SCORECARD_INSAMPLE_2026-11-12.md`). For every turn into risk-off (top) and back
to risk-on (bottom) it records:
- whether the turn was flagged, and the delay in sessions;
- the share flagged within [−21, +10];
- false risk-off calls per year;
- premature all-clears per year;
- the same figures by era.

A reliable call a few sessions after the turn counts. The loud state's confirmation job is scored
on its delay, and the all-clear is scored the same way. Paper economics move to a secondary
column. The window and hold length go to the research desk for reconciliation with its swing-rule
catalogue (one label set, one scorecard).

In-sample (≥5%, post 10):

| Series | Tops flagged | Bottoms flagged (clean all-clear) | Premature all-clears per year |
|---|---|---|---|
| Loud Radar | 1/9 | 1/8 | 1.75 |
| HY OAS velocity (11% of days) | 3/9 (early) | 4/8 | 2.9 |

### 14.2 PRO-RUN D, point by point (all accepted unless noted)

| # | Finding | Ruling |
|---|---|---|
| 1 | "3 of 5 folds" is not a superiority test on 7 clusters | **Accepted.** One primary endpoint and one comparator. Practical effect declared (±2 turns). "Inconclusive" is valid. The fold table is descriptive. |
| 2 | Literal 21-session post-fit embargo discards stress tests | **Accepted.** Label maturity at T replaces the score embargo. Score from the next session; January events are kept. |
| 3 | Trailing percentiles ≠ point-in-time | **Accepted.** A prefix-invariance proof is required before the first fit. Leg availability is recorded by date. |
| 4 | Net objective ≠ its labels | **Accepted.** Separate endpoints; net is secondary and renamed (remaining decline after first alert; retrospective arithmetic attribution). The §13.3 net objective is **withdrawn**; the fit objective is the pivot objective (prereg §3). |
| 5 | Eleven coordinates are too flexible | **Accepted.** One outcome-fitted quantity (gate cut, 4 candidates) plus an outcome-free budget offset. Retain-default rule. |
| 6 | Design selection sits outside the firewall | **Accepted.** Claim class "retrospectively designed, chronological refit reconstruction"; frozen components are listed as hindsight-informed. |
| 7 | Budget matching must be time-respecting | **Accepted.** Natural-share baselines plus fit-window-calibrated analogues; realized budgets reported. |
| 8 | Proofs could certify the wrong implementation | **Accepted.** Label maturity, prefix invariance, parameter intervention (the harness injects the gate; the module constant is not consumed), calendar, censoring, effective-state hash. Persistence is dropped (not consumed by the resolver). |
| 9 | Synchronise documents | **Accepted.** The prereg supersedes §3.2, §13.3 and the draft. |

"Is walk-forward with this little history informative?" D's answer, adopted: as a **development
audit**, yes. It can expose leakage, unstable fits, alarm burden and failure against simple
baselines. It cannot establish modest superiority. More information comes from:
1. The paired episode table with influence (leave-one-crisis-out) checks.
2. Multi-market replication, which is the desk's job.
3. Prospective tracking of the one frozen procedure.

Quarterly or monthly refits add drift information, not episodes.

### 14.3 PRO-RUN B (REWORK), judged against v2 + §13

- **Accepted:**
  - The seal is enforced on every label-support observation, not only on the origin.
  - Production replacement (slice 3) runs as a shadow path under its own identity; it needs a
    consumer inventory and separate authority before any live swap.
  - The probability target is named for what it is (≥5% loss within 21 observations), and
    onset/breach targets get separate IDs.
  - As-of joins on `consumer_available_at`.
  - Same-close recognition is kept apart from advance warning (delay ≤ −1).
  - Full-path parity including the gate.
  - Unavailable/stale outranks the badge, and the gate is shown as a qualifier.
  - Slice 2 ships observed duration only; no new sticky step-down rule.
  - Issued, receipt-bearing and admissible counts are reported separately.
  - NOT_ESTIMABLE never counts as PASS.
  - Configured values are separated from observed rates.
- **PR dispositions corrected:**
  - #8721 keeps its tested precedence for observed damage.
  - #7040's publication-relative "what changed" is preserved.
  - #10489 needs proof of writer custody, not elapsed time.
  - #9137 and #9198 are absorbed only as the union of their surfaces.
- **Slice order:** the truthfulness repairs in slice 2 no longer wait for a fit.
- **Rejected:**
  - "No 2024+ grading at all". Direction ruling point 6 allows the incumbent's walk-forward scoring
    of 2024+, labelled as seen history; challengers stay sealed.
  - Removing the walk-forward from the work packet, for the same reason.

### 14.4 PRO-RUN A

- **Accepted:**
  - The evidence-lane table, with 2024+ handled as in 14.3.
  - Freezing one champion with its selection history.
  - Version and correction rules.
  - **Close the back door.** `risk_radar_review` can write the calibration overlay that the engine
    reads at runtime. All 22 proposals were refused, but the write path exists. This is added to
    slice 3 as a first item, coordinated with #10740.
- **Deferred:** A's broader three-state measured-account redesign. It overlaps §2 and is weighed
  in slice 2 copy.

### 14.5 Prereg

Frozen as `walkforward/PREREG_WALKFORWARD_v1.md` (hash in `PREREG_WALKFORWARD_v1.sha256`).

### 14.6 Worker routing (steer)

- Raw testing, data rebuilds, reruns and sweeps go to `deepseek-v4.1-flash` workers in parallel.
- The principal directs, reviews and adjudicates.

### 14.7 Insurer profile (descriptive appendix; demoted 2026-11-12)

Added as declared secondary reads in `walkforward/PREREG_WALKFORWARD_v1_ADDENDUM_1.md` with no
frozen item changed. `engine/risk_radar_eval/insurer.py` reports:
- max drawdown and time under water;
- drawdowns avoided and gains kept;
- Sharpe and Sortino in excess of bills.

These are shown against SPY, RSP, vol-matched SPY + bills, 60/40 and SPY-or-bills 200d. Reports
read ≥10%, then ≥7%, then ≥5% turn recall, each with false alarms and gains forgone beside it.

The in-sample insurer figures are **not a result** (principal ruling 2026-11-12): they are the
incumbent on the years its parameters were tuned on, including the sealed years. They stay in
`walkforward/SCORECARD_INSAMPLE_2026-11-12.md` §5–§6, labelled in-sample, and out of every summary
until the walk-forward series replaces them.

### 14.8 Chairman correction: pivot identification only (2026-11-12)

"We're not doing portfolio management… The point is pivot identification." Every Radar summary
leads with the pivot read: flagged or not, sessions before or after the turn, false calls per year,
against the near-high placebo and the two mechanical references (within 1% of the high; ≥5% below
it). The insurer read and the sleeve comparators (vol-matched SPY + bills, 60/40, the 200-session
rule as a sleeve) are a descriptive appendix, never a bar or headline. The 200-session rule remains
an identification baseline only. The frozen primary endpoint was already the pivot read; nothing
frozen changes.
