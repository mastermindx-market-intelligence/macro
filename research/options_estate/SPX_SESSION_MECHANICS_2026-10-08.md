# SPX session mechanics: implemented calculation and recovery receipt

This is a bounded engineering checkpoint, not product acceptance. The new code is
a pure, non-publishing extension of `engine/options_scenario_surface.py` and uses
the incumbent `engine.intraday_greeks.bs_greeks_vec`. It creates no collector,
pricing kernel, source store, forecast lifecycle, or event ledger.

## Source and custody

- Full commission recovered from
  `/Users/chriswong/Downloads/CODEX_SPX_SESSION_MECHANICS_EXECUTION_PACKET_2026-10-08.zip`.
  The complete commission and kickoff were read; commission SHA-256
  `2ab447c172db12a996755fdeb9a950c344bf33fe181bafd263dc3b37a55cdf08`
  matches its manifest. The earlier missing-document blocker is resolved.
- Protected Mastermind procedure pin:
  `ad362ef45def043ee5970c2b131be9825fcea1ae`; same-commit Skillpack INDEX,
  ACTIVE_EXECUTION, SESSION_RELIABILITY and delegation procedure were consumed.
- Implementation base: Macro `4fd2d0e2b2fb0eeb5d98222e01c4a8b36d9e9396`.
  Carrier: `claude/spx-session-mechanics-20261008`, in the existing protected SSD
  worktree. This additive scenario calculation does not replace the Outlook
  carrier or republish its outputs.
- MAS-260 Macro branch `claude/mas260-exposure-baseline-20260918` survives at
  `b281fe529717656e070abaa15651c75fb74bf93f`. The issue's `700a33c2` frontier is
  older. The later commit already incorporates the separately developed
  calibration lane. Original Macro PR [#7328](https://github.com/mastermindx-market-intelligence/macro/pull/7328)
  remains open, labelled `hold`, at remote head
  `9515f2558a006c913a7c0eb30d966c47fa1a143b`; its local-only/CI-deferral history
  has not been treated as a new publication grant.
- Retained Terminal consumer branch
  `claude/mas260-exposure-outlook-terminal-consumer-20260921` is at
  `be92323426d9971ebd881ce3df6c529f182dc22d`. The separate original worktree
  `mas260-exposure-outlook-terminal-20260921` is at
  `6610c157c2498692b1550ed21be10e7d6f7f01ec` and still contains two untracked
  exposureOutlook files. Both branches and those files were preserved.
- Research PR [#8555](https://github.com/mastermindx-market-intelligence/macro/pull/8555)
  is draft at `82bc91ba18684f4a2c7f7f83ffd0c8d2a80625a6`, with native auto-merge
  null. Its `HOLD-FOR-SOL / DO NOT MERGE` boundary remains intact. Its dealer
  pressure corpus and the October 3 Options Intelligence contracts informed this
  bounded calculation; neither is a merge or data-rights grant.

## Implemented behavior

`build_inventory_scenario` conditions explicitly supplied signed positions on an
already-qualified customer-initiated signed Flow aggregate. Every contract needs
an explicit observation, including measured zero. For assumed dealer participation
`a`, the endpoint position is `n1 = n0 - a * signed_flow + nontrade_adjustment`.
Trade increments and nontrade adjustments remain separate in the output. Omitting
adjustments means an explicitly labelled zero-adjustment scenario assumption;
an explicitly supplied partial/unknown adjustment map is refused. This is a scenario, not
inferred actual dealer ownership. The Flow owner retains signing, corrections,
packages, deduplication and source availability qualification.

`build_hedge_target_change` reprices both endpoints of every selected member of
the supplied contract universe. It computes `B0 = -sum(n0 * multiplier * delta0)`,
`B1 = -sum(n1 * multiplier * delta1)`, and `Q = B1 - B0`. Its USD reference
notional is `target_SPX * Q`; it is not the change in dollar delta, actual trading
cash, or a count of ES contracts. Symmetric inventory/repricing attribution sums
back to Q, with an explicit numerical residual. A linear Greek approximation and
its residual remain diagnostics. Gross contract changes and the net/gross ratio
disclose cancellation; they do not estimate path turnover or market impact.

The calculation requires explicit SPX/AM or SPXW/PM identity, expiry, fixing
instant, right, strike, $100 multiplier, positive IV, signed start/end positions,
an expected contract-ID denominator, and a causal source receipt. It uses exact
time remaining in seconds, not a vendor one-hour floor. At or across fixing it
returns unavailable pending a separately qualified settlement/unwind model.
Missing contracts, unknown selected inventory/IV, stale sources, empty expiry
selection and nonfinite repricing cannot become zero exposure. Ambiguous identity,
duplicate economic contracts, duplicate JSON keys and impossible availability
ordering are rejected.

The receipt's clocks and reference are caller assertions. A successful calculation
does not independently qualify those assertions, data entitlements or distribution
rights. Supplied source and contract-reference revisions survive content identity;
unknown revisions remain null. Coverage means the supplied universe only. Optional selected expiries are
shown alongside expected/received/selected counts. The output always denies
publication, calibrated-probability, observed-inventory, executed-flow and trading
authority. The old scenario-surface function/schema and default CLI mode remain.

The reconciled commission slice adds `0DTE`, `1-7D` and `8+D` sums classified by
calendar days at the New York anchor date. Their signed changes reconcile to the
covered-book change. Endpoint cohort migration is disclosed separately, without
moving the anchor denominator or counting exposure twice. A complete explicit
`target_iv_by_contract` map permits a supplied endpoint volatility surface instead
of a parallel shift; combining both shocks is rejected. It remains a conditional
endpoint assumption, not a predicted volatility path. Ranking, portfolio, sizing
and auto-exit authority are also explicitly false.

## Reproducible local evidence

Synthetic fixture: `research/options_estate/SPX_HEDGE_TARGET_FIXTURE_2026-10-08.json`.
It is one invented SPXW contract and has no observed-market evidentiary value.

```sh
python3 scripts/build_options_scenario_surface.py --mode hedge-target \
  --input research/options_estate/SPX_HEDGE_TARGET_FIXTURE_2026-10-08.json \
  --output /Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/synthetic-hedge-target-v2.json
python3 -m pytest tests/test_options_scenario_surface.py tests/test_intraday_greeks.py tests/test_gex_engine.py -q --disable-warnings --maxfail=2
```

CLI exit 0; fixture output SHA-256
`8dcc57469e9c361d20f893022ea924afd37c4fe13a8f81cdb5b23a20f6ea4f5f`.
Target change is -3741.9617374099907 SPX index-equivalent risk units; attribution
residual is 2.2737367544323206e-13. This is an arithmetic demonstration only.
The regression command passed **183 tests**, one warning, exit 0. Tests include
independent scalar normal-CDF deltas through the final hour, puts/calls, both
inventory signs, zero moves, telescoping endpoints versus path turnover,
large-move linear residuals, netting, overflow, missing data, stale/late clocks,
fixing boundaries, expiry selection, conditional Flow and CLI compatibility.
Existing `options-data` CI enrollment already includes this test suite.

The unchanged October 3 reference reproduced **83 assertions**, exit 0, to
`/Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/oct03-reference-reproduced.json`.
The held October 6 witness wrote 62 passing numerical assertions but its complete
CLI exited 1 at figure rendering because Matplotlib is absent. A separate
numerical-only runner, `compare-held-witness.py` in the external evidence directory,
reran all **62 assertions**, then compared the unchanged 14-contract witness to
the actual incumbent-owner function: **PASS**, exit 0, target-change error
`7.275957614183426e-12` risk units. Receipt `held-witness-comparison.json` explicitly
records that no figure was rendered. Both witnesses are synthetic, not market
backtests or independent review of this implementation.

At first implementation head `4b3b1dbbbe66e2999e6485ed311c365d6114a417`,
`python3 scripts/check_contract_delta.py --base 4fd2d0e2b2fb0eeb5d98222e01c4a8b36d9e9396`
exited 0; its log is retained outside the repository at
`/Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/contract-delta.log`.
`python3 scripts/agentos.py validate` exited 0 with zero errors and 97 warnings
on other existing records. `git diff --check` exited 0. A prepublication fetch
advanced `origin/main` to `1f1580ef4f09`; none of the three modified code/test files
or the parent workstream changed between the pinned base and that revision.
Hosted CI run `37885493384` succeeded on that exact first head: all twelve packs,
contract-delta and ci-gate passed. This is prior-head proof; the commission
reconciliation requires its own exact-head CI before acceptance.

## Recovered scientific findings

These are recovered historical results, not experiments rerun in this session:

- At Macro `b281fe52`, `EXPOSURE_OUTLOOK_CROSS_INSTRUMENT_ABLATION_2026-09-21.json`
  has SHA-256 `5f241659cda73bb9283de75875b630ee79482ff318df674fb3541f095541b975`.
  QQQ's static local-GEX 120-minute mean CRPS improvement is negative
  (-0.00007751462099308137; day-block interval excludes zero); IWM has only one
  eligible exposure record. The state challenger also worsens Brier score.
  Exploratory SPY performance is not robust cross-instrument forecasting proof.
- At the same commit, `EXPOSURE_OUTLOOK_CALIBRATION_REPLAY_2026-09-21.json`
  has SHA-256 `2b66127aaa59f89dc1a37e6107898d4a6c18b9e0610ef6ac46de3a75a83bfbc6`.
  Widening-only and signed-CQR adjustments both failed the proper interval-score
  gate. Historical consumer availability remains unverified. Raw uncalibrated
  quantiles must not be promoted to calibrated probabilities.

The new SPX targets remain separately **NOT_EVALUATED**: 15-minute excursion,
remaining-session high/low, and closing outcome. The recovered negative evidence
neither licenses their publication nor proves a null for these new hypotheses.
No unsigned-OI, public Flow reconstruction, or participant-informed contender has
yet passed a common point-in-time SPX evaluation in this assignment.

## Current external gates and exact return conditions

1. **Commission recovered and mechanics reconciled.** The ZIP identified above
   resolves the missing-file gate. Its S1-S6 acceptance slices remain separate;
   reading the document is not source admission, independent review or acceptance.
2. **Raw source access unproven.** The existing local ThetaData owner's health read
   at configured 127.0.0.1:25503 returned ConnectionError. A single read-only request
   through incumbent `m1` transport failed before execution with exit 255,
   `exec request failed on channel 0`. No lease, service or credentials were changed.
   This does not prove that SPX history is absent or that licensing was refused.
   Resume source qualification when the existing source owner can serve a raw
   SPX/SPXW reference/quote/history sample with genuine availability clocks.
3. **Aggregate is not raw/live proof.** Committed `site/gex/SPX.json` is dated
   2026-10-08; `site/options_structure/gex_state/SPX.json` is dated
   2026-10-08T16:00:00-04:00. These are aggregate artifacts, not an independently
   qualified intraday book, live SSE chain or dealer inventory. No one-minute
   data was manufactured from candles.
4. **Rights scope partially established, not absent.** The existing
   `research/licenses/THETADATA_ENTITLEMENT_RECORD.md` records operator-confirmed
   private/professional subscription, Full Trade Stream and purchased
   display/redistribution rights. The remaining Theta gate is the written
   full-universe intraday-derived Terminal scope and prepublish terms check.
   No participant-tagged historical dataset or ES basis/history entitlement was
   established. Stock-data rights do not establish futures rights. No purchase was
   made. Standard identity follows
   [Cboe's SPX specification](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications/).
   [ThetaData's Greek-history documentation](https://thetadata.net/docs/operations/option_history_greeks_all.html)
   makes its time-to-expiry convention a qualification question; the local kernel
   itself is not floored at an hour. Vendor Greeks are not automatically suitable
   for final-hour inference. ES risk conversion additionally needs its own basis
   and contract evidence, not just a multiplier.
5. **Scoped independent mechanics review now passes.** Executive exposed read-only server 1.4.0.
   The permitted manual Fabric adapter request
   `spx-01a11ee7-contract-review`, rooted at
   `01a11ee7-d9fe-71f1-b582-193891266722`, returned exit 75
   `ECONOMIC_POLICY_REFUSED: leaf_labor_requires_escalation` before launch.
   The refusal was not retried through another carrier or native child. The separately user-assigned SPX principal reviewed exact `4e7e44bfcce3bf1292978266b813633bd6bbe5db` read-only, without retrying that dispatch or launching another worker. Its scoped numerical verdict is recorded below; Fabric admission, protected GitHub review and release remain separate.
6. **Production acceptance unavailable.** Actual Chrome navigation to
   `https://app.mastermind-x.com/options?tab=gex` confirmed a signed-in account but
   displayed the Options subscription gate. No trial or subscription was started.
   Screenshot: `/Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/production-options-entitlement.png`.
   This proves current access behavior only. No new source-to-API-to-browser,
   EN/ZH, mobile or deployed-product acceptance has occurred.

## One integration owner and disjoint source lane

Root `01a11ee7-d9fe-71f1-b582-193891266722` and PR #8684 remain the integration
owner/carrier. Sibling chat `01a11eed-84cf-75e1-af19-fec04c4e4d5e` acknowledged the
disjoint S1 source-contract/clock/rights lane and
`research/options_estate/SPX_SOURCE_ADMISSION_2026-10-09.md`; its subsequent
`collectors/thetadata.py` / `tests/test_thetadata.py` clock-retention repair is
disjoint from the scenario engine/tests/CLI. Its source-return evidence must be
consumed before any integration; no duplicate source acquisition or child exists
in this integration chat.

Terminal `master` was read at `048e019caf84fc8c2bc0e4180de313d6a02e7ca5`.
Source-path reconciliation confirms OPEN #640 at `df440cac848ffbb973ed6100579f0603ca3c5e19`
owns the typed scenario contract/composition; OPEN #661 at
`edea69ef044c2581bf38a463d1956cf72295e2ab` owns the contour overlay; OPEN #799 at
`8b39aa25a88a71ad437a673c87d460b0eed0e027` owns OptionsWorkspace/statistics; OPEN
#723 at `b85c8e525364719689a01defbaad8e36cc73e693` owns the chart companion.
OPEN draft #846 at `6369e5fa394aa391de5476d4e255285989882f23` owns GexDeskView,
the Options route and Research Lab. Its original chat
`01a118f3-fc4e-7941-b432-03703dccd19b` has a current continuation/CI/review return,
so it is a live integration dependency, not a ghost owner. No second Terminal
writer or transport/publication key was created. The pure JSON calculation is a
research contract; adapting it into the accepted scenario consumer still requires
that existing owner's source/schema reconciliation.

| Acceptance slice | Current scope |
| --- | --- |
| S1 source admission | Partial source/rights findings; actual fresh sample unavailable |
| S2 mechanics | Implemented; independent principal numerical/source-contract review PASS_SCOPED, protected release review remains |
| S3 research verdict | F1/F2/F3 NOT_EVALUATED; previous negative results preserved |
| S4 Terminal integration | Typed consumer built/reviewed in Terminal #870; UI/transport not integrated, active owners retained |
| S5 natural production proof | Not proven; source/release/entitlement gates remain |
| S6 probabilistic promotion | NOT_QUALIFIED; disabled |

Next critical dependency is existing source-owner access; the disjoint S1 source repair has now been integrated. Then qualify the raw book/Flow/clock denominator, review this numerical
seam, and bind it through the already-owned transport and Options Workspace.
Historical evaluation and UI acceptance remain separate gates. No merge,
installation, production publication or deployment is claimed.


## Source integration and independent numerical review — October 9 UTC

Source donor `8027a8aec907369add8ec14e8d3abb77f0131755` is integrated by
cherry-pick as `78d68942de59` on this existing branch. Six source/test/dossier
files retain optional Greek source clocks, keep raw cache/storage evidence,
and expose a deduplicated legacy economic projection. The existing daily test
now resolves its own repository instead of a deleted author worktree. The
[S1 dossier](SPX_SOURCE_ADMISSION_2026-10-09.md) records the exact separate
559-pass/one-existing-path-failure run and repaired one-test pass, rather than
claiming a single green 560-test run. Parent independent source review passed
22 adversarial checks, exit 0; collector/store hashes match the donor commit.
This is source retention and compatibility work, not admitted PIT evidence.

The independent user-assigned SPX principal returned `PASS_SCOPED` on exact
mechanics head `4e7e44bfcce3bf1292978266b813633bd6bbe5db`: **348/348 checks**,
exit **0**. Its separate scalar `erfc` oracle covered 40 synthetic 24-contract
books, varying rates/dividends, endpoint IVs and the final 20 seconds to fixing.
Maximum absolute hedge-target error was `4.656612873077393e-10` SPX risk units.
Four material mutants (one-hour floor, ignored spot move, reversed hedge sign,
dropped contract) were killed. The review also checked attribution/cohort/expiry
identities, selected expiry, permutation/content identity, conditional inventory,
unknown inputs, fixing/availability refusals, finite JSON, authority flags and
CLI duplicate-member rejection. No blocking finding was returned.

Receipt SHA-256: `261d12f5cdd7cb1659b411b25d51399187ce02913d1d6ddb5e253f262e1f1623`.
Runner SHA-256: `808298ad4f3734cb089c29a9bf58c2970de649e87c6c2236a8da974c3103b5b0`.
Both live under `/Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/source-admission/`:
`mechanics-independent-review-4e7e44b.json` and `review_mechanics_4e7e44b.py`.
Review provenance is principal `01a11eed-84cf-75e1-af19-fec04c4e4d5e`, independent
of author/integrator `01a11ee7-d9fe-71f1-b582-193891266722`. The integrated source
repair changes none of the reviewed mechanics, pricing kernel or CLI blobs.
This review excludes source admission, forecasts, live ES conversion, the entire
older scenario-surface implementation, runtime installation and browser/release
acceptance. The old refused Fabric request was not retried or reclassified.

Consumer clarification: `cancellation_ratio` is **abs(net)/gross**, so zero means
maximal cancellation and one means no cancellation. Label it net/gross; do not
present it as percent cancelled. No descriptive or predictive product acceptance
is inferred from these synthetic results.

Integrated parent regression command (the three mechanics suites plus collector,
store, snapshot-poller suites and the repaired daily-path test) passed **502 tests**,
one warning, exit **0**. Log: `/Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/integrated-source-mechanics-tests.log`.


## Terminal consumer return

Draft [Terminal #870](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/870)
is at `dd0284581b78751efbb333b7cff129a1d285c430`, branch
`claude/ssd-spx-hedge-target-consumer-20261009-36bff18d9fffdb05`. Its only new
production file is `terminal/lib/hedgeTargetContract.ts`, SHA-256
`b721f5747dbbd39352a7af854036d148f98304336ae861eddb72a63bd24db4d4`.
It validates and projects the existing Macro output; it does not price options,
fetch/publish data, create a store or modify any existing UI-owner path.

Local validation: **57 Vitest tests**, full repository typecheck after
`next typegen`, changed-file ESLint and diff check all exit **0**.
Independent principal review: **21 probes passed**, exit **0**, with six actual
Macro-owner positive controls. Review found and repaired overflow comparison,
microsecond causal ordering, invalid-calendar normalization, false cohort labels,
contradictory Flow assumptions, and two inconsistent IV policies. Parent tests
also prevent unvalidated extra numeric claims from entering the projection.
All negative examples were reproduced before repair. The original review refusal
and later passes are retained, not overwritten into a first-pass green claim.
Final receipt `source-admission/terminal-independent-review-dd028458.json` has
SHA-256 `f636150f52dbc3422d136aa981eb579686004b0ad4dde8105d393fedbbe3fa36`.

This is a scoped source-contract result. No UI/transport integration, authenticated
Options-content acceptance, theme/language/mobile proof or deployment occurred.
Terminal CI run `37892039909` was pending at the initial exact-head read; the
PR remains draft, labels empty and auto-merge null. The existing Options Workspace
owner retains customer component integration. Explicit platform-required permission
to message its separate user chat is still pending; no duplicate writer was started.

Macro run `37889433748` succeeded on prior mechanics head `4e7e44b` at
`2026-10-09T06:04:48Z`. The later source integration is not covered by that run.
The existing Macro observer must follow the new pushed integration head, while
source access, empirical outcomes, rights scope and real product proof stay open.
