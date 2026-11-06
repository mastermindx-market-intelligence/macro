# Macro PR #7503 — qualified historical audit record

## Records integration — 2026-11-06

This record preserves the useful plain-language, theme and claim-calibration findings from the original 2026-09-21 audit. The original product PR is already merged. This records integration does not rerun its tests, re-audit the live dashboard, release the held migration, or give historical PASS statements new acceptance.

The original audit remains available at [Macro 63b581e48eeb94bdd29a5f6c798367525c0b686e](https://github.com/mastermindx-market-intelligence/macro/blob/63b581e48eeb94bdd29a5f6c798367525c0b686e/orch/audits/macro_PR-7503.mm.md), blob `ac34f51480cafbe2fa6f7d948d9b8b52c3394ed4`. This path was absent from integration base `6931368ff29e250ce3c0065cfbf52cc2133b27c1`; the record is therefore useful retained evidence, not a filename-only duplicate.

## Exact product identity

| Field | Source-confirmed value |
|---|---|
| Product PR | [macro#7503](https://github.com/mastermindx-market-intelligence/macro/pull/7503) |
| Title | fix(macro): remove stacked UD-B1 hero from primary dashboard |
| Author | `mastermidx4` |
| Original branch | `sol/macro-unified-primary-rollback-20260920` |
| Final source head | `d1586a7f49a77519ceb40f27842499ff989816fd` |
| Merge commit | [c125178ed4e146e4cc15a4caa5586c790df0a13d](https://github.com/mastermindx-market-intelligence/macro/commit/c125178ed4e146e4cc15a4caa5586c790df0a13d) |
| Merged at | 2026-09-21T14:24:09Z |
| Original change | 12 files; +2657 / -593 |
| Current integration scope | Two historical audit records in Macro #7642; no product source change |

The original audit's alternative branch name `mastermidx4/fix/macro-remove-stacked-ud-b1-hero-20260919` is corrected above from the native PR record. Source head, merge commit and deployment proof are separate identities.

## Preserved outcome and design boundary

The source diff and original PR body describe a composition rollback. The UD-B1 hero was stacked above the established US dashboard, duplicated its primary regime decision, and exposed four of five cross-market spine rows as designed-null `BLOCKED_DATA`. Its top score used the default US `market_state` profile (`SPY / QQQ / IWM`), so labeling that score as a global composite overstated its scope.

The template include and committed `site/macro.html` hero were removed. The established `#regime-radar` remained the first primary decision surface. The UD-B1 component, CSS, specification and evidence were retained for redesign, not discarded.

The original disposition preserves accepted UD-B2-W1 US volatility-weather work and UD-B2-W2 HK/CN persistence and component bindings. The engines, persisted artifacts, component tests and evidence remain DO_NOT_REDO. Keeping the candidate off the primary route does not revoke those capabilities.

The recorded route decision remains explicit:

- `intl.html` is the ex-US international-economies comparison; the full hero is not to be moved there wholesale.
- `markets.html` is the existing global-cycle route. A compact successor should be evaluated through that route and its owner, using truthful global/country evidence.
- Primary-route migration was held under `DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` and `BL-G121`. This record does not lift that hold or commission a new dashboard.
- The original #6685 dashboard/site custody collision must be reconciled by its owning lane if it proceeds; this record makes no mutation on that branch.

The exact source disposition is [research/UNIFIED_DASHBOARD_DISPOSITION.md at the original head](https://github.com/mastermindx-market-intelligence/macro/blob/d1586a7f49a77519ceb40f27842499ff989816fd/research/UNIFIED_DASHBOARD_DISPOSITION.md).

## Useful audit findings

### Plain language and null disclosure

The deleted hero removed a US-as-global labeling hazard. The HEALTH strip gained four distinct states: `health-unknown`, `health-warn`, `health-ok` and `health-neutral`. The inspected template diff distinguishes no observations, active failures, all observed sources OK, and no active failures with blocked observations. It adds an empty-state table row.

The bilingual tooltip says “No entries means health is unavailable, not healthy” / “没有记录表示健康状态不可用，并不代表正常”. The corresponding empty-state message says that source health data is unavailable for this build. These are the useful copy and truthfulness findings retained from the original audit.

The original manual vocabulary scan distinguished technical CSS attributes/classes and operator comments from visible copy. It reported no newly introduced user-facing validation language. This is retained as a historical scoped assessment, not a freshly executed plain-language checker result.

### Theme and CSS fingerprint

The source file list confirms the new 2,389-line `site/assets/css/cac49af2.css` asset and the committed page's fingerprint change from `bdd40640` to `cac49af2`. The report describes externalized dashboard styling and the retained spine-caveat rule. The template's new neutral/unknown marker uses `var(--ink-3)`; the inspected surrounding rules also contain literal fallbacks for existing up/warn tokens.

The original audit's universal “token-only” wording is too broad: its own detail acknowledges literal ink colors and fallbacks. Preserve the narrower observation that the styling uses the existing token and theme-selector patterns. The reported contrast values, broad color inventory, dark/light/ZH parity and TP-0 assessment remain historical claims. This integration did not measure contrast, review screenshots, inspect every generated CSS declaration, or rerun visual gates.

The original report also mixes “next merge”, an earlier clock time, and “46 minutes later” when comparing #7621. That chronology is not adopted here. The related fingerprint-rebinding example is not needed to prove #7503's source change. Nor does a changed fingerprint establish that an older asset can never be served again; no new cache or production-delivery assertion is made.

### Claim calibration

The original PR body reports 38 pre-existing broad-estate validated-claims findings and says this deletion adds none. Preserve the distinction between a scoped contribution and a broad estate count. This records integration does not independently reclassify those findings, certify the whole estate, or assert that deletion alone proves all claim checks pass.

The original report's PASS verdicts are retained as the original auditor's conclusions. The useful implementation outcome is the truthful route composition and null-state disclosure, with explicit limits on authority and production acceptance.

## Historical execution evidence, attributed

The following results are reported by the [original PR body](https://github.com/mastermindx-market-intelligence/macro/pull/7503). They were not re-executed in this records integration.

| Original reported check | Historical result |
|---|---|
| Focused unified-dashboard and dashboard-template pytest command | 73 passed; five inherited cleanup warnings |
| Blocklist drift check | OK |
| Template/site synchronization | 99 pairs OK |
| Added-line design-system ratchet | Zero blocking findings |
| Diff whitespace check | PASS |
| Headless Chromium, branch site/macro.html, dark and light, 1440 x 1100 | Zero `#ud-hero`, one `#regime-radar`, radar near y=102, zero page errors |
| Broad validated-claims checker | 38 reported pre-existing findings; original author reports zero introduced by this diff |

A command name or quoted count is not a newly retained execution log. The original body explicitly separates branch browser evidence from the served `mastermind-x.com/macro.html` route. The product's real publication path would need its own source-bound receipt; no fresh production check is claimed here.

## Source surfaces retained by the original product

The native PR file list confirms the template and committed page, the generated CSS asset, four dashboard test files, the disposition document, DO_NOT_REBUILD registry, compiled kill registry, signal-foundry blocklist and CI ownership manifest. The source inspection for this integration read the exact template and disposition patches and native PR metadata. It did not alter any of those product surfaces.

Records integration acceptance concerns the fidelity of this historical summary and the reconciliation of the companion Terminal #701 audit. It does not mark the broader dashboard program complete.
