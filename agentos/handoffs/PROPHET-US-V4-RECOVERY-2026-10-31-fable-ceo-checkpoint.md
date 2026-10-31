---
workstream: WS:PROPHET-US-V4-RECOVERY
session: claude/ssd-quizzical-nash-0788e4-e8b383ae5709284c (Fable CEO handoff, Prophet US V4 / Entry Timing, 2026-10-31)
model: fable
ended_because: ci_handoff
mission: >
  Complete Prophet US V4 and Entry Timing (US share of R6/R7) end to end. This
  checkpoint: reconcile the October 31 completion brief and source census,
  reconcile incumbent writers and Fabric effects, and land the strongest
  independent engineering slice — the one that returns the lost nightly curated
  candidate tier to main — then bind the B4 alias seam.
state_before: >
  Completion brief and source census at macro e757498822a2255d3895b76232989dac3e739276
  (Draft #10242, planning artifact pending independent review); V4 recovery
  carrier Draft #10174 at 29cfb98b (Sol); A2 #10202/#10209 Draft/HOLD with the
  retained Fabric preflight operation prophet-v4-a2-source-issuer-preflight-20261031-01
  (TERMINAL rc0, NOT_ACCEPTED, patch retained unpushed). The curated US candidate
  tier had no committed rows on main for any session after 2026-10-19 (W3 ledger
  marked those sessions missing from the durable store) although the engine built
  them every night. The B4 prospective capture seam resolve_alias_table() returned
  None, so every B4 capture row was IDENTITY_ALIAS_UNRESOLVED by construction.
changed:
  - path: scripts/ci/qledger_carve.sh
    what: >
      New sourced helper (PR #10255) carrying #9556's accepted carve semantics to
      every wholesale nightly committer: custody snapshot (commit-tree -p HEAD,
      runner-local, unreachable), unstage + verified park at HEAD of data/qledger
      and site/qledger, per-path delta restore from the snapshot (only the paths
      this run changed; a qledger file main added or changed under the rebase is
      left as main has it), restore armed on EXIT and recorded to
      $RUNNER_TEMP/qledger_carve_snapshot.<run id> for the workflow's always()
      restore step; LOST is ::error, never success.
  - path: scripts/ci/daily_engine_commit_outputs.sh
    what: >
      Carve between the broad `git add data/ site/ reports/` and the first
      "no engine output changes" check (withhold reds the run); the post-rebase
      render-sync re-add keeps the carved planes unstaged.
  - path: .github/workflows/daily.yml
    what: >
      collect_tail "commit tail data" and stock_briefs "commit stock briefs" carve
      after staging (withhold stays green); an `if: always()` restore step follows
      each of the two engine committer steps so a SIGKILL on timeout/cancel cannot
      strand the runner's grown ledger bytes.
  - path: tests/test_qledger_carve.py
    what: >
      Real-git proof against a bare origin whose pre-receive hook enforces GH001:
      the rejection without the carve, the landed commit with it (after a
      concurrent-writer rebase, and after main added/changed qledger files), a
      hard-kill + always()-step restore, the park-failure withhold, a carved new
      file, trap chaining (one-line, multi-line, quoted), and the wiring pins.
prs: [10255]
verified:
  - claim: The nightly outage root cause is GitHub's GH001 blob limit on data/qledger/claims.jsonl, not the builders.
    command: >
      gh run view 40803269874 --log-failed (one bounded read); git log origin/main --
      data/us_prophet_rank/candidates/2026-10.parquet; git ls-tree -l origin/main
      data/qledger; python3 pandas groupby stamp_date/tier over the candidates store.
    result: >
      collect_tail and stock_briefs rejected with "File data/qledger/claims.jsonl is
      146.50 MB; this exceeds GitHub's file size limit of 100.00 MB"; the engine job
      (conclusion cancelled) has no landed "engine: regime update" commit since
      2026-10-21; claims.jsonl is 104,857,394 B on origin/main; curated tier rows per
      stamp: 10-14 2916, 10-19 1706, every later stamp 0 while the scan tier (its own
      committer) kept landing ~1,650 rows. #9556 protected only the `collect` job.
  - claim: The carve is proven against the exact rejection it prevents, and the fixes the independent reviewer required are covered.
    command: python3 -m pytest tests/test_qledger_carve.py tests/test_workflow_file_size.py tests/test_daily_collect_commit_path.py tests/test_push_retry.py -q
    result: 212 passed in 475.80s — the 20-test carve suite (including the reviewer's rebase, hard-kill, park-failure and new-file scenarios) plus the workflow-size, collect-commit-path and push_retry neighbours; daily.yml 482,502 B.
  - claim: An independent non-author reviewer (Opus, read-only) attacked the first revision e8a5afe5e09c and its findings were repaired, not argued away.
    command: Agent ROUTE review / MODE READ_ONLY over the PR diff and call sites; reviewer ran pytest tests/test_qledger_carve.py (13 passed) and a scratch-repo rebase simulation.
    result: >
      REVISE — FIX-BEFORE-MERGE (1) whole-plane restore deleted a qledger file main
      added under the rebase (reproduced); (2) restore lived only in an EXIT trap a
      SIGKILL skips; NITs: multi-line prior trap dropped, render-sync re-add leaked a
      carved new site/qledger file, missing tests. All four repaired in revision
      fd23dfbfa8e3 with discriminating tests; a second read-only review of the changed
      behavior is the pending gate (see next_actions).
  - claim: The B1 identity join is not broken; suppressions at the Oct 25 generation are reference-coverage, not join defects.
    command: >
      Read engine/us_candidate_episode_intake.py load_identity_spine; counted the
      `membership` vendor alias universe (1,941 rows) against the 2,072 generation
      inputs; checked the suppressed tickers' tier in the candidates store.
    result: >
      1,984 suppressed inputs are scan-tier tickers outside the ~1,628-key membership
      reference universe (S&P 1500 scope); the 88 mapped are inside it. True common
      stocks outside that universe are a reference-coverage gap owned by
      scripts/build_security_master.py (Data OS), not an identity-join bug. The
      fail-closed refusals are correct and were not bypassed.
  - claim: The Data OS alias reader binds to the committed reference and resolves store symbols.
    command: >
      python3 -c over engine.us_candidate_episode_intake.load_identity_spine(Path("data"))
      and lib.dataos.identity.VendorAliasTable on data/reference/vendor_aliases.parquet
      (8,930 rows; vendors yahoo 1,942 / membership 1,941 / store 1,939 / yahoo_fetch 1,938 /
      theme_graph_native 1,166 / ledger 2 / polygon 1 / thetadata 1).
    result: >
      1,938 store aliases cover 2026-10-30; vendor_symbol_for("store","SEC:US-XNYS-A")
      -> "A"; receipt sha256:ff8a32df8e47d88149d8ac8d8ae54b9b117a3c44cd34cfcd57eebcf0de816306.
      The seam can be bound without inventing identity (next action 3).
unverified:
  - claim: >
      The next scheduled nightly lands the "engine: regime update <date>" commit,
      the curated tier rows (~2,900) for that session, and the collect_tail and
      stock_briefs commits, with "::warning title=qledger carved out of this commit"
      in the engine, collect_tail and stock_briefs logs.
    what_would_verify: >
      After #10255 merges, read the next scheduled daily.yml run once (never dispatch
      it manually): the three warnings, the landed commits on origin/main, and
      curated rows for the session in data/us_prophet_rank/candidates/<month>.parquet;
      then the W3 ledger stops marking the session missing.
  - claim: Carved runner-local ledger bytes survive a real SIGKILL on the macstudio runner through the always() restore step.
    what_would_verify: A nightly where the engine committer step is cancelled or times out, followed by the always() step log "restored byte-identical from snapshot".
unresolved:
  - >
    Lost sessions 2026-10-20 .. 2026-10-30: the curated rows for those sessions were
    built on the runner and lost with the rejected commits; they are NOT reconstructed
    by #10255 (reconstruction is a separate decision owned by the W3/Data OS ledger
    owners — do not backfill from memory or re-run old nights).
  - >
    whitehouse-sentinel.yml (hourly) also runs a wholesale `git add data/qledger`;
    it was not changed in #10255 and will be rejected the same way if its W5 adapter
    appends to the oversize claims.jsonl; backfill.yml likewise unchecked.
  - >
    The qledger ledger's size itself (claims.jsonl at the GH001 limit, grades.jsonl
    79 MB) is the qledger publication program's (#9450/#9452/#10079) — the carve
    withholds publication; it does not shrink or shard the ledger.
  - >
    B4 nightly capture placement: NATIVE_LIVE_ROOT=/var/lib/macro-live exists only on
    the VPS (systemd macro-live-* units under app/deploy, installed by update.sh), where
    LEDGER LAW G0.2 forbids writing data/ paths; the capture stream's durable home
    (local state dir + R2 publication vs. a nightly-job read of VPS-published owner
    files) is an unmade design decision — binding the seam does not wire the nightly.
next_actions:
  - >
    1. Consume the second read-only review of #10255 (changed behavior only); on
    green hosted CI and a non-author approval, release through the normal ship
    path (merge --match-head-commit fd23dfbfa8e3); never self-approve or self-merge.
  - >
    2. Production proof on the next scheduled nightly (see unverified); record it
    here and in the W3 ledger; do not dispatch daily.yml manually.
  - >
    3. Bind the B4 alias seam: resolve_alias_table(root) -> lib.dataos.identity
    VendorAliasTable over data/reference/vendor_aliases.parquet via the intake's
    _records_snapshot (sha256 receipt in the run document; absent reference stays
    typed IDENTITY_ALIAS_UNRESOLVED; unlawful reference = typed whole-run refusal);
    tests + hosted CI + independent review in its own PR (patch prepared this
    session).
  - >
    4. Decide the B4 capture's durable home (unresolved above) with the Data OS /
    live-plane owners before any nightly wiring; preserve the amended B4
    preregistration (#7751 A1), its prospective population, H10 MAE endpoint, cost
    floor, multiplicity treatment, fixed looks and refusal handling unchanged.
  - >
    5. A2: consume the retained preflight patch of
    prophet-v4-a2-source-issuer-preflight-20261031-01 (TERMINAL rc0, NOT_ACCEPTED)
    through its existing carrier before any overlapping issuer work; do not
    re-run it.
  - >
    6. Entry Timing W1/W2 scientific denominator and the B-17 34-session window
    census (7,918 C0 episodes, none complete) — no favorable subset.
do_not_redo:
  - V4 waves 0A, 0B, A1, B1, D1 and Entry Timing W0 are DONE (do not reopen).
  - "PR #9556's inline carve in the `collect` job is accepted; #10255 does not touch it."
  - The B1 identity-join investigation above (suppressions = reference coverage).
  - The refused whole-plan review prophet-us-entry-timing-plan-independent-review-20261031-01 (exit 75, no verdict) is not a review and is not retried on an unchanged path.
  - The Fabric preflight operation prophet-v4-a2-source-issuer-preflight-20261031-01 is reconciled TERMINAL; do not replace or re-dispatch it.
danger_areas:
  - >
    daily.yml file-size budget (tests/test_workflow_file_size.py BUDGET_BYTES 487,000):
    482,502 B after #10255 — ~4.5 KB of headroom for every later edit.
  - >
    The engine committer runs TWICE per job (core checkpoint + final commit); each
    invocation carves and restores independently; the always() steps are idempotent.
  - >
    `git restore` with several pathspecs fails whole if one is unmatched; the helper
    loops per plane. `_git`-style test helpers strip stdout: never assert porcelain
    leading spaces.
  - >
    The candidates store has no security_id column (stamp_date, ticker, tier only);
    identity enters through the B1 episode store, so a capture's alias resolution is
    per episode, never per ticker.
---

# Prophet US V4 / Entry Timing — Fable CEO checkpoint, 2026-10-31

The commission's first engineering slice was chosen by effect: since 2026-10-21 no
wholesale nightly commit (engine, collect_tail, stock_briefs) had reached main,
because GitHub's GH001 blob limit rejects `data/qledger/claims.jsonl` whenever it is
staged, and only the `collect` job had #9556's carve. That is why the curated US
candidate tier — built every night — had no committed rows after 2026-10-19 and the
W3 ledger kept marking sessions missing. PR #10255 carries the accepted #9556
semantics to the other three committers through one sourced helper, proven in real
git against a GH001-enforcing origin, and repaired against an independent reviewer's
findings (per-path delta restore; always() restore step; trap chaining; render-sync
re-add). Merge, production proof and acceptance are distinct rungs; this record
reaches DELIVERED + hosted CI, no higher.

The B4 seam investigation found no lost legitimate opportunity in the identity join:
the Data OS alias reader resolves the canonical ids the B1 generation binds, and the
suppressions are reference-coverage (membership universe) by construction. Binding
the seam is next action 3, prepared and reviewable on its own.

Canonical sources: completion brief and census at e757498822a2 (Draft #10242),
recovery carrier #10174 (29cfb98b), program issue #6805 (comment 6539985230), shared
R7 issue #6817, original R6 delegation root prophet-us-fable-meta-ceo-20260923-001.
