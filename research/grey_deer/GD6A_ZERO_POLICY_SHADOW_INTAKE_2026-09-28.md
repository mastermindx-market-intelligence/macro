# GD-6A R6: published-result consumer and native CI repair

**PARTIAL / BUILT_NOT_PROVEN. MISSION_COMPLETE:false. PR #8141 stays DRAFT / HOLD-FOR-SOL.**

Same operation `gd6a-us-shadow-intake-20260928-sol-001`, branch
`claude/gd6a-us-shadow-intake-20260928`, resuming R5 head
`352022e60fb24f4e57118bb96ba666df481592a3`. The Chairman's self-audit exception
continues for this software slice; author review is not independent review.

## Actual capability delta

R5 connected the native builder, frozen inputs and publication checkpoint. R6
adds `read_publication_shadow` to the existing producer/qualification module and
connects it to `scripts/prophet_board_acceptance.py::check`. The existing path
remains an **alarm, never a new gate, policy or trading control**. No new API,
publisher, store, registry, calendar, scheduler or lifecycle plane is introduced.

The consumer qualifies the index receipt, raw sidecar digest, immutable board
and risk snapshots, native EOD expiry and full semantic recomposition together.
Counts, source-state summaries, paths, row order and authority cannot be changed
by rehashing a file. Digest-derived paths stay within existing owner roots.
The reader never rereads mutable latest inputs or writes snapshots. Producer and
reader share one native window interpretation, frozen-board resolver and receipt
constructor. The existing pure composer and bound-view function still own the
actual eligibility semantics.

Legacy absence remains legacy absence. A valid UNAVAILABLE/no-file receipt
returns no artifact, never an old apparently healthy sidecar. A WRITTEN result
with unavailable risk still returns every research row marked unavailable. The
alarm distinguishes those honest outcomes from a claimed mismatched artifact;
neither outcome creates a liquidation or overwrites native plan behavior.

## Exact CI findings and repair

Native reads of the new R5 candidate's checks succeeded. This is not a retry of
an older refused request and does not erase that historical action's refusal.
Run `36409269459` at the R5 head above produced:

* `contract-delta`, job `108885608179`: **2 introduced / 0 inherited**.
  `unrun-picks-boards.paths` omitted `engine/prophet_market_eligibility.py` and
  `scripts/build_prophet_market_eligibility.py`, now imported by the builder.
  R6 adds exactly those two paths; every other path, job and command is preserved.
  A fresh hosted differential pass is still required.
* `ci-pack-11`, job `108886573099`: `wri-risk-core` and
  `marketing-social-publisher` failed while installing dependencies. Logs show a
  pandas source build / NumPy-Cython header incompatibility before their tests.
  This is not a passed or failed Prophet assertion. Their commands were not
  changed or bypassed; required CI remains required.

Log SHA256: contract-delta
`0354ea92d22712ef9ef4cd68bd6bca65d7b6453099f29e80a247970a77776570`;
pack 11 `770395c676c01194ec74341c5137c5093f387df9dac5180bb96169ac5f4ccf56`.
A local gh terminal-escape output refusal was corrected using the client's named
capture flag; raw logs were retained and terminal escapes stripped before display.
No platform permission or failing CI gate was bypassed.

## Actual executed proof

The broader R5 baseline passed 189 tests / 58 subtests, including the whole
native bridge test file. R6 adds **23 distinct methods**. The final suite reports
**212 passed / 67 subtests passed**, Python 3.12.13, no failures. It executes
all three GD-6A suites plus `tests/test_prophet_bridge.py` in the existing
isolated native-source dependency fixture. This is not hosted CI or a full
production checkout. Final log SHA256 `5d021a2345dc2e7ae358eb0d509f12ed9985cf47d4d78897aa6d51e03d9b4d98`.

Two deliberate faults produce the intended assertion failures: disconnecting the
reader from the native alarm; removing the full receipt comparison. The latter
fails seven altered-summary subcases. Both originals were restored byte-for-byte.
Fault log digests:
`5244e98cbd2e91139c2b2031e83a0a6a670f78a5e0ebd1cfa35d4d96c22d1cde` and
`2a1237ebb96a63219a789693db1c26102aba7391898bb2c39863679dddd4e2de`.

Previously pinned real board/risk bytes also traverse the actual producer and
new reader: **69/69 rows**, exact order/content, AVAILABLE, zero errors, all eight
action flags false and no reader writes. Observation `2026-09-28T10:42:53.338247+00:00`;
sidecar SHA256 `9412951bfc805c8067a6a670ad5610d1c9ae9d16f5bb25f5d9db7337f4bae894`. The isolated index is assembled
from the native source receipt, not a served production index. Source hashes are
`934f56ac94e057cd5c0f1466d4a24a09382e8e253c2e59f10c9b248bcf7445a8` (board) and
`ae32e124808cf4fb64ef69687b32ad78382a71dd2f9b366eebbc06995ede45ae` (risk),
originally read at `56a4c5b83195e4a11445a481543499e6c63b23a8`.
No outcomes, fit, return improvement or live protection were measured.

## Policy frontier and unchanged boundaries

The inspected existing `config/reflexes.yml`, blob
`e61ea5a06ef1c5acffd3d7180389ee6ef3d50b52`, contains 19 entries. Its shock
rule is explicitly display-only; no active GD-6A new-long rule appears in that
snapshot. Risk Envelope v0 still emits no policies. This is not a claim about
every possible service. Future risk restrictions must be individually registered
under existing Reflex/Chronicle/Evaluation owners and bind scope, version,
evidence, expiry and repair. Seat A RP-R1 remains research/source-limited, not
an adopted calibration. Do not install a policy dictionary or derive order
permission from a red label, FRESH summary or this reader.

AVAILABLE/ELIGIBLE remains NO_MARKET_POLICY_CONSTRAINT_NOT_BUY_PERMISSION.
Core composer, B4, rankers, native plans, holding management and trading are
unchanged. Preserve R5 plan/state/ledger parity and all H1/Cycle/research seats.
No writer custody, production deployment or automatic wake is transferred.

## Material policy-clock binding finding

Seat A's published RP-R1 T3 nomination (parent comment 5863214473) fixes a
16:30 ET decision. The existing `lib.nyse_calendar.expected_last_session`
(blob `0ece6439ffe4b081ee7a268fe99b69e1de1216a3`, verified at the R5 head)
still returns the prior completed session at that time. Four native-function
witnesses on the September 28, 2026 boundary returned September 25 at 20:30Z
and 20:59:59Z, and September 28 at 21:00Z and the next 13:35Z observation.

Thus that proposed decision cannot silently consume the same day's settled
prices through this owner. Resolve it before any empirical run: either bind a
separately qualified earlier source with its genuine usable-time receipt, or
prospectively amend the decision/availability convention with the original study
owner. Do not backdate evidence, weaken the calendar, change the protected H1
study, or call the policy an early warning on the strength of this implementation.
These four source-clock witnesses are not four market trials. No policy timing,
financial threshold or trial registration was changed by R6.

## Exact continuation

Consume required exact-new-head/current-base CI, then release only after the
remaining findings and checks are resolved. Prove ordinary settled build ->
accepted checkpoint -> entitled served index/sidecar -> bound reader and next
refresh; source-fixture evidence is not that event. Only then advance separately
qualified active policy consumption. A compound app/deploy-source read was
refused before dispatch this turn and was not retried or proxied; this unit used
already acquired publisher/alarm sources, not those denied application details.

Protected law loaded at Mastermind
`c719d1ec6dfffa278103134b5d719e1c1e672256`, Skillpack1.0.1/bootstrap1. The six
required procedure blobs were unchanged from their previously read revisions.
No new worker, watcher or independent review was claimed. Existing parent #6817
and PR #8141 cumulative checkpoints retain the effects and release frontier.
