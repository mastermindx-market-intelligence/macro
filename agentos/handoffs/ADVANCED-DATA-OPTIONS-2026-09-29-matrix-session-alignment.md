---
workstream: WS:ADVANCED-DATA-OPTIONS
session: claude/macro-05-matrix-session-publish
model: opus
ended_because: blocked
mission: >-
  MACRO-05 "Empty heatmaps from mixed source sessions". Adopt the existing macro #7861 carrier after
  source/ownership reconciliation rather than starting a duplicate implementation, and own reproduction,
  code, current-tree integration, independent review, normal release, real acceptance, rollback readiness
  and durable closeout. Historical green tests are explicitly not new proof.
state_before: >-
  The repair existed only as uncommitted working-tree files in a separate worktree. Sol had hashed and
  provisionally qualified those bytes but they had never been committed, pushed or published, so no carrier
  held them and no CI had ever seen them. macro #7861 existed as the allocated carrier, DRAFT, under a Sol
  hold that grants no Ready/merge/deploy/source-writer authority. The defect: the matrix producer let OI
  publication date outrun same-root EOD/Greeks, mixing source sessions into one artifact, and an option
  premium close could stand in for underlying spot.
changed:
  - path: engine/options_matrix.py
    what: Producer repair. Bounds candidate source sessions to within _AUTO_SESSION_MAX_LAG=5 NYSE sessions of the latest OI publication via lib.nyse_calendar.sessions_apart; loads per-year Greeks once into selection_greeks_by_year; emits a first-class "session" field alongside the existing _build_meta.asof_date.
  - path: scripts/build_options_matrix.py
    what: Publisher repair. Adds MU/ARM to default roots; _payload_session() normalises the session (prefers "session", falls back to _build_meta.asof_date for pre-repair artifacts); _existing_usable_session() is fail-closed; anti-regression gate withholds a publication whose session precedes the published one; parquet cache cleared in a finally; health OK/DEGRADED/FAILED.
  - path: tests/test_options_matrix.py
    what: 65 tests including the discriminating RED/GREEN for the mixed-session defect and the anti-regression withhold.
  - path: .github/ci/legacy-jobs.yml
    what: Adds the options-matrix-code job at gate:code so this surface is merge-gating rather than data-health only.
  - path: ops/launchd/run_options_matrix.sh
    what: Comment-only. Reframes the SPY OI gate as a conservative readiness FLOOR, not the session selector.
  - path: config/r2_delivery_plane_classification.v1.json
    what: Required companion re-pin; anchor macro:scripts/build_options_matrix.py:55 to :59.
  - path: tests/fixtures/r2_delivery_macro_anchor_lines.v1.tsv
    what: Companion anchor re-pin.
  - path: tests/fixtures/r2_delivery_macro_evidence_files.v1.tsv
    what: Companion evidence re-pin, 242 lines/old sha to 325/d8fee7089.
  - path: agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-09-29-matrix-session-alignment.md
    what: This record.
verified:
  - claim: The repair is a real behavioural fix, not a historical green. A discriminating RED/GREEN exists.
    command: python -m pytest tests/test_options_matrix.py -q  (with the producer reverted for the RED arm)
    result: RED on the unrepaired producer, GREEN on the repaired one; 65 tests pass.
  - claim: _extract_spot never substitutes an option premium for underlying spot, and this commit did not weaken it.
    command: sed -n '1212,1222p' engine/options_matrix.py; git diff origin/main -- engine/options_matrix.py
    result: Unchanged from main. It returns None unless greeks_df carries a finite positive underlying_price; the EOD reader's close column is never a fallback.
  - claim: The 3 failures in test_r2_delivery_plane_classification.py pre-exist this branch and are not caused by it.
    command: git stash-free checkout of pristine ad114ece and of origin/main, then python -m pytest tests/test_r2_delivery_plane_classification.py -q
    result: Identical 3 failures on both. Cause is a stale 567-line pin against a 715-line publish_r2.py, unrelated to this change. Its job is gate:data (tier-gate, legacy-jobs.yml:1990) so it cannot block a merge.
  - claim: That pre-existing red masks the very check that would have validated this PR's own anchor re-pin.
    command: read of tier-gate job scope in .github/ci/legacy-jobs.yml
    result: True. The re-pin was therefore verified by hand against scripts/build_options_matrix.py:59 rather than trusted to a red check.
  - claim: The Terminal consumer reads the SESSION date, not the build timestamp, so the added "session" field is additive and non-breaking.
    command: read-only in charting-app at 81221cb15 — terminal/components/gexdesk/matrixDoc.ts:62,76-77; terminal/lib/gexLadder.ts:56-62; terminal/lib/flowSource.ts:282
    result: matrixDoc.ts types _build_meta?.asof_date as the session source and documents verbatim that the top-level asof is the build timestamp. The repaired producer still emits _build_meta.asof_date at engine/options_matrix.py:1092-1093. No Terminal change is required by this commit. Nothing in that repo was edited.
  - claim: A _null_payload lacks _build_meta entirely, but this cannot reach a consumer.
    command: read of scripts/build_options_matrix.py:239 and engine/options_matrix.py:1177
    result: Null payloads are withheld before any write or upload, ahead of _payload_session. No interaction.
  - claim: The source host runs the UNREPAIRED producer; the repair is not installed anywhere.
    command: fork-free bash-builtin probe over ssh m1 (see danger_areas for why); shasum -a 256 as a single trailing fork
    result: /Users/chriswong/flow-ops-wt/engine/options_matrix.py sha256 11146402f340c559...2883a, 48456 B - byte-identical to origin/main's unrepaired baseline. Marker counts agree - _AUTO_SESSION_MAX_LAG x0, sessions_apart x0. Publisher sha256 a00934e1b2a6424c...5bdd at 10436 B vs main's 056f992dfbb4ccb3...acf44 at 10401 B - a +35 B local divergence matching no committed revision.
  - claim: BLOCKING INSTALL PREREQUISITE - a file-level install of the two repaired files onto the current source host would break the producer at import.
    command: same probe against /Users/chriswong/flow-ops-wt/lib/nyse_calendar.py; grep -n of the import site locally
    result: That module is 10291 B / 229 lines with sessions_apart x0; its def list truncates after session_date, missing the ten functions main adds after it. The repair imports that symbol at MODULE TOP LEVEL (engine/options_matrix.py:56), so the producer would raise ImportError before any code ran - fail closed, not degrade. Any install must also carry lib/nyse_calendar.py or update the whole checkout.
  - claim: A producer is live on the source host, so the packet's never-patch-under-a-running-producer rule is active.
    command: launchctl list; kill -0 97385 (bash builtin)
    result: launchd binds PID 97385 to com.macro.optionsmatrix, last exit 0, and that PID is alive.
  - claim: The matrix publishes to R2, not to the source host filesystem.
    command: grep -n R2_PREFIX scripts/build_options_matrix.py; glob of the host's site/options_structure/
    result: R2_PREFIX = "options_structure/matrix/" at :59. The host's site/options_structure/ holds only examples/ and gex_state/, no matrix/. The outstanding two-session proof must come from R2 or the served endpoint.
  - claim: CI concludes green on the delivered head 46cf6f83096f, and the two earlier cancelled runs were a stale-base infrastructure artifact, not a defect in this change.
    command: gh run list --workflow ci.yml --branch claude/options-matrix-session-repair-20260924; gh run view 36604938778 --log-failed; gh run view 36627834814 --json jobs
    result: >-
      Runs 36601596875 (head a187c5d7a0ab) and 36604938778 (head 2e40c65abc6b) both concluded CANCELLED, never
      failed. The first was superseded 60s after the next push. The second ran 185 minutes and self-cancelled at
      20:31:44Z with ci-gate fail-closed on 267 passed / 46 unknown and ZERO pr_regression units; all 46 unknown
      traced to ci-pack-5, which spent 73 minutes (19:18-20:31Z) repeating "ancestry fetch failed at depth 2048,
      retrying legacy all-branches deepen" and was killed before it could write pack-5.json. Cause was base AGE,
      not content - the branch sat 1043 commits behind main on a base predating the pack fetch repair. After
      merging origin/main (no conflict; only .github/ci/legacy-jobs.yml overlapped and auto-merged; all three
      adopted sha256 byte-identical before and after) run 36627834814 on 46cf6f83096f concluded SUCCESS with
      "complete semantic proof is clear" and "contract-delta clear (result=success)", every job green. fences
      36627834084 and ci-authority 36627830602 also success.
  - claim: The one non-success check on #7861 is fleet-wide and environmental, not this PR's.
    command: gh pr list --state open --limit 12 --json statusCheckRollup filtered to merge-queue-pilot; gh api repos/.../check-runs/109609347031
    result: >-
      ci-authority/codex/merge-queue-pilot is FAILURE on 12 of 12 open PRs across the claude/, sol/ and worktree-
      branch families. Its own payload records allowed=true, reason=same_repo_admin_authority_change and
      admin_verified=true for #7861; the failing part is strictly context_active=false with
      context_reason=inactive_base_context for the codex/merge-queue-pilot base context, which this PR does not
      target. Zero duration, started==completed at 20:39:15Z. Same class as the known-spurious Workers Builds X.
unverified:
  - claim: The repair actually eliminates empty/mixed-session heatmaps in production.
    what_would_verify: A merged release installed on the source host with its lib/nyse_calendar.py dependency carried, then two natural untouched qualifying sessions whose published R2 matrix artifacts each carry a single coherent source session and a non-regressing session date.
  - claim: The repaired producer imports and runs cleanly under the source host's interpreter and .env binding.
    what_would_verify: An import smoke of engine.options_matrix under that host's interpreter AFTER the checkout carries a lib/nyse_calendar.py containing sessions_apart. Measured today it would raise ImportError, so this is currently known-false for the tree as it stands.
  - claim: The anti-regression gate withholds correctly against a real previously-published R2 artifact.
    what_would_verify: Exercised in tests against fixtures only. A live run observing an actual prior R2 publication would close it.
  - claim: The host's mid-July gex_state asof reflects a genuine production staleness rather than stale local copies of a lane that publishes elsewhere.
    what_would_verify: An owner read of where gex_state actually publishes from, and whether the served artifacts carry the same asof.
unresolved:
  - Sol's hold on #7861. The 02:41Z review explicitly grants no Ready/merge/deploy/source-writer authority. Merge authority is not this seat's.
  - Normal merged-source publication, and real published-data-to-Terminal proof over two natural qualifying sessions. Both are downstream of the merge AND of the install prerequisite above.
  - Owner reconciliation of the +35 B publisher divergence on the source host. A rollback preimage cannot be trusted while the installed publisher matches no committed revision.
  - The host's gex_state/*.json carry a mid-July asof. Different producer lane, possibly just stale local copies rather than the live publication. Flagged for an owner read, NOT claimed as a production defect.
next_actions:
  - Await Sol's disposition of the hold on #7861. Do not arm merge-on-green, mark ready, or merge.
  - On release, install must carry lib/nyse_calendar.py (or move the whole checkout to merged main), not just the two repaired files, and must happen with the producer idle and after the publisher divergence is reconciled by its owner.
  - Take the two-session published proof from R2 or the served endpoint, never from the source host disk.
do_not_redo:
  - Do not re-author the repair. The bytes are adopted, committed, pushed and independently reviewed PASS.
  - Do not re-run the m1 preimage probe to answer the same question; hashes, sizes and marker counts are recorded above and on #7861 comment 5895153520.
  - Do not re-investigate the 3 test_r2_delivery_plane_classification.py failures as a regression of this branch; proven pre-existing on both ad114ece and origin/main.
  - Do not "fix" _extract_spot. It is correct and unchanged; the packet's premium-as-spot concern is already handled.
  - Do not edit charting-app from this Macro carrier. The cross-repo check is read-only and already closed - the consumer needs no change.
  - Do not patch, pull, reset or restart anything on the source host. Installation is an owner act.
danger_areas:
  - m1studio is process-starved. Ordinary ssh commands die on a bash fork failure (Resource temporarily unavailable) and sometimes on an sshd exec request failure on channel 0. Only a probe using bash builtins and globbing with NO command substitution, NO pipes, NO subshells and NO external binaries runs to completion. A single trailing fork (shasum) succeeds often enough to be worth placing LAST, after the fork-free output. This is the only method found to observe that host in this state.
  - The source-host checkout is MIXED VINTAGE - producer exactly at main, lib/nyse_calendar.py many revisions behind, publisher locally diverged. Do not assume it is clean at any one commit.
  - A live producer (PID 97385) runs there. Any checkout move while it runs corrupts in-flight state.
  - "#7861 must stay DRAFT with autoMergeRequest null and no merge-on-green label while the Sol hold stands. DEC:SOL-HOLD-IS-A-MERGE-BARRIER binds every merge path including the sweeper."
  - "A ci.yml CANCELLED conclusion here can be an INFRASTRUCTURE verdict, not a red to heal in the diff: a stale base starves a ci-pack ancestry fetch until it is killed, and ci-gate then blocks on unknown units with zero pr_regression. Remedy is a base update, not a rerun. See DSC:STALE-BASE-STARVES-CI-PACK-ANCESTRY-FETCH-INTO-CANCEL."
  - Do not push to #7861 while its ci.yml run is in flight unless the commit is needed; a push supersedes the run. Do not edit the PR body twice inside one ci-authority run's lifetime - the second edit cancels the first.
  - Licensed ThetaData-derived values were read during the host probe. They are retained privately and must not be reproduced in the public PR; publish only sizes, hashes and safe summaries.
prs: [7861]
---

# MACRO-05 — options matrix session alignment (2026-09-29)

The job was custody and publication, not authoring. A correct repair already existed as uncommitted files
that Sol had hashed and provisionally qualified, but nothing held them: no commit, no carrier, no CI. This
session adopted those bytes unmodified onto #7861 so the digest custody chain stayed intact, produced the
discriminating RED/GREEN the packet demanded instead of leaning on historical green, and took an independent
opus review (PASS).

The substantive new finding is the install prerequisite. The repair depends on `sessions_apart`, imported at
module top level, and the source host's `lib/nyse_calendar.py` predates that symbol entirely. The obvious
minimal install — copy the two changed files — would therefore stop the producer with an `ImportError`
rather than degrade it. That was invisible from the repository and only became measurable by probing the
host directly; it is recorded on #7861 as comment 5895153520.

Delivery reached DELIVERED + independent review PASS with CI in flight. It did not reach MERGED,
PRODUCTION_PROOF or ACCEPTANCE, and this record does not claim otherwise. The remaining boundary is external
and in order: Sol's hold, then a release, then an install that carries its dependency, then two natural
qualifying sessions read from R2.
