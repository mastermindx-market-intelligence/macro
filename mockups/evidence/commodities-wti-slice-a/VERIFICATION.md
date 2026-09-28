# Commodities WTI/EIA Slice A — review repair and exact-source evidence

**BUILT_NOT_PROVEN · MISSION_COMPLETE:false.** PR #8125 remains a draft implementation of the first physical-evidence vertical, not the whole Commodities redesign or a release.

## Current candidate/source

Repaired source and generated page were committed **before** capture at `c5030870e1d60663210540d479762c1fc7065ea5`. Integrated main: `f6dae649ee6d32ec65a95ccea411b205d0b0bc45`. The following evidence-only commit must preserve all source/page/driver blobs below. Current procedure: Mastermind `dcc4829a811d3f6e4fe8c16a103f813c3501f48e`.

Canonical `capture.json` now records `target.resolved_sha_or_none = c5030870e1d60663210540d479762c1fc7065ea5`. This identifies the actual committed capture source, not the older pre-integration parent. Before and after capture, working page/driver/source bytes were compared to `git show <source>:<path>`. The WTI adapter also validates every actual HTTP page response against the expected generated-page SHA256 and verifies the page file did not change during the cell.

| Exact source path | Git blob | SHA256 |
|---|---|---|
| `site/commodities.html` | `521306f9989b1f6ab4c4d40e9bf95af29cb8640f` | `af1f202826211a336d66b5f68b52985d3f6dfc4807b2f08599509fde3a18ab3c` |
| `scripts/capture_commodities_wti_slice_a.py` | `567b3aa93c82d1302cb572b9875fe51f5255db1a` | `da1fcd71316948aa7a51642fe14685e0b4e84e2d0483852d1daa1c3fb7984507` |
| `scripts/capture_page_evidence.py` | `6f184c6469f6fd653d003716ad96605055e71f56` | `8d753e2859d5261eb0d0bad3f626f8870eedf03e23a7f87b4b588bd792e88f16` |
| `scripts/build_commodities.py` | `174ca6d1f419826f0bc0692510bea101c3f4e9b0` | `9b469e11b32d28d4c151bc5ee15bbbe8a8921bcb1937fc2b4b66e53f151f3aad` |
| `templates/_commodity_oil_physical.html.j2` | `2659a9eeafaa2aef350ad833f9f5a5a23a422496` | `7b8a79951c99425e853b6f225bdd2436a5de466141b5ae1d994fad5624d299ed` |
| `templates/commodities.html.j2` | `787b16f35937505c945eba5687f6daeb4b13c4c8` | `2b290ae10f8d5cb3851947266eb8d7efcb30a8dc48b89ad49a468b5da332bc26` |

Manifest SHA256: `bd81817caaf543187ff4fd485fab52fbea4dccb0d9494eae4cb07d76706b57e5`. All referenced PNG hashes and byte lengths were verified. No new schema, evidence store or global capture-owner change was introduced.

## Independent review findings and corrections

Codex review5333803932 reviewed prior head `b19a3b2ee956005db9f2084319f7754f274aadbe` and returned two P2 findings, not an approval.

1. **4118419745 — evidence binding:** the prior adapter put page/driver hashes into arbitrary `CellObservation.observed` keys, which canonical serialization discards. The prior manifest targeted `369f9150...`, so the earlier exact integrated-page binding claim was not supported. Those unused fields were removed; this evidence was regenerated from the committed repaired source above. The canonical manifest and exact source commit now provide the binding. Do not restore the old claim or assume every observed key is persisted.
2. **4118419749 — categorical balance:** a rejected NaN composite could leave the word Tight. The VM now calls the existing balance-word owner with the validated finite composite only. Missing/invalid composite returns n/a with a limitation while retaining usable crude data. It does not invent a new scoring threshold. Contradictory supplied labels cannot override a valid score.

Nine selected tests failed before these repairs, then the complete WTI suite passed **51 tests**. True-zero composite maps to balanced; negative valid anomalies and physical changes remain legitimate.

## CI registration correction

Hosted run36374799145 / contract-delta job108778326171 found exactly one introduced unwired suite: `tests/test_commodities_r2_wti_physical.py`. The suite and subjects are now registered in the existing `unrun-macro-panels` job of `.github/ci/legacy-jobs.yml`. No waiver, pipeline, dependency or weakened check was added.

Canonical `gated_unrun_suites()` reproduced one finding before registration and none afterward. The exact pytest command read from that job after all repairs passed **957 tests,337 warnings in55.08s**, exit0. This is a broader existing-owner command, not a directly comparable increase from the earlier853-test subset. Warnings include existing pandas fragmentation, fixture deprecation and covariance warnings.

Three focused CI manifest/scope contract tests also passed. The complete hosted contract-delta must still run on the new pushed head; these local checks are not an overall hosted-CI pass.

A preliminary owner run counted957 passing cases but correctly exited1 through MM_DATA_GUARD because a concurrently running legitimate builder changed the generated page. No guard was disabled or broad cleanup used. Build and tests were serialized; the accepted exit0 run preserved page bytes throughout. Logs remain in worktree Git metadata `wti-ci-registration/`.

## Real generated-page and browser proof

Existing cached EIA series → incumbent display-only physical-balance reader → WTI VM → oil-only template projection → actual generated `site/commodities.html`. Builder exited0. The current-main conflict was only generated-page build clocks; the page was rebuilt, not taken from a stale side. Equivalent incumbent whitespace was preserved. A dataframe-equal incidental signals-index rewrite was restored to the existing Git bytes; no model-data change is retained.

The real cached observation is **2026-09-18**, separate from daily analysis **2026-09-25**. It shows426.4million barrels, four-week change−2.5million barrels, crude seasonal anomaly+0.46σ, and a separately derived composite balance. It remains stale at build evaluation. Missing publication/receipt instants remain unknown; a quote cannot refresh physical evidence.

Canonical Chrome capture produced **24/24 cells**, using the incumbent matrix including tablet:
- desktop1440×900, tablet820×1180, mobile390×844;
- EN/ZH × dark/light;
- rest and actual keyboard-visible source focus.

All cells loaded the real localhost-served committed page, selected Oil, exercised native disclosure open/close and source link visibility, and passed the no-page-overflow assertion. No captured page exceptions or local HTTP failures were recorded. Each referenced PNG's SHA256 and byte length match the manifest. The initial verification wrapper expected16 cells and failed its count assertion because the canonical owner now supplies24; the successful captures were preserved and their complete actual axes verified, not rerun or relabeled.

Fresh visual review inspected the tablet-dark and Chinese-mobile-light component captures. Shared assistant-launcher overlay still obscures some lower tablet text; it is inherited and not fixed here. Functional capture/contrast review does not close independent full visual/accessibility acceptance.

External requests were deliberately blocked in anonymous local Chrome. This is **not** live EIA fetching, live quote delivery, authentication, account synchronization, production persistence or deployment proof. Invalid-state coverage remains predominantly unit/template tests; the actual browser source state was stale.

## Commands and limits

- WTI tests: `python3 -m pytest tests/test_commodities_r2_wti_physical.py -q` →51 passed.
- CI owner command: execute the existing `unrun-macro-panels` run step from `.github/ci/legacy-jobs.yml` →957 passed, exit0.
- Actual build: `python3 -m scripts.build_commodities` →exit0.
- Capture: `python3 scripts/capture_commodities_wti_slice_a.py --site-dir site --routes /commodities.html --force-state 'focus:focus(.oil-phys-receipt summary)'`, with outputs directed to this canonical evidence directory →24/24 captured.
- Python compilation, actual-diff design guard, runtime-style guard and105 paired assets passed; Agent OS validation0 errors/81 existing warnings. Final visual-manifest/whitespace/source-identity verification occurs before the evidence commit.
- Full-repository pytest is **not green**: previously stopped at collection with missing `marketdesk_extractor`. That unchanged failure was not rerun or waived here.

## Remaining release gates

Required new-head CI and independent rereview of both fixes; full visual/accessibility and generated/live release proof. Preserve #7596 Gold-publication and #7601 shared-navigation ownership. No merge, deployment, new source store, alert owner, score/forecast/portfolio authority or Research persistence. Slice B remains unimplemented.
