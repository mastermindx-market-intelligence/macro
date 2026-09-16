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
