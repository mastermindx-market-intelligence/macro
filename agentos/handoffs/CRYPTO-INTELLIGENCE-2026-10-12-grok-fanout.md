---
workstream: "WS:CRYPTO-INTELLIGENCE"
session: claude/ssd-crypto-intelligence-fable-3a13af-89a84c9617e3659b
model: fable
ended_because: complete
mission: >
  Chairman order 2026-10-11 (21:04 PDT): initiate the Governed Crypto Intelligence + Bitcoin
  Vector program from the Crypto_Intelligence_Fable_Masterplan_2026-10-11 zip; for two hours
  (until 10:54 PST = 05:54Z 2026-10-12) run Opus sub-orchestrators that drive Grok CLI and GLM
  lanes on the ubuntu hosts over SSH with NO native Claude labor subagents; afterwards continue
  via the Mastermind fabric or Opus orchestrators over the fabric. Deliverable: the acceptance
  matrix A01-A40 program (T01-T24) actually advanced on GitHub, not planned.
state_before: >
  The only candidate was Sol's DRAFT PR #8050 (branch sol/crypto-vector-r2-20260926, head
  fd8095012e91, merge-base 7150f29a7653, 704 files of which 424 research/crypto_science
  evidence + 218 mockups + 27 CRYPTO_SCIENCE_R* docs are evidence, not code), last updated
  2026-10-03, 2,785 commits behind origin/main, zero comments, no labels, autoMerge null.
  #7645 (Market Board accessibility) was OPEN ready; #8880 was the masterplan draft. Agent OS on
  main held WS-CRYPTO-INTELLIGENCE, DEC-CRYPTO-H5-BTC-BUDGET-AUTHORITY,
  DSC-CRYPTO-H5-BYPASSES-BTC-DECISION and four 2026-08 handoffs; DEC-CRYPTO-VECTOR-R2-20260926
  existed only on #8050's head. No lane had touched the program since 2026-10-03. Grok CLI was
  signed in on ubuntu0/1/2/3 and NOT on mb or m1; mini2 was below the GLM storage floor.
changed:
  - path: https://github.com/mastermindx-market-intelligence/macro/pull/8901
    what: >
      NEW draft PR "crypto: R2 candidate source split from #8050 (fd8095012e91) on current
      main" opened by Grok lane cx-t01b on branch claude/cx-t01b-20261012, head 0dc4915da247 at open, fast-forwarded to 7a47b4149bac by lane cx-t01c (restored the 10
      R2 study/reference paths the 13 test files import; 42 files), parent eaec265515a0.
      At open: 32 files = the 31 R2 source/test/agentos paths byte-identical to
      fd8095012e91 plus three hand-applied .github/ci/legacy-jobs.yml hunks. Carries
      DEC-CRYPTO-VECTOR-R2-20260926 (new), DEC-CRYPTO-H5-BTC-BUDGET-AUTHORITY and
      WS-CRYPTO-INTELLIGENCE edits from the R2 head. Marked READY by the seat at 05:25Z (no Sol objection on #8050 at that time).
      Seat heal commit 3b399fa364f3 (06:4xZ) cured the PR's own contract-delta red: new
      `crypto-vector-r2-organs` job (gate code, scope exclusive, 360-path measured closure,
      one packed pytest step) owns the nine R2 suites that unrun-vector-dsr (gate data,
      dark on every PR — T23 pre-review #8939 BLOCKER B1) had carried; that run line is
      back to main's; engine/btc_intraday_cvd.py added to nw-lobe-unfreeze paths;
      CURATED_EXCLUSIVE registered; tests/test_vector_r2_frontdoor.py's wiring pin
      repointed at the new job and asserting gate code. Unarmed, single writer.
  - path: https://github.com/mastermindx-market-intelligence/macro/pull/8050#issuecomment-6118002498
    what: >
      Seat custody notice on Sol's draft: names the seat session, states that the R2 source
      delta is being re-planted as a split PR on current main, that evidence/mockups are NOT
      carried, that #8050 itself is not modified/readied/labeled/armed/merged, and invites Sol
      to object in-thread before the split PR is marked ready.
  - path: agentos/discoveries/DSC-HOMEBREW-BASH-53-HEREDOC-WRITE-DEADLOCKS-AN-SSH-LAUNCHER.md
    what: >
      New landmine record: `bash ./g2lane.sh` under Homebrew bash 5.3.9 hangs in heredoc_write
      before ssh is exec'd; `/bin/bash … </dev/null` launched 20/20 lanes.
  - path: agentos/handoffs/CRYPTO-INTELLIGENCE-2026-10-12-grok-fanout.md
    what: This record.
  - path: "scratchpad $S/g2/ (NOT committed: g2lane.sh, watch.sh, waitfor.sh, common_header.md, missions/, missions2/, prompts/, lanes_wave1.tsv, launch*/ logs, results/)"
    what: >
      The direct Grok lane kit. One launcher per lane over ssh (worktree ~/g2/wt/<label> off
      fresh origin/main, sparse, grok-4.7, 200 turns, reasoning high, bypassPermissions), one
      local watcher that copies each lane's RETURN packet to results/<label>.result.md. 37
      lanes registered in lanes_wave1.tsv (cx-t01 cx-t01b cx-t02 cx-t11 cx-t06 cx-t07 cx-t21 cx-t08 cx-t18 cx-r15 cx-t05 cx-t03 cx-t09 cx-t04p cx-t10p cx-t13p cx-t12p cx-t15p cx-t16p cx-t20p cx-t01c cx-t14p cx-t17p cx-t23p cx-t19p cx-t22p cx-t24p cx-t02-r2 cx-t11-r2 cx-t21t cx-t12t cx-t15s cx-t16b cx-t18b cx-t13p-r2 cx-t20w cx-t08rr); orchestrators appended their
      own follow-on rows to the same register. The kit is reproduced in this record's body because the
      scratchpad does not survive the session.
verified:
  - claim: "#8901 head 0dc4915da247 carries the 31 R2 proof paths byte-identical to fd8095012e91"
    command: "for p in $(git diff --name-only 7150f29a7653 fd8095012e91 -- collectors engine scripts templates tests site agentos); do git diff --quiet fd8095012e91 0dc4915da247 -- $p || echo DIFFERS $p; done"
    result: "no DIFFERS lines; PATH_COUNT=31 (lane cx-t01b packet, re-checked by gh pr view 8901 --json files: 32 files incl. .github/ci/legacy-jobs.yml)"
  - claim: "#8901's 13 test files are red on the split head because the R2 study modules are absent"
    command: "python -m pytest tests/test_btc_impulse_falsifier.py tests/test_crypto_wave2.py <… the 13 R2 test files> -q -p no:cacheprovider --tb=line"
    result: "131 failed / 260 passed; 63 ModuleNotFoundError research.crypto_science, 60 missing research/crypto_science/r12/reference_cvd_before_price_guard.py.txt, remainder needs_full_checkout data/ reads"
  - claim: "All 20 wave-1/wave-2 Grok lanes launched on four hosts under the /bin/bash launcher"
    command: "grep -h LAUNCHED $S/g2/launch2/*.log $S/g2/launch3/*.log | wc -l"
    result: "20 (ubuntu0: t01 t01b t02 t11 t12p t15p; ubuntu1: t08 t18 r15 t16p t20p; ubuntu2: t03 t09; ubuntu3: t06 t07 t21 t05 t04p t10p t13p)"
  - claim: "ubuntu2 could not reach github.com for two consecutive launcher attempts at 04:4xZ, so cx-t05 was re-routed to ubuntu3"
    command: "grep -E 'Failed to connect|promisor|rc=' $S/g2/launch3/cx-t05.log"
    result: "two 'Failed to connect to github.com port 443 after 13xxxx ms', one 'could not fetch … from promisor remote', rc=8; relaunch on mmx-ubuntu3 printed LAUNCHED pid=988257"
  - claim: "Agent OS validates with the new discovery record staged"
    command: "python3 scripts/agentos.py validate"
    result: "0 error(s); discoveries file count 504 (ls agentos/discoveries/DSC-*.md | wc -l)"
  - claim: "#8901 head 7a47b4149bac (after cx-t01c) still carries the 27 collectors/engine/scripts/templates/tests proof paths byte-identical to fd8095012e91, and the only path main has also moved since merge-base eaec265515a0 is .github/ci/legacy-jobs.yml"
    command: "git fetch origin claude/cx-t01b-20261012; H=$(git rev-parse origin/claude/cx-t01b-20261012); for p in $(git diff --name-only 7150f29a7653 fd8095012e91 -- collectors engine scripts templates tests); do git diff --quiet fd8095012e91 $H -- $p || echo DIFFERS $p; done; MB=$(git merge-base origin/main $H); comm -12 <(git diff --name-only $MB origin/main | sort) <(git diff --name-only $MB $H | sort)"
    result: "proof paths checked=27 differs=0; overlap = .github/ci/legacy-jobs.yml (seat, 2026-10-12 05:33Z)"
  - claim: "cx-t01c turned #8901 green except sparse-only data/ and site/ cases"
    command: "lane cx-t01c RETURN packet: pytest on head 7a47b4149bac in its sparse worktree"
    result: "383 passed / 8 failed, all 8 needing data/ or site/ (omitted in sparse trees); .github/ci/legacy-jobs.yml untouched by the lane"
  - claim: "Seat heal head 3b399fa364f3 introduces no contract-delta finding and leaves the packing probes at their base readings"
    command: "python3 scripts/check_contract_delta.py --base origin/main; python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12 --validate-only; python3 -m pytest tests/test_ci_pack.py -k 'exclusive or packing' -q"
    result: "contract-delta: 0 introduced, 31 inherited (base b36f30e65580, 330 s); Validated 286 legacy jobs; 25 passed + the inherited curated_exclusive_scopes_cover_their_own_import_closure misses (byte-identical on main); probes index.html 5,782 / build_free_content 5,585 / plan_book 5,545 = base, breaches []"
  - claim: "The nine R2 suites pass under the new job's install line alone"
    command: "python3 -m venv $S/venv-r2 && pip install <the job's install line> && python -m pytest <the nine suites> -q"
    result: "269 passed, 1 failed = sparse-only site/vector_chart.js read (8 passed with the tracked blob materialized via git show)"
  - claim: "GLM fabric lanes during the window: one DELIVERED, two REFUSED, none STARTED beyond the delivery"
    command: "orchestrator RETURN packets $S/orch/orch-a/RETURN.md and $S/orch/orch-b/RETURN.md + glm.out"
    result: "ORCH-A attempt 1 DELIVERED rc=0 glm-5.3-flash (40 acceptance rows, 25 covered); ORCH-A attempt 2 REFUSED rc=78 host mb account_credential_unavailable; ORCH-B single attempt REFUSED LOCAL_SEAT_REMOTE_REQUIRED host=m2 pool=glm-codex"
unverified:
  - claim: "Homebrew bash alone (without the stdin redirect) reproduces the heredoc deadlock"
    what_would_verify: "/opt/homebrew/bin/bash ./g2lane.sh … </dev/null from a Bash-tool shell — hang isolates the interpreter, success isolates stdin"
unresolved:
  - "Sol objection window on splitting #8050: none posted before the 05:25Z ready act; re-read the #8050 thread (gh pr view 8050 --comments) immediately before the merge act."
  - "mb and m1 Grok CLI are not signed in (operator act); mini2 is below the 50 GiB GLM storage floor (expect STORAGE_GUARD_LOW_SPACE)."
  - "ubuntu2's GitHub reachability is intermittent (two 135 s connect failures, then HTTP 200 in 6.4 s); treat a single failure there as transient and a second consecutive one as a re-route."
  - "The 424-path research/crypto_science evidence tree, 218 mockups and 27 CRYPTO_SCIENCE_R* docs stay on #8050 until a separate evidence PR exists; #8050 remains draft and unmodified."
next_actions:
  - "DONE 2026-10-13T03:48:43Z: #8901 squash-merged by hand as 0918bc8c7c69ba4db36c88bc8874da671c3f0572 (head 2a0ea6f74971); landed bytes verified (52 paths, 0 blob mismatches vs origin/main; crypto-vector-r2-organs registered in legacy-jobs.yml and tests/test_vector_r2_frontdoor.py). PRODUCTION_PROOF owed: covering render.yml 38343462455 / engine-render 38343462452 at the merge sha, then https://www.mastermind-x.com/crypto.html + vector.html and /opt/macro/site bytes."
  - "Seat records PR off fresh origin/main after #8901 lands: this handoff + the heredoc DSC + WS-CRYPTO-INTELLIGENCE status/next_action + t23p R2 fix in DEC-CRYPTO-H5-BTC-BUDGET-AUTHORITY (the build_crypto bullet must say it reads the cockpit receipt's `decision` projection written by build_vector — it never builds a DecisionState; tests/test_crypto_wave2.py::test_h5_build_consumes_cockpit_decision_without_recomputing_authority pins that) + cite DEC:CRYPTO-VECTOR-R2-20260926; validate; ship."
  - "Lane integration (seat as single writer, one PR at a time, each rebased on post-#8901 main with its candidate-base commit dropped), ORCH-B order: #8937 t05 -> #8913 t02 -> #8911 t11 -> #8927 t13p -> #8915 t03 -> #8924 t09 -> #8914 t12p -> #8912 t15p -> #8933 t14p -> #8931 t17p -> #8907 t16p -> #8947 t16b; then ORCH-A's #8904 t21(+t21t), #8917 t04p, #8934 t22p, #8939 t23p, #8956 r15fix; ORCH-C's roster on its return. Patches under research/crypto_science/patches/ apply in the ORCH-B table order (t09's two need -p0); remove each paired strict xfail marker in the same commit. The crypto.html.j2 / vector.html.j2 patches are user-facing: render + dark/light x EN/ZH evidence + designer review before merge."
  - "ORCH-A follow-ons: re-cut the cx-r15fix patch (#8956) against post-merge scripts/build_vector.py (fails at hunk @206 on #8901's version) together with a vector.html.j2:600 null guard; correct the false 'stacked on #8050' lines in the #8939 and #8956 bodies before readying them; send t23p R3-R9 (R4 build_crypto.py:345 unknown stance painted bull first) to ORCH-C; an R15 MAJOR-1 lane on post-merge main; the pre-existing dark suites test_crypto_wave2/wave3/cockpit_contract stay on the data gate (not B1) and want their own code-gate owner."
  - "Report operator items once: mb and m1 Grok CLI not signed in; mini2 below the GLM storage floor; mmx-ubuntu3 carries a stray /home/ubuntu2 directory created by lane cx-t05."
  - "Chairman 06:30Z 2026-10-12: Grok pool refreshed, no rush to spend it; revert to normal subagent-fabric orchestration. Chairman ~02:30Z 2026-10-13: the seat acts as Fable Meta-CEO end to end; Opus suborchestrators drive the m2 subagent fabric (NOT the executive plugin) to spawn operators who spawn workers; the seat may also delegate straight to the fabric. Running Grok lanes are never killed; the Grok CLI kit stays a fallback when the fabric has no eligible host."
  - "Separate evidence PR for the research/crypto_science tree from fd8095012e91 once the source split is live (T01 recommendation 4)."
do_not_redo:
  - "Never merge, ready, label, arm, rebase or force-push #8050 / sol/crypto-vector-r2-20260926 — the split PR #8901 is the carrier; the T01 read-only recovery (cx-t01 packet) is settled: do not re-run it."
  - "Never re-spawn the three Opus orchestrators (ids in the seat's memory file); continue them with SendMessage only."
  - "Never launch a Grok lane over an EXISTS worktree (~/g2/wt/<label>) — g2lane.sh exits 4; pick a new label."
  - "Never invoke the launcher as `bash g2lane.sh` on this Mac; always `/bin/bash $S/g2/g2lane.sh <alias> <label> <prompt> grok-4.7 200 yes high </dev/null`."
  - "Mastermind PRs #1337 (active-Stop MiniMax proof — do not rerun), #633 (Auth0 DCR EFFECT_UNKNOWN — never repeat DCR or bypass OAuth) and #1344 (preserve native parent and Executive boundaries) are untouchable constraints from the Chairman's order."
  - "Standing exclusions: no options engine, Grey Deer, Market OS, Prophet, GMI, single-name equity, aggregate risk/flow score, trade sizing or LLM-originated signal work inside this program; R1-R9 stay unpromoted."
  - "Never push ORCH-A's side branch claude/cx-t01d-20261012 (1f7ecd1d) onto #8901: it repairs B1 by adding the suites to conviction-profile while keeping them on unrun-vector-dsr, so the probe breach the red was about stays. Superseded by the seat heal 3b399fa364f3, which already carries its R1."
danger_areas:
  - "A push onto an armed PR can land after the sweeper's merge with every PR field reading success — arm LAST, and verify landed bytes against a freshly fetched origin/main, never against the PR object."
  - "#8901 already edits agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md and both crypto DECs; a seat records PR that touches WS before #8901 lands will conflict."
  - "Lane worktrees and the seat worktree are sparse (data/, site/, mockups/, verify_shots/ omitted): a write into an omitted tree truncates the committed artifact, check_template_site_sync REFUSES, and tests marked needs_full_checkout fail as artifacts, not regressions."
  - "The 13 R2 test files import research.crypto_science study modules — carrying tests without the 8 modules + the r12 reference file is a guaranteed red; carrying the whole 424-path tree is a 1,080,000-line evidence diff that does not belong in a source PR."
  - "ubuntu2 and ubuntu3 ran at load 31-34 on 32 cores with 7-9 concurrent lanes: pytest there is slow, not broken; route repairs to ubuntu0/ubuntu1."
  - "tests/test_vector_r2_frontdoor.py pins all nine R2 suites onto ONE pytest step of crypto-vector-r2-organs and asserts gate code: splitting the step, renaming the job, or moving a suite back to a data job fails the pin by design."
prs: [8901, 8050, 7645, 8880, 8904, 8907, 8908, 8909, 8910, 8911, 8912, 8913, 8914, 8915, 8916, 8917, 8924, 8926, 8927, 8931, 8932, 8933, 8934, 8935, 8937, 8939, 8947, 8956]
decisions: ["DEC:CRYPTO-H5-BTC-BUDGET-AUTHORITY", "DEC:CRYPTO-VECTOR-R2-20260926"]
discoveries: ["DSC:HOMEBREW-BASH-53-HEREDOC-WRITE-DEADLOCKS-AN-SSH-LAUNCHER", "DSC:CRYPTO-H5-BYPASSES-BTC-DECISION"]
---

## Records carried by #8901, not by this PR

DEC-CRYPTO-VECTOR-R2-20260926 exists only on the R2 head fd8095012e91 and on #8901's branch; it is
not cited in this record's frontmatter because the Agent OS validator resolves references against
the tree this file lands in. Cite it as DEC:CRYPTO-VECTOR-R2-20260926 once #8901 has merged.

## Topology actually run (2026-10-12 04:20Z → )

Fable seat (this session) → three native Opus orchestrators spawned as
`Agent(subagent_type='orchestrator', model='opus', run_in_background=true)` with the
fable-mode skill directive, `ROUTE: orchestration`, `WHY OPUS: Chairman 2026-10-12 standing
authorization`, the seven-point FABRIC-ONLY training block and a seat override making direct
Grok CLI lanes the authorized labor path → Grok CLI lanes over ssh. Orchestrators spawn no
native children; seat-only acts (carrier posts, ready/labels/merge, reviews, holds) stay with
the seat. ORCH-A = integration (t01, t01b, t01c, t21, r15, t04p, t22p, t23p); ORCH-B = sources
and science (t02, t03, t05, t09, t11, t12p, t13p, t14p, t15p, t16p, t17p); ORCH-C = product
and decision (t06, t07, t08, t18, t10p, t19p, t20p, t24p).

## The lane kit, reproducibly

- Hosts: ssh aliases `mmx-ubuntu0` (user ubuntu0), `ubuntu1` (user longr), `ubuntu2`
  (user ubuntu2), `mmx-ubuntu3` (user ubuntu3). Each has `~/lanes/repos/macro` (clone),
  `~/g2/venv`, Grok CLI signed in, gh on the shared fleet token, git identity
  chriswong6031-creator.
- Per lane: `scp` the prompt to `~/g2/prompts/<label>.md`; remote script (quoted here-doc to
  `ssh … bash -s`) fetches origin/main, `git worktree add --detach --no-checkout ~/g2/wt/<label>`,
  sparse-checkout `/* !/data/ !/site/ !/mockups/ !/verify_shots/`, then
  `nohup grok --model grok-4.7 --max-turns 200 --reasoning-effort high` (bypassPermissions) with
  the prompt as input, stdout to `~/g2/out/<label>.log`, exit code to `~/g2/out/<label>.rc`,
  and the lane's own RETURN packet to `~/g2/out/<label>.result.md`.
- Prompt = `common_header.md` (program context, candidate-base recipe, hard rules, RETURN
  contract with `## STATUS / RESULT / EVIDENCE / GAPS / DEVIATIONS`) + one mission file.
  Write lanes do the CANDIDATE BASE step first: branch `claude/<label>` off origin/main,
  `git diff 7150f29a7653 fd8095012e91 -- collectors/ engine/ scripts/build_crypto.py
  scripts/build_vector.py templates/crypto.html.j2 templates/vector.html.j2 tests/ | git apply
  --3way --index`, one base commit. Shared files (build_crypto/build_vector/the two templates/
  .github/agentos/data/site) are never edited by lanes — they write
  `research/crypto_science/patches/<LABEL>__<basename>.patch` for the seat to apply.
- Watcher: one local loop re-reads `lanes_wave1.tsv` (label, alias, remote result path) each
  pass, so lanes can be appended or re-routed live; a finished lane (`.rc` present and
  `.result.md` present) is copied to `results/<label>.result.md` plus `.logtail` and `.done`.

## Orchestrator returns (ORCH-A 06:3xZ, ORCH-B 06:1xZ, ORCH-C interim verdicts to 06:17Z then died 06:41Z; ORCH-D Phase 0 03:17Z 10-13)

ORCH-A (integration): t01 census PASS; t01b/t01c PASS = #8901 @7a47b414 (383 passed / 8 sparse-only);
t01d PASS on side branch claude/cx-t01d-20261012 @1f7ecd1d — NOT taken (see do_not_redo); t21 #8904
(+t21t @c6fc78d6: 19 passed, 5 strict xfail, enrolled on push-retry-policy); r15 read-only audit 3
MAJOR / 6 MINOR / 9 NOTE; r15fix #8956 @b4891adf PASS-with-conditions (patch cut against main's
build_vector.py, must be re-cut post-merge); t04p #8917 @1303e11f; t22p #8934 @c603e92f (3 patches
apply --check clean); t23p #8939 @7a93c063 pre-review: 1 BLOCKER (B1, healed by the seat), R1-R9,
N1-N7. Two A-numbering schemes exist (t23p's masterplan-line IDs vs the portable GLM/prep-map IDs) —
never cross-read them.

ORCH-B (sources + science): all 12 lane PRs PASS — #8937 t05 @96e03772, #8913 t02 @359efd9b (20 strict
xfail), #8911 t11 @910c3a99, #8927 t13p @2c4242f3, #8915 t03 @bfff0d2e, #8924 t09 @9f8c3366 (needs
#8901's R2 files), #8914 t12p+t12t @d7c6b586, #8912 t15p+t15s @1dbb08b1, #8933 t14p @d45d60c8, #8931
t17p @0596b3e0, #8907 t16p @7acf220a (doc only), #8947 t16b @6510acd0 (34 passed). Ten patch files
under research/crypto_science/patches/ apply cleanly in sequence on top of the t05 head (8 files,
+183/-37). No lane mocks the function it tests; t11 and t02 were repaired once each for test quality.

ORCH-C (consumers + design): did not return a packet — the agent died at 06:41Z 10-12 after its
interim verdicts file (scratchpad orch/orch-c/verdicts.md, reproduced here in substance). t08 #8910
PASS after repair at 8bc698c6bd37 (NYSE closures -> pending via lib/nyse_calendar, sign-agreement
attribution; the unattributed hero summary was left EMPTY pending seat copy); t18 #8908 census PASS;
t18b #8953 PASS re-stacked at b2cd9bf0cba5 (decision binding, single decision_page_as_of key); t20p
#8909 + t20w #8955 PASS at 140b7b3452aa (getAiContext attach, 10 passed / 2 skipped until the template
patch applies); t07 #8926, t10p #8916, t06 #8932, t19p #8946 PASS; t24p #8935 PASS after one repair at
55d5851f0f23. Stack-order finding: t18b must apply BEFORE t19p on vector.html.j2 (t19p fails at hunk
@490 otherwise); GLM on m2 refused `LOCAL_SEAT_REMOTE_REQUIRED` once and was not retried.

ORCH-D (integration, DIED 2026-10-13 ~04:18Z with a seat session restart that wiped the scratchpad before any lane/cx-int-* writer existed; Phase 0 verdicts below stand): Phase 0 ledger replays all 24 picked lane heads as patch files onto
113b990d9741 in three stacks — engine b03c87576b5d (t18, t08, t07, t06, t19p, t18b, t20w), science
774c0c7b2e1a (t16p, t11, t15p, t02, t12p, t03, t09, t13p, t17p, t14p, t05, t16b, t10p), governance
b92f72299a03 (t21t, t04p, t22p, t24p, t23p) — all CLEAN including the chained science-on-engine and
governance-on-chain merge-trees. r15fix #8956 is NOT picked: its build_vector.py hunk @206 fails on
#8901's version and is re-cut post-merge. Phase 1 (three integration PRs) starts only when the seat
sends the #8901 squash sha.

ORCH-E (integration successor, spawned 2026-10-13 04:4xZ): replays the 27 open DRAFT lane heads
(#8904-#8956, oids in the seat ledger) from GitHub onto fresh origin/main at or after
0918bc8c7c69 in the same three stacks, applies seat rulings R1-R8 below, re-cuts r15fix at the end
of the science stream, captures the engine-stream visual-evidence receipt on the m2 full checkout,
and opens DRAFT PRs on lane/cx-int-{engine,science,governance}-20261013 (lane/* so no ship-loop
hook pushes or arms them). Labor runs on the subagent fabric (remote_sub.sh GLM/Grok; local
sub.sh grok on m2), never native Claude children. Ledger: handoff kit orch/crypto/orch-e/.

## Seat rulings on the held integration patches (2026-10-13 03:4xZ, sent to ORCH-D)

- t18b #8953: ACCEPT every `data-decision-*` attribute (crypto `.desk-budget` + H5 section; vector
  `.hero-position-value`, `.overview-evidence .v`, S2 section). REJECT every visible raw-date
  injection (crypto `.desk-target` date span and the ` · date` suffix on `.exposure-big`; vector the
  date span inside `.hero-position-value`, the trailing date on `.overview-evidence .v`, the second
  `.decision-eyebrow` date div). A raw ISO date inside a hero numeral is a glance-tier violation and
  the date already renders in the canonical "Decision date" rows and `.asof-chip`. The binding test
  reads attributes only, so it is unaffected.
- t08 #8910: ACCEPT the nav/H3/eyebrow renames ("Subscriptions and supply / 申购与供应",
  "Subscriptions, supply, participation / 申购、供应与参与", "Stablecoin supply · 30D / 稳定币供应量 ·
  30日"), the cap-basis splice paragraph and aria copy. FILL the empty `notes["unattributed"]` hero
  summary with seat copy — EN "Bitcoin's own price and token supply moved against the class total.
  The total-cap change is not narrated as a bitcoin leg and is not a measured subscription." ZH
  "比特币自身的价格与代币供应量与总市值方向相反。此处总市值变化不归因于比特币，也不是已测量的申购。" — and
  assert non-empty in both languages.
- t16b #8947: ACCEPT engine/builder/tests; REJECT the template `lane-coverage` hunk as drafted (raw
  `path_momentum`/`path_risk` slugs and the internal phrase "display only, no authority" on a glance
  surface). Engine-only ships; a plain-word "Price path" row is a later designer packet.
- t19p #8946, t20w #8955: ACCEPT whole (null guards; brain attach with zero runtime style injection,
  `.vector-brain-error` styled in governed CSS only).
- t21t #8904: ACCEPT the `.github/ci/legacy-jobs.yml` registration in the governance stream, which
  therefore becomes the only authority-changing stream (clears only via a main-descendant ci.yml
  baseline).
- r15fix #8956: re-cut on the real #8901 head at the END of the science stream.
- Base correction: Phase-0 replays used 113b990d9741; the #8901 head is 2a0ea6f74971 and the Phase-1
  base is the squash sha on origin/main.
