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
prs: [10255, 10267, 10277, 10283, 10289]
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
  - claim: >
      B4 alias seam bound (PR #10267): resolve_alias_table(root, required=…) reads
      data/reference/vendor_aliases.parquet through the intake's _records_snapshot
      into lib.dataos.identity.VendorAliasTable; durable --nightly refuses an absent
      reference (ALIAS_REFERENCE_MISSING, exit 3, nothing written); report/dry-run
      keep the adapter's typed IDENTITY_ALIAS_UNRESOLVED; unlawful table =
      ALIAS_TABLE_MALFORMED. Independent read-only review r1 REVISE (F1 silent
      degrade of uncorrectable rows; F2 sparse-tree test; F3 docstring) repaired at
      12ffc06a; r2 APPROVE-READY; r2 nit fixed at 750dd2c2 (test only).
    command: >
      python3 -m pytest tests/test_capture_prophet_b4_same_read.py -q; plus
      tests/test_prophet_b4_same_read.py test_prophet_strategy_definition.py
      test_us_candidate_episode_intake.py test_us_candidate_episode_reconciler.py
    result: 25 passed; 280 passed across the neighbouring suites (local, head 750dd2c2).
  - claim: >
      Entry Timing W1 denominator (PR #10277, head 942a4ed8): for the selected B1
      generation peg:23be3409… on main 91b936c4, 88,325 inputs / 15,511 mapped /
      62,500 IDENTITY_UNRESOLVED; replaying every refused (ticker, session) pair
      through the ONE Data OS reader (membership vendor, same `on` as the intake):
      51,347 rows no current reference knows, 11,153 rows whose alias was ingested
      after the session (lawful as-known refusal), 0 rows resolvable at their session.
      The identity join has no intake defect; the loss is reference coverage.
    command: >
      python3 scripts/report_us_candidate_episode_waterfall.py --json;
      python3 -m pytest tests/test_report_us_candidate_episode_waterfall.py -q
    result: >
      run document as above (outcome-blind, writes nothing); 4 passed. Written up in
      research/prophet_v4/ENTRY_TIMING_W1_INTAKE_WATERFALL_2026-10-31.md.
  - claim: Entry Timing W1 (PR #10277) survives independent non-author review; the turn_watch clock defect found in round 1 is repaired.
    command: >
      three read-only Opus review rounds on heads 942a4ed8 -> 4e53d95a -> d03acfd0;
      python3 -m pytest tests/test_report_us_candidate_episode_waterfall.py -q (7 passed);
      python3 scripts/report_us_candidate_episode_waterfall.py --json --git-history origin/main.
    result: >
      r1 REVISE (mapped turn_watch rows were binned by trigger date) -> receipt->document
      data_session recovery over 54 distinct turn_watch blobs (full history), 1,694/1,694
      events and 13,649/13,649 suppressions recovered; r2 REVISE text-only -> r3
      APPROVE-READY at d03acfd0 (reviewer rebuilt every _source_id; reconciliation
      88,325 = 88,325). Armed merge-on-green at d03acfd0; not merged at this write.
  - claim: PR #10255's contract-delta red is a CI-manifest gap, not a code defect, and is repaired.
    command: >
      gh api repos/.../actions/jobs/<contract-delta job>/logs (one read);
      python3 scripts/check_contract_delta.py --base origin/main after the edit.
    result: >
      "tests/test_qledger_carve.py is a new pytest suite named by no run: step in any
      workflow" (1 introduced, 0 inherited); wired into the push-retry-policy job of
      .github/ci/legacy-jobs.yml (owner of push_retry.sh and the append-only fence)
      at 6454a74a; local gate: 0 introduced, 0 inherited (base 51404df7).
  - claim: The Entry Timing W2 design registration's round-1 incumbent proxy was degenerate and revision 2 replaces it with a real admission event.
    command: >
      python3 research/prophet_v4/entry_timing_w2_t1_census.py (dates, tickers and lane
      flags only; no price, grade, outcome or paired-race column read).
    result: >
      curated tier: 916/1,087 OPENED episodes already curated before discovery, 77.3%
      zero lag (a universe, median 2,932 rows per stamp). BUY lane (lane == "buy",
      engine/us_candidate_lanes.py): 365 admissions stamped >= discovery, 6.0% zero lag,
      median lag 14 grid sessions (IQR 5-23), 722 never; lane/tier/featured populated on
      35 of 54 stamp dates (last 2026-10-19), buyable/eligible on all 54. Registration
      r2 at 549d416f on Draft PR #10283; round-2 review REVISE (ITT primary with
      T1 = cash was a selection contrast with a 50 bps cost asymmetry; BUY coverage
      has gaps inside the decision window; session units, knowability, REJECT rules,
      B4 futility quote, MDE, falsifier). Superseded by revision 3 (next claim).
  - claim: W2 census v3 on the freeze basis identifies only the per-protocol timing contrast in R, and revision 3 registers that estimand with the policy contrast demoted to a P-only secondary.
    command: >
      python3 research/prophet_v4/entry_timing_w2_t1_census.py --receipt-sessions
      <W1 r3 receipt map> --commit-walk --k 10 --buffer-minutes 30 (dates, tickers,
      lane/tier flags and commit times only; SPY parquet opened for its date index).
    result: >
      1,087 admissions (all W1 r3 discovery sessions inside R) -> 98 INCUMBENT_LED ->
      96 identified pairs (31 exact + 65 interval-censored by producer gaps), 892
      CENSORED (a gap and no BUY stamp in the window), 0 CASH (no R window is free of
      gaps), 1 UNKNOWN; healthy stamps on 26 of 42 R sessions; earliest-possible lead
      median 2 sessions (IQR 1-4), observed-stamp median 6; k* = 2 = k (T2m
      UNIDENTIFIED); every BUY stamp becomes knowable 1-2 sessions after its date
      (275 commits walked). Output committed as
      research/prophet_v4/entry_timing_w2_t1_census_2026-10-31.json (c1a0724a).
      Registration r3 at 8d86c28c (DRAFT - UNFROZEN): conditional timing primary
      with argued bias direction and a placebo negative control; policy contrast as
      P-only decomposition; INCUMBENT_LED class; interval-censored admission; NYSE
      session units; as-committed knowable session + next-close fill; REJECT/RETAIN
      rules; B4 futility quoted; MDE stated. Round-3 review (8d86c28c) REVISE: P1
      interval-censored units had no defined incumbent entry; P2 the t_disc-5 placebo
      cannot control admission selection and PROMOTE would endorse an inexecutable
      rule; P3 the discovery-side knowable session was unmeasured; N1-N14.
  - claim: W2 revision 4 (c38416ae) registers the implementable policy contrast as the P-only primary under three recorded seat adjudications, and census v4 times both arms by first commits.
    command: >
      python3 research/prophet_v4/entry_timing_w2_t1_census.py --receipt-sessions
      <W1 r3 map> --commit-walk --document-walk (dates, flags, commit times only).
    result: >
      W2-ADJ-01 policy contrast (buy at every discovery vs follow the lane, ITT, cash
      0, decomposition printed) is the promotable primary, P only, unidentifiable in R;
      W2-ADJ-02 timing contrast + executable lead is a guard on exactly identified,
      gap-free-pre-window pairs (floors 300 units + 100 pairs); W2-ADJ-03 lane state
      from the first-commit blob (HEAD carries 59 BUY rows and three healthy dates
      07-31/09-14/10-19 that only later heals added) and a turn_watch document commit
      walk (54/54; every discovery knowable 1 session after its data session).
      Security-first identity join confirmed by the forward resolver (the clocked
      reverse lookup returns UNAVAILABLE for the membership namespace). Census v4:
      1,087 -> 98 INCUMBENT_LED -> 989 pre-window gap -> 26 exact (executable lead
      median 0; 15 of 26 zero) / 65 interval / 873 censored / 0 cash / 25 UNKNOWN
      signal_asof; k* = 0 so T2m UNIDENTIFIED; generation recorded_at within 2
      sessions for all units. Estimator = cluster bootstrap on t_disc (4000, seed
      20261031); FRAGILE blocks PROMOTE; tolerance (ii) rescaled to a -25 bps mean.
      Round 4 returned REVISE on c38416ae: P1 the session-cluster bootstrap ignores
      dependence between overlapping holds and the floors count units, not periods;
      P2 the lane-state rule differed between code and prose and the "59 BUY rows /
      07-31 heal" evidence was an artifact of walking 2026-08..10 only; N1-N14.
  - claim: W2 revision 5 (438b1ac45ec1) resolves round 4 with census v5; the r4 heal evidence is retracted.
    command: >
      python3 research/prophet_v4/entry_timing_w2_t1_census.py --receipt-sessions
      <W1 r3 map> --commit-walk --document-walk (v5: all four monthly parquets,
      first-parent arrival, one heal rule, uniform identity span, K on k(c_cur),
      HEAD never read; dates, flags, arrival instants only).
    result: >
      1,087 -> 98 INCUMBENT_LED -> 989 pre-window gap -> 26 exact (lead median 0,
      15 of 26 zero) / 44 interval / 0 cash / 918 censored / 1 UNKNOWN signal_asof;
      21 units had a BUY row on the last window session that arrived one session too
      late (not inside K); HEAD differs from first-arrival by 154 BUY rows, ALL from
      the 09-14 (+50, healed 09-16) and 10-19 (+104, healed 10-21) heals, so both
      sessions are GAPs; 07-31 is healthy on both bases (r4's "59 rows / 07-31" was
      a July-walk artifact, exactly as round 4 said); recorded_at <= T0 fill instant
      for 1,087/1,087; alias snapshot sha256 ff8a32df8e47... pinned; 0 strict primary
      units and 0 strict pairs in R. r5 adds W2-ADJ-04 (one heal rule: healed session
      = GAP), ADJ-05 (circular moving block bootstrap, l = 22 sessions, shared index
      set; floors 300 units over >= 110 distinct discovery sessions / 100 pairs over
      >= 44), ADJ-06 (-25 bps as a differential only; PROMOTE also needs T0's own
      lower bound >= 0 and the timing point estimate >= 0); critical values restated
      with design effects (policy SE ~43, crit ~+46 bps, pass-at-zero ~0.14; r4's 0.29
      was wrong); tolerance (ii) differential at -50 bps; T3 gate availability-only;
      anchor knowability; REJECT_FUTILITY terminal; trim once; R maturity from
      observed t_exec; the frozen YAML block parses (49 keys). Round-5 review running
      on 438b1ac4. The seat does not self-approve.
  - claim: W2 round 5 returned REVISE on 438b1ac4; revision 6 (2d81bf311b88) with census v6 answers every finding.
    command: >
      python3 research/prophet_v4/entry_timing_w2_t1_census.py --receipt-sessions
      <W1 r3 map> --commit-walk --document-walk --server-arrival (v6: pinned
      origin/main SHA, GitHub check-suite createdAt witness per first-arrival commit,
      window scan continues past a late-knowable BUY row, strict sets need a fully
      covered window, skipped-blob counter, knowable maps + shift distributions
      exported; dates, flags, arrival instants only).
    result: >
      Round-5 REVISE: B1 futility/monitoring looks had no session floor; B2 l = 22
      too short, floors must count full blocks, percentile bound anti-conservative
      with few blocks; M1 arrival clock was the bot's commit clock; M2 scan broke at a
      late-knowable row; M3 exact units with a gap after admission entered the strict
      set; M4 anchor gates applied to T1; M5 walk unpinned; m1-m5, n1. r6 adds
      W2-ADJ-07 (block 44 = 2(K+H+2); deciding bound = more conservative of MBB
      percentile and t(B-1) on full non-overlapping block means; fixed look >= 5 full
      blocks = 220 sessions, futility >= 150 units and >= 3 blocks, monitoring looks
      point estimates only; planning on block means: SE ~50, crit ~+82 bps, power80
      ~+125, pass-at-zero ~0.09; r5 design-effect figures withdrawn), W2-ADJ-08
      (arrival = max(commit clock, earliest check-suite createdAt); witness for 31/44
      stamp commits and 23/54 document commits, every witness within 2 min after the
      commit clock, no knowable session changed; unwitnessed commits listed; R
      readout also with both clocks +1), W2-ADJ-09 (AVOIDED/REFUSED apply to T0/T2/T3
      only; T1 enters whenever _classify_buy_row admitted inside K). Census v6:
      counts unchanged except 23 (was 21) censored units carry a late-knowable BUY
      row (stamp lag 9/10) and all 26 exact pairs carry a gap after admission -> 0
      strict pairs, 0 full blocks in R; discovery-document shift over 1,087 R units:
      1,076 at +1, 11 at +2 (LATE_DISCOVERY_ARRIVAL, flagged); over all 54 receipts
      1 session for 37 and 2-11 for 17 (08-21 / 09-04 documents that reached main
      days later); pinned origin/main 761e814eda84 (the ref moved between two
      same-day runs). YAML block: 54 keys, every flow value with commas inside
      parentheses quoted, validator walk clean. Round-6 review running on 2d81bf31.
      The seat does not self-approve.
  - claim: PR #10277's contract-delta red is repaired at 82812b818eb3; the merge-blocked marker stays until hosted CI is green.
    command: >
      wired tests/test_report_us_candidate_episode_waterfall.py into the prophet-lab
      run step (.github/ci/legacy-jobs.yml) and the ci.yml paths; python3
      scripts/check_contract_delta.py --base 91b936c46424 -> 0 introduced, 0
      inherited; one GraphQL read of the head's check contexts.
    result: >
      At 82812b81: contract-delta SUCCESS, ci-authority/main SUCCESS, ci-plan /
      fence-pack / capability-broker / grader-manifest / self-mod-fence SUCCESS;
      ci-pack-0..11 IN_PROGRESS; the only red is the standing
      ci-authority/codex/merge-queue-pilot. The merge-blocked label and the guard
      comment ("bootstrap under the pre-existing check standard") remain; the seat
      posted the repair note (comment 6542015074) and will remove the marker only with
      a visible comment once ci-pack and ci-gate are green; never self-merge.
  - claim: The retained A2 preflight patch has a reviewable carrier — Draft PR #10289, stacked on #10209.
    command: >
      git apply of the fabric result's patch onto da3a04518f13 (the exact #10209 head)
      -> 1504ca7e; python3 -m pytest tests/test_prophet_settlement_preflight.py -q;
      contract-delta (base da3a0451) then required a run: step -> 0cfffbab wires the
      suite into the prophet-lab code gate and the ci.yml paths block.
    result: >
      27 passed locally. File SHAs match the fabric manifest. Draft, base
      sol/web-prophet-v4-a2-producer-clock-20261030 (Sol's Draft/HOLD lane), not
      armed, not reviewed, not accepted, not released; hosted CI not yet consumed.
      The fabric operation prophet-v4-a2-source-issuer-preflight-20261031-01 stays
      TERMINAL / NOT_ACCEPTED and is not re-run.
  - claim: W2 rounds 6 and 7 returned REVISE (no blocker); revision 8 (51ea53823b8e) answers every finding, the estimator is a tested module, and the census re-run at the pinned SHA reproduces v7 exactly.
    command: >
      Opus reviewer (read-only) rounds 6 and 7 on 2d81bf31 and 1116bb7e; r7 edits
      (ADJ-10 SE inflation, pinned origin/main walk, main-branch check-suite witness,
      per-unit late counter, three-way +1 sensitivities, ENTERED_BELOW_ANCHOR
      exclusion); r8 edits (+1-clock readouts on every deciding P look, census
      --main-sha, 126-session pair-floor deadline, constant 1.1682, bootstrap
      rationale, N8 test); python3 research/prophet_v4/entry_timing_w2_t1_census.py
      --commit-walk --document-walk --server-arrival --main-sha a7eef2ce9737;
      python3 -m pytest tests/test_entry_timing_w2_estimator.py -q;
      python3 scripts/check_contract_delta.py --base a7eef2ce9737.
    result: >
      Round 6 REVISE (B1 YAML avoided window, M1 t bound ignored lag-1 block-mean
      autocorrelation, M2 walk SHA read after the walk, m1-m7, n1-n2) -> r7 1116bb7e;
      round 7 REVISE on minor items only (N1 P looks had no +1-clock readout, N2 census
      not re-runnable at the pinned SHA, N3-N8 text/constant/rationale/test) with the
      planning numbers reproduced independently (policy critical +86..+100 bps, timing
      +107..+114, pass-at-zero 0.099-0.106, inflation 1.1682 at r=0.17 B=5) -> r8
      51ea53823b8e. Estimator research/prophet_v4/entry_timing_w2_estimator.py (MBB
      l=44 circular, shared index set, t(B-1) with inflated SE, conservative-of-two
      bounds) 9 tests passed; wired into legacy-jobs.yml + ci.yml paths (contract-delta
      0 introduced / 0 inherited at base a7eef2ce9737). Census v8 at --main-sha
      a7eef2ce9737: identical top-level output to v7 (in_R 1087, 26 exact / 44 interval /
      918 censored, 21 late-knowable units, witness 31/44 + 23/54 on main, 0 off-main).
      Round-8 bounded delta review commissioned on 51ea5382 (session bcc7e91f). Still
      DRAFT, UNFROZEN, no outcome read; #7751 A1 untouched.
  - claim: A2 #10289 round-1 and round-2 independent reviews returned REVISE (no blocker); round-3 repairs at 645caaa6cf60 with 70 tests passing.
    command: >
      Opus reviewer (read-only) on 0cfffbab then dd9c840c; repairs in the A2 worktree
      (claude/a2-prophet-fullpop-preflight-salvage-20261031); python3 -m pytest
      tests/test_prophet_settlement_preflight.py tests/test_prophet_durable_checkpoint.py -q.
    result: >
      Round 1 (M1 identity-hash conflation, M2 no pass-through test, M3 snapshot
      InfrastructureError left no receipt, M4 inventory write could withhold
      publication, m1-m6) -> dd9c840c: raw-to-raw / semantic-to-semantic identity
      binding, pass-through test under a lifted owner ceiling (tripwire fails when W3B
      lifts it), typed SOURCE_SNAPSHOT_MISSING/UNBOUND, SNAPSHOT_PATH_UNQUALIFIED,
      INVENTORY_MALFORMED, CANDIDATE_STORE_EMPTY, receipt refused inside the repo,
      nightly inventory write wrapped (warning only), ::warning/::notice + step summary.
      Round 2 (N1 zlib.error crash, N2 unvalidated receipt content echoed, N3
      precedence, N4 docstring vocabulary, N5 heredoc-only test, N6 VALID_EMPTY
      decision) -> 645caaa6: zlib.error typed as DURABLE_SOURCE_SNAPSHOT_MISSING,
      receipt fields echoed only after owner validation and only as str / list[str],
      executed nightly-write test, VALID_EMPTY adjudicated as an accepted reference
      (empty candidate store still refused). 37 + 33 = 70 passed. Round-3 bounded delta
      review commissioned (session bcc7e91f). Draft, never armed, stacked on #10209
      (HOLD); ci-authority/main rejects the non-main base as expected; the dag.yml
      entry is a declaration only (dag-conformance), the nightly runs the preflight
      inside scripts/ci/daily_engine_prophet_nightly.sh after delta_manifest.
  - claim: Entry Timing W2 registration r8 is FROZEN (freeze commit 7cdea8919475, SHA recorded at 915e50b3c6e7) after a round-8 PASS; T3 is in the P family; the R look is no earlier than 2026-11-19.
    command: >
      Round-8 Opus review on 51ea5382 (PASS; nits confirmed at 90c54a11);
      python3 research/prophet_v4/entry_timing_w2_t1_census.py ... --main-sha a7eef2ce9737
      --units-out research/prophet_v4/entry_timing_w2_units_2026-10-31.json;
      python3 research/prophet_v4/entry_timing_w2_freeze.py --review-head 51ea53823b8e ...;
      shasum of the registration at 7cdea891 == PREREG.json registration.sha256_at_freeze;
      python3 -m pytest tests/test_entry_timing_w2_freeze.py -q (3 passed); gh pr ready 10283.
    result: >
      Machine freeze research/prophet_v4/entry_timing_w2/PREREG.json mirrors the 59-key
      frozen-field block; per-unit population file committed (1,087 R units, sessions and
      ids only); T3 availability gate 26/26 exact pairs (120-session 3-day-bucket lookback
      on the panel DATE index) -> T3 in the P Holm family, descriptive at R; R maturity
      session 2026-11-19 (T3 bound t_disc+K+1, + H=10; observed arms alone 2026-11-10);
      entitlement exclusion list pinned EMPTY (none exists; Data OS owner role); --main-sha
      must lie on origin/main's first-parent line. No outcome/price/grade read. #10283
      marked ready; contract-delta gate running locally; CI pending; the sweeper merges only
      on green + reviewDecision (never self-approved/self-merged).
  - claim: A2 #10289 round-3 review returned APPROVE-READY; nits fixed at ea8e38052b3e (38 preflight tests).
    command: Opus reviewer (read-only) on 645caaa6; python3 -m pytest tests/test_prophet_settlement_preflight.py -q.
    result: >
      N1-N6 all REPAIRED (N1/N2 tests discriminate by mutation probe; no new fail-open or
      crash; QUALIFIED path unchanged; VALID_EMPTY consistent with the owner reader). Nits:
      duplicate import removed; VALID_EMPTY -> QUALIFIED and STALE/PENDING/UNAVAILABLE ->
      GMI_RECEIPT_NOT_AVAILABLE pinned by a test with the owner validator stubbed (the
      production ceiling makes that branch unobservable today). Draft, never armed, stacked
      on #10209 (HOLD): retarget to main and arm only after #10209 lands.
  - claim: PR #10255 round 2 (fresh bounded reviewer at 6454a74a) returned APPROVE-READY and the PR is armed merge-on-green.
    command: gh pr view 10255 --comments (the round-2 verdict comment); one GraphQL read of mergeStateStatus/labels.
    result: >
      APPROVE-READY with four non-blocking nits (warn on snapshot-record write
      failure; per-step record tag; LOST return non-zero; explicit ci.yml two-halves
      entries) deferred to a follow-up PR; label merge-on-green set; UNSTABLE while
      ci-pack runs (10-31 ~10:xxZ read: #10277 d03acfd0, #10267 750dd2c2, #10255
      6454a74a all OPEN/UNSTABLE/armed).
unverified:
  - claim: W2 freeze PR #10283 (head 915e50b3) merges to main through the sweeper against that exact head.
    what_would_verify: green hosted CI on 915e50b3, reviewDecision, then merge --match-head-commit 915e50b3 by the sweeper; until then no freeze and no outcome read. T3 gate (union_admission reads completed closes only, asof-capable) is evaluated at freeze.
  - claim: PR #10267 (head 750dd2c2) hosted CI green and merged by the merge-on-green sweeper against that exact head.
    what_would_verify: the sweeper's merge commit on origin/main; mergeStateStatus read once via the bound PR status, not by polling.
  - claim: PR #10277 (head 82812b81) and PR #10255 (head 6454a74a) merge through the sweeper against those exact heads.
    what_would_verify: the sweeper's merge commits on origin/main; #10277 first needs ci-pack + ci-gate green at 82812b81 and the merge-blocked marker removed with a visible comment (the guard's condition: green under the pre-existing standard, not a semantic excuse); #10255 additionally needs the fresh bounded round-2 non-author review (the first round-2 reviewer stalled 70 min without a verdict and was stopped) and green hosted CI at 6454a74a before arming.
  - claim: W2 registration revision 2 is READY TO FREEZE.
    what_would_verify: the round-2 independent review verdict on 549d416f; then the census re-run with the W1 r2 session + VendorAliasTable join, k*, the T3 gate, the price-panel commit SHA, the Data OS exclusion list, and a machine freeze mirroring §2-§7. No outcome may be read before that.
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
    1. #10255 at 6454a74a is reviewed APPROVE-READY and armed merge-on-green:
    consume the sweeper outcome once at a real boundary (merge --match-head-commit
    6454a74a); never self-approve or self-merge; then open the nits follow-up PR
    (snapshot-record write warning, per-step record tag, LOST non-zero, explicit
    ci.yml two-halves entries).
  - >
    2. Production proof on the next scheduled nightly (see unverified); record it
    here and in the W3 ledger; do not dispatch daily.yml manually.
  - >
    3. #10267 (B4 seam, 750dd2c2) and #10277 (W1, now 82812b81 after the
    contract-delta repair; reviewed APPROVE-READY at d03acfd0, the repair touches CI
    wiring only) are armed merge-on-green; #10277 also carries merge-blocked from the
    semantic-proof guard: consume its checks once at a real boundary, and when
    ci-pack + ci-gate are green at 82812b81 remove merge-blocked with a visible
    comment naming this session and the green evidence; if hosted CI reds, repair on
    the branch (never relabel silently, #5291). Never self-approve or self-merge.
  - >
    4. Decide the B4 capture's durable home (unresolved above) with the Data OS /
    live-plane owners before any nightly wiring; preserve the amended B4
    preregistration (#7751 A1), its prospective population, H10 MAE endpoint, cost
    floor, multiplicity treatment, fixed looks and refusal handling unchanged.
  - >
    5. A2 PR #10289 (head ea8e3805, APPROVE-READY by independent review, draft, stacked on
    #10209's head da3a0451): nothing to do until #10209 lands; then retarget to main, consume
    one hosted CI run, arm merge-on-green (never self-merge). ci-authority/main's
    unsupported_base_ref is expected while stacked. Do not re-run the fabric operation.
  - >
    6. Entry Timing W2 is FROZEN (PR #10283, head 915e50b3, ready): consume hosted CI once;
    arm merge-on-green after the local contract-delta gate is green; the sweeper merges on
    green + reviewDecision. P looks begin only once the nightly producer commits every
    session (#10255) and the §2 floors are reached (300 units / 100 pairs / 5 full blocks of
    44); the single R look is no earlier than 2026-11-19 (PREREG.json r_maturity) and reads
    outcomes through the frozen estimator only; T3 is in the P family; the entitlement pin
    is EMPTY. A different study may not change this registration; #7751 A1 untouched. B-17
    34-session window census stays null - no favorable subset.
  - >
    7. Reference coverage (the whole W1 loss): ROUTED 10-31 by a
    HANDOFF_SOURCE_LINK_V1 comment on program issue #6805 to the Data OS owner role
    of scripts/build_security_master.py / the membership ingest (source PR #10277);
    delivery is not pickup — never force ticker matches or accept a later snapshot
    for historical sessions; consume the owner's return on #6805 once.
do_not_redo:
  - V4 waves 0A, 0B, A1, B1, D1 and Entry Timing W0 are DONE (do not reopen).
  - "PR #9556's inline carve in the `collect` job is accepted; #10255 does not touch it."
  - The B1 identity-join investigation (suppressions = reference coverage), now measured in PR #10277 (0 rows resolvable at their session).
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

The B4 seam investigation found no lost legitimate opportunity in the identity join,
and the Entry Timing W1 waterfall (PR #10277) measured it: of 62,500 IDENTITY_UNRESOLVED
rows, none was resolvable by a reference already ingested on its session; 11,153 became
resolvable only after later ingests (lawful as-known refusals) and 51,347 are tickers no
current reference knows. The seam itself is bound in PR #10267 (two independent review
rounds; REVISE → APPROVE-READY; armed merge-on-green at 750dd2c2). The capture's durable
home is still an unmade design decision (unresolved above), so no nightly is wired.

Second segment (same session, after context compaction): W1 went through three
independent review rounds — the round-1 finding that mapped turn_watch rows were
binned by their trigger date, not by the session the document was read, was repaired
by recovering each row's document session from its source receipt over the full git
history of the turn_watch documents (54 blobs, 100% recovery) — and is armed at
d03acfd0. The #10255 contract-delta red was a manifest gap (a new suite no job ran)
and is wired into push-retry-policy at 6454a74a. The W2 design registration's first
review showed its incumbent proxy (first curated-tier stamp) was a universe, not an
admission; revision 2 (549d416f, PR #10283) uses the BUY-lane placement, an
intention-to-treat primary, the existing grade producer's next-close fill on the
pinned yahoo close panel, declared identity join and knowability rules, and W2's own
futility rule. Everything here is DELIVERED at most; nothing is merged, frozen or
production-proven.

Third segment: #10255's fresh round-2 review returned APPROVE-READY (nits deferred)
and it is armed beside #10267 and #10277; all three sit UNSTABLE while ci-pack runs,
owned by the sweeper. The W2 round-2 review rejected the intention-to-treat primary
as a selection contrast and found BUY-lane coverage gaps inside the decision window,
so a census v3 was built on the freeze basis (W1 r3 receipt sessions, VendorAliasTable
join, NYSE sessions, producer-health coverage, a commit walk for as-committed
knowability) and revision 3 (8d86c28c) registers what that census shows is identified
in R: a per-protocol timing contrast on 96 admitted pairs, declared conditional with
its bias direction argued and a placebo negative control, while the policy contrast
becomes a P-only secondary. The reference-coverage finding was routed to the Data OS
owner role on #6805. Round 3 then rejected r3's conditional primary and placebo, and
census v4 — lane state from first-commit blobs, a security-first join, a document
commit walk — showed that HEAD's healed stamps overstate the practised lane, that every
exact R pair has a pre-window gap, and that the lane admitted on the discovery session
itself in 15 of 26 exact pairs. Revision 4 (c38416ae) therefore registers the
implementable policy contrast as the P-only primary under three recorded adjudications,
with the timing contrast as a guard. Round 4 returned REVISE (dependence between
overlapping holds; a code/prose lane-state mismatch whose "59 rows / 07-31" evidence was a
July-walk artifact); census v5 confirmed the reviewer (154 HEAD-only BUY rows from the
09-14 and 10-19 heals, 07-31 healthy) and revision 5 (438b1ac4) registers a block
bootstrap with session floors, one heal rule, a T0 lower bound and a binding timing
guard; round 5 returned REVISE (block too short, floors in units not blocks, bot clock,
anchor gates on T1, unpinned walk) and revision 6 (2d81bf31) answers it with a 44-session
block, full-block floors, the more conservative of two bounds, a server-witness arrival
clock and a T1 that is never anchor-gated; rounds 6 and 7 returned REVISE (no blocker)
and revision 8 (51ea5382: +1-clock readouts on every deciding P look, census --main-sha
with the pinned re-run committed, tested estimator module) PASSED round 8 and is FROZEN at
7cdea891 (PREREG.json; T3 in the P family; R look no earlier than 2026-11-19; PR #10283
ready, CI pending). The A2 preflight patch's carrier (Draft #10289, stacked on #10209) is
APPROVE-READY at ea8e3805 after three review rounds and waits only for #10209;
ci-authority rejects the non-main base as expected. #10277's contract-delta red is repaired at
82812b81 (ci-pack running; merge-blocked stays until green). Still nothing merged,
frozen or production-proven.

Canonical sources: completion brief and census at e757498822a2 (Draft #10242),
recovery carrier #10174 (29cfb98b), program issue #6805 (comment 6539985230), shared
R7 issue #6817, original R6 delegation root prophet-us-fable-meta-ceo-20260923-001.
