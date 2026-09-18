---
key: OPTIONS-WORKBENCH-R0-REPLAY-GEOMETRY-FAILURES
claim: >
  Options Workbench R0 now has reviewed source candidates for Terminal geometry/replay
  and Macro gamma-sign correctness, while the expiry-clock lane remains explicitly held
  on a reproduced valuation/source-clock mismatch. Terminal #608 is current at
  1f94c551ff997a50dc915a3d7565d626d89f87c4 with current-base integration proof;
  none of these slices is production acceptance or full Quanted parity.
falsifier: >
  Terminal #608 at 1f94c551ff997a50dc915a3d7565d626d89f87c4 fails its mounted
  replay/contract regressions or current-base integrated browser matrix; Macro #7271's
  modeled regime disagrees with its own gamma curve at spot; or Macro #7279 is promoted
  without resolving review comments 5724395435 and 5724455441 and proving a coherent
  valuation/source/publication clock path.
so_what: >
  Continue the existing carriers and release gates. Do not redo the old replay/tool
  blocker, geometry repair or gamma-sign repair. Keep #7279 held until its source-clock
  reconciliation is accepted, obtain an independent exact-head review for #608, and
  preserve production proof as a separate post-release gate.
kind: runtime
verified_at: 2026-09-17
verified_by: >
  Terminal #608 current head 1f94c551ff997a50dc915a3d7565d626d89f87c4;
  current-base proof fb361092f4a17c12c303f0de13882b8100143811;
  Macro #7271 current head cadb7ec4a5029150dea3eb9445d9481f3f2aff66;
  Macro #7279 review comments 5724395435 and 5724455441.
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
R0 replay candidate itself regressed that owner. Exact-head hosted CI remains the
binding repository gate for the current head.

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

## Macro #7279 — expiry-clock lane is held on a real review finding

Candidate head `7bf15e63e66b780dc5b21575b1cf7508e2f66498` correctly removes the old
fixed four-hour 0DTE floor from the surface producer and reuses the existing US
session/early-close calendar. Its original candidate and current-main integrated broad
families each passed 509 tests with one existing skip.

That does **not** make the head acceptable. Review comment `5724395435` reproduced a
material clock mismatch: the candidate valued fetched quotes at `cycle_started_at`,
which can predate the actual network response by minutes and can retain an option past
cash-session maturity. Comment `5724455441` then proved that merely swapping in the
fetched-root observation is insufficient if the output discards the per-root valuation
basis and republishes multiple roots under one later global clock.

Required same-carrier repair:
- value each root against the clock at which its fetched source is actually available,
  or enforce a true common cutoff;
- preserve valuation/source/publication clocks as distinct evidence;
- never make an older root fresh because another root returned later;
- include regular-close, early-close, unequal-root and after-close regressions;
- retain existing replay/storage/calendar owners rather than creating another
  freshness plane.

The original #7279 head therefore remains **REQUEST_CHANGES / DO NOT MERGE** regardless
of its earlier green tests. Same-carrier local repair activity has begun, but no new
committed exact head or accepted repair result is recorded here yet. Do not promote
working-tree bytes or partial tests into canonical completion.

## Completion boundary and next action

R0 is not full #603 completion. Remaining parent work includes truthful expiry-clock
repair/review, adaptive/convergence-tested profile resolution, explicit missingness and
metric identity across all paths, forward conditional Greek fields, broader linked-pane
composition, entitlement qualification and real production/browser proof.

Next actions, in order of available evidence:
1. consume exact-head hosted CI for Terminal #608 and obtain an independent exact-head
   review before any Ready/merge transition;
2. consume #7271 current-head CI and normal release gates without redoing its modeled
   sign implementation;
3. keep #7279 held until the reproduced clock/provenance findings are repaired and
   independently re-reviewed on one immutable head;
4. after lawful merges, use existing release owners and natural RTH inputs for real
   production-path acceptance. Merge, green CI and fixture-browser proof remain
   distinct from production acceptance.

Do not restart the competitor teardown, replace existing carriers, create a new replay
or freshness store, or infer profitability/observed dealer positioning from these
correctness slices.
