# Intraday R5: scan, evidence and source basis

## Delivered native designs

Native file: https://app.paper.design/file/01M6Y2QK8TQZRN8T4BHG10CJXT/p-3-0

| Board | Purpose |
|---|---|
| IK-0 | Desktop light: compact classification controls, five-name list, selected evidence |
| MB-0 | Desktop dark counterpart |
| OD-0 | English 390px recorded scan: all five candidates |
| PO-0 | Chinese 390px recorded scan: all five candidates |
| RY-0 | EMR detail: seven checks, absent values explicit, named source/method destination |
| TF-0 | No current assessment: unavailable required inputs, source and refresh recovery |
| UP-0 | All six original classification counts |
| W6-0 | Native architecture, source findings, route contract and build sequence on p-4-0 |

All ten original p-1-0 boards remain. Original CG-0/DX-0 source details, FE-0/GN-0 method, 9F-0 no-match and AP-0 loading views remain named dependencies. The other writer's AGENT README on p-2-0 is unchanged. New product and build pages are ordered after it, ahead of retained R1.

## Reading and interaction decisions

Six large classification cards were consolidated into a compact row. The two nonzero recorded classes remain visible; all original counts remain reachable in UP-0: Buy now 0, Almost ready 5, In favour 0, Take profits 0, Watch—don't chase 0, Stand aside 111. This is not asserted as a complete current universe count.

The five original candidates remain EMR, ENTG, HII, HUBB and KTOS. A row opens its own evidence; EMR is the pictured detail specimen, not a hard-coded destination. The phone scan now presents all five instead of two long report cards. A separate detail route keeps reading depth away from the scan.

The board build time (2 November, 10:21 UTC) and volume source time (27 July, 22:32 UTC) remain distinct. Price and options clocks are unavailable in the supplied specimen. No replacement quote, score, forecast, source time or per-check result was invented.

RY-0 explicitly says original check values are not supplied. Seven checks show Not provided rather than fabricated pass/fail marks. Source details retain the separate options meanings, dealer context and nightly reference levels.

TF-0 is an all-unusable-current-input specimen. It is not the same as a qualified scan with zero matching rows. Preserve the existing degraded / No read state and show current coverage honestly. Refresh uses the current readers and inflight latches. A recorded fallback is offered only when its actual fixed basis is qualified.

## Primary source audit

Product source pin: cf07e7a73334c646a09c043647c43e43ee6e4060.

- templates/intraday_flow.html.j2 — blob 8832ceba22068eccc65704f7bf6d7bbe027a9e45.
- engine/intraday_flow.py — blob bc5b88bec9f0f077e8153f6b98e6bcb60611834a.

The exact inspected function excerpts are in evidence/intraday.source_functions.json. These are source findings; application behavior was not executed or repaired in this design amendment.

### Current versus recorded

The existing template computes from BASE_DATA plus mutable quoteState, pulseState and flowState. The shared path is render → computeAll → computeLegs + computeStance → laneCounts → hero/spotlight/list.

There is no immutable recorded-assessment object established by this reader. Board build time is not automatically evaluation time. Consequently, these new designs are explicitly labelled Recorded example. A runtime historical view requires a fixed result and basis supplied by the existing producer. Recomputing with today's clock and retained inputs is not historical retrieval.

### Reader qualification gaps

| Source function | Observed behavior | Required build treatment |
|---|---|---|
| fetchQuotes | Marks live at 90% finite-price coverage; merges into retained dictionary | Qualify verified source time/session and distinguish retained from current values |
| fetchPulse | Marks live at 80% coverage; merges retained members | Coverage and fetch success are separate from observation freshness |
| flowMetaFresh | Returns true outside the ET window; inside accepts future timestamps via an upper age bound only | Repair within the existing freshness owner; verify producer clocks and session policy |
| updateFlowStamp | Uses BASE_DATA build label and feed-status phrases; does not print passed asof/meta source clocks | Display exact clocks with their real scope |
| laneCounts | Omits degraded / No read | Unknown coverage cannot become quiet tape or a complete six-zero scan |

Missing members in later quote or pulse payloads are retained; failures also leave earlier values available to computation. The source owner must define retention semantics explicitly. Do not add a second polling loop.

### Classifier differences

| Input | Browser JavaScript | Python confluence_legs |
|---|---|---|
| Missing reclaim | L2 starts false | L2 starts None; can use one available reference |
| Missing relative volume / durability | L3/L4 become false | Remain None |
| Missing trend state | L6 false, with K fallback | None; no K fallback |
| Known failed-breakout trap | L7 becomes null | False |
| Missing washout basis | May use status-text or squeeze proxies | No such proxy in confluence_legs |

Resolve these differences within the existing owner or record an accepted, explicit divergence. Do not silently change financial classifications in a presentation patch. Valid zero volume and missing volume also need separate treatment.

Call-only cumulative minutes[].ncp and its durability must remain separate from net total calls-plus-puts premium. The current detail owner already exposes those rows; preserve their approximate direction labels. K remains a count of true checks, not a composite score.

## Exact navigation/state owner

Reuse activeBasket, activeStance, searchQ, groupByStance, openRows and boardExpanded. Selecting a company changes the inspected subject; Back restores the current filters, scroll and invoker focus. Selecting a class updates the existing activeStance and returns to the scan. Do not add a parallel return store.

Use existing loading for an unsettled fetch, existing no-match only after a qualified successful evaluation/filter result, and TF-0 for unusable required inputs. Partial results keep their own qualification and do not inherit whole-board current status. Optional options inputs must not be made universal eligibility gates without the existing rule requiring them.

## Build order

1. Verify producer identity, source clock/session fields and a legitimate fixed recorded basis.
2. Extend existing fetch/state owners with qualification and retained/current metadata.
3. Resolve tri-state and classifier mirror differences; account for No read.
4. Feed the same qualified current result into summary, counts, list and detail.
5. Add the new presentation and exact return behavior.
6. Prove browser/account behavior under the actual application's release controls.

Discriminating checks: missing versus valid zero; known trap versus unknown; omitted/failed retained members; stale, future and off-session source clocks; all-degraded and partial coverage; fixed recorded/current isolation; summary/list/detail agreement; both themes and EN/ZH narrow layouts.

## Visual verification and motion

All eight boards were exported to JSX and screenshotted with no native tool errors. Desktop light/dark, both phone lists, evidence, classification and no-read screens were visually inspected. Phone actions remain visible, text wraps at readable sizes, and all five candidates fit. W6-0 includes an original source→existing state→single evaluation→shared projections diagram.

Missing data uses a static three-source illustration rather than a fabricated price curve. Panel entry may use a short opacity transition; reduced motion is immediate. Counts update atomically and do not count up from zero while unavailable. Existing ilx remains the owner for any eligible display chart.

## Verification limits and continuation

These are editable Paper designs and build contracts. Real browser animation, runtime source parity, authenticated navigation and deployment were not proven by native screenshots. The subsequent shared-state and bounded AI/Comparison phases are included in the final README and verification packet. The broader implementation programme remains open.

