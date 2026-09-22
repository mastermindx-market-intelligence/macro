# TURN WATCH v2: exact-source preparation proof

The existing producer can rewrite a same-session document when build runtime or sibling rows change. V1 ordinary row identity can remain identical while its whole-document receipt changes. The real B1 reconciler then correctly refuses conflicting committed bytes. This preparation adds a versioned semantic-row receipt without changing the immutable core, episode identity, generation writer, or correction authority. Full-file checksums and source lineage remain recorded separately.

## Actual current verification

Semantic head `ea961c7998687952ec5539e4909df4236e7b081e`: five existing owner suites passed **201 tests in 29.01 seconds** in an immutable exact-source archive. All 12,928 original source-file hashes were unchanged after the run. The new code-gate job preserves every existing CI owner.

The real nonwriting reconciler using this candidate source also consumed all seven hash-verified inputs of the previously accepted production generation. It appended zero events, preserved the ledger hash, projection hashes and source hashes, performed no durable write, and changed no input file. This is legacy compatibility, NOT production freshness or a historical migration.

Two runtime-only forbidden mutations were detected: replacing v2 row evidence with the document hash caused two tests to fail; omitting semantic definitions from evidence caused four tests to fail. The source files themselves were not edited for those probes. Positive coverage includes runtime-only rebuilds, sibling changes, exact file provenance, definition drift, full-generation preservation, downgrade and backdating refusal, explicit version selection and malformed envelopes.

Git composition against main `44e1292182e65da921e4f19efb254ba0e27d2815` was conflict-free (tree `3eb20fb02976787c9bba6f0f78a4f9879585de8b`). Relevant core, registry and governing B1-law blobs are unchanged from the candidate base. This is source integration evidence, not hosted CI or review.

## Release hold

The default remains v1; no production workflow or dataset-registry current-value is changed. The existing V4 authority must accept the protocol and explicitly coordinate registry/cutover on a genuinely new source session. Old v1 events and input receipts must not be rewritten. The Yahoo archive cadence problem is a distinct producer dependency and is not repaired by changing event evidence. A complete live recovery still requires genuinely current data, canonical nonwriting reconciliation, one acknowledged publication owner and authorized served-payload/browser proof.

Reproduce: `python -m pytest -q tests/test_us_candidate_episode_intake.py tests/test_us_candidate_episode.py tests/test_us_candidate_episode_reconciler.py tests/test_us_candidate_episode_wiring.py tests/test_us_turn_watch.py`. Exact machine outcomes and hashes are in `verification.json`. Original tests/source semantics were recovered from the interrupted session; no already completed prototype work was recreated or passed off as new deployment.

## Refused transition cannot leak a changed public deck

The first published candidate still wrote the public deck before refusing an in-place upgrade, downgrade or backdated v2 transition. Three tests through the real builder failed on that source: the return code reported refusal, but the public file had changed.

The transition check is now a single non-writing helper shared by builder preflight and the existing sidecar writer. Refusal happens before the public write; the writer independently rechecks before its own persistence. Successful v1 output and emission order are unchanged. This is not a new publication plane or a claim of cross-file crash atomicity.

After the three intended RED cases, the five-suite battery passed **204 tests in 98.41s**. All three forbidden transitions preserve both public bytes and private input files. The exact code digests and observed results are in `refused-transition-proof.json`; the earlier 201-test/legacy-input receipts remain historical evidence of their recorded semantic head. The real reconciler/intake path used by the legacy-input replay has not changed in this follow-up.

## NYSE-session authority repair after independent review

Independent review of PR #7227 found that v2 treated any canonical ISO date as a source session. A holiday or weekend could therefore become the first v2 protocol date and, with a matching document checksum, pass intake. The bounded repair reuses the existing `lib.nyse_calendar.is_session` authority at both the producer transition preflight and the closed-envelope v2 intake boundary. It adds no calendar, protocol, identity, retry, writer, or publication plane; v1 remains the default and is intentionally unchanged.

The new tests were observed RED on parent `0e57dc01e494475802c62fc664924236544abb90`: both Thanksgiving 2026-11-26 and Saturday 2026-11-28 producer requests returned success and both matching-checksum envelopes emitted observations, while the real Friday 2026-11-27 early-close control passed. After the repair, all five focused cases pass: non-session producer requests fail before either public or private bytes change, non-session v2 intake reports `MALFORMED_SOURCE`, and the real early close remains `2026-11-27T18:00:00Z`. The existing genuine later-session transition on 2026-11-30 remains green.

The exact five-suite owner battery now passes **209 tests in 49.41s**. The governing NYSE calendar/session-digest battery passes **172 tests with one unchanged skip in 45.93s**, and the three modified Python files compile. Exact commands, source digests, RED/GREEN outcomes, and release holds are recorded in `session-calendar-proof.json`. This is source repair and review-return evidence only—not v2 activation, current-data proof, publication, or served-product acceptance.

## Existing CI owner preserved; redundant owner removed

Current-base composition exposed that the candidate's `prophet-turn-watch-row-evidence-v2` manifest job repeated `test_us_candidate_episode_intake.py` and `test_us_candidate_episode_reconciler.py`, both already owned by the established `prophet-us-context-and-grades` job together with the other B1 suites. A new wiring fence was observed RED with those exact two duplicate-owner lists. The repair removes only the redundant candidate job and keeps the incumbent owner unchanged; the fence is now green and the five-suite battery is **210 passed in 33.45s**. This removes infrastructure that unlocked no new capability and avoids a second CI control path.

After that correction, no-ref/no-worktree composition with current main `53efe6f47e9efcdde45a12bce483d7ec33f0bb8d` is conflict-free at tree `7e9482f6bde1bea0e5532225f7a72bbe36135ac2`, with no overlapping changed paths. The semantic source/test/evidence blobs survive exactly and the integrated CI manifest is byte-identical to current main, retaining one owner for each B1 suite. This is integration evidence only, not merge or production authorization.
