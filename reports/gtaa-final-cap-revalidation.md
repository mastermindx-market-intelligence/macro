# GTAA cap repair and composed verification

Issue #11003. Retained source carrier: #11059.

## Current composition

The final 30% / 40% / 55% per-name cap remains applied after volatility and gross scaling, with unused capacity left unallocated. This composition preserves that allocator and adds the qualified contributions from [#11058](https://github.com/mastermindx-market-intelligence/macro/pull/11058):

- Finite Sharpe comparisons require a positive benchmark.
- Missing historical half comparisons remain unavailable.
- Phase0 requires complete existing trial evidence and a budget covering the exposed profiles.
- Regression cases cover asymmetric allocations without redistribution, cash and financing, zero trends, optional missing assets, late-history eligibility, changing volatility, and comparison copy.

The composed native campaign passed **114 tests, zero skips**, across active allocation, hub/detail and Signal Lab. The added qualification and copy counterexamples produced **8 failures and 6 passes** on the previous #11059 source. The actual native builder's pages and JSON agree with the unchanged native allocations and scorecards.

The final Phase0 numerical code is the tested version; a subsequent comment and heading clarify that revised-history carry remains in the no-regime sensitivity. The final harness executed successfully and retained the historical diagnostic values and existing trial evidence. This establishes source and native rendered-output proof. Deployment and live-portfolio acceptance remain separate.

## Historical evidence retained unchanged

The allocator and historical input set did not change during this composition. The complete accepted [historical report](https://github.com/mastermindx-market-intelligence/macro/blob/dce159d5786954dd36a46653f04c1603e086c7e4/reports/gtaa-final-cap-revalidation.md) and [machine-readable evidence](https://github.com/mastermindx-market-intelligence/macro/blob/dce159d5786954dd36a46653f04c1603e086c7e4/reports/gtaa-final-cap-revalidation.json) remain at their original source pin.

The JSON file in this branch is intentionally unchanged from that prior head. Its source identities and rendered-output hashes describe that historical execution, not this composition. The diagnostic values consumed by the existing quote-correspondence test are identical. A refreshed detailed manifest is not part of this commit.

The separate [donor report](https://github.com/mastermindx-market-intelligence/macro/blob/19ed5957ec767bad41166f21f20ed70828ef4c1c/reports/masterminds-cap-validation-2026-11-11.md) remains evidence at its own pin. Its results are not relabeled as an execution of the composed source.

## Reproduction and release

Run `python -m pytest tests/test_active_alloc.py tests/test_masterminds_hub.py tests/test_signal_lab.py -q` in the repository's native test environment. The existing builder and Phase0 entry points provide the rendered-output and diagnostic checks described above.

The strategy's existing classification is unchanged. Historical diagnostics do not authorize trades. This PR remains held for current-head natural CI, the enrolled allocation command and a clear semantic gate before release.
