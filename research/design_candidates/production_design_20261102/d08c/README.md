# D08C — Options Plan, Compare & Review

**Bounded design/specification return to D08, not product implementation. RIG: draft.** This package develops a coherent investigation → research plan → assumptions → comparison → explicit save/watch → revisit journey. It preserves the incumbent contract identities, observations, calculation limits, Investigation owner and uncertain-operation custody.

The integration owner remains **mastermindx-3 on [Macro #10649](https://github.com/mastermindx-market-intelligence/macro/pull/10649)**. The existing Plan persistence carrier remains **[Terminal #804](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/804)**, Draft/HOLD. D23 owns the shared saved-state and alert contract; D22 owns actual holdings. This package creates neither a service nor a runtime store.

## Read this package

| File | Decision it supports |
| --- | --- |
| [SOURCE_AUDIT.md](SOURCE_AUDIT.md) | Exact source, route, producer, incumbent implementation and Paper baseline |
| [PRODUCT_AND_RETENTION.md](PRODUCT_AND_RETENTION.md) | Persona, complete journeys, capability dispositions and reachable successors |
| [INTERACTIONS.md](INTERACTIONS.md) | Controls, state transitions, copy, navigation, input, focus and recovery |
| [DATA_AND_BUILD.md](DATA_AND_BUILD.md) | Identities, units, clocks, actual APIs, owner boundaries and future integration sequence |
| [ACCEPTANCE.feature](ACCEPTANCE.feature) | Executable future acceptance scenarios; no claim they have run against the product |
| [fixtures/expiry_payoff.json](fixtures/expiry_payoff.json) and [verify_oracle.py](verify_oracle.py) | Independent synthetic arithmetic oracle; not a service response or contract-coverage proof |
| [DESIGN_MANIFEST.json](DESIGN_MANIFEST.json) | Exact editable targets, responsive classes and captured artifact identity |
| [VERIFICATION.md](VERIFICATION.md) | Actual visual/read-only proof, critique, remediation and remaining gates |
| [RETURN.md](RETURN.md) | Bounded receiver action and continuity dispositions |

## What changed in the design

The plan leads with an expiry payoff, exact legs and authored assumptions. Evidence stays reachable with its own dates. Comparison exposes the changed assumption and common basis before showing a numerical difference. Revisit separates the immutable saved revision from newly acquired observations. Save, exact-revision readback and watch activation have distinct states, including known commitment with unavailable readback.

These are editable **provisional specimens**. The shell input is `F01-F02-SHELL/1.0.0-candidate.4`, and F02 is `1.0.0-candidate.2`; final released foundations and formal independent reference acceptance remain outstanding. Capturing an immutable review artifact does not qualify that provisional shell or approve the design.

## Exact source and action boundary

| Input | Pin |
| --- | --- |
| Protected law | Mastermind `910803421beca53ca25145392725ab2d84c7a8e9`; compatible `mastermind.sol_skillpack.v1` 1.0.1, bootstrap major 1 |
| Programme / assignment | Macro `6e1862867193ec6486a22001a0e4fb515da20448` |
| D08 semantic interface / audited producer | Macro `d0516e1bad9cb5982d43d20c4167d0355cb70e2c`, `D08-OPTIONS/1.0.0` |
| D08 integration head inspected | `e89f527e3267b1d1dd27ac7507e9a25983c0c903` |
| Current Terminal consumer | `2ded360882b9c721e690907ff363b553781fb920` |
| Held Plan persistence implementation | Terminal #804 `27df56d997df0ae94a17b6b8e2d14867431bb394` |
| F01 source inspected | `c1fc69b3452b92dff0f1863c1689e18b049cb56f`; joint contract blob `1160f14b108bf0948384f59a249320385a1dfb6c` |
| F02 source inspected | `f7c25c4b9870cff260c2a4b998be18d6c04d36d0`; token map blob `a7ec801d3b559cc64f4fd57141c32f63098c6461` |

Only the assigned `d08c/` source package and newly created disjoint Paper candidate targets are changed. Existing Paper references, D08 shared integration board `1N2L-0`, held PRs, routes, services and data are untouched. No merge, Ready/un-draft, enqueue, held-PR relabel, deploy or uncertain-operation replay is authorized or performed.

## Reality check

The live `/options?tab=structure` route displayed **“Options is temporarily unavailable”** and could not verify access. Normal-data browser paths and authenticated save/watch behavior were therefore not proved. The exact access screen is retained in `evidence/browser_access_unavailable.png`; this does not establish a changed subscription or a data outage.

The illustrative spread is SPY 20 November 2026, long one 600 call at 5.20 and short one 610 call at 2.00 USD per option unit, with an **assumed** ordinary multiplier of 100. The arithmetic is independently checkable; actual installed reference coverage and current executable quotes are not claimed. Account saving remains unavailable in the current-source specimen. Saved/review/watch specimens express the conditional future owner contract.

Completion for this return means a concrete, reviewable design package with source and evidence. Foundation release, formal RIG approval, implementation, merge, deployment and served-product acceptance are separate later gates.
