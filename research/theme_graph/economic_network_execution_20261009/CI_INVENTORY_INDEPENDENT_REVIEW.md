# Independent review: relationship candidate CI inventory repair

## Decision

**PASS for the bounded inventory repair. No required source corrections found.** This review does not authorize merge, declare the full hosted workflow green, or admit the economic relationship capability to production. It confirms that registering `company-relationship-candidates` in the existing curated-exclusive inventory repairs the observed missing-registration condition while leaving the enforcement machinery intact.

Reviewer: independent agent `/root/ci_inventory_review`.

Review completed: 2026-10-09 03:43:54 UTC.

Reviewed native workspace: `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-execution-20261009-pro-001`.

Parent source head: `2a00eff6125d07cc2303b1edbafa00ba1d50d4a5`.

Delivery carrier: [Macro PR #8667](https://github.com/mastermindx-market-intelligence/macro/pull/8667).

## Failure and exact correction

The parent supplied the concluded hosted failure from [run 37877395436, job 113649821453](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37877395436/job/113649821453): `tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared` failed with the symmetric difference `['company-relationship-candidates']`. The candidate application step and contract-delta check had passed; that history remains separate from this review and is not relabeled as an entirely green workflow.

I independently read the current manifest and test source and reproduced the exact set mismatch from the original source without modifying any file. The manifest declares the new job as exclusive, while the original pinned set lacks its identifier. The repaired set exactly equals the manifest's declared exclusive jobs.

The complete source correction under review adds three lines after the existing `ratio-lens` member:

```python
    # 2026-10-09 PR #8667: file and pinned-source relationship inspection.
    # Register the reviewed 68-path owner; closure audits and ceilings stay fixed.
    "company-relationship-candidates",
```

| Check | Independently observed result |
|---|---|
| Inventory members added | Exactly `company-relationship-candidates` |
| Inventory members removed | None |
| Original inventory symmetric difference against actual manifest | Exactly `company-relationship-candidates` |
| Repaired inventory symmetric difference against actual manifest | Empty |
| All other top-level Python AST nodes | Identical before and after |
| All test function ASTs | Identical before and after |
| Manifest working diff | Empty |
| Candidate job scope / gate / declared paths | `exclusive` / `code` / 68 |

The all-other-AST comparison includes imports, helper definitions, test bodies, assertions, packing probe limits, and all other module-level constants. It ignores source location offsets, so the inserted lines do not create false differences. The literal inventory comparison separately establishes that existing members are preserved.

## What the static inventory affects

An exact source search found only one runtime use of `CURATED_EXCLUSIVE`: the equality assertion in `test_the_curated_exclusive_set_is_actually_declared`. Registering the new identifier makes the expected inventory describe the actual declared inventory. It does not add an exclusion, bypass, skip, weakened assertion, or expanded ceiling.

The more consequential closure audit remains independently derived from the manifest. `test_curated_exclusive_scopes_cover_their_own_import_closure` calls `curated_exclusive_closure_findings(MANIFEST)`. It does not use the static inventory to select which jobs to inspect. Therefore adding this member cannot hide a missing import or read dependency from that audit. The shared implementation is also used by the contract-delta check.

`test_every_declared_scope_in_the_real_manifest_is_covered` still calls `PACK.load_legacy_jobs(MANIFEST)`, which raises on declared command coverage gaps. `test_exclusive_curation_narrows_ordinary_code_prs` retains its existing fixed packing probes and limits. The job manifest remains unchanged, including its 68 explicit dependency paths, existing executable test command, and lack of a broad fallback.

This is a metadata registration correction for a previously reviewed exclusive declaration. It is not a new curation design, a new closure derivation, or a substitute for the original native-reader and semantic-boundary reviews.

## Independent validation

I executed this existing targeted test through Studio Direct in the canonical workspace:

```sh
python3 -m pytest tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared -q
```

Native process: `59760`. Result: **1 passed, 8 warnings in 1.32 seconds; exit code 0**. The warnings concern pre-existing temporary Chromium directory cleanup under `/private/tmp/pytest-of-chriswong/garbage-*`; no warning points to this patch or its data. I did not delete or change those temporary directories.

Two independent read-only Python inspections established the source hashes, exact set delta, full function-AST preservation, all-other-top-level-AST preservation, manifest identity, and source/test identity. Those processes were `59511` and `61029`.

The parent is running the recommended existing coverage and packing tests plus fallback-preservation coverage. I intentionally did not duplicate those longer checks. Their outcome must be recorded separately by the parent; it is not assumed here.

Recommended and identified existing checks for the repair class:

- `test_the_curated_exclusive_set_is_actually_declared`
- `test_curated_exclusive_scopes_cover_their_own_import_closure`
- `test_every_declared_scope_in_the_real_manifest_is_covered`
- `test_exclusive_curation_narrows_ordinary_code_prs`

## Reviewed identities

| File | SHA-256 |
|---|---|
| `tests/test_ci_pack.py` before correction at parent head | `55875715430d9e30873be72279d62e057cc5451f6ab093ebad031aec67485383` |
| `tests/test_ci_pack.py` after correction | `c7fc028a53f58f6a9310cb874c535dee1fa1556b211691ea4bf5c873fae41357` |
| `.github/ci/legacy-jobs.yml` | `195921e289363a9ecc6036c9b53fbcbb6c991df8ad8d08138b51fe23b63f2d64` |
| `engine/company_intelligence/relationship_candidates.py` | `27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d` |
| `engine/company_intelligence/pinned_relationship_candidates.py` | `1000497dcfef316f1ad0726c08bcba7ba12dbe305175887e191d6f96512649bd` |
| `tests/test_company_relationship_candidates.py` | `0a8c73d5e5b968fd3795fed1e08305597f9c254cc5702b9946b702b8f31bdbd4` |
| `tests/test_company_pinned_relationship_candidates.py` | `3c85ace77022c2b37c8abfab915ae8bf97ee711a8f315ea9e3b6f27d01872406` |

## Ownership, limits, and release requirements

The parent refreshed the active-map collisions and live PR source patches before the edit. Its reported results were: #8586 adds a distinct `leadership-lab-recovery` member at an earlier position; #8245 adds its distinct private-publication member earlier; #8444 changes dashboard assertions; #8192 adds a prospective-context test. I did not independently refetch these PRs. My direct source comparison confirms this correction removes or modifies no existing member, assertion, helper, or declaration. Live integration must still preserve any changes those carriers land after this review.

No blocker was found in this three-line correction. The prior closure review's missed static registration remains an explicit release finding; this report does not retroactively claim that review caught it. The concluded hosted run remains failed until superseded by a genuinely successful new run.

The reviewed source must be committed and synchronized normally to trigger fresh current-head integration. Fresh hosted checks, the actual semantic plan and merge composition, native proof freshness, the integration baseline, current holds/reviews, and the expected-head merge fence remain delivery requirements. This report does not replace them. No PR close/reopen was performed by this reviewer; the parent's previously contemplated lifecycle reproof is superseded by the real source correction.

I made no source or Git mutations, did not run `run_ci_pack --execute`, did not change credentials or native-reader configuration, did not invoke a live source acquisition, and did not change any PR state, label, approval, or owner communication. The only written artifact is this scratch review for the parent to preserve with the delivery evidence.

The full project still requires the real retained native source binding and the existing owner's fact, dataset, temporal, identity, rights, and product-admission decisions. This CI repair grants none of those authorities.
