# US trigger truth: TKR incident, 2026-11-05

## Assignment and source

Chairman asks why TKR leads the fresh-trigger table on `us_stocks.html` despite a
falling chart, and how to address the failure class while distinguishing WELL and
ARCB. Existing programme: `WS:PROPHET-US-V4-RECOVERY`; related signal research:
`WS:PROPHET-US-ENTRY-TIMING`. This is a bounded incident investigation and source
repair, not a new signal, ranking model, runtime operation, or trading authority.

Protected Mastermind procedure: `49c2e1d93e5e080b1671c98087a845e5beb09dd5`,
skillpack 1.0.1 / bootstrap 1. Macro source base:
`e39ec45902c1a2bb28507beb851593be6e422167`.
Source carrier: `claude/prophet-trigger-truth-20261105`.
Native parent/root: `01a1adb7-6569-7576-a2e1-85e092c83027`.

## Outcome and completion evidence

Explain the actual producer-to-page failure with immutable records; stop a
historical or pending trigger from being presented as a verified current buy;
preserve the existing selection/ranking/ledger semantics; prove the repair with
discriminating state, freshness, paid/public parity, and rendered-page tests.
Source, hosted CI, release, and live acceptance remain distinct.

## Recovery and expanded assignment — 2026-11-05

The Chairman subsequently authorized publication of the prepared patch/PR and
architecture plus implementation to materially improve Prophet, then assigned
this successor to resume the timed-out assessment. That authorization addresses
the destination-consent reason recorded in the historical publication section
below; it does not authorize merge, deployment, new trading rules, or bypassing
scientific, source-custody, and release controls.

Recovered source remains the original branch and clean local candidate
`3342a1bfe40a99756a166843f61b5da6ccba8d18`. Exact GitHub ref and PR-head reads
found no published branch or PR before this continuation. No modifying process,
Fabric child, watcher, or unresolved publication effect is inherited. This is
source continuation, not transfer of an admitted Runtime Job.

Current protected procedure is Mastermind
`32450bbb13634351f32fd0221ddd9c79277e5197`, compatible skillpack 1.0.1.
Macro main was read and fetched at
`96633a798efda34d899e1b135487c89b596215fc`. All eight candidate source/test
paths and the workspace guide are unchanged between the original base and this
main, so accepted focused source tests remain applicable; fresh hosted CI and
real-browser proof remain owed. The resumed native session identifier is
`01a1ae3a-f705-715b-a3f5-add7720f703f`; the historical root above is retained as
provenance, not asserted as a current Fabric grant.

The existing task tree continues:

- **P4 — publication**: authorized; publish on this original branch, open its
  reviewable PR, then consume the actual hosted checks. No duplicate carrier.
- **P5 — entry-quality integration**: trace current candidate-state,
  entry-availability, geometry, and risk inputs through their existing owners;
  identify the smallest complete producer-to-consumer improvement. Preserve
  nullable/unknown states and exact observation clocks. No parallel ranker,
  lifecycle, evidence store, or hand-tuned TKR exclusion.
- **P6 — validation and product proof**: verify the repaired states in actual
  browser renders and regressions. Any predictive promotion requires the
  existing point-in-time, episode-level evaluation and release owners; truthful
  UI/contract repair does not assert improved returns.

The principal retains source integration for `PRINCIPAL_JUDGMENT` and
`CRITICAL_PATH_SHORTCUT`: the unresolved question is which existing authority
must supply the absent inputs, not how to invent an additional signal. Bounded
delegation requires a real original-root/parent binding; exposed Fabric tools
alone do not establish that identity.

## Resumed implementation and publication receipt

The original carrier is now published as **Macro draft PR #10786**:
<https://github.com/mastermindx-market-intelligence/macro/pull/10786>.
The initial remote commit is `6b140691fc3a6418c9c28c172ac3816e38075727`.
Its complete tree, `fd866698e73c17010924d5e9d0bb553097b863cd`, exactly matches
local recovery commit `7e42db77b4987036c0afb504ad4dbeda91d3584b`.
The local shell push failed before a remote effect because it had no GitHub
credential helper; an exact ref read still returned absent. The already
authenticated GitHub connector then created each verified blob, the matching
tree and commit, and this same branch/PR. No credential was read or changed.
This supersedes the historical publication human gate below. Draft, merge,
deployment, and live product acceptance remain separate.

Initial hosted checks: fences run `42137333759` passed. CI run `42137333877`
was still running at this receipt; its planner passed. These receipts apply to
the initial remote head only, not automatically to subsequent commits.

### P5a — existing daily-cycle context reaches the trigger table

The existing `engine.entry_signal.assess` already distinguishes `blocked` /
`avoid`, `bounce_wait`, `extended` / `topping`, wait states, and legacy open
states. `scripts/build_stock_library.py` already attaches that result to the
wide board but omitted it from `setups.json`. The resumed patch connects the
same admitted result to the trigger rows after selection and ranking:

- `price_context` is a closed display projection containing only `status` and
  `asof`. The date is the last non-null close actually supplied to `assess`,
  not the build time, residual-alpha snapshot, or independently enriched
  technical-price clock. Missing owners/clocks remain explicitly unavailable.
- The projection is populated only in the existing non-stale/non-delisted
  branch. It adds no membership rule, rank, score, price geometry, size, or
  entry-availability fact. The original owner output is unchanged.
- The shared public/paid row displays the dated price context alongside the
  independent signal observation. A confirmed historical trigger can therefore
  show a decline or unconfirmed turn without hiding the conflict. Legacy
  `buy_now` / `partial` becomes **Entry check needed** on this surface; it does
  not become an `ENTRY_OPEN` assertion.
- English and Chinese use the existing mobile-visible signal column. Missing
  context in older snapshots stays visible as unavailable. Unknown future
  statuses cannot produce a positive entry label.

Focused validation after this change: **55 passed**, covering actual cycle
owner outputs, exact source-bar clocks (including a later missing bar), pending
confirmation, malformed/absent inputs, same-date snapshot replacement,
producer-to-loader-to-public/paid propagation, unchanged row ordering/scores,
paid-name separation, and the existing mobile-column contract. These overlap
earlier accepted tests and are not an additional 55 independent checks to add
to the previous 67. Actual browser visual/accessibility acceptance remains owed.
The separate existing entry-gauge, feed-freshness and price-clock compatibility
selection passed **56 tests** (8 new trigger cases excluded because they ran in
the focused selection). Python compilation and `git diff --check` also passed.
Commands used the recovered test dependencies via
`PYTHONPATH=/workspace/scratch/2b4262f6094d/test_deps:.`:

```text
python -m pytest -q tests/test_build_stock_library_price_clock.py tests/test_dashboard_template_render.py tests/test_us_board_gate.py -k 'trigger or strip_tables_mobile_column_contract'
python -m pytest -q tests/test_entry_signal.py tests/test_stock_library_freshness.py tests/test_build_stock_library_price_clock.py -k 'not trigger'
```

### P5b — canonical current-entry integration boundary

The implementation must continue through the incumbent owners below. It must
not translate the legacy display projection into trading authority.

| Responsibility | Existing owner | Verified boundary / required next evidence |
| --- | --- | --- |
| Candidate identity, episode, generation and factual projection | `engine/prophet_candidate_state.py` | B3 intentionally emits unavailable B4; preserve its source-only contract. |
| One native B3/B4 read and exact binding | `engine/prophet_b4_same_read.py` | Uses `verified_pair`, the same snapshot, identity/session matching and owner-byte re-attestation. Currently passes empty geometry and metric mappings. |
| Quote/live-state source qualification | `engine/prophet_entry_availability_sources.py` | Private source timestamp, matching quote age/price, alias reversal and measured quote/armed-pack basis are checked. That measurement does not establish the independently produced geometry basis. |
| Dated daily-cycle display context | `engine/entry_signal.py` and the existing stock-library producer | Safe for the bounded display projection above. Its `atr_pct` is a close-to-close proxy; it can fall back to 2% of spot. It has no native episode-bound first-trigger/anchor/ATR contract. |
| Current-entry decision | `engine/prophet_entry_availability.py` | Sole B4 evaluator; required unknowns must remain unavailable. Do not infer a healthy structure from an oscillator tier or reuse an old snapshot as a live quote. |
| Risk, liquidity and gap policy | `engine/prophet_entry_policy.py` | Existing control constants are `SHADOW_ONLY` / `CONTROL_ONLY` and not calibrated. Wiring them as live admission PASS would be a scientific promotion, not a neutral integration. |

**Next native vertical:** extend the existing source adapter only when the
incumbent geometry/metric producer can bind a canonical security, episode,
candidate generation, market session, source-bar observation clock, exact
geometry/anchor/first-trigger inputs, and measured adjustment basis to native
receipt material. Carry the inputs through the same-read join and re-attest
their bytes, then let the existing B4 evaluator consume them. Preserve unknown
risk, liquidity, gap and structural facts until their own qualified outputs
exist; a fresh quote does not repair these absences. No substitute ranker,
metric store, guessed fallback ATR, or generic injected gate verdict is needed.

Required discriminating checks for that vertical include mismatched security
or alias reversal, episode/generation/session drift, changed source bytes,
stale/future observation clocks, split/adjustment-basis mismatch, absent
first-trigger/anchor/true-range inputs, invalid geometry, and a valid quote
with any required gate still unknown. Point-in-time episode evaluation,
costs, false exclusions and scientific promotion remain prerequisites for
claims of improved returns or new admission/ranking/sizing authority. The
three reported stocks are incident regressions, not threshold calibration.

### Product proof boundary

The current browser URL policy explicitly denied opening the local `file:`
preview. That denial is preserved; no alternate browser, data URL, local
server, or host route was used to reproduce the blocked action. The browser
completion-summary call itself returned a tool-schema error after the denial.
No screenshot, responsive visual acceptance, keyboard journey, or deployed
reconciliation is claimed. The code/contract/CI lanes continued independently.
The next product-proof step needs an already authorized HTTP(S) preview of
the exact candidate, with the ordinary site access and release controls intact.

## Verified initial findings

1. Screenshot values exactly match `site/factordata/setups.json` at
   `8b78baf69777e3d0d937886789b965617b2ef636`, source date **2026-11-03**:
   TKR alpha 1.83 / setup 2.33; ARCB 1.67 / 1.52; WELL 1.58 / 1.46.
2. The base commit's `site/us_stocks.html` has a **2026-11-04** title yet retains
   those November 3 trigger rows. The publicly retrieved page also showed them.
3. At the same base, November 4 `setups.json` no longer includes TKR, and
   `signal_gate.json` records TKR `eligible=false`, `tier_cascade=null`.
4. `rank_setups(..., rank_by="alpha")` sorts the trigger list by sector-neutral
   residual momentum, not the Prophet evidence-family score or shown readiness.
   Residual momentum uses a 12-minus-1-month window. Its `pullback` label is a
   reversal-percentile overlay, not a verified intact price structure.
5. `signal_gate.gate` permits both held and pending masters to carry T1.
   `buy_signal` drops `tier`, `sub`, reasons and event/observation clocks.
   `_us_setups_rows.html.j2` maps every T1 to green `Buy zone` / `Confirmed`.
6. The existing late rerender refreshes setups inside a condition driven by the
   main board. It retains the old setups on parse failure. The observed snapshot
   mismatch is proven; the exact production run/exception responsible is not yet
   established.

## Bounded task tree — local candidate

- **P1 — forensic attribution** (`complete`): bind the three examples, clocks,
  rank key, signal states and public/generated-page mismatch; separate observed
  facts from hypotheses. Do not infer forecast skill from three selected charts.
- **P2 — source repair** (`complete locally`): retain producer signal
  state/clocks, render pending/unknown/provisional conditions honestly, show the
  panel's actual source date, and refresh changed trigger input independently.
  No numerical eligibility/rank/size/ledger change and no symbol-specific rule.
- **P3 — verification** (`local tests complete; browser proof unavailable`): regress pending T1, missing
  evidence, inactive signals, valid historical triggers, same-date corrections,
  malformed refresh and public/paid rendering; inspect real rendered states.
- **P4 — publication and remaining release evidence** (`EXACT_HUMAN_GATE`):
  publish the exact source on this carrier, consume applicable CI, and record
  separately any remaining release/deployment/live-data requirements.

## Custody and delegation

Read-only screenshot analysis ran in the native child
`/root/chart_failure_analysis`; it performed interpretation, not source writing
or a formal GitHub review. WHY NOT FABLE: this bounded interpretation needs no
scarce principal continuity. Parent retains cross-layer diagnosis and integration
(`PRINCIPAL_JUDGMENT`). Eligible routine leaves use the existing Fabric route;
no duplicate dispatch or denied-effect substitution is authorized.

Open source census found Lane D #7508 on group-context/Board V2 paths and #7384
on sector history, not this row partial. Their holds and carriers are untouched.
No source effect or worker is inherited from those programmes.

## Research boundary and next action

Any new trend/structure risk gate needs point-in-time, episode-level evaluation
across both retained opportunities and rejected failures, with costs and false
exclusions reported. TKR is a regression example, not a threshold-tuning target.
WELL and ARCB screenshots use 3D bars; TKR uses daily bars. Historical Oracle
labels, research labels, Prophet coverage and current entry availability are
different fields and must not be treated as interchangeable.

Next: obtain explicit permission to push the concrete candidate to
`mastermindx-market-intelligence/macro` on this branch and open its reviewable PR.
Do not replay the denied publication through another tool, account, host, or worker.

## Incident assessment

This is a recommendation-contract defect, not evidence that one losing trade
alone invalidates a strategy. The product presented an older, incompletely
qualified trigger as a current buy and put it first using a different quantity
from the one a user reasonably infers from that placement.

### Observable evidence

| Item | Historical list / screenshot | Newer artifact at the source base | Interpretation |
|---|---|---|---|
| TKR | Strength 1.83, readiness 2.33, `UNCONFIRMED TURN`, green `Buy zone`, green `pullback` | Absent from the Nov 4 list; gate says `eligible=false`, cascade null, per-verdict asof Nov 3 | The page retained a superseded candidate. The old compact record does not establish held versus pending confirmation. |
| WELL | Strength 1.58, readiness 1.46; rich source signal says `take` / held confirmation | Still present in the Nov 4 list | A healthier chart and a held signal are distinct from an independently verified current entry. |
| ARCB | Strength 1.67, readiness 1.52; rich source signal says `take` / held confirmation | Still in the list, but marked `event_blackout`; current standouts earnings exclusion includes ARCB | Historical confirmation cannot override the current event gate. The existing earnings filter must see current input. |

The older and newer ranking snapshots each contain 12 names; eight older names
are absent from the newer list. This establishes meaningful membership change,
not that all eight names failed trades or became signal-ineligible. The visible
subtable additionally excludes carded names and earnings-watch names.

The user's TKR image is a daily chart showing a sustained decline before the
latest -6.27% bar, not merely a single unexpected red candle. WELL and ARCB use
3-day bars: WELL shows an established rising structure; ARCB shows a pullback
with an attempted recovery. Those are useful structural distinctions, not proof
of future returns. Do not directly compare the daily and 3-day bar percentages.

The Terminal panels show historical Oracle classifications alongside separate
research and entry-availability fields. All three screenshots say current entry
availability is not yet verified; TKR additionally says Prophet source
unavailable. This audit does not repair Terminal's separate coverage/source join.

### Failure class 1: stale membership under a newer page date

The Nov 4 committed HTML retains the exact Nov 3 trigger values. The raw newer
list has already removed TKR. The initial dashboard render reads the prior list;
the late refresh was coupled to main-board changes and retained prior triggers
on a parse error. Those are reproducible source-level retention paths.

The precise production job/exception that caused this particular stale page is
not established. Do not claim a log-confirmed incident root cause or that one
specific exception definitely occurred.

### Failure class 2: oscillator state becomes a current-buy assertion

T1 includes both a held signal and a pending master. The slim serializer omitted
the distinguishing `tier` and `sub`, and the partial rendered every T1 as
`Buy zone` with a `Confirmed` tooltip. Replaying a pending T1 through the base
serializer and base partial reproduces that incorrect assertion. The candidate
renders the same source as `Unconfirmed — wait`.

This proves a general failure class; it does not prove the original TKR row was
pending. Its old compact payload lacks that evidence. A confirmed oscillator
signal can also subsequently fail, so confirmation alone is not a current-entry
or healthy-price-structure guarantee.

### Failure class 3: older strength is mistaken for current trend quality

The subtable sorts by residual alpha, with factor quality breaking ties. It does
not sort by the displayed readiness score, probability of success, or the
Prophet evidence-family score. Its sector-rank column is a within-sector rank.

The residual score uses older returns: the default construction rolls 252
sessions after shifting by 21 sessions. Recent weakness is a separate reversal
overlay. For a sufficiently positive older alpha, a low recent return percentile
becomes `pullback`; that does not test higher lows, support integrity, or whether
price is still declining. The readiness calculation also gives that category a
positive timing tilt, although readiness is not the ordering key here.

`rank_setups` has an optional multi-timeframe alignment filter, but the US
trigger producer does not pass `align_map`. This is a concrete absence of that
specific structure filter, not evidence that no risk gate exists anywhere in
Prophet. Automatically enabling it here would change the strategy's admission
population and needs prospective, point-in-time validation.

### Failure class 4: presentation blends populations with different evidence

The historical presentation charter explicitly merged the appearance of the
Prophet board and the separate trigger list while preserving their different
data and grading populations. Therefore the nearby 46% win / -0.54% per-trade
display cannot be assumed to describe this exact trigger population. Its
population, horizon, sample count, fees and contemporaneous entry rules must be
verified before using it to judge or calibrate this table.

## Implemented containment

1. Preserve scalar confirmation, reason, event and observation clocks in
   `buy_signal`, without changing gate logic or ranking inputs.
2. Replace the trigger table's current-buy assertions with explicit historical
   signal states. Pending, provisional, unverified, ineligible and event-blocked
   states cannot receive a green buy badge. Held signals say `Signal confirmed`
   and explain that current entry and invalidation remain separate checks.
3. Retitle the panel `Signal watch`, label within-sector rank explicitly, and
   describe recent relative performance as weak/strong/middle instead of
   implying verified pullback/trend integrity.
4. Show the list's own date and each available signal observation date. A list
   date never substitutes for a signal's event or observation clock. Comparing
   list and main-board dates discloses relative age; it does not establish live
   market freshness.
5. Read the trigger snapshot once per rendering pass. Validate the date and
   render-required field contract before either consumer renders. Missing or
   malformed input becomes an explicit unavailable state, distinct from a valid
   empty list; individual names are not silently filtered.
6. Decouple the final rendering decision from main-board refresh success. A
   same-day trigger correction or unreadable trigger source reaches the existing
   shared shell/payload rendering path even when the main-board source is
   missing or malformed. No second publisher, selection engine or retry system
   was introduced.
7. Correct the producer comment that previously implied oscillator eligibility
   guaranteed absence of a downtrend.

This is containment and semantic repair. A future TKR-like pattern may still
qualify for the research watch list. No improved returns, eliminated false
positives, or new validated trading rule are claimed.

## Strategy work required before promoting a stronger gate

Use the existing entry-timing workstream and historical evidence owners. Freeze
the baseline and evaluate candidate rules over all contemporaneous trigger
episodes, not a handpicked set of winners and failures.

- Separate trend-continuation pullbacks from countertrend reversals. Pending
  reversals need their own wait/confirmation treatment and performance bucket.
- Evaluate existing structural/alignment information and canonical current-entry
  availability before considering additional thresholds. Unavailable required
  evidence should stay unknown; it must not become permission to buy.
- Use information known at the actual observation time, including unfinished
  2-day/3-day bars, confirmation availability, earnings calendars and execution
  latency. Do not backdate a trade to an earlier signal event that became
  confirmable only later.
- Compare the baseline against each candidate through chronological out-of-sample
  evaluation, with overlapping episodes handled, costs and next-tradable-price
  assumptions stated, and market/sector regimes separated.
- Report expectancy, adverse excursion, drawdown/tail loss, premature failures,
  coverage, and false exclusions. Include rank-one and top-three outcomes.
  Count good early turns removed by the filter as well as bad entries avoided.
- Keep WELL/ARCB-like retained opportunities and TKR-like rejected failures as
  regression classes. Do not fit a ticker blacklist or an arbitrary moving-average
  rule to these three screenshots.

## Verification and limits

Local verification completed against the candidate, **67 targeted tests passed**:

| Check | Result |
|---|---|
| `python -m pytest tests/test_signal_gate.py -q --tb=short` | 24 passed; existing pandas deprecation warnings |
| Dashboard + gate tests selected by `trigger_snapshot or trigger_rows_do or trigger_only or trigger_pending or trigger_observation` | 31 passed |
| Dashboard + gate compatibility selection: `ts_rows_are_terminal_routable or strip_tables_mobile or no_withheld_panel_row or payload_carries_exactly or candidate_visibility_follows or same_session or archive_recovery_alone or fresh_native_binding_change` | 12 passed |
| `git diff --check` and changed Python compilation | Passed |
| Base/candidate pending-T1 replay through actual serializer and row partial | Base incorrectly says confirmed buy; candidate says unconfirmed/wait |
| Actual Nov 4 `setups.json` through the new loader | All 12 rows accepted unchanged; TKR absent |

The targeted tests use the existing production template environment and shared
row partial. Main-board absence/malformed-input cases execute the actual board
read/recovery block and common render predicate, then the real public/paid split
and rendering helpers. They are not a full nightly build or hosted release test.

The source changes preserve `gate`, `is_buyable`, `engine/setups.py`, and
`engine/residual_alpha.py` logic; AST/byte comparison against the source base
confirmed this. The actual Nov 4 12-row snapshot passes the new boundary
unchanged, with TKR absent.

Production-template fixture renders exercised the three historical examples,
the newer example list with ARCB's existing earnings exclusion, a synthetic
pending signal, unavailable data, and a valid empty list. These are local HTML
renders, not screenshots or production acceptance.

Real-browser proof is unavailable: the local Chromium download returned invalid
archive bytes, and the connected browser could not reach the workspace's
loopback preview. Later browser access reported that the originating browser
context was unavailable. No successful visual, keyboard, responsive or
accessibility interaction pass is claimed. EN/ZH strings and the existing
mobile column contract have automated render/source coverage only.

An unrelated existing test of the committed macro-health projection fails on
the unchanged base `site/macro.html` (`health-unknown` missing). The broader
suite is therefore not claimed green. Full nightly regeneration, hosted CI,
deployed artifact reconciliation and live-browser acceptance remain outstanding.

## Publication effect and continuation

Automatic approval review rejected the attempted GitHub push because it would
publish an internally detailed audit to a remote not established as an explicitly
authorized destination. The compound command did create the local plan commit
`4dc6d19c24fbabb7449be7e81d5df75e795390a5`; the subsequent read-only remote-branch
check returned no branch. No remote PR, source publication, merge or deployment
is claimed. The denial has not been retried through another carrier.

The next human control is permission to publish this exact candidate to the
named repository/branch and open a PR. After authorization, re-read the live
source/holds, preserve this carrier, reconcile any upstream changes, run required
CI, and verify regenerated public/paid artifacts and real browser behavior.
No self-approval, self-merge or release-rule bypass is authorized.

State: `EXACT_HUMAN_GATE` for publication; diagnosis proven and patch locally
verified. Shared canonical persistence of this candidate is not established.
DO_NOT_REDO: the screenshot/source-value match, source pins, identified compact
serializer defect, and confirmed local test results absent material change.
No background worker, watcher, Fabric run or durable execution claim is active.

## Immutable source references

- Historical list: https://github.com/mastermindx-market-intelligence/macro/blob/8b78baf69777e3d0d937886789b965617b2ef636/site/factordata/setups.json
- Newer list: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/site/factordata/setups.json
- Gate artifact: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/site/factordata/signal_gate.json
- Persisted page: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/site/us_stocks.html
- Signal owner: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/engine/signal_gate.py
- Ranking: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/engine/setups.py
- Residual score: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/engine/residual_alpha.py
- Builder: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/scripts/build_stock_library.py
- Refresh path: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/scripts/build_site.py
- Original row partial: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/templates/_us_setups_rows.html.j2
- Population charter: https://github.com/mastermindx-market-intelligence/macro/blob/e39ec45902c1a2bb28507beb851593be6e422167/research/PROPHET_TOPSETUPS_PRESENTATION_MERGE_MASTERPLAN.md
