---
key: OPTIONS-WORKBENCH-R0-REPLAY-GEOMETRY-FAILURES
claim: >
  Options Workbench R0 has source candidates for Terminal geometry/replay and Macro
  gamma-sign correctness, but both active R0 implementation carriers now have bounded
  review blockers. Terminal #608 exact head 1f94c551ff997a50dc915a3d7565d626d89f87c4
  has green hosted/current-base proof but independent review REQUEST_CHANGES because a
  same-HHMM frame refresh failure discards a usable stored field and falsely reports
  accrual. Macro #7279 head 6d4db997f371df4f5500cdd32ff387fcb2a7849d
  retains two provenance blockers: mixed unknown NBBO clocks disappear in aggregation
  and reconstructed earlier replay copies the newest full-frame asof. None of these
  slices is production acceptance or full Quanted parity.
falsifier: >
  Terminal #608 is promoted while a successful index refresh followed by failure of the
  same exact current-frame refresh can still erase the admitted frame and render the
  no-data/accruing copy; Macro #7271's modeled regime disagrees with its own gamma curve
  at spot; or Macro #7279 is promoted while mixed unknown quote clocks can publish a
  known-only quote_at envelope or an earlier reconstructed stamp can report the newest
  full-frame asof instead of its selected valuation basis.
so_what: >
  Continue the existing carriers and release gates. Do not redo the replay architecture,
  geometry repair, Greek semantic repair, gamma-sign repair, fetched-root valuation
  repair, whole-row selection or RTH gate. Repair #608 only at the frame-refresh failure
  boundary and repair #7279 only at aggregate quote-clock unknownness plus selected-stamp
  asof reconstruction, then refresh exact-head proofs/reviews. Preserve production proof
  as a separate post-release gate.
kind: runtime
verified_at: 2026-09-18
verified_by: >
  Terminal #608 current head 1f94c551ff997a50dc915a3d7565d626d89f87c4;
  hosted CI run 35301191243 SUCCESS; fresh protected-master proof
  a7d6aad120a28e7978d75ab4822fc040724dce56 over tree
  e72b3e94cf8368f77cf4aafc20565e9eacee66bf; independent REQUEST_CHANGES review
  5245552829; Macro #7271 current head
  cadb7ec4a5029150dea3eb9445d9481f3f2aff66; Macro #7279 current head
  6d4db997f371df4f5500cdd32ff387fcb2a7849d with hardening proof against
  d2c2b085c46f0745f9996e7de3d1eb9b1a379984 and review comments 5724395435,
  5724455441, 5724614973, 5725715278, 5726707566, 5726860312 and 5726974122;
  parent #603 entitlement ruling 5724610745.
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
`1b2cc28f6ed8a59eedd9420f904c68fcce52c7e3`.
State: **BUILT_NOT_PROVEN / DRAFT / REQUEST_CHANGES / not merged or deployed**.

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

Fresh protected-master proof for the exact current head:
- protected master: `1b2cc28f6ed8a59eedd9420f904c68fcce52c7e3`; the only movement
  since the prior compatibility base is six path-disjoint release-preflight files;
- merge tree: `e72b3e94cf8368f77cf4aafc20565e9eacee66bf`;
- proof-only integrated commit:
  `a7d6aad120a28e7978d75ab4822fc040724dce56`;
- independent focused replay/surface/cache/geometry: 268/268 on exact head and
  268/268 on the integrated candidate;
- exact-head and integrated TypeScript: pass; integrated diff check: pass;
- integrated real-route browser matrix: 30/30, one worker, zero retries.

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

Independent exact-head review is now resolved as **REQUEST_CHANGES** in GitHub review
`5245552829`. The review verified the shared replay/index architecture, exact context
admission, modeled-Greek semantics and numeric heat geometry, then found one release
blocker in the newly added same-HHMM refresh path. After a successful live index poll,
the pane refreshes the current frame with `refresh:true`; if that exact frame request
returns 503, `flowGet` returns null and `SurfacePane` clears `frameResult`, while the
index remains healthy. A real-route browser probe started from a visible admitted SPY
09:31 frame, let the same-head index refresh succeed, failed only `surface:SPY:0931`,
and reproduced the field disappearing while the rail still said LATEST STORED and the
chart falsely said `No surface data yet — accruing ... Nothing is hidden.`

The smallest repair is to retain the previously admitted exact root/session/stamp frame
on a same-identity refresh failure, surface a bilingual refresh-unavailable/stored-state
indicator, and distinguish an initial frame read failure from genuine accrual. The
existing cancellation/context fencing, index-error semantics, zoom, geometry and metric
semantics remain frozen. A successful index refresh + same-frame 503 regression and an
initial-frame-failure regression are required before rereview.

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

## Macro #7279 — expiry/source clock repair remains REQUEST_CHANGES

Current head: `6d4db997f371df4f5500cdd32ff387fcb2a7849d`.
Hardening compatibility base: `d2c2b085c46f0745f9996e7de3d1eb9b1a379984`.
State: **BUILT_NOT_PROVEN / DRAFT / REQUEST_CHANGES / DO NOT MERGE**.

The earlier clock repair remains valid: fetched-root `observed_at` is the valuation
basis, root clocks are not relabelled by later roots/builds, trade and actual provider
NBBO clocks stay distinct, sub-second valuation identity is preserved, OI vintage is
retained, and normal/early 0DTE maturity uses the existing session/calendar owners.

Review hardening on `6d4db997...` closed two additional defects without widening owners:
- pandas `GroupBy.last()` could splice an older non-null quote timestamp onto the
  newest trade/bid/ask row; stable latest-RTH whole-row selection now preserves row
  identity and an honestly missing `quote_timestamp`;
- the Greek quote tap consumed raw bulk frames that can include extended-hours rows;
  it now reuses `engine.session_digest.session_window_et` before latest-row selection,
  excluding normal 16:05 and canonical early-close 13:05 rows with the same `< close`
  boundary already used by `engine.live_flow`.

Exact-head hardening proof supplied and independently spot-checked by Sol:
- candidate owner pack: 624 passed / 1 skipped / 0 failed;
- focused whole-row / cash-session / sub-second regressions: 4 passed on the detached
  immutable head during principal review;
- compileall and diff check: pass;
- local current-main proof commit `f354804bac36660067930fcdb46eb097cfb55eaa`,
  tree `383299fd5f67537cf8c8a28da4c01bc9669e8a52`, owner pack 624/1/0;
- exact-head fences `35319389099`: SUCCESS;
- exact-head CI `35319389391`: still queued at the last canonical read.

A further principal review found one still-blocking public-provenance defect. The
per-contract path correctly leaves a missing quote clock as `quote_at=None`, but
`greek_columns_for_stamp::_clock_bounds("quote_at")` skips unknown clocks. With ten
otherwise valid/OI-matched inputs, one unknown quote clock and nine known clocks, the
public frame still emitted `quote_at_first=13:30:01Z` and `quote_at_last=13:30:09Z`,
`coverage=1.0`, and no quote-clock missingness indicator. The public replay boundary
therefore loses partial NBBO-clock unknownness even though the per-contract source is
honest.

Review comment `5726860312` requires the smallest same-carrier repair: preferably set
both aggregate `quote_at_first` / `quote_at_last` to null whenever any selected Greek
input summarized by that stamp has a missing/malformed quote clock. An explicit
known/total source-clock count is possible but is a larger public-contract change and
is not required merely to close this blocker. Add a mixed-known/missing regression
through the public frame while retaining the all-known bounds and all-missing-null tests.

Supplemental integration review `5726974122` independently confirmed that blocker and
found one more bounded replay-provenance defect: `frame_for_stamp` selects the earlier
column's `valuation_at`, `built_at` and quote provenance but still copies `asof` from
the newest full frame. A two-column witness requested 14:00, returned the correct
`valuation_at=18:00:00.123456Z`, but reported `asof=18:43:00.654321Z`. This is a
reconstructed-replay helper inconsistency, not evidence that already-written earlier
JSON was overwritten. The narrow compatible repair is selected `valuation_at` as the
frame `asof` when present, with the legacy full-frame fallback only when valuation
metadata is absent. The supplemental review's private prototype is diagnostic only,
not source truth or an adopted patch.

The separate Greek field-completeness denominator from parent #603 remains outside this
carrier and must not be folded into these two repairs. Independent exact-head
numerical/source review is still owed after a repaired immutable head returns.

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
1. keep Terminal #608 on the same source carrier and close independent review
   `5245552829`: retain the exact stored frame on same-identity refresh failure, expose
   refresh-unavailable state, and distinguish initial read failure from true accrual;
2. consume #7271 current-head CI and normal release gates without redoing its modeled
   sign implementation;
3. keep #7279 on the same source carrier and close both bounded provenance findings:
   mixed unknown NBBO-clock truth (`5726860312`) and selected-stamp `asof` reconstruction
   (`5726974122`), with direct red/green public-frame/replay regressions;
4. after repaired immutable heads return, refresh exact-head/current-base proof and
   complete the required rereviews before any Ready/merge transition;
5. only after #7279 is accepted, repair the separately recorded Greek field-completeness
   denominator through the existing producer rather than opening a parallel writer;
6. after lawful merges, use existing release owners and natural RTH inputs for real
   production-path acceptance. Merge, green CI and fixture-browser proof remain
   distinct from production acceptance.

Do not restart the competitor teardown, replace existing carriers, create a new replay
or freshness store, or infer profitability/observed dealer positioning from these
correctness slices.
