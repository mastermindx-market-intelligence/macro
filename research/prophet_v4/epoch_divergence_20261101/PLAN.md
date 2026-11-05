# Prophet board / index epoch divergence fix

Operation: `prophet-a2-board-index-epoch-divergence-20261101-sol01`.
Receiver: current Chairman-assigned Pro fix owner (ChatGPT4 / Sol).
Procedure: Mastermind protected master `19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec`,
skillpack `mastermind.sol_skillpack.v1`, version 1.0.1, bootstrap major 1.
Pickup source: Macro main `9fe98ab14db8ccc1bb35d9dd8b1d11617527dfdf`.
Related existing workstreams: WS:PROPHET-US-V4-RECOVERY and
WS:PROPHET-US-AVAILABILITY. This is one bounded repair, not a new program.

## Authority and completion boundary

Chris assigned this operation end to end on November 1, 2026. DONE_WHEN:
a bounded fix PR is open against macro/main, required CI is green, and an
independent non-author Fabric review is complete with its verdict posted on the PR.
Same-session changed-membership regression, actual candidate reader/browser proof,
and an explicit no-false-SETTLED attestation are required.

No merge, auto-merge, deployment, credential/security change, private raw-data
disclosure, or trade signal. Do not modify PRs #10202, #10209, #10289 or their
branches; do not contact/modify the Y7 6ae60699 and ModernLuxe 6ae6540c chats.
#10202 remains Draft with no rerun before the original #9596 fix reaches main;
#9596 was observed Draft/unmerged at `1d6d5468eeb81311cf08189ac02b1f21a32370a3`.
#10209 remains Draft. #10289 retains its separate repair.
Keep this PR Draft and unarmed under the Chairman's explicit no-merge instruction.

## E1 — Census (complete before source edits)

The captured census examined 881 open PRs and their changed files. 139 matched
Prophet or the requested builder/workflow paths. All 33 transient file-list read
failures were resolved through exact GitHub reads; no unresolved coverage gaps.
Full diagnostic census SHA-256:
`b1d6ab1d2b26573496111e1b4e11983de4cffd6dd5733b8959b09144cc3f7c8d`.
A compact source-bound overlap census accompanies this plan.

The evidence comment was read:
https://github.com/mastermindx-market-intelligence/macro/pull/10174#issuecomment-6567098234

Current pickup-tree reproduction:
- index: 11,846,549 bytes; asof 2026-11-01; source_asof 2026-10-30;
  source_board_sha256 `f4e834dc62541c21e2a9b6d5525662aabd28e6c1af12d71fe03e70fb0d046dc9`.
- Its existing gzip snapshot decompresses to 2,636,414 bytes and that exact hash.
- Current board: 2,627,139 bytes; SHA-256
  `2de0cfff3d10218163bd67465e9e7e8a7ab5d5817ec7628d62b9581d2cb5db2d`.
- Same source session, 95 members each, 94 common members; this is actual
  membership change, not just formatting. Sunday does not make Friday stale.
- No computed_at was fabricated and no committed-tree observation is described
  as served-production proof.

Recent observed main CI: ci.yml 41363446158 SUCCESS at 2f6d6734;
daily.yml 41373916776 SUCCESS; daily 41378879186 was running;
render 41373697116 pending and engine-render 41373876150 queued.
No run was cancelled, rerun, or dispatched by this census.

Shared-file overlaps include #9495 (Prophet presentation), #8444 (Plan relations),
#9369 (Today provenance), #10381/#10489 (unrelated build_site sections),
#10432/#10363 (daily), #9995 (render), and the held A2 family.
Changes use new isolated files and narrow existing reader hooks, never another
live owner's branch. Main movement requires only an affected-path reconciliation.

## E2 — Design and implementation

Decision: intentional dual epochs, with a fail-closed reader identity projection.
The current board may refresh independently. Existing plans retain their exact
immutable origination source. A current board is not silently promoted to the
source of the existing index.

Code basis: build_prophet.py::_freeze_origination_source_board explicitly declares
us_standouts.json a live artifact with several lawful render publishers and binds
the index to a content-addressed immutable gzip copy. build_site.py documents that
build_site precedes build_prophet and express render never runs build_prophet.
Both render.yml and engine-render.yml stage site/ after build_site regenerates the
board; daily checkpoints the index separately and later mirrors it to R2.

Rejected alternative: running origination again in every site render would move
plan lifecycle/ledger authority into an express presentation lane and change
frozen provenance. No second publisher or new bundle-ID issuer is needed.

Bounded implementation surfaces:
- new deterministic `engine/prophet_source_epochs.py`;
- narrow capture/integration in `scripts/build_site.py`;
- an existing-dashboard disclosure through a new template partial;
- focused Python/browser tests and their existing CI registration;
- this plan, evidence and one scoped Agent OS decision/handoff if required.
Do not change build_prophet, build_stock_library, daily, render or engine-render
production behavior.

Projection contract: consume captured exact board/index bytes and verified frozen
snapshot bytes; distinguish SAME_SOURCE, SEPARATE_EPOCHS and UNAVAILABLE.
Dates alone never establish identity. Only fixed allowlisted hashes/dates/status
may leave the reader; no plans, tickers, scores, prices or raw snapshot content.
The projection never emits SETTLED: two-source identity is not A2's exact
four-family source-published/read agreement. Mixed/missing/malformed bytes remain
PENDING, and no accepted bundle ID is created. The ordinary producer remains sole
authority to publish accepted identities.

Read the index once and bind its displayed document and raw hash to those same
bytes. Recompute the current-board relation from the post-library raw bytes during
the existing fresh-board re-render, without reopening or rebinding the index.
Validate the canonical snapshot link/encoding and exact raw digest; fail closed
when unavailable. Never mutate the source documents, index or snapshot.

## E3 — Discriminating proof

- Freeze synthetic board A; create index I bound to A.
- Re-render board B with the SAME market date and one changed member.
- Assert I and A remain byte-identical, current board digest changes, reader
  exposes SEPARATE_EPOCHS and PENDING, and no false SETTLED is emitted.
- Also cover exact-byte equality, formatting-only byte differences, missing or
  invalid metadata, incorrect snapshot path/encoding/hash, corrupt/missing gzip,
  and first/fresh reader consistency.
- Exercise the real dashboard reader integration with synthetic data, not only
  a standalone helper. Candidate browser proof uses the actual template path,
  desktop/mobile, dark/light, EN/ZH, accessible disclosure and no overflow.
- Preserve tier gates and source-only metadata allowlists. Candidate proof is
  explicitly not deployment or served-production proof.

## E4 — Review and PR completion

Economical admitted Fabric labor; root owns architectural judgment and integration.
WHY NOT FABLE: bounded source projection and adversarial review have frozen inputs
and deterministic acceptance criteria; no frontier delegation is needed.
Independent reviewer must not author implementation. Bind review to exact PR head,
source base, diff, tests, browser evidence and all forbidden effects.
Post the actual independent verdict with run/reviewer provenance; do not self-approve.

Tasks: E1 complete; E2 implemented and pre-audit adjudicated; E3 selected local
checks green (545 passed, 2 skipped, 5 deselected) and final browser 8-cell /
5-refusal matrix passed against implementation 409c08d0d5df78ffb068db20eb9ded9976c0c4aa; E4 PR/CI and
final independent non-author review pending. These are editorial task labels,
not Runtime Job states.

Current main was reconciled at b394a98baf2d4a695fb05a276d72dd739fd7eb72.
Among the specified source surfaces only .github/ci/legacy-jobs.yml changed,
through unrelated additions outside the modified board-test step. The reader,
template and producer source used for the design remain unchanged.

## Recoverable frontier

Initial plan/census published at 6343a18748e4ce2bed5a34b2e015acdb39a5d7a7 and
read back through GitHub. The installed typed Studio Git wrapper was unsupported
for Macro: its legacy Mastermind-only workspace lookup failed before any effect.
Exact repository-qualified workspace status succeeded. Ordinary Git in the same
acquired Macro workspace committed/pushed successfully, preserving hooks and
configuration; no gateway/security settings changed.

Original Fabric requests completed and were accepted after parent verification:
- helper: prophet-epoch-helper-20261102-01, controller PID 96833;
- audit: prophet-epoch-audit-20261102-01, controller PID 98322.

Both terminal results have verified root linkage. No retry, alternate carrier,
cancellation or duplicate labor occurred. Their exact response digests and the
adopted/declined audit findings are in FABRIC_ADJUDICATION.md.

The implementation captures first/fresh reader identity, fences the existing
paid payload, and discloses the index used by this page. The immutable pickup-tree
projector proof is SEPARATE_EPOCHS/PENDING with a verified frozen source. Focused
regressions, existing consumer checks and preliminary actual browser proof pass;
see VERIFICATION.md for commands and honest exclusions. Agent OS validates with
zero errors (unrelated existing warnings).

Next: commit the candidate, record the browser matrix against that immutable
source, open the held PR, and finish green CI plus the exact-head independent
non-author review. No deployment or served-production acceptance is claimed.

Milestones stay in Slack C0CBC6AEAQZ thread 1793583933.705299, mentioning
<@U0BTCHX8HMF>; never DM. GitHub remains implementation/evidence authority.
