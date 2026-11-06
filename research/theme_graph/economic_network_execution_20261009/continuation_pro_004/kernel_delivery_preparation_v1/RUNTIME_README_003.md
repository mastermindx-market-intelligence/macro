# WP02 source diagnostic: structural research kernel

This directory contains the corrected implementation revision 2 of the version 1 input/output contract. The `source_diagnostic_kernel_v1` path is the stable runtime namespace. It does not select a real issuer cohort or authenticate supplied source evidence.

## Behavior

`diagnose(request_bytes, policy_bytes=..., adoption_bytes=...)` validates bounded, explicitly supplied UTF-8 JSON and returns a deterministic diagnostic object. The artificial mode exercises historical membership replay, scoped assertion revisions, exact reported-share capitalization, relative size bands and quota-constrained selection. The real-source mode always retains `STRUCTURAL_ONLY`, `NOT_READY`, `NOT_ADMITTED`, false authority flags and null real population, capitalization, quantiles, selection and acquisition freeze.

The input contract requires explicit UTC instants with seconds and at most six fractional digits. Unsupported sub-microsecond precision is refused before datetime conversion. This fixes the independently reproduced v1 post-cutoff admission defect; supported prior outputs remain byte-identical. See the retained original review and the separate corrective review for the full failure and resolution evidence.

## Reproduce from the repository root

```sh
python -m pytest tests/test_gmi_source_diagnostic_kernel.py -q
python research/theme_graph/economic_network_execution_20261009/continuation_pro_004/source_diagnostic_kernel_v1/source_diagnostic.py --help
```

The public CLI takes explicit request, policy and adoption files as documented in `INPUT_CONTRACT.md`. Its structural result intentionally exits 2 (`NOT_READY`), including when the artificial model completes. The two JSON inputs in this directory are wholly artificial examples; their author execution receipts and exact expected outputs are preserved in the implementation revision 2 archive. They are not actual global listings or the thirty genuine difficult disclosure cases required by WP02.

## Source and evidence

The sole runnable pytest suite lives under `tests/`. Original author and reviewer packets, including old test filenames and failure witnesses, are retained as exact tar archives with member manifests under the adjacent implementation and review directories. No archive needs extraction for normal execution. `KERNEL_SOURCE_MAP_003.json` maps the corrected runtime files to the exact authored inputs and original review hashes. Hashes establish byte identity; they do not authenticate a source, reviewer, license or acquisition.

The policy and principal adoption sidecar remain in their existing adjacent directories. The CI recommendation is a frozen pre-application proposal, including historical v1 source hashes and the 90-test count. The applied source mapping identifies the v2 module and 117-test suite explicitly; native and hosted execution receipts record what actually ran.

This capability remains a research kernel. It introduces no provider acquisition, trust registry, callback-based admission, application route, Graph1 relationship promotion, ThemeState, propagation engine, rank/gate/size/trade authority or predictive result. The public 8 MiB whole-output refusal was not exercised by the independent replay; that bounded verification limit remains explicit.
