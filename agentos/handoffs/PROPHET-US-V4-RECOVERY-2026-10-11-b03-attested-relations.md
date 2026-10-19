---
workstream: WS:PROPHET-US-V4-RECOVERY
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb / claude/ssd-prophet-b03-attested-relations-cbdbb215de0325e1
model: codex
ended_because: ci_handoff
mission: Complete authenticated B03 paging and exact candidate return while preserving canonical B1 integrity.
state_before: "PR8832 and PR8845 merged normally; installed8845 engine and later API process boundary verified.\
  \ Live initial8-row browse, exactAMZN filter and Showall returned200 in9.43\u201311.58s, but offset8 paging aborted\
  \ at15.000550s. Return to candidate works live in grid and filtered table with exact MCK candidate, query, focus\
  \ and scroll restoration."
changed:
- path: engine/us_candidate_episode.py
  what: Expose B1-owned exact-byte attestation of canonical HEAD, manifest, file set and every actual payload hash.
    The public snapshot reader still performs complete semantic validation every call.
- path: engine/prophet_early_observations.py
  what: Cache one compact immutable receipt-specific relation index, bounded to4MiB. Reattest all B1 bytes before
    each reuse; cold build performs full semantic validation and same-token post-attestation. Clear cache on any
    read failure. Current source, identity and public coverage remain freshly read; authorization remains with API.
- path: tests/test_prophet_early_observations.py
  what: Pin every-read attestation, single cold semantic construction, all-artifact corruption/file-set changes,
    coherent semantic corruption, current identity, generation changes, concurrent construction, immutable return
    and size bounds.
prs: []
verified:
- claim: Complexity controls distinguish unchanged source while integrity controls already pass.
  command: Run initial cache-count and actual-byte corruption tests against original source; b03-attested-relations-red-20261011.txt.
  result: 2 failed,8 passed,36 deselected. The two failures replayed semantics twice instead of once.
- claim: All affected B1/B03/API regression suites pass.
  command: python3 -m pytest tests/test_prophet_early_observations.py tests/test_us_candidate_episode.py tests/test_us_candidate_episode_reconciler.py
    tests/test_us_candidate_episode_intake.py tests/test_us_candidate_episode_wiring.py tests/test_prophet_observations_api.py
    -q
  result: 213 passed,0 skipped,0 deselected; five existing deprecation warnings.
- claim: Complete retained-input output remains byte-identical for cold and repeated reads.
  command: b03-attested-comparison-20261011.py on exact released8845 and new source with the same retained October8
    source/identity/B1 input. Compare all projection bytes.
  result: 371 rows and all relation/snapshot fields equal, SHAaa46fb4a73393b8e8eb76dea9c7eed45ac1cbb07f109dae5d87dfff6cf1e7950.
    One local baseline4.174964s, new cold3.141365s and repeat0.092554s. These are local timing samples, not production
    latency or causation.
- claim: Independent bounded review approves semantic and integrity scope.
  command: Read-only exact-diff review /root/b03_runtime_read_reasoning and parent git hash-object.
  result: APPROVE B1 blob80ad7ae0d646b89d7abd29af3b8cbe62967e994e and B03 blob5c7a62b98461dfc10fd364ab18ddf0a3d037956d.
    Reviewed tests d574e55e3fd12bd53b1ebde00f4d9cc1832834f9; parent then added the reviewer-requested direct attestation
    counter. Reviewer did not run tests or write source.
- claim: Related Plan return works on the authenticated live page.
  command: Actual entitled IAB MCK candidate to related MCK-BULL-20261005 Plan, Return to candidate, Close in grid
    and MCK-filtered table; return-to-candidate-live-grid/table-20261011.json.
  result: Original candidate reopens; Close restores original trigger focus and exact scroll2178/grid or1453/table.
    Table retains MCK query. Same-security relationship remains explicitly distinct from exact candidate episode.
unverified:
- claim: The cache resolves authenticated production paging.
  what_would_verify: Normal exact-head CI/release and source/runtime adoption followed by entitled browse, filter,
    next/previous same-snapshot relation and sign-out journeys.
unresolved:
- Cold construction and concurrent requests serialize under one lock; this preserves atomic publication but is a
  throughput/deadline risk until live proof.
- B03 pagination and sign-out acceptance remain open.
next_actions:
- Publish the original branch, consume canonical exact-head CI and normal authority/fences, reconcile current main/proofs,
  then expected-head squash.
- Verify ordinary installed-source/process adoption and authenticated B03. Retain accepted live Return proof unless
  relevant source changes.
do_not_redo:
- PR8832,8845,8827 and earlier source/reviews/CI/releases are closed; retain merged worktrees, never reset/reuse.
- No cache by HEAD/mtime/size. B1 owner must hash every actual file on every reuse; public snapshot API still fully
  validates semantics.
- No client deadline/auth/data/checker/allowlist change; no fixture substitution for live proof.
- No replay of Fabric log-reservation refusal, denied org403 or /api/health. No retry of low-memory optional VPS
  candidate probe.
- Preserve P1a8444 and DailyBrief8249 refusals, foreign custody and scientific holds.
danger_areas:
- Byte identity attestation is not semantic validation. Only a successful full semantic cold read can create the
  entry.
- No full generation or mutable event payload retained. Duplicate cardinality and first episode match must remain
  unchanged.
- Original browser request arrival/first fault are not established by isolated local timings.
---

Evidence: /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89.
