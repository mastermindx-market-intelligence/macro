# Preserve older Door sightings in the existing B1 intake

Capability: an older persisted research sighting must not vanish from reconciliation merely because a newer source date exists. This is source-intake repair, not a new detector, episode lifecycle, ranking rule, entry rule or historical trade.

Parent: `WS:PROPHET-US-V4-RECOVERY`. Chairman directs this session as main CEO of US/China Prophet recovery without Slack. Operation: `prophet-door-intake-retention-20260922-sol-001`. Procedure: `Mastermind@ce18ed4f1eaa28e65a616a90aecca5c5ce1c5a2e`, Skillpack1.0.1/bootstrap1. Base: `macro@758b052ff0278e9842fd1b392e0b04617124d1bb`.

## Custody and accepted prerequisite

B1 chronology #7477 was independently approved at `cfcd27e7e57942c17a5e33e7c2021a14291d8a0a`, with concluded hosted checks green. Current-base integration tree `a2cf5f596d9f12fc88b86a3433401c9d83b3112e` passed 124 B1 tests. Sol lifted its source-review/CI hold in comment `5770525727`, performed one normal expected-head squash merge, and read back merge `758b052ff0278e9842fd1b392e0b04617124d1bb`. That is source acceptance, not production behavior or historical replay.

This leaf does not replace #7572, which remains at `44ee80f30878d5709a24afb9f21866644ac22960`. The original #7227 worktree has uncommitted calendar-repair changes, including the intake module. Those files are untouched. This leaf changes only the existing reconciler and its already-registered tests, reusing the original normalizer. The 422-open-PR census plus immutable local-Git checks of six saturated file lists found no remaining overlap on these two paths after #7477 merged. This is path evidence, not an official source-continuity receipt.

## Before and after

Before: the Door adapter selects only the maximum date in its persistent ledger. Missed older identities are not automatically reconsidered.

After on candidate: the reconciler reads one bounded source snapshot, validates schema/session/source identity and payload fingerprints, and submits all completed unique Door rows to the existing core. New observations become known at the current ingestion time. Existing events retain their original knowledge time; suppressions remain immutable and are not reopened. Identical duplicates collapse; conflicting evidence refuses before publication.

Data OS identity, raw-row hashes, event identities, structural anchors, generation/HEAD publication, report/replay modes and nightly-only permission remain controlling. No new store, cursor, schema or retry loop. Candidate archive and TURN WATCH selection policies are not changed.

## Clock and failure behavior

Require a real NYSE session, including holidays and early closes. Future sessions or explicit future timestamps wait before identity normalization; early arrival must not irreversibly suppress a future record for missing identity. Invalid explicit clocks refuse, including booleans, numbers and timezone-free instants.

Preserve source dates and hashes. Late observations are known now, never retroactively. The existing suppression schema retains its own observation-session convention; the source ID preserves the original source date. Unanchored Doors follow the incumbent active-episode attachment rule or explicit suppression: no fabricated anchor, re-arm or historical-entry claim.

Read at most 8 MiB and 25,000 rows; exceeding either refuses without partial publication. Existing source files, events, suppressions and generations remain unchanged.

## Verification and limits

TDD commit `3aed2282ce92` reproduced 16 failures with one pre-existing conflict control passing. The first working 17-case suite passed. Further legacy-known-time, one-read and invalid/future-clock cases were added to the existing suite. The complete final B1 owner battery passed **148 tests, zero failures/skips**; see `owner-tests.txt`.

A real-input nonwriting probe read the pinned Door ledger, the exact HEAD-backed episode generation and the existing identity spine. Old intake returned six newest-date rows; the candidate accounted for 167 completed unique records, of which 21 already had owners. It computed 146 newly accounted records: 115 observations and 31 suppressions (20 unresolved identities, 11 missing anchors). Old source/history bytes remained unchanged, and repeat computation added zero events. Intel/Micron September 10 and AMD September 18 sightings attached with the probe's current ingestion time. No Arm sighting was fabricated.

That probe preceded final explicit-clock hardening. Its attempted final repeat was platform-blocked; it is not relabeled as exact-final-source or production proof. Final hermetic tests cover the added boundary. Current exact-source full-writer/nonwriting qualification remains owed; the probe did not rebuild TURN WATCH/candidate inputs or write canonical ledgers.

## Release and continuation

`BUILT_NOT_PROVEN / HOLD-FOR-SOL`. Independent exact-head review, complete hosted CI/current-base proof and source-bound nonwriting full-writer acceptance precede source release. Natural production consumption is separate. No nightly dispatch, immutable-conflict erasure, registry change, rank/entry/size/order change, provider request, worker or watcher occurred. #7227, #7180 and #6992 retain their own gates.

Primary next action: qualify and release this retention leaf through B1, then evaluate context-conditioned continuation entries under the existing strategy/promotion owner. Saved research is not Buy Now. `MISSION_COMPLETE: false`.


## September 22 exact-source continuation

Semantic source `d2ec700e98b584e25db695711db8f1655f2e9c6f` fixes an independently
reproduced future-clock leak: the incumbent normalizer emits whole seconds, so
using its normalized value for admission could consume a fractional-second
future observation early. The intake now compares the original precise instant
while retaining date-only exchange-close resolution and unchanged source
normalization/identity semantics. Seven new RED cases now pass. Final four-suite
owner battery: **155 passed, zero failures/skips**.

The bounded proof runner now records its implementation hashes and can exercise
all pinned sources through the real `reconcile(... nightly=False, replay=False)`
path. On data source `1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee`, the complete writer
REFUSED `ordinary source key reused with different committed bytes`. The harness
reported 2,312 source-receipt conflicts; its successful process exit records the
refusal, not writer acceptance. Source/history preservation assertions passed.
A subsequent diagnostic extraction of the detailed report was platform-blocked
and was not rerouted. No per-source attribution or new cohort counts are claimed
from that unread diagnostic. See `final-writer-status.json`.

Complementary staged TURN WATCH #7227 is now at
`1f7aa1bb4e067a9a6fecd783857f984a8b6a2e87`, with its requested calendar repair and
concluded hosted CI. Its own current return independently identifies a changing
v1 document receipt as a full-writer blocker. This candidate and #7227 compose
without conflicts on the source above: tree
`426d996b454c18f5b7d4617784d41a7ebdf0178f`. Five combined B1/TURN WATCH suites:
**256 passed, no failures/skips**. This is compatibility evidence, not v2 activation,
independent GitHub approval, or natural production proof. Neither source branch
was replaced or rewritten. Both remain governed by their original release holds.

Primary next action: independent exact-head reviews, then the accepted TURN WATCH
new-session protocol/registry transition and a nonwriting full-pipeline PASS before
any natural-run retention activation. Do not weaken the immutable conflict check,
rewrite old v1 events, replay the cancelled nightly, or claim a retained observation
as a buy. The raw current-archive publication issue remains with #7180.
