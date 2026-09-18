---
key: OPTIONS-WORKBENCH-R0-REPLAY-GEOMETRY-FAILURES
claim: >
  Options Workbench R0 has source candidates for Terminal geometry/replay, Macro
  gamma-sign correctness and an exact-head expiry/source-clock repair. Terminal #608
  has exact-head hosted CI plus current-base integration proof; Macro #7279 now closes
  the reproduced cycle-start/root-clock/NBBO-clock defects on candidate
  d254917fc6cafb5031f805fa663ca0ddf645ca2d but still awaits hosted CI and independent
  exact-head review. None of these slices is production acceptance or full Quanted parity.
falsifier: >
  Terminal #608 at 1f94c551ff997a50dc915a3d7565d626d89f87c4 fails its mounted
  replay/contract regressions, exact-head hosted CI or current-base integrated browser
  matrix; Macro #7271's modeled regime disagrees with its own gamma curve at spot; or
  Macro #7279 current head d254917fc6cafb5031f805fa663ca0ddf645ca2d fails the
  source-clock regressions/current-base owner pack, exact-head hosted CI or independent
  review before promotion.
so_what: >
  Continue the existing carriers and release gates. Do not redo the old replay/tool
  blocker, geometry repair, gamma-sign repair or #7279 source-clock implementation.
  Keep #7279 draft until exact-head hosted CI and independent review accept the new
  immutable candidate, obtain an independent exact-head review for #608, and preserve
  production proof as a separate post-release gate.
kind: runtime
verified_at: 2026-09-17
verified_by: >
  Terminal #608 current head 1f94c551ff997a50dc915a3d7565d626d89f87c4;
  hosted CI run 35301191243 SUCCESS; current-base proof
  fb361092f4a17c12c303f0de13882b8100143811; Macro #7271 current head
  cadb7ec4a5029150dea3eb9445d9481f3f2aff66; Macro #7279 current head
  d254917fc6cafb5031f805fa663ca0ddf645ca2d with current-main proof
  033a488b9cede633e3decf288ba36197705f7a89 and review comments 5724395435,
  5724455441, 5724614973, 5725715278; parent #603 entitlement ruling 5724610745.
scope:
  - terminal
  - options-intelligence
  - terminal:terminal/components/surface
  - terminal:terminal/lib/heatSeries.ts
  - macro:scripts/build_flow_surface.py
confidence: verified
---

## Mission and authority

Chairman commissioned Quanted-level feature, interaction, reliability and visual
quality in the existing Options Workbench recovery and repeatedly authorized
continuation. Parent: Terminal #603. No new program, pricing kernel, collector,
replay store, control plane, scheduler or runtime is created. Preserve #591/#592,
#598/#599 and Macro #6604.

Protected procedure used for this continuation:
`Mastermind@320f586126b7c82c843ef17612f12d40d20a42e0`,
`mastermind.sol_skillpack.v1` 1.0.1 / bootstrap major 1.

## Terminal #608 — current R0 UI/replay candidate

Carrier: `claude/options-workbench-r0-replay-20260917-sol-001`.
Current head: `1f94c551ff997a50dc915a3d7565d626d89f87c4`.
Original base: `75c22083249e7a1529be3d6baf819b9ad5ea509f`.
Current protected Terminal master used for compatibility:
`82ca818be7ea592f7cdb1fb6731cc19f94610593`.
State: **BUILT_NOT_PROVEN / DRAFT / not merged or deployed**.

The original reproduction and the earlier geometry/cache correction remain preserved.
The formerly missing provider/view/pane integration is now implemented on the same
carrier. One shared replay owner admits and refreshes the live index, preserves an
explicitly paused selected time across new frames and layout changes, refuses malformed
or wrong-root/date indexes, retains usable stored frames on refresh failure, and labels
the end of loaded data as LATEST STORED rather than claiming source freshness.

The price-band renderer maps every numeric band boundary through actual chart price
coordinates, preserving correct proportions on linear, inverted and logarithmic axes.
Current-head revisions refresh field/candle data even when the HHMM filename is
unchanged; ordinary candle growth does not re-fit the user's price view.

Hardening after the first integrated head closes two temporal/semantic defects:
- fetched surface frames are now bound to exact root, accepted session and selected
  HHMM identity, so a same-session 09:32 response cannot wear a 09:31 cursor label;
- Net Premium keeps observed-flow / inflow-outflow language while Gamma/Vanna/Charm
  say positive/negative modeled exposure and disclose observed quote snapshots plus
  prior-day OI. Style-control accessibility uses the same semantic split.

The empty-time-scale route crash found by the browser suite is also closed by checking
for real chart time points before framing; no catch-and-hide or reload workaround.

Current source proof recorded on #608:
- full Vitest: 336 files, 5,548 passed, four existing todo, zero failures;
- TypeScript: exit 0;
- semantic mounted consumer suite: 23 passed;
- semantic replay browser: 6/6 EN/ZH × desktop/tablet/mobile;
- replay/alignment/geometry browser matrix: 30/30, one worker, zero retries.

Fresh latest-base proof for the exact current head:
- merge tree: `bd8e03734eccb8f2d1585b9b7ce29f4407374b70`;
- proof-only integrated commit:
  `fb361092f4a17c12c303f0de13882b8100143811`;
- integrated focused replay/surface/cache/geometry: 180/180;
- integrated TypeScript: pass;
- integrated real-route browser matrix: 30/30.

The earlier full responsive run produced 820 passing / 279 skipped / four failures
outside #608's changed paths. The tablet crosshair case passed on protected master and
on the then-current integrated candidate, so that broad run is not evidence that the
R0 replay candidate itself regressed that owner.

Exact-head hosted GitHub Actions run `35301191243` is now **SUCCESS** for current head
`1f94c551ff997a50dc915a3d7565d626d89f87c4`: unit/typecheck, Quote Hub,
ingest/signal-layer, desktop, tablet, mobile and serial responsive shards all passed,
and the final Terminal typecheck+tests aggregation gate passed. Repository/compatibility
CI is therefore closed for this immutable candidate; independent review and production
acceptance remain separate gates.

Independent exact-head review remains unresolved. The existing bounded review brief in
#608 prefers Terra and is WAITING_CAPACITY / needs_placement. A GitHub `@codex review`
attempt returned the provider usage-limit receipt; it was not blind-retried. Executive
v2 was separately observed READONLY/stale and did not provide a lawful submit path.
No receiver/START or completed independent review is claimed.

## Macro #7271 — local gamma-regime consistency

Current head: `cadb7ec4a5029150dea3eb9445d9481f3f2aff66`.
The implementation semantic head remains
`4bb58c0eb4566a21e3cb3d2b1bdd2a6a2cf962c5`; the later head only wires the
regression into the existing GEX modeling-core CI owner.

The correction reads gamma regime from the same modeled `gamma_profile` sign at spot
rather than assuming every nearest zero crossing has one orientation. It does not
create another pricing kernel or infer observed dealer inventory.

Current-head review reuse was adjudicated and a fresh current-main integration proof
was run:
- current Macro main: `3c39f71bfd526ac35e5af67a497dd28f4c9a889d`;
- merge tree: `916d33420902b6a9d570d7ed509a3a2f84c03ca1`;
- proof-only integrated commit:
  `6ba09ac7d533ce579095617b4e07af69758d5a00`;
- exact GEX owner pack: 249 passed / 11 skipped;
- compileall and diff check: pass;
- fences: green; main CI remained queued at the last canonical read.

This remains modeled/internal-consistency evidence only, not dealer inventory,
prediction, production or Options Workbench completion.

## Macro #7279 — expiry/source clock repair candidate returned

Current head: `d254917fc6cafb5031f805fa663ca0ddf645ca2d`.
Current protected Macro main used for compatibility:
`4114d282b1b85be534c53b150523db1d39400c7b`.
State: **BUILT_NOT_PROVEN / DRAFT / exact-head review + hosted CI owed**.

The prior head `7bf15e63...` removed the false fixed four-hour 0DTE floor but remained
REQUEST_CHANGES after review comments `5724395435` and `5724455441` reproduced a
cycle-start valuation mismatch and a multi-root output-clock mismatch. Comment
`5724614973` additionally required preserving trade and NBBO quote clocks separately;
`5725715278` corrected one detail of that review: the live `bulk_trade_quote` path
already retains `quote_timestamp`; the defect was the surface extractor discarding it.

The current same-carrier candidate now:
- values each root at its fetched-root `observed_at`, not `cycle_started_at`, and uses
  that clock for the root stamp, frame `asof` and `valuation_at`;
- skips a root with no valid current observation instead of relabelling cumulative
  state as fresh;
- retains `built_at` separately from valuation time without claiming it is the later
  R2 publication receipt;
- retains selected trade-event time as `trade_at` and the real provider NBBO clock as
  `quote_at`; missing/malformed quote time remains null rather than inheriting trade time;
- carries per-stamp trade/quote bounds plus exact prior-session `oi_vintage` through
  replay truncation;
- rejects source clocks later than fetched availability and excludes 0DTE contracts
  after both regular 16:00 ET and existing 13:00 ET early closes;
- preserves the existing session/calendar, pricing, replay and storage owners.

Discriminating proof includes `trade_timestamp != quote_timestamp`, missing quote-time
nullability, quote-after-observation rejection, real `run_cycle` response-vs-cycle-start
separation, normal/early after-close cases, unequal-root timestamps and selected-stamp
provenance.

Fresh exact-head owner pack: 620 passed / 1 skipped / 0 failed across surface, live-flow,
session-digest, intraday-Greek and ThetaData owner tests; compileall and diff check pass.
Fresh current-main integration proof is conflict-free:
- merge tree `eaa6907bcc7dcd3c91e60755159265c8036e6de2`;
- proof-only integrated candidate
  `033a488b9cede633e3decf288ba36197705f7a89`;
- integrated owner pack 620 passed / 1 skipped / 0 failed;
- integrated compileall and diff check pass.

Exact-head hosted CI `35312086917` and fences `35312086243` are running at the last
canonical read. Independent exact-head numerical/source review remains required.
The separate Greek field-completeness denominator defect is deliberately not folded
into this carrier.

## R1 entitlement and source boundary

Parent #603 ruling `5724610745` freezes two capability classes. The current first useful
vertical remains SPY on the modeled surface plane; exact Terminal #608 still materializes
`SPY / QQQ / IWM`. Macro has additional derived/historical index-option stores, including
SPX-family rows in some owners, but those are assumption-signed display context and do
not become Quanted-style measured participant inventory. Raw `thetadata_eod/**` is
classified `VENDOR_RAW / OPERATOR_ONLY` in the current delivery-plane source, with no
repository evidence of signed browser/public redistribution rights.

The binding competitor teardown records Quanted's SPX/VIX MM/Firm/BD/Customer product
as separately licensed CBOE signed positioning while its ticker product is OPRA/OI
based. Therefore workflow/interaction quality may advance now on lawful modeled inputs,
but participant-labelled signed SPX/VIX remains an explicit entitlement/input gate.
Existing OI-derived SPX data is not an acceptable cosmetic substitute and no provider
purchase is implied before the exact missing entitlement is qualified.

## Completion boundary and next action

R0 is not full #603 completion. Remaining parent work includes release/review of the
expiry/source-clock candidate, adaptive/convergence-tested profile resolution, explicit
missingness and field-completeness semantics, forward conditional Greek fields, broader
linked-pane composition, entitlement qualification and real production/browser proof.

Next actions, in order of available evidence:
1. obtain an independent exact-head review for Terminal #608 before any Ready/merge
   transition; its exact-head hosted CI and current-base integration proof are already green;
2. consume #7271 current-head CI and normal release gates without redoing its modeled
   sign implementation;
3. consume #7279 exact-head hosted CI/fences and obtain independent exact-head
   numerical/source review on d254917fc6cafb5031f805fa663ca0ddf645ca2d; do not redo
   the source-clock implementation unless that review returns a concrete finding;
4. only after #7279 is accepted, repair the separately recorded Greek field-completeness
   denominator through the existing producer rather than opening a parallel writer;
5. after lawful merges, use existing release owners and natural RTH inputs for real
   production-path acceptance. Merge, green CI and fixture-browser proof remain
   distinct from production acceptance.

Do not restart the competitor teardown, replace existing carriers, create a new replay
or freshness store, or infer profitability/observed dealer positioning from these
correctness slices.
