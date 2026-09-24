---
key: MARKET-TIDE-RESEARCH-FOUNDATION-20260924
claim: "Time decay and falling implied volatility do not imply uniformly supportive dealer hedging: a fixed-price short-put model reverses hedge-flow signs between out-of-the-money and in-the-money positions."
falsifier: "Inspect #7929 and run git show 8de2d6b386ba2b9102c708caf6db71af84929167:agentos/discoveries/DSC-MARKET-TIDE-RESEARCH-FOUNDATION-20260924.md; execute the contained Python short-put example. Incorrect signs or arithmetic falsify this specific model illustration."
so_what: "Use the tested C1-M1 numerical runner to investigate the frozen event/momentum question without granting supplied inputs qualification or conflating risk, opportunity and trading authority."
kind: constraint
verified_at: 2026-09-24
verified_by: "Macro #7925/#7929; original mechanical example remains at 8de2d6b386ba2b9102c708caf6db71af84929167. MARKET_TIDE_C1_M1_RUNNER_PROOF_2026-09-24.json records 40 native tests and a synthetic end-to-end benchmark at c2a00e4d392c9328bd8415c1f337daa9208e8934; no empirical market edge."
scope:
  - macro
  - WS:ADVANCED-DATA-OPTIONS
  - market-tide-research-20260924-sol-001
confidence: verified
---

# Market Tide — cumulative continuation

## Mission, authority and carrier

Sol retains the Chairman's live September 24 end-to-end research/product commission and continuation. User job: exposure and entry/exit/re-entry preparation using expiry/positioning, ordered economic events, and observed trend/participation/stress. Machine job: useful synthesis with honest evidence quality, availability, horizon and invalidation. A dedicated page remains conditional on useful evidence. Research prioritization, forecast qualification and trade/size authority stay separate.

Operation `market-tide-research-20260924-sol-001`; research parent Macro #7925; same checkpoint comment `5812208225`; same Draft/HOLD PR #7929 and branch `claude/market-tide-research-20260924-sol-001`. GitHub remains the sole source writer. No replacement workstream, runtime Job, source lease or control plane.

Fresh protected procedure: Mastermind `819abc8c23609cdded2b33f6e1bfc7854bd5c847`, Skillpack 1.0.1/bootstrap 1. INDEX and same-revision COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT blobs match their previously fully read canonical contents. The present Chairman continuation authorizes this bounded research implementation; it does not authorize production forecast or policy promotion. Retained execution rationale: PRINCIPAL_JUDGMENT on frozen statistical/time semantics plus lower total overhead for the focused native test/repair loop. No worker was submitted.

## New executable capability

Before: C1-M1 was a frozen method and measurement illustration. After: `research/options_estate/market_tide_c1.py` implements the supplied-prepared-input numerical benchmark, with exact fixed-window arithmetic, four comparators, monthly chronology, maturity/purge checks, mean-consistent scoring and paired block uncertainty. It is research software, not a live forecasting service or admitted study cohort.

Exact tested code head: **`c2a00e4d392c9328bd8415c1f337daa9208e8934`**. New proof record added at **`afb832dbd52f61dd884b934f8035d3aa781542bd`**:
`research/options_estate/MARKET_TIDE_C1_M1_RUNNER_PROOF_2026-09-24.json`.
Later record-only commits do not become tested code heads by implication. Final candidate head/blob and checkpoint readback are recorded in #7925.

Source identities:
- Runner `research/options_estate/market_tide_c1.py`, blob `4cd4200a040d2cfbe372fd07a7d7694bdb129ea2`, SHA-256 `a1d507100615319f9c02db9dfb8ca71fac3d199a1a2aca27165c124f7caf06f4`.
- Main tests `tests/test_market_tide_c1.py`, blob `e6da925f60e0950d9372e9f2e46f137ec7716290`.
- Adversarial tests `tests/test_market_tide_c1_boundaries.py`, blob `d75da274311d587cd5df4550dadeb982e7b01526`.

### Actual proof and defects repaired

Native Python 3.12.14 / NumPy 2.5.3, using complete repository `lib.dataos.temporal` rather than copied time functions. Forty focused tests passed at the exact code head. No dependency installation or new worktree.

Tests were committed before implementation at `6e274db15ad4b00ac00d1a5115f510eadbc3e7c1`. The initial suite reported a class-setup error from the missing module, not 35 behavioral failures; a separate explicit presence assertion then failed. First implementation passed 35 checks. Five further adversarial checks at `5577275f2eb01775813426d3ff5c21ffc8033017` produced two failures and three passing controls. The repair at c2a00e4d39 fixed:

1. Exactly constant nonzero columns could have a tiny nonzero computed standard deviation from floating summation; the implementation now detects exact equality of observed training values and maps constants to zero without a tuned threshold.
2. Completed-close inputs could carry an availability timestamp before the supplied session close; the runner now rejects that impossible ordering. A later decision still cannot claim a same-close fill.

Other discriminators verify that future targets do not change earlier predictions, label availability equal to the training cutoff remains excluded, incomplete training-year coverage does not pass, missing events do not become zero, feature groups remain nested, repeating the same training rows does not weaken a mean-loss ridge penalty, and the optimized bootstrap matches an independent direct-index implementation on 10,000 draws.

Final process 3050 printed 40 passing tests and a successful actual CLI result. Its final unrelated zsh cleanup assignment used the reserved variable `status`, so the aggregate shell exited 1 after those successful subprocesses. Separate same-carrier process 3366 then verified clean `git diff --check`, empty `git status --short` and exact HEAD. Do not relabel the aggregate wrapper as exit 0 or repeat the already-proven tests merely for that shell typo.

### Synthetic end-to-end result, not market evidence

The committed test factory supplied 1,310 synthetic prepared origins and an explicitly synthetic weekday roster. At evaluation 2022-01-20T00:00:00Z, the CLI produced 25 monthly refits and 528 held-out predictions starting 2020-01-01. There were 111 synthetic event origins and 417 other origins; distinct synthetic event dates CPI 48 / NFP 40 / FOMC 32. These are not actual exchange sessions or releases.

All four comparators, 63-session primary and 21/126-session sensitivity bootstrap calculations ran with 10,000 draws each. Input JSON traveled in memory through stdin; no market data file or new corpus was created. CLI exit 0, empty stderr. Input SHA-256 `f5a84e2e732244f13a1879dd8b875e0f7ad54cd16114d2a4f688deed623f60bf`; output 216,750 bytes, SHA-256 `49bfd981e01e69e7b6a166973e25265f10d28fbe13c442d42ab3dc8934a26280`. The boundary fixes did not change that normal-path output.

The runner always leaves source admission, forecast publication, promotion and trading authority ungranted. It does not authenticate its supplied roster or prepared numerical values. `measure_closes` supplies arithmetic; the owner-qualified historical-row adapter remains a separate unbuilt dependency. No supplied `source_qualified` flag can release the hold.

## Frozen method and remaining conformance

C1-M1 remains unchanged: conditional mean of original normalized five-session downside Y5; N training mean; P/PE/PEI fixed nested features; fixed 0.01 mean-loss ridge; train-only continuous scaling; unpenalized intercept; negative prediction clipping; minimum three full training years; monthly fits with mature, purged labels; common paired cohorts; primary MSE with secondary MAE; event floors 40 CPI / 40 NFP / 30 FOMC; seed 20260924 / 10,000 paired 63-session resamples / 97.5% intervals and 21/126 sensitivities. No OPEX window optimization, GEX rescue, full-sample regime threshold, new oscillator or live risk multiplier.

Implementation choices made before market outcomes: month-start 00:00 UTC is the computational fit cutoff; complete-year accounting compares supplied eligible origins against supplied calendar coverage before ordinary boundary-label purge; both remain subject to independent review and real source qualification. Calendar coverage declarations are not an authentication service.

Remaining diagnostic clauses are explicitly printed by the runner: risk-strata diagnostics, descriptive 1/3/10-session views, and cross-instrument report composition. Per-year and leave-one-test-year-out **score** influence are present; the latter is not refitting the model without that year. No claim of complete empirical evaluation or full preregistration acceptance.

CI enrollment remains owed: the inspected existing job is `.github/ci/legacy-jobs.yml::unrun-factor-research` (near line 11561 at the tested checkout); it does not name these new tests. Adding them requires current shared-file custody/collision reconciliation and the existing CI owner, not another workflow. No CI configuration was changed, no hosted current-head result inspected, and no manual rerun/dispatch performed.

## Preserve prior results and exact ownership

- Original Greek-sign illustration at `8de2d6b386ba2b9102c708caf6db71af84929167`, R0 preregistration/unexecuted state, R1 design and C1-M1 amendment remain unchanged. Do not repeat the 16-check scoring illustration or source census.
- Existing event consumer is unchanged and was not retested this tranche. Its prior 35 native tests/full-owner CLI at `cb79d84ae460db4a5148cb4b2552b39c6f47448f` remain separate proof; documentary input does not provide complete schedule coverage.
- Frozen panel v2026-08-06 remains INELIGIBLE_FOR_C1_PRIMARY for insufficient chronology. Market Memory raw v1 and unadjusted REST v2 are not dual-basis total-return inputs. Do not re-open those exact dispositions without a material invalidator.
- MAS-260/#7328 GEX-transfer rejection, receipt SHA-256 `5f241659cda73bb9283de75875b630ee79482ff318df674fb3541f095541b975`, local lock/CI-deferral and 30/60/90/120-minute scope remain untouched. Historical current-membership breadth remains excluded.
- Prior tail OOS audit at `3774cd2cc40b9e4e7e11c34c90e7fccd4b4bd294` recovered A4; do not recover it again. Published point estimates are not replicated returns. Later minutes cannot enter earlier decisions; unstandardized moment scale is not standardized shape. Tail-return replication remains separate from C1 downside.
- Risk versus opportunity and preregistered re-entry conditions remain the product thesis. Existing event/price/Market Memory/Risk Radar/Portfolio/Prophet/learning owners retain their authority.

Owner-reference inquiries remain exactly MAS-204 comment `fffe9f72-7379-40e9-a117-580bbb26d404` and MAS-94 comment `356dafb3-8370-486c-b768-7db190757188`. They requested existing refs only. This implementation tranche did not inspect new replies; do not claim a response or an active worker. Consume actual returned evidence before another source search.

## Custody, holds and continuation

Native locked detached verification checkout: `/Users/chriswong/lanes/repos/macro/.claude/worktrees/market-tide-research-20260924-sol-001`, MacBook device `2b8a329e-0a82-413c-b9d0-958a7de6d836`, interpreter `/Users/chriswong/lanes/venv/bin/python`. Latest verified native HEAD is c2a00e4d39; only exact-commit clean fast-forwards occurred. GitHub remains sole source writer. No primary checkout change, new worktree, unlock or custody transfer.

Earlier R0 acquisition/write, R1 native data footer/hash and combined local full Agent OS validator/options-manifest refusals remain held TOOL_DEGRADED/EFFECT_NONE. None was retried, rephrased, moved or delegated. This tranche has no new safety refusal or unresolved modifying effect. All native processes have returned. No worker, child, watcher or automatic wake is active.

Keep #7929 Draft/HOLD/unarmed. Independent code/method review, test enrollment/required exact-head CI, full record/source acceptance and eventual production/browser proof remain owed. No admitted market cohort, empirical timing edge, live page, sizing or trade effect, merge or deployment.

**Exact next unit:** complete the remaining frozen diagnostics with test-first implementation and reconcile enrollment of the two suites in the existing CI job; consume any actual data-owner reference returns without repeating their investigation. Then connect an owner-qualified prepared-input cohort and run C1-M1 only when its source/coverage gates are met. A source-owner return is not automatic admission; the runner's synthetic output cannot supply it.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION only after this record/proof and the same-comment exact-head checkpoint are read back. MISSION_COMPLETE: false. Boundary: initial executable C1-M1 numerical core, end-to-end synthetic run and discriminating repair tranche completed with substantial accumulated implementation/native-test context. This is continuity, not completion, cancellation or writer release. Intended resume: fresh accountable Sol conversation from #7925 comment 5812208225 and this exact candidate, not historical tool replay.

DO_NOT_REDO: programme/branch/PR/workspace; prior R0/literature/measurement/source audits; A4 recovery; rejected panel/profiles/GEX/calibration; unchanged event component; now-passing C1 tests absent changed code/dependencies; refused effects; or existing calendar/clock/source-freeze/forecast/learning/control owners.
