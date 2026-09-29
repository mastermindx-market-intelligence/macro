---
workstream: "WS:RUNNER-FLEET-RESILIENCE"
session: "claude/macro-01-nightly-checkpoint-20260929 (worktree macro-01-nightly-checkpoint-5a8361)"
model: opus
ended_because: ci_handoff
mission: >
  MACRO-01 nightly checkpoint publication. Make the ordinary collection -> commit ->
  push -> build path advance the affected market source session and the served
  dashboard without manual rescue, after the 2026-09-25 night left a committed but
  unpublished checkpoint. Adopt the existing PR #8008 carrier rather than open a
  duplicate; reconcile it onto the current branch without overwriting unrelated
  workflow edits; keep the collect cap and the W2 timing argument synchronized; and
  explicitly assert that no comment or status promises a post-timeout salvage step
  that GitHub will never execute.
state_before: >
  PR #8008 existed on branch claude/prophet-delivery-nightly-collect-cap-20260925,
  raising `jobs.collect.timeout-minutes` 240 -> 300 and the W2 finish argument with
  it. Its stated mechanism was that a GitHub job-level timeout makes the
  `if: always()` / `if: cancelled()` tail unreachable, asserted in four prose sites in
  `.github/workflows/daily.yml` and pinned by three tests in
  `tests/test_daily_collect_commit_path.py`. `data/ops/nightly_timings/collect.jsonl`
  showed five recent nights between 220.1m and 242.5m against the 240m cap, four of
  them past the 85% tripwire. The 2026-09-25 collect job (107895940199) had committed
  the night's market data locally and never pushed it.
changed:
  - path: .github/workflows/daily.yml
    what: >
      `jobs.collect.timeout-minutes` 240 -> 300 and the W2 finish call `240` ->
      `300 240` (cap, then creep budget). Four prose sites rewritten off the false
      absolute onto the measured bounded-grace model, each citing BOTH job ids so a
      later reader can re-run the observation rather than trust the sentence. The
      push step renamed to `push market data (commit already local; alarm-bounded git
      ops)` so no step NAME promises the tail is guaranteed. No other job, trigger,
      concurrency group or step was touched.
  - path: scripts/nightly_timings.py
    what: >
      `cmd_finish` gained `warn_minutes`, defaulting to `cap_minutes`. The 85%
      tripwire and the row's new `warn_pct` measure against that basis; `pct_of_cap`
      still measures against the cap, so the existing ledger contract is unchanged.
      Rows carry `warn_minutes`; the dark path writes `warn_pct: None`. The tripwire
      annotation names both numbers when they differ ("240m creep budget (cap 300m)")
      and reads exactly as before when they do not. New `--warn-minutes` flag.
  - path: scripts/ci/nightly_timings_finish.sh
    what: >
      Accepts an optional second positional argument, the creep budget, and forwards
      it as `--warn-minutes` only when non-empty. A one-argument call is
      byte-identical in behaviour to before.
  - path: scripts/nightly_timings_report.py
    what: >
      Reads `warn_minutes` off the newest row and computes median/max/breaches
      against it, falling back to `cap_minutes` when absent so historical and
      backfilled rows render unchanged. The `cap` column is now `budget` and marks a
      split basis with a trailing asterisk.
  - path: tests/test_daily_collect_commit_path.py
    what: >
      The three pins were token-presence checks that an independent reviewer defeated
      with one-word rewrites; all three rewritten and a fourth added. `_SURVIVES` and
      `_BOUNDED` widened, `_collect_region()` slices only the `collect:` job, and
      `_comment_block_above()` now walks THROUGH blank lines so a blank line cannot
      orphan a comment from its step. The salvage pin is a positive pin: the block
      must carry both job ids and the exhausted-grace case, not merely lack a
      forbidden word. The W2 pin is unconditional - the previous `if` guard made it
      assert nothing when its own anchor moved.
  - path: tests/test_nightly_timings.py
    what: >
      The cap/argument lockstep test now tokenizes the finish call, requiring
      `toks[2] == str(cap)` and `0 < budget <= cap`, so cap and budget cannot drift
      apart or invert. Three tests added: the regression itself (229.4m at a bare
      300m cap is SILENT), the repair (229.4m at cap 300 budget 240 warns at 95.6%
      with both numbers in the annotation), and that omitting the budget preserves
      the historical behaviour exactly.
  - path: agentos/discoveries/DSC-A-JOB-TIMEOUT-RUNS-THE-ALWAYS-TAIL-INSIDE-A-BOUNDED-GRACE.md
    what: >
      NEW. The corrected runtime mechanism with both measured jobs, the null
      `started_at` tell, and why the false belief is harmful in both directions.
  - path: agentos/decisions/DEC-SPLIT-THE-CREEP-BUDGET-FROM-THE-SURVIVAL-CAP.md
    what: >
      NEW. Why the alarm basis is now separable from the kill point, the five nights
      a coupled raise would have silenced, and the four alternatives rejected.
verified:
  - claim: >
      A job-level timeout does NOT skip the always()/cancelled() tail; it runs the
      remaining steps inside a bounded grace of about five minutes. Job 105033526139
      hit its 240m cap at 04:48:55Z and still completed `push market data` at
      04:50:53Z and `salvage push` at 04:50:57Z.
    command: "gh api repos/mastermindx-market-intelligence/macro/actions/jobs/105033526139 --jq '.steps[]|select(.number>=31)|\"\\(.number) \\(.name) \\(.conclusion) \\(.started_at) \\(.completed_at)\"'"
    result: "31 push market data success 2026-09-17T04:47:31Z 2026-09-17T04:50:53Z / 32 salvage push success 04:50:53Z 04:50:57Z / job completed 04:51:54Z = cap+2:59"
  - claim: >
      The grace is bounded and the 2026-09-25 night exhausted it. Job 107895940199
      committed inside the grace, started its push at cap+2:32, and was killed at
      cap+5:00 with every later step never scheduled.
    command: "gh api repos/mastermindx-market-intelligence/macro/actions/jobs/107895940199 --jq '.completed_at, (.steps[]|select(.number>=30)|\"\\(.number) \\(.name) \\(.conclusion) \\(.started_at)\")'"
    result: "commit market data success 04:43:31Z->04:45:40Z; push started 04:45:40Z (cap+2:32); job completed 04:48:08Z = cap+5:00 exactly; steps 32-38 started_at null"
  - claim: >
      A bare 240 -> 300 cap raise silences the creep alarm on every night that
      justified it; the creep budget restores it.
    command: "python -m pytest -q tests/test_nightly_timings.py -k 'creep or silences or historical'"
    result: "4 passed - 229.4m is silent at a bare 300m cap, warns at 95.6% with budget 240, and a one-argument call is unchanged"
  - claim: >
      The four new pins reject each defeating rewrite and accept an innocent edit -
      a RED control replay, not a green-only run.
    command: >
      For each mutation: edit .github/workflows/daily.yml in place (the tests read
      that exact path), then
      `python -m pytest -q tests/test_daily_collect_commit_path.py -k "survives or salvage or w2_finish_comment or creep_budget"`,
      then `git checkout -- .github/workflows/daily.yml`. The six mutations were:
      (1) rename the push step to promise it outlives the cap; (2) rewrite the
      salvage comment as a false promise wrapping a literal disclaimer; (3) the same
      against the W2 finish comment; (4) drop the `240` creep-budget argument;
      (5) insert a blank line between a comment block and its step (INNOCENT);
      (6) unmodified head (CONTROL).
    result: "name-outlives rejected=True / salvage-false-promise rejected=True / w2-false-promise rejected=True / creep-budget-dropped rejected=True / blank-line-innocent rejected=False / unmodified-head rejected=False - the four attacks fail the pins, the innocent edit and the control pass"
  - claim: "The packet's own §5 verification matrix passes on head d1e53a094592."
    command: "python -m pytest -q tests/test_daily_collect_commit_path.py tests/test_nightly_timings.py tests/test_daily_et_gate.py tests/test_workflow_file_size.py tests/test_gh_annotation_line_start.py && git diff --check && bash -n scripts/ci/nightly_timings_finish.sh"
    result: "110 passed; git diff --check rc 0; bash -n clean"
  - claim: >
      The trend report is unchanged for rows written before the split, so no
      historical breach was erased by the new basis.
    command: "python3 scripts/nightly_timings_report.py"
    result: "collect still reads budget 240m, 96% max, 4 breaches, TRIPWIRE"
  - claim: >
      The reconciliation overwrote no unrelated workflow edit: no commit touched any
      of the six files on origin/main between the merge-base and now.
    command: "git log --oneline 2868086f84a2..origin/main -- .github/workflows/daily.yml scripts/nightly_timings.py scripts/nightly_timings_report.py scripts/ci/nightly_timings_finish.sh tests/test_daily_collect_commit_path.py tests/test_nightly_timings.py"
    result: "0 commits - zero base drift on the changed set"
  - claim: >
      The only red check on #8008 is base-side, not this head's: it fails identically
      on independent sibling PRs and its own payload says the authority change is
      allowed.
    command: "gh pr checks 8008 --json name,state; gh api repos/mastermindx-market-intelligence/macro/commits/<head>/check-runs --jq '.check_runs[]|select(.name|test(\"ci-authority\"))|.output.summary'"
    result: "ci-authority/codex/merge-queue-pilot fails on \"context_active\": false / \"inactive_base_context\"; same failure on #8201 and #8200; ci-authority and ci-authority/main pass on all three"
  - claim: >
      The 2026-09-29 US staleness is a DIFFERENT failure from the cap exhaustion and
      was preserved on #8164 rather than folded into this repair.
    command: "gh api repos/mastermindx-market-intelligence/macro/actions/runs/36566370352/jobs --jq '.jobs[]|\"\\(.name) \\(.conclusion) \\(.started_at) \\(.completed_at)\"'"
    result: "collect CANCELLED at 98.9m of a 240m cap, `run collectors` cancelled at 91.4m, `commit market data` SKIPPED, later steps scheduled and green. Every job >~90m cancelled, every job <=~23.5m green. Posted as issuecomment-5895187021."
  - claim: >
      The source-to-live chain is INTACT and the loss is entirely upstream of
      publication: the served Canada page matches the protected remote exactly. Both
      carry session 2026-09-25 while US carries 2026-09-28.
    command: "curl -s https://www.mastermind-x.com/canada.html | grep -oE 'as of 2026-[0-9-]+' ; git show origin/main:data/canada_stocks/latest.json | python3 -c \"import json,sys;print(json.load(sys.stdin)['date'])\""
    result: "served = 'as of 2026-09-25' (HTTP 200, 250,831 B); origin/main data = 2026-09-25; site/canada.html @origin/main = 14x '2026-09-25'; data/us_stocks/latest.json = 2026-09-28"
  - claim: >
      The CURRENT Canada staleness is NOT the cap exhaustion. The 09-26 nightly
      re-collected and pushed session 09-25, so that loss self-healed. The missing
      session is Monday 2026-09-28, lost to the 09-29 mass cancellation.
    command: "git log -10 --format=%H origin/main -- data/canada_stocks/latest.json | while read s; do git show $s:data/canada_stocks/latest.json | python3 -c \"import json,sys;print(json.load(sys.stdin).get('date'))\"; done"
    result: "last advance c7f88de510a5 on 2026-09-26 carrying session 2026-09-25; nothing since. Run 36566370352 on 09-29 cancelled collect at 98.9m of 240m with `commit market data` SKIPPED."
  - claim: >
      Canada session loss is CHRONIC, roughly one trading session in four, not a
      one-off. Sessions 09-14, 09-22 and 09-24 never appear as a published value.
    command: "for sha in $(git log -30 --format=%H origin/main -- data/canada_stocks/latest.json); do git show $sha:data/canada_stocks/latest.json | python3 -c \"import json,sys;print(json.load(sys.stdin).get('date'))\"; done | sort -u"
    result: "09-04, 09-08, 09-09, 09-10, 09-11, 09-15, 09-16, 09-17, 09-18, 09-21, 09-23, 09-25 - 09-14/09-22/09-24 absent (09-07 correctly absent, Labour Day). Bound: samples the 30 most recent commits touching that one file; WHY each session is missing is NOT established."
  - claim: >
      None of this alerted because the production freshness sentinel has no Canada
      surface at all - Canada is not stale, not blind, not indeterminate, it is
      unwatched.
    command: "grep -cin canada scripts/freshness_sentinel.py ; curl -s https://www.mastermind-x.com/live/staleness.json | python3 -c \"import json,sys;d=json.load(sys.stdin);print(d['ok'],d['stale_surfaces'],d['blind_surfaces'])\""
    result: "grep = 0. Live at 2026-09-29T17:42:11Z: ok=False, stale=['prophet_live'], blind=['entry_radar_live','prophet_us','us_standouts']. SURFACES registry = us_stocks/china/hub/r2_massive_stock_day/prophet_us/prophet_live/prophet_live_armed/cn_board_live/entry_radar_live/us_board_provisional/us_standouts."
  - claim: "The change touches no published market data and is therefore rollback-safe."
    command: "git diff --stat 2868086f84a2..HEAD -- data/ site/"
    result: "empty - 6 files changed overall, all workflow/script/test/records"
unverified:
  - claim: >
      That 300m is sufficient headroom for the collector's growth trajectory rather
      than only for its five observed nights.
    what_would_verify: >
      Ten or more consecutive nights of `data/ops/nightly_timings/collect.jsonl`
      after the merge showing elapsed minutes flat or falling against the 240m creep
      budget. The budget is the instrument for exactly this; until those rows exist,
      300m is containment sized at ~1.24x the worst COMPLETE observed path (242.5m on
      09-17 - the 245m figure often quoted is a kill point, not a finish).
  - claim: >
      That the ~5-minute grace is a GitHub-wide constant rather than something a
      runner or org setting can change.
    what_would_verify: >
      A third capped job on a different runner label showing the same cap+5:00 kill.
      Two observations on the same label is what exists. Nothing in the repair
      depends on the exact number - only on it being bounded and smaller than the
      ~10m market-commit-push band.
  - claim: "Who or what cancelled every long job in run 36566370352 on 2026-09-29."
    what_would_verify: >
      An actor in the run's own audit trail. Searched every transcript under
      ~/.claude/projects for the run id: 5 files matched, all observation, ZERO
      cancel invocations. That bound does NOT exclude a Codex or other-account
      session, a runner-host watchdog, or an operator acting outside this fleet's
      transcripts.
unresolved:
  - >
      The 2026-09-29 mass cancellation (#8164) is currently a LARGER constraint on
      freshness than the cap exhaustion this PR repairs, for Canada as well as US.
      MECHANISM NOW ESTABLISHED at step level, run 36511549800: `run collectors` was
      CANCELLED 02:16:29Z->03:47:56Z (91.45m) and `commit market data` was SKIPPED, so
      the 2026-09-28 session was lost at COLLECTION, entirely upstream of the
      checkpoint. The publication path this PR repairs was never reached and is NOT
      implicated - the commit gate refusing a partial collection, `published` staying
      unset, and `government_revenue_projection` + `capital_structure` skipping at
      exactly 03:50:23Z is the designed behaviour working. The three cancelled jobs are
      the three longest (97.2m/240, 96.3m/200, 118.8m/300 = 40-59% of cap) across TWO
      runners, while 14 jobs succeeded including `tech_lab_offrender` at 74.8m on the
      same mac-builder-5 AFTER both its cancels; the W2 rows read 40.3% and 41.1% with
      `bands:2` vs a healthy `bands:4`. Concurrency supersession and step-level timeout
      are both eliminated by config. A cap raise therefore cannot help this night, and
      the agent of the cancel is NOT established. See
      `DSC:THE-W2-LEDGER-DISCRIMINATES-A-CAP-KILL-FROM-A-FOREIGN-CANCEL`. Both failure
      modes are real; this PR fixes one. MERGING THIS PR CANNOT BY ITSELF MAKE CANADA
      CURRENT - do not report it as though it does. Acceptance requires the next
      natural nightly to complete publication inside the raised budget AND not be
      cancelled.
  - >
      Canada has no surface in `scripts/freshness_sentinel.py`, so a lost Canada
      checkpoint is reported as nothing at all. That is the detection half of the
      packet's Task 1 and it is NOT fixed here: adding a surface starts real paging,
      needs a TSX-calendar-free way to tell a closed market from a lost session (the
      repo has no TSX holiday table - sessions derive from yfinance price data), and
      deserves its own owner. Spawned as its own lane.
  - >
      #8008 is OPEN and awaiting its CI conclusion on head 17edf671b485. The independent
      opus reviewer APPROVED on d1e53a094592 (code identical to 732d3e8b55a1; the two
      later commits are the agentos records, a comment rewrap, the failed-push pin and
      the source/detection records), having replayed its
      own round-1 evasions against the new pins rather than accepting the summary. Its
      three residual nits were non-blocking; the cosmetic one is fixed. GitHub carries
      no formal reviewDecision because the review is a session-internal opus lane, not
      a GitHub reviewer - read `reviewDecision` before merging anyway, since a human or
      another session may have added one.
  - >
      `ci-authority/codex/merge-queue-pilot` is red on this head and on independent
      siblings for a base-context reason. It is base-side, but nobody owns healing it.
  - >
      The structural fix - trimming the collector workload so the cap is not the
      binding constraint - is untouched. The creep budget is the instrument that will
      say when that becomes urgent, not a substitute for it.
  - >
      The `engine` job is the SAME failure mode one job over and is closer to its cap
      than collect ever was: median 242.4m and max 289.6m against a 300m cap, with 7 of
      the last 20 nights past the 255m tripwire. Its inline cap comment still asserts
      "the honest warm floor is ~105m" and "the next cap move on a healthy fortnight is
      DOWN, not up", which the ledger refutes. Deliberately NOT fixed here: daily.yml is
      a serialized shared composition surface and MACRO-01's scope is the collect
      publication path. It needs its own lane.
  - >
      THIS PR'S OWN `ci-pack-11` RED WAS A DOWNSTREAM SYMPTOM OF THE SAME UNPUBLISHED
      NIGHT, and it is healed here. The failing job is `market-os-macro-suite-pages`
      (named by the check annotations, not the pack index) and it failed on exactly ONE
      test: `tests/test_macro_command_p4_copy.py::test_credit_funding_e4_needs_the_capture_fixture_flag`
      - `1 failed, 545 passed, 8 skipped`. That test fabricates a `capital_structure`
      view to prove E4 is fixture-gated, but builds it from
      `builder.read_workspace(DATA_ROOT, page)`; `capital_structure` currently reads
      `STALE_SOURCE` BECAUSE the 2026-09-29 collection was cancelled and its step
      skipped at 03:50:23Z, so the test's NEGATIVE control (`empty is None` with the
      fixture flag OFF) saw E2 rather than None and graded the bake instead of the gate.
      CORRECTED by the exact-head review: E4 OUTRANKS E2, not the reverse -
      `build_macro_suite_pages.py:1281` checks the withheld gate first and returns E4,
      reaching the E2 path only in its `else`, so E4 fires even on a stale base. The fix
      is unchanged and correct; only its stated rationale was inverted. Healed with the idiom #7790 established for the two sibling tests it
      missed: pin `availability.state = "CURRENT"` on the fabricated workspace. RED
      controls both fire - flipping the pin to `STALE_SOURCE` fails, and dropping
      `allow_empty_state_fixture=True` fails, so the pin is load-bearing and the E4 gate
      is still genuinely asserted. GREEN: CI's exact step-4 command is `rc=0,
      554 passed` locally, matching CI's own 545+1+8=554 total. The red was NOT
      attributable by the standing sibling-head rule - see
      `DSC:A-GLOBAL-INVALIDATOR-PR-CANNOT-USE-SIBLING-HEAD-EXONERATION` - because pack
      membership is recomputed per head from its changed-file scope, so sibling #8205's
      green `ci-pack-11` never contained the failing job at all. Reachability, not
      similarity, settled it: importing the failing module loads 307 modules and NONE of
      this PR's changed modules is among them.
next_actions:
  - >
      Open a lane for the `engine` cap comment and its creep. Verify first with
      `python3 -c` over data/ops/nightly_timings/engine.jsonl - median 242.4m, max
      289.6m, cap 300m - then decide whether engine wants the same creep budget or a
      workload trim. The reviewer's read was that engine is already tripping its
      tripwire, so a budget would add nothing and the trim is the real lever.
  - >
      Merge #8008 on CONCLUDED checks only - never mid-flight - excluding the known
      spurious "Workers Builds: macro" and the base-side
      `ci-authority/codex/merge-queue-pilot`. Use `--match-head-commit`; read
      `reviewDecision` in the same invocation as the merge.
  - >
      After the merge, observe ONE complete natural authoritative cycle and trace it
      end to end: collected session -> checkpoint commit -> protected remote bytes ->
      generated artifact -> served Canada page. A green workflow run is CI, not
      PRODUCTION_PROOF.
  - >
      Then confirm the next natural affected-market update advances normally. Until
      both are observed the honest terminal state is BUILT_NOT_PROVEN.
  - >
      Watch `data/ops/nightly_timings/collect.jsonl` for the first post-merge rows and
      confirm `warn_minutes: 240` and a `warn_pct` near 95% on a ~229m night. A row
      with `warn_minutes: 300` means the second argument was lost in a later edit.
  - >
      Carry the 36566370352 cancellation on #8164 as its own lane. Identifying the
      canceller needs a surface outside this fleet's transcripts.
do_not_redo:
  - >
      Do NOT re-assert that a job-level timeout skips the always()/cancelled() tail.
      It is measured false on this exact job and cap (DSC:A-JOB-TIMEOUT-RUNS-THE-
      ALWAYS-TAIL-INSIDE-A-BOUNDED-GRACE). Four prose sites in daily.yml were rewritten
      off that claim and a test now rejects its return.
  - >
      Do NOT raise a nightly cap without passing a creep budget as the second argument
      to nightly_timings_finish.sh. `tests/test_nightly_timings.py` pins that a bare
      raise silences the alarm, and `test_the_creep_budget_is_pinned_below_the_raised_cap`
      fails if the argument is dropped.
  - >
      Do NOT write these pins as token-presence checks. A reviewer defeated all three
      earlier ones with single-word rewrites ("outlives"; a literal disclaimer wrapped
      inside the opposite claim; an `if` guard that made the third assert nothing).
      The current pins are positive: the block must carry the measurement, not merely
      lack a forbidden word.
  - >
      Do NOT treat the salvage push as dead code. It is a real belt that demonstrably
      rescued 2026-09-17. It is also not a budget - it has a hard ceiling smaller than
      the ~10m market-commit-push band, which is why 09-25 was not rescued.
  - >
      Do NOT diagnose the 2026-09-29 outage as a sick runner. `mac-builder-light` ran
      10 green jobs in that same run. The signature is duration-based, not host-based.
  - >
      Do NOT open a second PR for this repair. #8008 is the adopted carrier and the
      reconciliation is complete against a zero-drift base.
danger_areas:
  - >
      `.github/workflows/daily.yml` is a GLOBAL CI invalidator - editing it forces the
      full suite, so every push here costs a complete run. It is also a shared
      composition surface: this repair serializes ahead of MACRO-02's operation clock
      and MACRO-04's producer guard. Re-fetch and re-read before any further edit.
  - >
      The `_SURVIVES` regex has NO negation handling. A correct sentence containing
      "survives" in a negated form is rejected exactly like a false promise. Write
      around the word - the corrected comments say "clears the whole publish path" and
      "is NOT reachable once that grace is spent" for this reason.
  - >
      Two `gh pr edit --body-file` calls inside one `ci-authority` run's lifetime make
      the second CANCEL the first, leaving an armed PR red forever over a run that did
      nothing. Exactly ONE body edit was made this session; every later carrier write
      is a comment.
  - >
      `pct_of_cap` must keep measuring against the cap. Repointing it at the budget
      would silently rewrite the meaning of every historical row in the ledger.
      `warn_pct` is the new field precisely so the old one did not have to move.
  - >
      This is a sparse worktree. `data/` and `site/` are omitted, so an unredirected
      write into either TRUNCATES the committed artifact rather than extending it.
      Never `git add -A` an unexpected `data/` or `site/` diff here.
prs: [8008]
decisions: ["DEC:SPLIT-THE-CREEP-BUDGET-FROM-THE-SURVIVAL-CAP"]
discoveries: ["DSC:A-JOB-TIMEOUT-RUNS-THE-ALWAYS-TAIL-INSIDE-A-BOUNDED-GRACE"]
---
