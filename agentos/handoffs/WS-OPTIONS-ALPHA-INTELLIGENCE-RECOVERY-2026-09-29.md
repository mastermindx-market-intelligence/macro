---
workstream: "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
session: "claude/macro-03-options-ledger-durability (worktree macro-03-ledger-durability-5abee7)"
model: opus
ended_because: complete
mission: >
  MACRO-03 commission: let the canonical nightly publish newly matured session
  outcomes while retaining every logical row, byte-prefix identity and consumer
  contract. Adopt the existing #7265 carrier after source/ownership
  reconciliation rather than starting a duplicate implementation, and own it
  through reproduction, current-tree integration, independent review, release
  and durable closeout.
state_before: >
  #7265 carried a complete bounded-parts implementation (immutable frozen base
  plus contiguous 48 MiB part-NNNNNN.jsonl files read as one logical ledger),
  independently APPROVED by mastermidx4 on 2026-09-20 at head e562578d, but sat
  unmerged behind a stale CHANGES_REQUESTED from undismissed 09-17/09-18 reviews
  and behind a reported "concrete source-integrity blocker" — a campaign run
  failing with `CampaignContractError: ledger prefix changed` on
  data/options_signal_episode/outcomes_session.jsonl. Its own size-boundary test
  matrix ran entirely under a monkeypatched toy ceiling, so nothing exercised
  the real 48 MiB constant that broke publication.
changed:
  - path: tests/test_options_signal_episode.py
    what: >
      +247 additive lines closing the real-ceiling gap: real committed 95.82 MiB
      base rolling over at the true 48 MiB ceiling with the historical prefix
      frozen byte-for-byte and global 1-based ordinals continuing; inclusive
      bound with rollover only on overflow; interrupted publication leaving a
      valid strict prefix plus replay-safe re-entry; and four broken part
      topologies (numbering gap, unexpected filename, directory alias, part
      symlink). The two real-byte cases are marked needs_full_checkout("data").
      No engine or publisher byte changed.
  - path: agentos/discoveries/DSC-OPTIONS-SESSION-LEDGER-PREFIX-FAILURE-IS-A-CONTAMINATED-CHECKPOINT.md
    what: >
      New landmine record: the `ledger prefix changed` failure is a contaminated
      campaign checkpoint, not source corruption, and must not be used to hold
      the durability carrier or to justify reissuing receipts.
verified:
  - claim: >
      The adopted engine/publisher bytes are identical to the independently
      approved head e562578dc0097b5281bf73422e044e43f70a9777, so that approval's
      semantic coverage still holds on the integrated tree.
    command: >
      for f in engine/options_signal_episode.py engine/options_signal_episode_contract.py
      engine/options_signal_campaign.py scripts/ci/options_signal_nightly.sh
      scripts/build_options_signal_episode.py tests/test_options_signal_campaign.py; do
      test "$(git rev-parse HEAD:$f)" = "$(git rev-parse e562578d:$f)"; done
    result: >
      All SIX enumerated carrier blobs IDENTICAL. The seventh file on the PR
      surface, tests/test_options_signal_episode.py, differs BY DESIGN
      (593d658494aa -> the session head) and is the only session work; an
      earlier draft of this row said "all seven", which overstated a check
      whose own command lists six paths. Independently corroborated: git diff
      --name-only e562578d d99070a2 -- 'engine/options_signal*'
      'scripts/ci/options_signal*' 'tests/test_options_signal_campaign.py' is
      EMPTY, so the carrier re-adopted no changed engine or publisher byte.
  - claim: >
      The real consumer path -- options_signal_campaign.load_ledger over the
      logical ledger -- survives a genuine rollover of the real 100,471,221-byte
      base with its historical prefix receipt UNCHANGED, which is the exact
      equality whose failure raises CampaignContractError: ledger prefix changed.
    command: >
      A standalone harness on a temp copy of the real base (COLLECT_LANE=nightly,
      data/ never written): load_ledger before, append_session_outcomes, load_ledger
      after, then compare _receipt(after, before.count) to the before receipt.
    result: >
      ALL PASS, 10/10 properties. 30,327 -> 30,332 rows; base byte-identical after
      the append and after a re-entry; only part-000001.jsonl created and within
      the ceiling; logical bytes == frozen base + part; historical prefix receipt
      and prefix rows unchanged; global 1-based ordinals continue 30328..30332 via
      LedgerRow.ordinal; a re-append writes 0 rows (dedupe spans base AND parts).
      The ordinal check matters because the size-boundary tests prove continuity
      only as list order and never read LedgerRow.ordinal -- this closes that gap.
  - claim: >
      Independent adversarial review found no input, crash point or interleaving
      that loses, reorders, truncates or rewrites a committed row, and judged all
      four size-boundary tests discriminating rather than vacuous.
    command: >
      Read-only opus reviewer over the integrated tree; attacks attempted:
      append-after-rollover to the frozen base, later-part-before-earlier-part,
      lost directory entry, duplicate rows after rollover, planted part topology,
      ceiling off-by-one, stale-candidate truncation of a published part via the
      publisher replay, and working-tree clobber by exclude_broad.
    result: >
      MERGE_WITH_FOLLOWUP; every attack blocked, with the mechanism named for each.
      Three claim overstatements were upheld and are corrected here and on the PR:
      (a) the row above, (b) the commit message's bullet 2 -- the INCLUSIVITY case
      runs under a monkeypatched constant within ~5 KB of 48 MiB, not under the
      real one, so only the under-ceiling step uses the true constant (the commit
      is pushed and no force-push is authorized, so this correction lives here and
      on the PR rather than in rewritten history), and (c) the writer's own in-code
      comment claiming a crash "can never expose a torn row", which is false
      because neither lock_fh.write nor part_fh.write is atomic across pages. (c)
      is in the incumbent owner's engine file and was NOT edited; instead
      test_session_outcome_reader_fails_closed_on_a_torn_or_empty_part now pins the
      consequence that actually governs durability -- the reader refuses the whole
      logical ledger rather than reporting a short row count, so a torn tail can
      never read as the end of history. Mutation-proved: dropping the torn-line
      raise fails exactly the 2 torn params, dropping the empty-part raise fails
      exactly the 1 empty param.
  - claim: >
      No append-only violation exists anywhere in the ledger history; every
      historical version of all three source files is an exact byte-prefix of
      main's current file.
    command: >
      git rev-list origin/main -- data/options_signal_episode/outcomes_session.jsonl
      (and outcomes_h60.jsonl, episodes.jsonl), then for each distinct blob compare
      it byte-for-byte against the same-length prefix of main's current file.
    result: >
      Zero violations across 11 versions of outcomes_session.jsonl, 10 of
      outcomes_h60.jsonl and 10 of episodes.jsonl.
  - claim: >
      The campaign checkpoint at main pins source receipts at row counts main's
      ledgers never passed through, and outcomes_h60.jsonl is contaminated too.
    command: >
      Read data/options_signal_campaign/checkpoint.json source receipts, then for
      each recorded {records, prefix_sha256} search every published row count of
      the corresponding ledger in main's history for a matching prefix digest.
    result: >
      episodes 8,872/577173f2 MATCHES; session 23,771/6b95148d matches at NO
      count (main went 20,364 -> 27,770); h60 6,525/129b56d4 matches at NO count
      (main went 5,709 -> 7,122). Checkpoint ocp_e3255025e9e8d98b72c3e9ec,
      published by broad sweep 55d267539a7a2e "data: asia collection 2026-09-03".
  - claim: >
      The failure is pre-existing and carrier-independent — unmodified
      origin/main reproduces the identical error on the same real data.
    command: >
      Check out origin/main (1df73c1ac9289a21e192aeb50088a4f9119aee82) engine and
      run the stored-data campaign dry run against the committed data/ trees.
    result: >
      exit 1, identical `CampaignContractError: ledger prefix changed:
      data/options_signal_episode/outcomes_session.jsonl`, 683.92s user /
      18:15.82 wall. The carrier does the same work in 46.5s.
  - claim: The full owning episode and campaign suites pass on the integrated tree.
    command: >
      python3 -m pytest -q tests/test_options_signal_episode.py
      tests/test_options_signal_campaign.py
    result: >
      263 passed, 1 failed in 500.26s. The single failure,
      test_locked_broad_snapshot_blocks_late_index_writer, is a pre-existing
      flake: it exists unchanged on origin/main, is absent from both this diff
      and the carrier's diff, exercises oip_commit_locked_roots which the carrier
      does not modify, passes in isolation (3.83s), and passed again at the same
      ordinal position on a re-run with this change's 7 tests deselected. No
      pytest-randomly or xdist is installed, so ordering is deterministic and
      these additions run after it.
  - claim: No data/ artifact was mutated by any verification run.
    command: >
      git hash-object on each participating data file compared with
      git rev-parse origin/main:<path>, before and after every run.
    result: >
      outcomes_session.jsonl, outcomes_h60.jsonl, episodes.jsonl and
      options_signal_campaign/checkpoint.json all IDENTICAL to their
      origin/main blobs.
  - claim: >
      The committed base's true size relative to the part ceiling and the real
      row-size spread, both of which the monkeypatched matrix could not see.
    command: >
      wc -c data/options_signal_episode/outcomes_session.jsonl; then a python
      pass measuring per-line lengths over the whole file.
    result: >
      100,471,221 bytes = 95.82 MiB = 1.996x the 48 MiB (50,331,648 B) ceiling
      and 95.8% of GitHub's 100 MiB blob limit. 30,327 rows, min 1,445 B, max
      5,239 B — a 3.63x spread.
unverified:
  - claim: >
      The nightly publishes new canonical outcomes durably through the one
      logical ledger with the historical prefix unchanged, on two natural append
      observations.
    what_would_verify: >
      Two nightly runs after merge whose `engine` JOB concluded success --
      NOT two runs whose run-level conclusion is success: daily.yml is
      DST-paired and the wrong-DST run reports run-level SUCCESS with every job
      skipped (DSC:NIGHTLY-ARTIFACT-ATTRIBUTION-NEEDS-THE-ENGINE-JOB) --
      showing outcomes_session.jsonl byte-unchanged,
      outcomes_session_parts/part-*.jsonl extending contiguously, and the
      campaign consuming them as one logical ledger without a prefix error.
      This is a scheduled event; it cannot be replayed or fabricated
      in-session. Measured at closeout: ZERO such observations exist yet; see
      the acceptance section for the two post-merge runs and why neither
      counts.
  - claim: >
      The mechanism behind the locked-index flake — whether a real TOCTOU window
      exists in oip_commit_locked_roots or only in its test harness.
    what_would_verify: >
      Looping that single test under load to obtain a reproduction, then tracing
      which call reverts config/foreign.txt in the worktree (the only reverting
      call on that path is the `git checkout HEAD -- "$root"` cleanup loop).
      Owned by the shared-publisher recovery lane, not by this carrier.
unresolved:
  - >
      Production acceptance. Source merge alone is not Options Alpha acceptance
      and authorizes no training or scoring.
  - >
      The contaminated campaign checkpoint ocp_e3255025e9e8d98b72c3e9ec and the
      campaign-outcome suffix built against that foreign generation. Belongs to
      the incumbent campaign owner per commission §7 and this workstream's
      "preserve the existing recovery owners".
  - >
      main's own ci.yml was red on ci-pack-11 -> ci-gate on 2026-09-29 (runs
      36596076962, 36572059667), so PR checks on this branch may inherit it.
next_actions:
  - >
      After merge, confirm on two consecutive nightly runs that
      data/options_signal_episode/outcomes_session.jsonl is byte-unchanged and
      that outcomes_session_parts/part-*.jsonl extend contiguously from
      part-000001 with no prefix error from the campaign reader.
  - >
      Hand the locked-index flake to the shared-publisher recovery lane (#7263)
      with the reproduction data recorded above; do not patch
      scripts/ci/options_signal_nightly.sh from this carrier.
  - >
      Schedule the two owner-bound performance/serialization follow-ups below
      once the reused approval no longer has to be preserved.
do_not_redo:
  - >
      Do NOT re-audit the historical ledger prefixes for append-only violations.
      Done over the full history of all three files; the result is zero
      violations and the falsifier recipe is in
      DSC:OPTIONS-SESSION-LEDGER-PREFIX-FAILURE-IS-A-CONTAMINATED-CHECKPOINT.
  - >
      Do NOT re-diagnose `ledger prefix changed` as source corruption, and do
      NOT hold the durability carrier on it. It reproduces identically on
      unmodified origin/main.
  - >
      Do NOT reimplement bounded session-outcome parts. #7265's engine work is
      adopted verbatim and independently approved; only its test matrix was
      incomplete.
  - >
      Do NOT reissue historical receipts, regenerate old hashes, rewrite,
      compact or rewind the ledger, or delete parts. Forbidden by the
      commission's rollback clause.
  - >
      Do NOT treat the pre-existing locked-index test failure as a regression of
      this work; it is a flake on untouched main code.
danger_areas:
  - >
      Once parts exist, rollback must retain a parts-capable reader or stop the
      writer through its existing operator mechanism. NEVER install a legacy
      reader that silently ignores committed parts, and never delete parts,
      compact history or rewind the ledger as rollback.
  - >
      The committed base is 100,471,221 bytes = 95.82 MiB: 1.996x the 48 MiB
      part ceiling and 95.8% of GitHub's 100 MiB blob hard limit (it already
      exceeds 100 MB decimal, which is why some reports call it "over 100 MB").
      Never push an intentionally oversized blob to production as a test.
  - >
      Real session rows vary 3.63x in size (30,327 rows, 1,445 B to 5,239 B).
      Size-boundary tests that assume uniform rows silently mis-plan which part
      a row lands in; that defect appeared in the first draft of the
      interruption test here.
  - >
      data/ is omitted in a sparse worktree and an unredirected writer TRUNCATES
      the committed artifact. Real-byte tests carry
      needs_full_checkout("data"); opt in with
      `python3 scripts/worktree_sparse.py add data`.
  - >
      Every pre-existing size case monkeypatched SESSION_OUTCOME_PART_MAX_BYTES
      down to a toy value, so a green size suite there proves nothing about the
      real ceiling. Keep at least one real-byte case in the matrix.
  - >
      append_session_outcomes jsonschema-re-validates every existing row on each
      append (~33s at 30,327 rows, linear growth) and its duplicate scan
      re-resolves the path via load_session_outcomes rather than reading through
      the locked descriptor. Both are pre-existing in the replaced
      _append_validated, both are owner-bound follow-ups, and patching either
      changes approved bytes and forfeits the reused review.
prs: [7265]
discoveries:
  - "DSC:OPTIONS-SESSION-LEDGER-PREFIX-FAILURE-IS-A-CONTAMINATED-CHECKPOINT"
---

# MACRO-03 — Options session-outcome ledger durability

This is a continuation of carrier PR #7265, not a second implementation. Its head
`d99070a2755c61895c493e189d512517e5601623` is an ancestor of this branch and every production blob
is byte-identical to the approved head, so no reviewed engine byte is re-litigated. The delta here
is an additive test matrix plus one discovery record.

The reported blocker inverted on inspection. The source ledgers are pristine; the campaign
checkpoint is the contaminated artifact, and the same error reproduces on unmodified `origin/main`,
so it neither originates in this carrier nor justifies holding it. A side measurement from that
reproduction: main needs 18m16s where the carrier needs 46.5s on the same input, which incidentally
clears the ten-minute campaign step budget that main's own dry run already exceeds.

What remains outside this carrier is stated in `unresolved` above: production acceptance on two
natural append observations, the incumbent campaign owner's checkpoint reconciliation, and the
shared publisher lane's locked-index flake.

## Delivery closed — merged, verified in main's bytes, acceptance baseline pinned

PR #8205 squash-merged as `fd04137075019a471a78ffc6374051c942417489` at 2026-09-29T21:14:46Z, at the
exact head `dbf4d6a1e21b` that had concluded clean (`--match-head-commit`; the sweeper had
update-branched the PR twice during the wait, so the flag is what kept an unverified head out).

Verified in `origin/main` after a **bare** `git fetch origin` — a bundled fetch of main plus the
now-deleted head branch fatals and leaves `origin/main` stale, i.e. the merge's own success breaks the
naive check that verifies it. All seven paths byte-identical between merged head and main:
`engine/options_signal_episode.py` `699b7573847e`, `..._contract.py` `22e97d1e589a`,
`..._campaign.py` `f2b1f59611c2`, `scripts/ci/options_signal_nightly.sh` `d7ac2dd9390e`,
`tests/test_options_signal_episode.py` `6364169d7bd5`, and the two `agentos/` records. Those four
engine/publisher blobs are the objects the independent review verified against approved head
`e562578d`, so main now carries exactly the content that approval covered.

**Installed generation flipped (measured).** Pre-merge, `SESSION_OUTCOME_PART_MAX_BYTES`,
`session_outcome_part_paths` and `session_outcome_logical_bytes` were ABSENT from `origin/main`; they
are now present at 7 / 4+2 / 2+5+1 references. #8205 was therefore the release vehicle for the
capability, not a test supplement — an earlier comment of mine that called it "tests-only" was wrong
and is retracted on the PR.

**Acceptance baseline, pinned for the two natural observations:**

```
base size : 100,471,221 B   (1.996x the 50,331,648 B ceiling; ~4.4 MB under GitHub's 100 MiB blob limit)
base blob : c73ec6998a03b193e219dffa62f668e9eb426420   <-- MUST NOT CHANGE, ever
parts dir : 0 entries at merge time
```

**An observation is an `engine` JOB, never a run.** `daily.yml` is DST-paired, so each night
produces TWO scheduled runs: the wrong-DST one exits in seconds reporting run-level **SUCCESS** with
every job skipped, while the run that actually builds can report run-level CANCELLED/FAILURE from a
late job hours after `engine` already succeeded and pushed. The session-outcome publisher lives
inside the `engine` job (`daily.yml:3358-3426`, build → publish-episode → publish-campaign;
`assert-integrity` at :4861), so a run whose `engine` is `skipped` is **not an observation at all**
whatever its run-level colour, and `parts/ == 0` after such a run says nothing about maturation.
Canonical method and receipts: `DSC:NIGHTLY-ARTIFACT-ATTRIBUTION-NEEDS-THE-ENGINE-JOB`.

Observation #1 = the first post-merge nightly whose `engine` job concludes `success` **and appends**.
Because the frozen base is already 1.996× the 48 MiB part ceiling, that first append necessarily
creates `part-000001.jsonl` — the **first rollover**. Observation #2 = the next such run, the first
append into an *existing* part, a different code path. An `engine success` night that matures no rows
is a legitimate null, not a failure, and is not one of the two.

**Status at closeout: ZERO observations, cause external.** The only two `daily.yml` runs created
after the merge (2026-09-29T21:40:32Z) were `36658978247` (02:15:12Z, run-level completed/**success**,
`engine` **skipped** — the DST decoy) and `36655184116` (01:27:15Z, the EDT-intended firing), still
`queued` and never started 4h26m after creation as of 2026-09-30T05:53Z. `daily.yml` is the only
workflow that can append these rows, so no alternative observation source exists. Base blob and
parts count re-verified unchanged at that time (`c73ec6998a03…` / 0) — the expected reading when the
writer has not run, and NOT evidence about maturation.

Attribute first, then read the ledger. The path is `options_signal_episode`, not `options_signal`; a
wrong prefix returns a false `0` rather than an error:

```bash
gh api "repos/mastermindx-market-intelligence/macro/actions/runs/<id>/jobs?per_page=100" \
  --jq '.jobs[]|select(.name=="engine")|"\(.conclusion) \(.started_at) \(.completed_at)"'
git fetch origin
git rev-parse origin/main:data/options_signal_episode/outcomes_session.jsonl   # must equal c73ec6998a03…
git ls-tree -r origin/main -- data/options_signal_episode/outcomes_session_parts/
```

A changed base blob SHA stops the lane; it is the single failure this design exists to prevent. After
a part exists, **rollback is no longer a revert** — a revert would install a reader with no knowledge
of `outcomes_session_parts/`, and because the base stays a valid prefix the receipt check keeps
passing, so it presents as the ledger quietly ceasing to grow. The lever is then the `COLLECT_LANE`
writer-stop (`engine/ledger_lane.py:24`), which makes `append_session_outcomes` return `-1` before it
validates a row, takes the base lock, or creates the parts directory.

**Open, owner-bound, NOT done by this session** (filed on carrier #7265): unbounded in-memory
rehydration is now the binding growth constraint, because GitHub's 100 MiB blob limit was silently
capping it and the parts design removes that cap — measured 49.71 s / 39.78 s for a 2-row and 3-row
append against the real base. Also two MINORs: the shell gate at
`scripts/ci/options_signal_nightly.sh:58-59` tests `-e` before `-L`, so a *dangling* parts symlink
returns 0 instead of being rejected (engine raises first, so not exploitable); and the writer's
in-code comment claims a crash "can never expose a torn row", which is false — pinned instead by
`test_session_outcome_reader_fails_closed_on_a_torn_or_empty_part`.
