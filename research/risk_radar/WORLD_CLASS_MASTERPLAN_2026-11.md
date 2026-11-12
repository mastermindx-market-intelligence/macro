# Risk Radar — world-class risk-state master plan (2026-11)

Status: **DRAFT for ruling** by the Prophet programme CEO. Project lead: Risk Radar upgrade lead
(Claude session, commissioned 2026-11-12). Built on `research/risk_radar/CENSUS_2026-11-12.md`
(Macro `main` `aed66e338d`). Pro inputs: PRO-RUN A (independent plan) and PRO-RUN B (critique of
this draft) return to issue #11104 and are folded in under §11 when they land.

Phase 1 changes nothing in the engine. This document proposes; nothing in it is installed.

---

## 0. Verdict

Risk Radar already has the right skeleton: typed scare legs, a context gate, a forward log with
issue receipts, and an envelope that keeps state, hazard and policy apart. Three things stop it
from being world class:

1. **It has no clean definition to test.** Every load-bearing threshold was chosen on data that
   includes 2020 onward (census §2: 14 tuned-in-window groups, 19 unknown, 11 convention). The
   test bed and the tuning window are the same years.
2. **It shows the wrong thing first.** The badge is `CAUTION · 74.6/100`, and the workspace opens on
   a pullback percentage that its own audit calls a gradient, not odds. Caution measures *below*
   base rate (0.90×), yet it is the state shown on 54 of 79 logged days.
3. **It has no series a consumer can join.** Rotation research, Prophet and the Shared Shell each
   have to read `latest.json` or the forward log and re-derive what the state was on a date.

The plan: **freeze one versioned definition, publish it as a dated point-in-time series, and let
the forward record from the freeze date be its test.** Fix the four-second read first. Add a
second, clean candidate fitted only on pre-2020 outcomes so the rotation desk has something it can
legitimately test on 2020–2023. Defer every new input until it has a point-in-time history and a
preregistration.

---

## 1. The four-second read, and the depth behind it

### What a user sees first (one line, one badge)

> **RISK STATE: GUARDED** · since 3 Nov · tape not confirming — *what would change it: SPY below its 200-day average with breadth in its bottom 40%*

- **Badge** = one of four public states (§2), worded for action, not a score.
- **Since** = date the current state began (from the series, §4). Users act on changes, so the
  age of the state is the second most useful fact.
- **Tape** = whether the broad market confirms (the context gate, today's single most measured
  lever: 2020+ gated H21 precision 42.0% vs 24.5% raw, census §3).
- **What would change it** = the nearest named trigger in each direction (§2.3), in plain words.

No number appears in the first read. The 0–100 score, the leg percentiles and the pullback
percentage move to the second layer.

### The depth (second and third layers, unchanged data, re-ordered)

1. **Why**: the hot scare types in words (e.g. "growth scare: defensives leading, 94th
   percentile"), each marked *validated* / *watching* / *accruing*.
2. **Track record of this state**: how often a ≥5% pullback followed within 21 sessions when this
   state was shown, with its sample size and window (e.g. "risk-off, 2020–2026: 43.8%, n=224, vs
   17.6% base"). Thin cells say "thin". This replaces the bare probability.
3. **Forward record since freeze**: rows, alerts, outcomes graded, readiness progress
   (`n / 252 sessions`).
4. **Full evidence**: today's workspace inspector, unchanged.

Chinese and English copy are written together; the four public state words get fixed
translations in the shared glossary, not per-page wording.

---

## 2. Target system

### 2.1 Public states (four, mapped from today's five)

| Public state | Means for the user | Mapped from current engine | Why |
|---|---|---|---|
| **CLEAR** | No scare type is hot. Normal risk appetite is supported. | calm, watch | Watch carries no measured lift; it is an internal early flag |
| **GUARDED** | One or more scare types are hot, but the broad tape does not confirm. Watch for confirmation; do not add new risk on the scare's axis. | caution | Caution is below base rate alone (0.90×). It is context, not a warning |
| **RISK-OFF WARNING** | Hot scare *and* the broad tape confirms (context gate met). | elevated | Gated; 2020+ H21 30.3% (thin, n=33) |
| **RISK-OFF** | Confirmed and broad. | risk-off | 2020+ H21 43.8% (n=224) |

Watch stays in the internal series for research. Collapsing it publicly removes a state with no
measured edge and halves the badge churn users see (watch↔calm↔caution flips are most of the 20
state changes in the log).

### 2.2 Transition hazard (separate output, not part of the state)

- **What**: probability of a ≥5% SPY drawdown *onset* within 21 sessions (the target the record
  already grades), shown as a **band** (`below base / near base / above base / well above base`)
  with the state's own measured rate and sample size beside it.
- **Not**: a precise percentage. The displayed-probability audit (cell calibration error 6.1 pp)
  and the failed walk-forward refit (worse Brier at all horizons) both say the current table is a
  gradient. The band is honest about that; the number stays in the evidence layer.
- Hazard never changes the state, and the state never sizes anything (DEC:RISK-STATE-HAZARD-POLICY-SEPARATION).

### 2.3 What would change the call (named triggers, both directions)

Every state publishes its triggers as data, computed from the same row that produced the state:

- **Up** (escalate): context gate becoming met (SPY < 200dma *and* %>200dma breadth ≤ 40th
  percentile); a second Tier-A scare reaching watch while a validated leg is armed; a hot Tier-B
  scare with a non-display-only leg firing.
- **Down** (de-escalate): the dominant scare's sub-score falling below the caution band; the gate
  lapsing; the existing trajectory phase turning `receding`.
- Each trigger shows its distance (e.g. "SPY 3.1% above its 200-day average").

No new model is needed: these are the existing `_resolve_state_row` conditions, exposed.

### 2.4 Repair and re-entry

The existing recovery engine (`engine/risk_radar_recovery.py`, recovery log 67 rows) and its
rebound ruler (first significance read 2027-01-15) own this. The plan adds one rule for the
public state: **a step down from RISK-OFF to GUARDED requires the down-trigger to hold for 5
sessions**, matching the persistence window already frozen before outcome inspection
(`RISK_RADAR_CAUTION_PERSISTENCE_RESULTS_2026-09-21.md:34`). This avoids flip-flopping and is
the knife-catching guard. Its effect on re-entry timing is graded by the forward record, not
tuned.

---

## 3. Evidence standard

### 3.1 Every element graded

Each constant and rule in the frozen definition carries one of four grades in the definition file
itself (machine-readable, rendered in the evidence layer):

| Grade | Meaning | Current count (census §2) |
|---|---|---:|
| `convention` | Textbook choice, never searched | 11 |
| `tuned_in_window` | Chosen on data that includes 2020 onward | 14 |
| `tuned_pre2020` | Chosen only on data ending ≤ 2019-12-31 | 0 |
| `unknown` | No evidence either way. Never rounded up | 19 |

### 3.2 The Chairman's ruling, applied

- **2020 onward is the product's test bed.** For the *current* definition (Radar v2), 2020+ is
  in-sample. Its 2020+ numbers are reported as *development evidence*, never as validation.
- **Long history is a secondary stability read.** 1993/2006–2019 numbers are shown as "does the
  rule behave the same way in older markets", never as the main claim.
- **The forward record from the freeze date is the test.** The definition is frozen by content
  hash. Every issued row carries the hash. Grading uses only rows issued under that hash.

### 3.3 Freeze and versioning

- `definition_id` = `rr-state-v2.0-<freeze date>`, with a SHA-256 of the canonical definition
  (bands, weights, thresholds, gate, rules). The envelope already has a `definition_id` field
  (`grey-deer-v1-2026-08-19` today); the radar series gets its own.
- **Any change to a graded constant = a new version.** The old version's forward record stops at
  that date; the new one starts at zero. Both stay published. This makes back-door re-tuning
  visible and expensive, which is the point.
- **The self-retuning review loop** (`engine/risk_radar_review.py`, 22 proposals, 0 applied) stays
  propose-only. Its proposals become candidate versions for a dated, preregistered review; it can
  never write `calibration.json` for the frozen version.
- Readiness bar (already frozen, `DEC-RISK-RADAR-PROSPECTIVE-VALIDATION-READINESS-BAR`): ≥252
  receipt-bearing same-version sessions, ≥300 days, per-horizon event and cluster minimums, paired
  Brier CI < 0. Passing it makes the version *eligible for a promotion review*, nothing more.

### 3.4 A clean candidate for 2020–2023 testing: Radar-P (pre-2020 fit)

The rotation desk can only test a state whose fitting used no 2020–2023 outcomes. Radar v2
cannot qualify. The plan therefore proposes **Radar-P**: the same legs and state machine, with every
`tuned_in_window` constant re-derived by a preregistered procedure using **outcomes dated ≤
2019-12-31 only** (inputs and their percentiles may extend later; outcome labels may not).

- Fitting window, procedure, search space and selection metric are preregistered and hash-pinned
  before any fit runs.
- Output is a dated series under its own `definition_id` with `fit_outcome_window_end:
  2019-12-31` in the definition file.
- It is then *handed* to the desk as a candidate. This programme never computes Radar-P's relation
  to 2020+ outcomes itself; the desk tests 2020–2023 under its own ledger, and 2024-01-02 onward
  stays sealed for everyone.
- **Known leak, declared up front:** the *set of legs* was itself chosen with 2020+ evidence (legs
  were kept or killed against a 2020+ holdout; e.g. VIX-term ROC, SKEW and VVIX were dropped that
  way, `engine/risk_radar.py:8-10`). Re-fitting constants does not remove that. Radar-P therefore
  ships in two variants: **P-legs-v2** (current leg set, constants clean, selection not) and
  **P-declared** (a leg set declared from economic rationale before any fit, including legs v2
  dropped, with constants fit ≤ 2019). Only P-declared may be described as clean of 2020+ outcomes;
  the desk is told which is which.
- **How the rotation desk treats them (Research Director, 2026-11-12):** P-legs-v2 is a *touched
  family*: its 2020–2023 result is reported as "replication on a seen period", never discovery
  evidence, and it is not eligible for the sealed-block read; its confirmation is the forward
  record. P-declared is a testable candidate only if its leg set is declared before the fit from
  pre-2020 information only (literature or pre-2020 data), even if smaller. Slice 3 therefore
  commits the P-declared leg set and its basis in the preregistration, before any fit, and the
  hand-off carries: path, commit, declared fitting window, leg set and its basis. The desk writes
  its own ledger rows; this programme never touches its ledger.
- Expected result, stated in advance: several 2020+-only legs (`bubble_ext`: lift 2.34 in 2020+,
  1.00 full history) will get small weights or drop. That is the honest cost of a clean test.

### 3.5 World class, in measurable terms

Bars graded on the forward record of a frozen version (and, for Radar-P, by the desk on
2020–2023). Numbers marked † are proposals for the CEO's ruling.

| Dimension | Metric | Bar |
|---|---|---|
| Point-in-time integrity | issued rows with a receipt; rows revised after issue | 100%; 0 |
| Freshness | sessions published by 06:00 ET next morning | ≥ 98%† |
| Loud-state selectivity | share of sessions in RISK-OFF WARNING or RISK-OFF | ≤ 20%† (2020+ gated today: 15.4%) |
| False alarms | loud episodes per year with no ≥5% drawdown onset within 21 sessions | ≤ 2†|
| Lead | median sessions from first loud state to ≥8% drawdown onset | ≥ 3 (today's gate median latency is 3)† |
| Recall | share of ≥10% drawdowns preceded by a loud state by onset | ≥ 60%† |
| Stability | public-state changes per year | ≤ 12† |
| Hazard skill | paired Brier vs base, 90% block-CI upper < 0 | the frozen readiness bar |
| Hazard honesty | band claims match observed rate band | ≥ 80% of graded cells† |
| Re-entry | median sessions from SPY trough to step-down from RISK-OFF | ≤ 15†, and no step-down that is followed by a new low within 10 sessions more than once a year† |
| Explanation | every loud state names its dominant scare, its triggers and the record of that state | 100% |

---

## 4. Consumer contract: the dated risk-state series

### 4.1 Artifact

`site/riskdata/risk_state_series.json` (and a mirror in the envelope's sources). One row per NYSE
session, append-only, **published from the existing nightly path that already writes the forward
log**. It is a projection of the forward log, not a new event store: the forward log stays the
system of record and the series is regenerated from it deterministically.

### 4.2 Row fields

| Field | Meaning |
|---|---|
| `session` | NYSE session date the state describes (data through that close) |
| `issued_at` | UTC time the row was first written (from the forward-log issue receipt) |
| `definition_id`, `definition_sha256` | version that produced it |
| `pit_class` | `prospective` (receipt-bearing) / `historical_replay` (computed later from stored inputs) / `pre_receipt` (logged before 2026-09-23) |
| `state` | public state (§2.1) |
| `engine_state`, `engine_state_ungated` | the five-step internal state, before/after gate |
| `gate_met` | context gate |
| `dominant_scare`, `hot_scares` | names only |
| `state_since` | first session of the current public state |
| `hazard_band` | §2.2 band |
| `triggers_up`, `triggers_down` | §2.3, with distances |
| `data_state` | `complete` / `partial` / `degraded` and the missing inputs. Null means unavailable, never calm |

### 4.3 Revision rules

- A prospective row is **never** edited. A correction is a new row with `supersedes` and a reason.
- Replay rows are labelled and are never mixed into the prospective grade.
- Late data: if an input arrives after issue, the row stays; the next session reflects it.

### 4.4 What each consumer may do

| Consumer | May | May not |
|---|---|---|
| Rotation research desk | Use `state`/`engine_state` as a dated feature, joined by `session`, filtered by `definition_id` and `pit_class`; test Radar-P on 2020–2023 under its own ledger | Treat Radar v2 2020+ rows as out-of-sample; join any signal to outcomes on 2024-01-02 onward |
| Prophet | Read `state` as an **eligibility sidecar** (display/flag beside the rank) | Change rank, population, size or order (DEC:PROPHET-RANK-PRESERVED-MARKET-ELIGIBILITY-SIDECAR) |
| Shared Shell beta | Render the four-second read and depth directly from the series + envelope | Recompute state, re-band, or show a probability as odds |
| Macro dashboard | Same as Shell | Same |
| Any LLM explainer | Explain and de-escalate wording | Produce or alter a state, band or probability |

Nothing in the series grants execution, sizing, gating or exit authority. The envelope's
`envelope_may_*` flags stay false.

---

## 5. Inputs: what carries information beyond sector and index prices

Current Tier-A legs that are **not** just prices: HY OAS velocity (credit), MOVE (rate vol), real
yields. Legs built only from ETF price ratios (bubble extension, SMH/SPY, XLU/SPY, XLY/XLP) are the
ones rotation research already sees directly, so they add least to a rotation desk. They stay in
the frozen v2 definition (changing them is a new version), but Radar-P and any v3 should prefer
non-price inputs.

| Input | Beyond prices? | PIT history | Status / rule before it may move a state |
|---|---|---|---|
| HY OAS 21d velocity | yes (credit) | FRED, deep | keep; only era-robust leg |
| MOVE level | yes (rate vol) | deep | keep |
| 10y real-yield change | yes | FRED, deep | keep (weak) |
| VIX term structure | partly | deep | Tier-B (lift 0.44 in 2020+) |
| Put/call, dealer GEX | yes (positioning) | forward only, gaps unbackfillable | accruing; preregister when ≥252 rows |
| COR1M implied correlation | yes | collector exists | confirmer only, display-only |
| Funding/dollar liquidity (e.g. FRA-OIS, cross-currency basis, broad dollar) | yes | partial, licence-dependent | **candidate for v3**; needs PIT source + prereg |
| Breadth (%>200dma, new highs) | partly | store exists | gate input; NH-contraction null at phase-0 |
| Country-ETF breadth, JPY carry | partly | yes | Tier-B accruing |
| Macro surprise | yes | vintage issues | not before a vintage-correct source exists |

Rule for any new input: point-in-time history, a preregistration naming its window and bar, and
entry as Tier-B (display/escalator-only) until it passes on a window that is not the tuning window.

---

## 6. Recommendations on the open PRs (recommendation only; owners decide)

| PR | Recommendation | Reason |
|---|---|---|
| #8721 measured "Pullback underway" in dialogs | **Keep** (owner ships) | Active writer (11-11); adds measured depth, fits the depth layer; slice 1 must rebase over it, not duplicate it |
| #10795 display-only multi-asset context | **Keep**, then absorb as a depth-layer section | Display-only, within the envelope contract; useful "why" context; merge-blocked by its owner |
| #7872 episode-aware international authority | **Keep**, separate lane | International authority, not the US state series; CI failing is the owner's |
| #7897 China probability/hazard revalidation | **Keep** (research HOLD) | Same evidence discipline this plan asks for; feeds the international version later |
| #10489 rotation freshness/coverage in workspace | **Absorb** into slice 1 if dormant 14 days, else keep | Overlaps the depth layer; conflicting and failing CI |
| #7040 score velocity + regime-change explanation | **Supersede** by slice 1 + §2.3 triggers | Dormant since 09-14; triggers-with-distance replace score velocity as the "what changed" explanation |
| #9137, #9198 escape strings in dialogs | **Absorb** (one combined escaping fix, credited) | Small, correct security hygiene; both conflicting and dormant |
| Also touching Radar files: #9548, #10389, #10740, #7875 | Keep; coordinate file order | Live writers on workspace JS/template; slice 1 lands after or rebases |

---

## 7. First three slices (ordered by user value; one PR each)

### Slice 1 — The four-second read (display only)

- **Change**: card and workspace lead with the public state word, `since` date, tape
  confirmation and the nearest trigger each way (§1, §2.1, §2.3). Score and probability move to
  the second layer; probability rendered as a band plus the state's own record and n. Bilingual
  glossary entries for the four states. No engine math changes: the mapping and triggers are
  computed from fields `compute()` already returns (state, state_ungated, context_gate, scare
  scores, bands).
- **Proof**: (a) unit tests that the mapping is total over the five engine states and that
  triggers equal the `_resolve_state_row` conditions on fixture rows; (b) a byte check that
  `forward_log.jsonl` rows and `_PROB_CAL` are unchanged by the PR; (c) dual-theme desktop + mobile
  screenshots of US and China cards in the PR; (d) existing Radar template tests pass; (e) a
  reader test: the first visible line contains no number other than the date.
- **Value**: fixes what every user sees today, and stops presenting caution as a warning.

### Slice 2 — Freeze v2 and publish the dated risk-state series

- **Change**: canonical definition file with grades (§3.1) and SHA; `definition_id` +
  `definition_sha256` written into each new forward-log row; deterministic projection to
  `site/riskdata/risk_state_series.json` (§4) from the existing nightly writer; review loop held
  propose-only for the frozen version; envelope source entry.
- **Proof**: (a) the series regenerates byte-identically from the forward log; (b) every row since
  2026-09-23 has `pit_class: prospective` and a receipt, older rows `pre_receipt`; (c) a test that
  changing any graded constant changes the SHA and fails a "frozen version" check; (d) contract
  schema in `contracts/` with a consumer read test that needs no engine import; (e) first nightly
  run on main shows the new artifact, verified from `origin/main`.
- **Value**: the rotation desk, Prophet sidecar and Shell get a joinable state; the forward record
  of a fixed definition starts counting from its freeze date.

### Slice 3 — Radar-P preregistration and fit (pre-2020 outcomes only)

- **Change**: preregistration (the P-declared leg set and its pre-2020 basis, window, outcome definition, search space, selection metric, stop
  rule) committed and hash-pinned first; then a research script that fits the `tuned_in_window`
  constants using outcomes dated ≤ 2019-12-31 only, and emits a Radar-P definition file and its
  replay series labelled `historical_replay`. No change to the live engine or live state.
- **Proof**: (a) prereg commit precedes the results commit; (b) a guard test that the fitter
  rejects any outcome label dated after 2019-12-31 (fails if a later date is fed); (c) results
  report pre-2020 in-sample fit only, with no 2020+ outcome number computed anywhere; (d)
  path + commit sent to the rotation desk's Research Director as a candidate.
- **Value**: the first risk state the desk can legitimately test on 2020–2023.

Later (not sized here): hazard-band honesty grading on the forward record; repair/re-entry
persistence rule live; funding/liquidity input preregistration; Shared Shell move.

---

## 8. What stays out

- **do_not_redo (binding)**: no universal fused risk score in authority paths; no new event store
  or forward ledger for risk episodes (the series is a projection of the existing forward log);
  no Prophet rank or population mutation; no posture_decider arming and no LLM probability in any
  authoritative consumer; no automatic exits; no re-runs of pullback stage-1/1b; no edits to frozen
  preregistrations (corrections ship as dated addenda).
- No trading permission, sizing or execution from any state. Paper-only.
- No re-tuning of v2 on any window. Any change is a new version with a fresh forward record.
- No displayed probability as calibrated odds.
- No new leg into Tier A without PIT history and a preregistered out-of-window pass.
- No computation of any signal–outcome relation dated 2024-01-02 onward, by anyone in this
  programme. No 2020+ outcome evaluation of Radar-P by this programme; that is the desk's test.
- No QLedger-dependent slice while `data/qledger/claims.jsonl` sits at the GitHub size limit.
- No edits to the open PRs listed in §6.

---

## 9. Dependencies and risks

- Slice 1 touches templates also touched by #8721, #9548, #10389: land after them or rebase.
- Slice 2 adds a field to forward-log rows; the scorecard reader must tolerate it (test).
- Radar-P may underperform v2 on 2020+ when the desk tests it. That is information, not failure.
- The readiness bar cannot be met before late 2027 at one row per session; the four-second read
  must say "record: n sessions since freeze" rather than imply validation.

## 10. Not verified

Provenance of the shipped band literals 55/68/78/88; the leg-lift study scripts (not in repo);
why the contagion log stopped on 2026-10-16; whether the public four-state mapping reduces flips
as much as expected (to be measured on the forward record, not tuned).

## 11. Pro inputs

- PRO-RUN A (independent plan, chatgpt4): pending — issue #11104.
- PRO-RUN B (adversarial critique of this draft): pending — issue #11104.
- Adjudication of their points will be recorded here, each as accepted / rejected / deferred with
  the reason.
