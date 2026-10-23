---
key: OPTIONS-WORKBENCH-R0-REPLAY-GEOMETRY-FAILURES
claim: >
  Options Workbench R0 has repaired immutable candidates for the previously blocking
  Terminal replay-refresh and Macro public-provenance defects, while release gates remain
  open. Terminal #608 head 14f9a8d83dc7651eff26032ad3b084357e8ec1a3
  retains exact stored-frame identity on same-HHMM refresh failure and distinguishes
  first-read failure from accrual; local/current-base proof is green. Its first repaired-
  head CI attempt failed only in the unrelated tablet marker-tooltip journey; the bounded
  same-run failed-job rerun returned green, so exact-head CI is now SUCCESS while fresh
  independent rereview remains pending. Macro #7279 head
  ff27f0a3408a3ddf5a29e0b6e59507501ebea8bb closes same-minute atomicity, mixed
  unknown source-clock envelopes and selected-replay asof identity; fences/current-base
  proof are green while hosted CI and exact-head independent review remain open.
  None of these slices is production acceptance or full Quanted parity.
falsifier: >
  Terminal #608 at 14f9a8d83dc7651eff26032ad3b084357e8ec1a3 fails its exact-context
  stored-frame retention / first-read-unavailable regressions or rereview; Macro #7271's
  modeled regime disagrees with its own gamma curve at spot; or Macro #7279 at
  ff27f0a3408a3ddf5a29e0b6e59507501ebea8bb fails same-minute atomicity, mixed-unknown
  source-clock nullability, selected replay-asof identity, hosted CI or independent review.
so_what: >
  Consume the already-running #608/#7279 exact-head release gates and fresh independent
  rereviews; do not redo their repaired semantics. Preserve replay architecture, geometry,
  Greek labeling, gamma-sign, fetched-root valuation, whole-row selection, RTH gating,
  same-minute atomicity and public clock identity. Keep the separate Greek field-completeness
  denominator blocked behind #7279 acceptance and preserve production proof separately.
kind: runtime
verified_at: 2026-09-18
verified_by: >
  Terminal #608 current head 14f9a8d83dc7651eff26032ad3b084357e8ec1a3;
  repair return 5727869977; protected-master proof 3134f967ccdb2430ec0be37e61a9450e10549d70
  over tree e70bc97f91d5f79d3f7e36d3d8f252864ea48b0c; exact-head CI
  35328161453 first attempt failed only in unrelated tablet marker-tooltip; the exact
  failing test passed locally and the bounded failed-job rerun completed green, leaving
  the run SUCCESS; prior independent REQUEST_CHANGES review 5245552829 awaits fresh
  rereview. Macro #7271 current head
  cadb7ec4a5029150dea3eb9445d9481f3f2aff66 with fresh protected-main proof
  a40b1a53c60d57d0b8652a26b06abdedf94a92c1 over tree
  48d3d2fdc09821d4d4d397c2c3b6b3d3fca04a55. Macro #7279 current head
  ff27f0a3408a3ddf5a29e0b6e59507501ebea8bb; repair return 5727998620;
  latest protected-main proof d40218557367551c9ada3ce29baa7c4929f17901 over tree
  d781cb721f8724d0908e714544d6710b8f600630; fences 35329144961 SUCCESS;
  CI 35329145976 queued at latest read; formal independent review requested from MastermindX1.
  Parent #603 entitlement ruling 5724610745.
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
`Mastermind@61a2ff79aba4e8a5685e779707ad5c4426cf5cc5`,
`mastermind.sol_skillpack.v1` 1.0.1 / bootstrap major 1.

## Terminal #608 — current R0 UI/replay candidate

Carrier: `claude/options-workbench-r0-replay-20260917-sol-001`.
Current head: `14f9a8d83dc7651eff26032ad3b084357e8ec1a3`.
Original base: `75c22083249e7a1529be3d6baf819b9ad5ea509f`.
Fresh protected-master compatibility base:
`a09eafdf8da027fe7416b3a7d209b36925709cee`.
State: **BUILT_NOT_PROVEN / DRAFT / REREVIEW_PENDING / not merged or deployed**.

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

Review `5245552829` found that a successful index refresh followed by failure of the
same current-frame refresh erased a usable stored field and falsely labelled the result
as still accruing. Head `14f9a8d8...` closes that exact finding: hard refresh failure
retains a prior frame only when the existing root/session/stamp admission contract still
validates it, displays a bilingual stored-frame refresh failure, and reports an initial
frame read failure as unavailable rather than accrual. The stored tuple now carries root
identity and the render boundary re-runs the existing context validator; no second cache
or replay owner was created.

Fresh exact-head repair proof:
- discriminating mounted RED: two expected failures before source repair;
- focused replay/surface/cache/geometry: 270/270 passed after repair;
- TypeScript: pass;
- real-route replay/alignment/geometry: 30/30 passed, EN/ZH × desktop/tablet/mobile,
  one worker, zero retries.

Fresh protected-master compatibility for this repaired head:
- protected master: `a09eafdf8da027fe7416b3a7d209b36925709cee`; no movement on #608
  owned paths since the prior proof base;
- merge tree: `e70bc97f91d5f79d3f7e36d3d8f252864ea48b0c`;
- proof-only integrated commit: `3134f967ccdb2430ec0be37e61a9450e10549d70`;
- integrated focused suite: 270/270; TypeScript: pass; diff check: pass;
- integrated real-route browser matrix: 30/30, one worker, zero retries.

The earlier full responsive run produced 820 passing / 279 skipped / four failures
outside #608's changed paths. The tablet crosshair case passed on protected master and
on the then-current integrated candidate, so that broad run is not evidence that the
R0 replay candidate itself regressed that owner.

The prior exact-head run `35301191243` remains SUCCESS evidence for the unchanged
accepted replay/geometry/Greek-semantics foundation, but it does not prove repaired
head `14f9a8d8...`. Fresh hosted CI `35328161453` completed its first attempt with one
failure in the unrelated tablet `marker-tooltip` journey while unit/typecheck, desktop,
mobile, serial and the other CI shards passed. The exact failing tablet test passed
locally on the repaired candidate, and a bounded rerun of that failed job on the same
canonical run returned green. The exact-head hosted run is therefore **SUCCESS**.

Independent review `5245552829` remains the valid REQUEST_CHANGES receipt for the
superseded head and its concrete defect. The exact defect is now closed by the
red→green repair above. Formal GitHub rereview of `14f9a8d8...` is requested from
`MastermindX1`; routing correction is #608 comment `5728070280`. The PR author
`mastermindx-3` and repaired-head source writer `mastermindx-2` are not used to
self-approve. Until that rereview and exact-head CI conclude, keep the PR draft and
do not merge/deploy.

## Macro #7271 — local gamma-regime consistency

Current head: `cadb7ec4a5029150dea3eb9445d9481f3f2aff66`.
The implementation semantic head remains
`4bb58c0eb4566a21e3cb3d2b1bdd2a6a2cf962c5`; the later head only wires the
regression into the existing GEX modeling-core CI owner.

The correction reads gamma regime from the same modeled `gamma_profile` sign at spot
rather than assuming every nearest zero crossing has one orientation. It does not
create another pricing kernel or infer observed dealer inventory.

Current-head review reuse remains valid. Fresh protected-main compatibility now uses
Macro main `c495a4fb7a01c9ecbcd3cbd91e02bcb102427e04`; no movement since the prior
proof touched the candidate's engine/test/CI-owner paths:
- merge tree: `48d3d2fdc09821d4d4d397c2c3b6b3d3fca04a55`;
- proof-only integrated commit:
  `a40b1a53c60d57d0b8652a26b06abdedf94a92c1`;
- authoritative GEX modeling-core owner pack: 249 passed / 11 skipped;
- compileall and diff check: pass.

An exploratory broad `test_gex*.py` invocation on the temporary integration worktree
reported one `FileNotFoundError` solely because that proof worktree intentionally omits
`site/theme.css`; the exact same IV-rank color test passes on a full checkout of current
protected main. This is a sparse-checkout artifact, not candidate semantic evidence.
Fences remain green; the trusted-executor main CI is still partially executed/queued.

This remains modeled/internal-consistency evidence only, not dealer inventory,
prediction, production or Options Workbench completion.

## Macro #7279 — expiry/source clock repair returned for rereview

Current head: `ff27f0a3408a3ddf5a29e0b6e59507501ebea8bb`.
Fresh protected Macro main used for compatibility:
`c495a4fb7a01c9ecbcd3cbd91e02bcb102427e04`.
State: **BUILT_NOT_PROVEN / DRAFT / REREVIEW_PENDING / DO NOT MERGE**.

The accepted clock/custody repairs remain intact: each root is valued at its fetched
`observed_at`; root clocks are not relabelled by later roots/builds; trade, provider
NBBO, valuation, build and exact prior-session OI-vintage clocks remain distinct;
sub-second valuation identity is preserved; normal/early 0DTE maturity reuses the
existing session/calendar owners; stable latest-RTH whole-row selection prevents a
newer trade row from borrowing an older non-null quote timestamp.

Head `ff27f0a3...` adds three bounded same-carrier provenance repairs without widening
ownership:
- **same-minute atomicity:** when a Greek-bearing minute is retried but the Greek stage
  produces no snapshot (`None` / failed or unavailable), the coherent prior minute is
  retained rather than combining newer net-premium/spot/frame clocks with older Greek
  cells. An explicitly supplied empty Greek snapshot remains authoritative and clears/
  replaces the current column;
- **mixed unknown source-clock envelope:** any missing, malformed or timezone-naive
  member makes both aggregate source-clock bounds null. A known-only envelope can no
  longer hide partial source-time unknownness;
- **selected replay `asof`:** reconstructed replay uses the selected column's
  `valuation_at` as public `asof` when present. Legacy frames without valuation metadata
  retain the previous wrapper-`asof` fallback.

Discriminating exact-head proof:
- same-minute atomicity RED captured both forbidden old behaviors; focused GREEN 4/4;
- public-provenance RED before the two output fixes: 3 failed / 1 passed exactly on
  earlier replay `asof`, mixed-null bounds and malformed/naive bounds;
- combined provenance/atomicity GREEN: 6/6;
- five owner packs: **629 passed / 1 skipped / 0 failed**;
- compileall and diff check: pass;
- evidence is committed under
  `research/evidence/options-workbench-expiry-clock-20260917/review-hardening/`.

Fresh protected-main proof is conflict-free with no movement on #7279 owned/dependency
paths since the prior hardening base:
- merge tree `d781cb721f8724d0908e714544d6710b8f600630`;
- proof-only integrated commit `d40218557367551c9ada3ce29baa7c4929f17901`;
- integrated owner packs **629 / 1 / 0**;
- integrated compileall and diff check: pass.

Exact-head fences `35329144961` are **SUCCESS**. Exact-head CI `35329145976` is
**QUEUED** at the latest checkpoint. Formal independent numerical/source rereview is
requested from `MastermindX1`; routing correction is #7279 comment `5728070883`.
The prior `5726860312` and `5726974122` findings are preserved as the red problem
statements, not treated as cleared review gates merely because source repair exists.

The separate Greek field-completeness denominator from parent #603 remains outside this
carrier and must not be edited until #7279 is accepted. No observed-dealer-inventory,
signed-participant, prediction, deployment, live-freshness or full-parity claim follows.

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
1. consume the requested fresh semantic rereview of Terminal #608 head `14f9a8d8...`;
   exact-head CI `35328161453` is green, so do not redo the stored-frame repair;
2. consume Macro #7279 exact-head CI `35329145976` and the requested fresh numerical/
   source rereview of `ff27f0a3...`; do not redo its atomicity/clock/asof repairs;
3. consume #7271 current-head CI and normal release gates without redoing its modeled
   sign implementation;
4. only after #7279 is accepted, repair the separately recorded Greek field-completeness
   denominator through the existing producer rather than opening a parallel writer;
5. after lawful merges, use existing release owners and natural RTH inputs for real
   production-path acceptance. Merge, green CI and fixture-browser proof remain
   distinct from production acceptance.

Do not restart the competitor teardown, replace existing carriers, create a new replay
or freshness store, or infer profitability/observed dealer positioning from these
correctness slices.
