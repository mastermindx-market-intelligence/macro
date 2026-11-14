# Inflation owner publication proof — 14 November 2026

## Outcome and boundary

Two mandatory synthetic-input regressions exercise the canonical Inflation owner, workspace publisher, manifest-first reader and consumer view. They prove values and provenance survive the real publication path. They do not establish a current live feed, authenticated serving, a deployed native page or completion of the wider native Macro programme.

Source pin: `348f33411bb2f27807e99e547d6b56981a5843c2` on Macro `main`. The isolated source was first verified at `40770a48e986d4e26e8c50c0add9cd941809de79`; the exact compare to this publication base changed only the research-vault catalog and excerpts. All exercised source and CI files retain their verified blobs.

## Discriminating cases

The first case writes thirteen monthly collector-shaped observations under a temporary root and calls `write_inflation_intelligence`. Its actual output path is passed as `inflation_intel_path` to `build_all`. The view is built from `read_workspace` and that reader's actual artifact receipt.

| Reading | Independently expected result |
| --- | ---: |
| All prices, annual change | 3.02 |
| All prices, monthly change | 1.00 |
| Core prices, annual change | 2.00 |
| Core prices, monthly change | 0.00 |

The second case retains thirteen headline observations but removes the exact August 2025 annual endpoint and includes an older July observation. The August 2026 annual rate must remain absent; a positional twelve-row substitute would produce a false number. Monthly headline, annual core and zero monthly core remain available.

Assertions cover owner rates, raw snapshot values, EN/ZH formatted view values, monthly reference periods, unit/basis/freshness labels, owner and definition references, latest-revised seasonal basis, unknown release/availability/collection/revision clocks, the current typed absence, manifest generation/digest/bytes, reader-to-view evidence binding, unchanged owner bytes and exact false authority flags.

Unrelated publisher inputs are explicitly isolated from ambient repository feeds. The owner is never mocked. This main-source view does not yet include #11258's new raw-value/token/history additions; this proof does not pretend those feature-branch fields exist on main.

## CI qualification

The existing `market-os-macro-workspaces` job already executes this test file. Its eighteen-suite command, timeout, gates and exclusive-scope policy remain unchanged. Two earned paths are added: `engine/inflation_intelligence.py` and its local basis dependency `engine/rates_command_basis.py`. The same job installs `pandas pyarrow` for the actual Parquet path.

Local verification:

- **27 passed, 1 skipped** in the complete Inflation workspace suite. The one pre-existing optional check reads a checked-in real owner artifact absent from this isolated source; both new publication tests execute and pass.
- All **35 observed first-party runtime imports** are covered by the job's declared paths; both newly declared owner files execute.
- YAML semantic comparison confirms **one of 402 jobs changes**. All other jobs and the existing test command are unchanged.
- The full tracked-tree static closure and hosted pack are left to the repository's canonical CI gate. A sparse local import check is not claimed as that global audit.

## Ownership and integration

This is an isolated main-based qualification change. Active Macro #11258 remains at `5f464a227fd33799210bcfca294b8b63099d5c4a` and owns history/provenance feature work. Its CI dependency line already ends with the same `pandas pyarrow`; the new two-path declaration is additive. No source, branch, hold, label or publication of that live writer is changed here.

Native Terminal #1533 at `8fb0c80cef0d461eb87e5d3bf10781c1dcec946c` contains the paired Inflation UI and strict monthly-period decoder repair. Its hosted responsive proof is a separate boundary from this backend proof.

Release remains through Macro's existing qualified `merge-on-green` controller, after exact-head gates and hold checks. No native auto-merge, manual merge or global CI policy change is part of this patch.

## Next proof

Bind this owner publication to the qualified native reader, preserve genuine zero and absent annual data, then verify deployed authenticated desktop/mobile EN/ZH light/dark consumer paths after registry and release dependencies are satisfied. The larger programme still owes full production acceptance and remaining masterplan reconciliation.
