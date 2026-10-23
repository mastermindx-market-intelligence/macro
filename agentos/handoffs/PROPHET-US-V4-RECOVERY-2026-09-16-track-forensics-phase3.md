---
workstream: WS:PROPHET-US-V4-RECOVERY
session: sol/us-prophet-track-forensics-20260916
model: sol
ended_because: blocked
mission: >
  Explain the US Prophet 50.8-percent historical record, preserve useful early
  discovery, reduce avoidable losses through a coherent entry/risk/management
  contract, and prove economic improvement rather than improve the headline.
state_before: >
  Screenshot and admission joins plus V2/V3 matched-score diagnostics were saved.
  Extreme price paths and a coherent historical price generation remained
  uncertified; no superior strategy or funded-portfolio replay was accepted.
changed:
  - path: research/prophet_v4/forensics/US_TRACK_RECORD_PHASE3_2026-09-16.md
    what: >
      Recorded fixed-generation price reconciliation, a paired protective-stop
      diagnostic, issuer-dependence sensitivity, entry-limit reachability and limits.
  - path: research/prophet_v4/forensics/US_TRACK_RECORD_PHASE3_RESULTS_2026-09-16.json
    what: >
      Preserved machine-readable counts and negative results without granting
      production, trade, statistical or lifecycle authority.
verified:
  - claim: The 843 mature episodes agree with checked original admission fields in the same frozen snapshot generation.
    command: >
      git -C /Users/chriswong/Documents/Cluade/macro-main show
      cf28b6bcb8e77b7143ab618e5780f90221b25001:data/us_board_ledger/snapshots.jsonl;
      compare frozen_admissions against the saved screenshot rows.
    result: >
      38 boards; zero disagreements on rank, spot, entry stop, chase ceiling,
      entry status and stage. Snapshot SHA256
      0b58bb38d292ec34737d2886134b1d32177493912171e35889ee4931c0b5fed4.
  - claim: The strictly reconciled paired stop diagnostic reduces some tail losses but remains negative.
    command: >
      reconcile_episode(row, prices.get(row['t'])) followed by
      protective_stop(row, prices[row['t']]) on status matched;
      summarize_policy for reference_pct and policy_pct.
    result: >
      413 of843 episodes; mean -0.511903 to -0.309956 percent; large losses44 to30;
      same25 large-winner identities preserved;14 eventual reference winners stopped.
      PCG supplies75.2519 percent of net paired improvement.
  - claim: Research checks passed without production-suite or funded-portfolio acceptance.
    command: assert all(test_results.values()), test_results; assert all(invariants.values()), invariants
    result: >
      Seven synthetic stop/cost checks and seven actual-replay invariants passed.
      Capital tests and replay were platform-refused and have no passing result.
  - claim: The phase evidence was saved and the owned analysis process terminated.
    command: >
      Hash and zip the existing phase3 research carrier; Desktop Commander
      interact_with_process89745 exit(); read_process_output89745.
    result: >
      Full local archive1399999bytes SHA256
      287a923df1d0bcc875b4c01cb074acc31afa4ab26626dbe37ce86062b9d147ce;
      process89745 exited0. No worker, Job, Attempt or watcher was dispatched.
unverified:
  - claim: All843 episodes can support a same-basis gap-aware replay.
    what_would_verify: >
      Resolve246 quote-basis/return exceptions and obtain suitable opening-price
      coverage for184 episodes absent from the selected OHLC family, with explicit
      raw/adjusted and corporate-action policy. Never silently rescale or splice.
  - claim: A complete executable and funded entry/risk policy improves outcomes.
    what_would_verify: >
      Permitted execution of the frozen capital design after source reconciliation,
      including limit-entry semantics, same-bar stop ordering, realistic gaps/costs,
      one-position-per-issuer constraints and exposure/drawdown accounting.
  - claim: The archived candidate record is certified forward and the overlay is statistically robust.
    what_would_verify: >
      Decision-time publication and observation evidence, preserved reconstruction
      labels, chronological evaluation, overlap/issuer-aware uncertainty and independent review.
  - claim: This records candidate passes canonical Agent OS validation and is accepted on main.
    what_would_verify: >
      Run python3 scripts/agentos.py validate on the exact candidate tree and
      independently review the evidence; obtain explicit Sol release from HOLD-FOR-SOL.
unresolved:
  - Parent remains PARTIAL; no production strategy change or accepted replacement.
  - Capital-kernel-tests/portfolio run and an additional compound source/composition read were platform-refused; do not route them through another actor or tool.
  - Daily-bar reachability is not a guaranteed order fill; ten cases have same-bar limit/stop ambiguity.
  - Known August14 reconstruction is not a served-before-entry record; other archive rows are not automatically certified-forward.
next_actions:
  - >
      Load the saved phase3 frozen_price_slice.parquet, price_reconciliation.json
      and protocol.md; resolve raw/adjusted quote and stop geometry with the
      existing price owner before expanding the paired population.
  - >
      Recover allowed opening-price coverage, then finish feasible limit-entry and
      the frozen20-slot no-leverage one-position-per-issuer capital comparison only
      after the execution path permits the previously refused operation.
  - >
      Review selection challengers through the existing Conditional Fusion/shadow
      mechanism on matched eligible populations; require independent review and
      real source-to-UI-to-outcome proof before any promotion.
do_not_redo:
  - Do not repeat the843 headline bridge, admission joins, V2/V3 matched-score comparison or phase-two numeric toy checks.
  - Do not reread the67.7MB raw Git price batch; the exact frozen research slice and source manifest are already saved.
  - Do not rerun the primary413-episode stop overlay,14 research checks or entry-reach scan without a material input/method invalidator.
  - Do not change WS ownership/status, mint a second grader/ranker/price store, or treat a priority score as a success probability.
  - Do not promote the stop overlay or close-only filter; negative means and issuer concentration remain load-bearing results.
danger_areas:
  - Primary413 is only49.0percent of the original sample; do not substitute its mean for the843 headline.
  - A valid stop can gap through severely; EIX still loses24.14percent in the gap-aware model.
  - ONTO's distant captured stop does not protect its23.91percent loss; stop existence is not risk suitability.
  - MRNA closed above its chase ceiling but reached its original upper buy limit intraday; closing-price exclusion is not an order replay.
  - TEM entry_stop41.55 and hold invalidation40.30 are different source fields.
  - No hidden provider, capital, publication, independent-review or production proof is granted by this handoff.
---

# Forensic replay continuation

## Mission, authority and scope

Current Chairman continuation authorized this research. Protected procedure remains
Mastermind `4537f066775c73d305f82acf0643701f01f5e53c`; macro record base is
`27ec910d04fc81692cf9640347ac31fd3de40170`. The historical ledger, snapshots and
prices are pinned together at `cf28b6bcb8e77b7143ab618e5780f90221b25001`.

This handoff is organizational continuity, not runtime admission or a worker
assignment. Parent workstream ownership is unchanged. The phase is a bounded
research checkpoint; the capital lane is blocked and production acceptance is
not claimed. No current session is being replaced or claimed by this packet.

## User journey and data behavior

Preserve broad discovery while making current entry permission, interval, expiry,
feasible fill, execution stop and portfolio/event risk explicit. Outcomes must
measure the same contract the user followed. Keep rejected/unfilled candidates
for missed-winner analysis. Unknown evidence remains unknown; publication,
observation, corporate-action and correction vintages stay distinct.

## Exact recovery artifacts

Local evidence root on Mac-Studio:
`/Volumes/Mastermind/Mastermind/research/us-prophet-track-audit-20260916/phase3/`.

Start with `CONTINUATION.md`, `protocol.md`, `paired_policy_summary.json`,
`event_dependence_results.json` and the exact next inputs. Source-level detail,
all843 reconciliation rows,413 paired rows, source hashes and frozen price slice
are already present. The sibling full archive is
`US_Prophet_Phase3_Research_20260916.zip`, SHA256
`287a923df1d0bcc875b4c01cb074acc31afa4ab26626dbe37ce86062b9d147ce`.

The research report and machine results in `research/prophet_v4/forensics/` contain
the reproducible method, precise source identities, outcome tables and limits.
There is no reason to recover the old chat or full tool transcript.

## Method, failures and implementation order

Read-only Git objects supplied one historical generation. Strict price checks
admitted413 pairs;246 exceptions and184 missing-family episodes remain explicit.
The original recorded stop was evaluated after the close-fill, using gap-open
execution rather than an idealized trigger-price fill. This is a protection
comparison against retained incumbent exits, not an alternate execution engine.

First resolve source/basis coverage. Next settle actual limit-entry and stop
ordering, then the blocked capital/exposure test through a permitted path. Only
then evaluate selection changes and production integration through existing
V4/Conditional Fusion owners. The previously discovered numeric correctness
repairs remain distinct and do not magically explain the realized hit-rate denominator.

## Acceptance and stop boundary

HOLD-FOR-SOL. Do not arm, auto-merge, merge or treat this records candidate as
strategy acceptance. Release condition: exact evidence review plus canonical
Agent OS validation, with the statistical/portfolio/production holds preserved.
No reciprocal worker dialogue exists for this research; no watcher shutdown or
ACK/START is owed. Owned process89745 is terminal with exit0.

The next major phase requires additional source-owner and permitted-execution
work. Resume from this reference, not by repeating the completed diagnostics.
