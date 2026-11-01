# Independent CI binding review — private company-news drafts

**Disposition: APPROVE, bounded source review.** No blocking source defect found. The existing independent private-product source approval is unchanged.

## Exact source binding

Repository: `mastermindx-market-intelligence/macro`; [PR #9888](https://github.com/mastermindx-market-intelligence/macro/pull/9888).

- Candidate: `f9270eadd1013a1c1cf69dc6bdf3f04e3c46c74e`.
- Compared main and merge-base: `1aed18a0f066ecd82ece1473fbe7aca172696f54`. GitHub reports the candidate is ahead of that exact main, with 29 changed files overall; this review covers only the two CI files below.
- Review recorded: 2026-10-20 18:55 UTC.

| Reviewed file | Independently computed SHA256 |
| --- | --- |
| [.github/ci/legacy-jobs.yml](https://github.com/mastermindx-market-intelligence/macro/blob/f9270eadd1013a1c1cf69dc6bdf3f04e3c46c74e/.github/ci/legacy-jobs.yml) | `b660a85a3dcb3d2389b0672b512660a296b95b948ce79e949d1199cf9ba44dd8` |
| [tests/test_ci_pack.py](https://github.com/mastermindx-market-intelligence/macro/blob/f9270eadd1013a1c1cf69dc6bdf3f04e3c46c74e/tests/test_ci_pack.py) | `929978eea728dc987d839f20e17a22bf68db2a9ba878f7fda0eda6ae380bc43b` |

Both hashes match the parent's sealed candidate. The manifest Git blobs are `3d90df1d4af50b26e73fb40fab5aa1be2a353111` on main and `6fede589b7b1fa6239e40f3baf916f35ee16a8dc` on the candidate.

## Source findings

1. **The suites reach the ordinary source PR gate.** `ticker-news-qbus` remains `gate: code` and `scope: exclusive`; the existing `press-lane` remains `gate: data`. Both `tests/test_press_run.py` and `tests/test_press_writer.py` occur once in the real folded pytest command, which now contains 47 suites. No prior suite or option was removed and no deselection, skip, or failure masking was added.

2. **Inherited jobs are preserved.** Direct comparison of all 341 named manifest job blocks finds only `ticker-news-qbus` changed, with no added or removed jobs. Its additions are 80 literal paths: the two suites, 74 supporting closure paths, and the four canonical data files identified by the red audit. No prior path is removed; no wildcard root or fallback is introduced. Dependency installation adds only `jinja2` and `beautifulsoup4`. The four final paths are `site/basketdata/breadth_split.json`, `site/factordata/attention.json`, `site/factordata/tech_confluence.json`, and `site/marketdata/sp500_heatmap.json`.

3. **The measured census rebase is justified and exact.** The packing test changes only the `scripts/build_free_content.py` probe from **134 jobs / 5,697 weight** to **135 jobs / 5,795 weight**, plus a dated explanation tying the new selected news job to code-gated Press coverage. Other probes, the ten-pack cap, selector code, and assertions stay unchanged. The addition is exactly one job and 98 estimator units with no padding. These are planning weights, not elapsed seconds. Removing a suite or its real builder dependency just to retain the earlier census would drop relevant coverage. No narrower restructuring is necessary to make this repair correct.

4. **The false-if marker does not disable this gate.** Supporting reads of [scripts/run_ci_pack.py](https://github.com/mastermindx-market-intelligence/macro/blob/f9270eadd1013a1c1cf69dc6bdf3f04e3c46c74e/scripts/run_ci_pack.py) show the loader validates the legacy marker and filters jobs by `gate` before planning/execution. The [production workflow](https://github.com/mastermindx-market-intelligence/macro/blob/f9270eadd1013a1c1cf69dc6bdf3f04e3c46c74e/.github/workflows/ci.yml) explicitly passes `--gate code` for plan, pinned execution and fallback execution. Neither file changes in this PR.

## Verification attribution and limits

The parent reports exact-head canonical contract-delta PASS against `1aed18a0f066ecd82ece1473fbe7aca172696f54`: **0 introduced / 0 inherited**, with measured build **135 / 5,795 / ten packs**. Its sealed log SHA256 is `f78f4b0cebba9160b5ccabdd3c2d9f811539c264dc0ec86bb5361bedce30eea5`. The parent also reports all six existing CI guards PASS; log SHA256 `427397724a75a52604b112bc21385010976f1b3ac94d03c23e89f7b1e368bba2`. At 18:52 UTC the parent reported all twelve hosted packs and `ci-gate` successful for run `39471764135`.

Those tests and closure measurements belong to the parent. This reviewer independently read the immutable source and diff, verified the two content hashes, compared job blocks, inspected the actual command/scope changes and read the gate mechanism. No duplicate full audit or test run was performed. This receipt makes no live-provider, deployment, release or runtime-capability claim.

The earlier read-only Studio command was interrupted after 4,086.8 seconds without a returned PID or result. Its completion is unknown; it supplied no evidence for this ruling. No reviewer remote mutation occurred.

The private-product source approval and its separate patch/hash receipt remain valid. The parent retains publication and release responsibility; this bounded child review does not mark the parent mission complete.

