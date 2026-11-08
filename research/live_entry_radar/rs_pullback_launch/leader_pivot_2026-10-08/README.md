# Leader Pivot Intelligence — research publication and P0B-30M kickoff

Parent: **WS:LIVE-ENTRY-RADAR / RS Pullback Launch**. This is an extension of that existing project, not another workstream or entry engine.

The Chairman requested publication and project initiation on October 8, 2026. The complete research text is preserved as the original 14 chapters plus final decision block. Their historical dates, source pins, proposed thresholds, negative results and limitations remain unchanged. The [implementation kickoff](P0B30M_INITIATION_2026-10-08.md) is a separate, later record.

**Current state:** research text saved; a pure, research-only completed-30m descriptor and 29 tests implemented. The tests passed in an isolated exact-source harness. No real market pilot is admitted; no detector, consumer, collector, scheduler, probability or trading authority is activated. Full P0B-30M remains incomplete.

## Read the report

| Chapter | Content |
|---|---|
| [01 — Executive ruling](chapters/01_EXECUTIVE_RULING.md) | MVP A; conditional fixed-multiscale North Star C |
| [02 — Estate and collisions](chapters/02_CURRENT_ESTATE_AND_COLLISIONS.md) | Original source snapshot and incumbent boundaries |
| [03 — Public evidence](chapters/03_PUBLIC_EVIDENCE_SYNTHESIS.md) | Primary research and its limits |
| [04 — Source register](chapters/04_SOURCE_REGISTER.md) | Internal pins and external primary sources |
| [05 — Hypotheses](chapters/05_HYPOTHESES_AND_FALSIFIERS.md) | Explicit rivals, falsifiers and prior kills |
| [06 — Relative architecture](chapters/06_THEME_RELATIVE_ARCHITECTURE.md) | Ex-self groups, residuals, support and PIT themes |
| [07 — Clocks](chapters/07_CLOCK_AND_TIMEFRAME_DESIGN.md) | G/A/K/D, session anchors and matched memory |
| [08 — Empirical protocol](chapters/08_EMPIRICAL_PREREGISTRATION.md) | B0/P1 first; later bounded comparisons and gates |
| [09 — Models](chapters/09_MODEL_ARCHITECTURE.md) | Separate targets; no opaque confidence score |
| [10 — Product](chapters/10_PRODUCT_AND_UX_SPEC.md) | Descriptive states, evidence and replay |
| [11 — Ownership](chapters/11_OWNERSHIP_AND_INTEGRATION.md) | Existing owner-native integration |
| [12 — Masterplan](chapters/12_IMPLEMENTATION_MASTERPLAN.md) | Staged source, model and product work |
| [13 — First implementation handoff](chapters/13_IMPLEMENTATION_HANDOFF.md) | Real-source witness and full P0B-30M DONE_WHEN |
| [14 — Open questions](chapters/14_OPEN_QUESTIONS_AND_ACCEPTANCE.md) | Claim-specific blockers and acceptance accounting |
| [Final decision](chapters/99_FINAL_DECISION_BLOCK.md) | Recommended build and do-not-redo boundaries |

## Exact reproduction

The 15 chapter files reconstruct the delivered **124,006-byte** Markdown report exactly:

`SHA-256 f73b345fa542768008c6a7271d7eacc6f46b57a26ddf3c62b18010aae65365a9`

From this directory:

```sh
python verification/rebuild_report.py --output /path/to/new/leader_pivot_report.md
python verification/mechanical_audit.py --output /path/to/new/mechanical_results.json
```

The first command verifies [SOURCE_BLOBS.json](verification/SOURCE_BLOBS.json), reconstructs the exact report and refuses to overwrite an existing destination. The original audit executes 40 mathematical/synthetic assertions, not 40 market experiments. Its reproduced result digest is `d6904e5e0115ee35c13e24bca72831f74104a7991e89ff2569fec2f53ed8023c`.

This GitHub source publication stores all report text, the original source-free audit and the new implementation/evidence files. The duplicate rendered PDF/HTML and ZIP exports remain conversation attachments; they are not claimed to be GitHub assets. Research references to earlier attachment delivery retain their historical scope.

## Initial implementation

- `engine/entry_radar/replay/leader_pivot_descriptor.py`: calls the existing Phase-1 panel owner and its minute aggregation helpers; owns no data store, admission or live lifecycle.
- `tests/test_entry_radar_leader_pivot_descriptor.py`: reuses the existing Phase-1 synthetic fixture.
- [Verification receipt](verification/P0B30M_CONFORMANCE_2026-10-08.json): actual red/green identities and proof limits.

The bounded tranche uses four prior full 30m bars from the same supplied session and preserves the Phase-1 owner's existing combined daily eligibility. This conservative warmup scope is **not** a final experiment-population decision. Confirmation, invalidation, expiry, actual issuance, approved consumer enrollment and the real admitted witness remain unfinished. Neither a synthetic pivot nor an `OBSERVED_MARKET` input label can set `source_admitted=true`.

No old source carrier, original refusal, registered calendar, incumbent Entry Engine or research threshold is changed. Keep publication/review, source admission, scientific efficacy and deployment as separate gates.

## Additive Terminal design proposal — 3 November 2026

[Terminal Rotation & Pivot Intelligence](ROTATION_PIVOT_EXTENSION_2026-11-03.md) connects the existing RS study, Leadership Rotation measurements, Quote Hub and Radar/Evaluation owners into a proposed live observation and causal pivot-watch experience. It includes the current-code integration audit, primary research and counterevidence, latency/clock requirements, Terminal UX, staged backtests and implementation slices.

Status: **SPEC_ONLY**. This dated proposal does not change the historical report, existing DNR dispositions, admitted source/experiment state, event authority or production behavior. No new market backtest or live forecast is claimed.

## R1 implementation candidate — 3 November 2026

[Terminal PR #1259](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1259), head `17798f2331ab24c0821cc76d9d6761e3c195e842`, implements a current-session **Rotation monitor** beside the RS × 30m study. It compares eleven sector ETF proxies with SPY over common completed 5m/30m intervals, separates prior-close returns, displays source ages and fixed coverage, and transfers a selected ETF into the existing study controls.

Local verification passed **95 unit/component tests** and **24 responsive browser journeys** across desktop, tablet and phone in English and Chinese, plus TypeScript, scoped lint and whitespace checks. The [implementation evidence](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/17798f2331ab24c0821cc76d9d6761e3c195e842/terminal/docs/rotation-regime/r1/README.md) contains the source contract, commands and synthetic-fixture screenshots. The [Agent OS handoff](https://github.com/mastermindx-market-intelligence/macro/blob/41e31ce7ec4a1c70c7c31080a8deb02b53ffd4b8/agentos/handoffs/LIVE-ENTRY-RADAR-2026-11-03-rotation-r1.md) records the original workspace, review request, exact next actions and non-retry dispositions.

Status: **IMPLEMENTED_CANDIDATE / LOCAL_PROOF_ONLY**. Hosted CI and a requested non-author review remain separate gates; no merge, deployment, production latency qualification, admitted market backtest or predictive edge is claimed. The broader specification, prospective pivot work and original B0/P1 research programme retain their existing scientific and authority boundaries.
