---
workstream: WS:PROPHET-US-V4-RECOVERY
session: claude/prophet-lab-earnings-view-20260917
model: sol
ended_because: blocked
mission: Make the existing private Lab earnings view discoverable by exact canonical
  B1 episode and generation, without ticker joins or new source/authority owners.
state_before: 'PR #7264 published head 0fe505b186c51455a73778a672dd1e02794c628a. The
  native view required an already-known episode ID; no bounded discovery path existed
  and it did not check a caller-supplied generation pin.'
changed:
- path: engine/prophet_lab/episode_directory.py
  what: Read/filter/decorate one validated B1 generation into bounded links; no earnings
    reads, no identity minting, no filtering by evidence coverage.
- path: app/prophet_lab.py
  what: Private directory route and optional expected-generation guard on the existing
    research view. Reuse auth, kill switch, no-store headers and canonical loader.
- path: tests/test_prophet_lab_earnings_view.py
  what: Add 21 discovery, privacy, paging and generation cases. Correct shared fixture
    imports to the native tests package, removing an import-path dependency.
- path: research/prophet_v4/earnings_view/2026-09-17-episode-directory-proof.json
  what: Preserve actual source hashes, 511-test result, real 866-episode read and
    explicit limitations.
prs:
- 7264
verified:
- claim: The complete native Lab owner battery passes without an injected PYTHONPATH.
  command: python3 -m pytest -q -p no:cacheprovider tests/test_prophet_lab.py tests/test_prophet_lab_api.py
    tests/test_prophet_lab_earnings_view.py tests/test_company_intelligence_workspace_chain.py
    tests/test_prophet_lab_timeparse.py tests/test_prophet_lab_commissioning.py tests/test_caddy_hub_boundary.py
  result: 511 passed; zero failures/errors/skips; 10 framework/OpenAPI warnings.
- claim: Real committed B1 input reaches the private directory through the complete
    canonical reader.
  command: Materialize HEAD.json and its eight exact generation blobs from macro@63fb8dd9fa7dbe43c02ca6eac84b22fbbc9706dd
    into isolated test inputs; FastAPI TestClient GET /api/prophet/lab/v1/episodes?limit=100
    with local-only auth fixture; hash readback.
  result: HTTP 200; 866 total episodes; first 100 links pin peg:18dfbb8a9d7152382ca6da8a2ac4177d6ea617dddc7cad082b3645c100fb53a7;
    native B1 loader was not mocked; all nine input files unchanged. Local HTTP, not
    production authentication proof.
- claim: Five forbidden mutations are detected by their intended assertions.
  command: Load isolated mutated directory/app modules and run the corresponding new
    registered pytest selectors; retain original source byte hashes.
  result: Unpinned pagination, ticker collapse, rank authority, malformed pin and
    changed-generation acceptance each fail. The two injected-spy cleanup errors in
    initial diagnostics were superseded by clean non-throwing-spy retests.
- claim: Source whitespace is clean.
  command: git diff --check
  result: Exit 0.
unverified:
- claim: Hosted checks and independent review accept the new semantic head.
  what_would_verify: Concluded applicable CI/security plus an actual independent review
    on the published head and current-base integration.
- claim: Users can open this evidence through the deployed entitled Prophet interface.
  what_would_verify: Mount in the incumbent prescribed product surface, preserve exact
    episode+generation and existing auth, complete real entitled browser proof.
- claim: The targeted full CI import-closure audit passes.
  what_would_verify: A concluded result from the existing CI owner. This local three-test
    run timed out at 100 seconds and is not a pass.
unresolved:
- Original UI source-read lane is still platform-refused; do not fabricate an auth
  bridge or a ticker-to-episode join. The approved Lab contract names the Macro US
  Prophet experience with MDXAuth, not the separate Pick Lab.
- Shared CI and independent reviewer remain external release dependencies; the review
  request is not a START receipt.
- The original +1y expectation-revision source archive and its identity/B-17/rights
  gates remain separate. No model, threshold or 21-session outcome evaluation was
  opened.
next_actions:
- 'Continue PR #7264 and this exact branch. Publish this bounded directory addition,
  consume exact-head CI and independent review, then refresh current-base compatibility
  before any release.'
- Connect the incumbent entitled consumer to the directory, copy its exact episode
  reference and expected_generation into detail requests, and handle 409 by discarding
  the stale view rather than silently rebinding.
- Obtain normal deployment and actual entitled covered/unavailable/correction browser
  proof. Keep the original expectation-revision compiler separate.
do_not_redo:
- 'Do not recreate PR #7264, the worktree, D5, B1, B-17, B3/B4, auth or publication.'
- Do not repeat the collector investigation, 291-PR census, 14-paper synthesis or
  unchanged initial view implementation.
- Do not infer a B-17 complete population from the 866 B1 episodes, and do not deduplicate
  them by ticker.
- No raw source data is committed by this directory slice; isolated 20MB input snapshots
  are evidence only.
danger_areas:
- The directory is a read projection, not a scientific population or a ranker.
- A changed generation must return 409 without old/new evidence blending.
- A real-data local TestClient auth override is not production entitlement proof.
- Current-frontier canonical notes supersede only older next-action prose; old proofs
  remain scoped to their original heads.
---

# Native Lab episode discovery

The source data is read from one validated current B1 generation. Human search narrows the display only; exact episode and generation references supply identity. No action, holding instruction, scoring or complete-population claim is produced.
