---
key: OPTIONS-FLOW-ENRICH-CONFLATES-SWEEP-PACKAGE-AND-CREDITS-UNKNOWN
claim: >
  At Macro 2051ac78c0fae30d21e799996a09285453fe045f and Terminal
  a4be9a3f4b51246200cb1b7c4f1d44730066a9a9, the legacy Flow Desk enrichment
  conflates a per-contract multi-exchange sweep-like urgency flag with MULTI_LEG
  package ambiguity: detect_multi_leg returns only event.swept, so a swept single
  contract is direction-discounted while an unswept coherent two-leg package is not
  detected by that predicate. The q-score also gives positive points to unknown
  prior-OI and unknown moneyness, while event premium_z is deliberately null on the
  current producer, leaving the unusualness component, Z_OUTLIER and the soft whale
  branch unavailable on that path. No current R2 prevalence, predictive failure,
  user trade, production false-green or repaired implementation is established.
falsifier: >
  Re-run the exact source/predicate checks documented at
  research/options_estate/OPTIONS_FLOW_SEMANTICS_AND_PACKAGE_GAP_2026-09-11.md:1
  on Macro PR #7027. Inspect pinned blobs 323be029c88ef8ee03d97c2ae3a878fce95ba191,
  272e7f8e035e4bba085462fd4ae857e8a64ac3b3,
  1f29d5626ebcd4bb2a9dc00a2941b51d5b70b23d,
  e0b77ce30404895a1624c034c6ead1320d9aa4cc and
  89a8aff5364c67292df978e8f4fbfe5d9aac802d. The claim is refuted if those
  identical sources associate package legs independently of swept, do not award the
  stated missing-value factors, populate per-event premium_z on the admitted source,
  or withhold score/signal/elite projection as described. Later implementation or
  deployment evidence requires a dated amendment, not rewriting this observation.
  The 98.3% figure is a conditional application to the pinned historical SPY
  tape-reconstruction cohort and is not a current-production estimate.
so_what: >
  Preserve sweep urgency, parent-order/package association, opening-pressure proxy,
  settled OI persistence, attention ordering, research candidacy, calibrated
  probability and operator issue as separate semantics. After the existing OA-1T
  scheduled-source adoption and natural-RTH proof, extend existing event/campaign/
  candidate contracts with explicit package-candidate and missingness states; do not
  overwrite component events or create another collector, event identity, campaign/
  outcome ledger, score-control plane, Issue Desk or trade manager. Until then,
  retain the fixed q-score only as partial attention/salience and do not promote it.
kind: architecture
verified_at: 2026-09-11
verified_by: >
  Source and reproducibility receipt at
  research/options_estate/OPTIONS_FLOW_SEMANTICS_AND_PACKAGE_GAP_2026-09-11.md:1
  on #7027. Exact current-source reads covered Macro engine/live_flow.py blob
  323be029c88ef8ee03d97c2ae3a878fce95ba191, engine/flow_enrich.py blob
  272e7f8e035e4bba085462fd4ae857e8a64ac3b3 and FLOW_SIGNAL_FIELD_GUIDE blob
  e992dd088dd3120d69639bfd040f9cae673ff45c, plus Terminal flowScore/FeedPane/
  FlowCard blobs named in the falsifier. Offline mastermind_flow_semantics_audit.py
  passed22 tests and its mutation probe rejected10of10 deliberately wrong variants;
  it loaded no market rows and fitted no model.
scope:
  - macro
  - terminal
  - options-intelligence
  - options-alpha
  - "engine/live_flow.py"
  - "engine/flow_enrich.py"
  - "terminal/lib/flowScore.ts"
  - "terminal/components/flowdesk/*"
  - "research/options_estate/*"
confidence: verified
---

Parent: WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY. Same records-only carrier: Macro #7027.

## Capability delta

Before this source audit, the competitive research identified that Nightglass separated
flow, package interpretation, settled positioning and plan quality, but it did not explain
why Mastermind's existing Flow Desk could still feel semantically weak despite its wider
data estate. The current-source read now localizes that gap: the producer's one-contract
sweep fact is converted into a package claim, several association badges use weaker
root/strike-count proxies, and the q-score mixes unavailable evidence with positive
fallback points before the governed candidate composition exists.

The per-event notability gate correctly leaves premium_z null because a root-day EOD-252
baseline is the wrong denominator for one contract cluster. The downstream 20-point
unusualness term is therefore structurally zero on this path. Unknown prior-OI contributes
7.2 points and unknown moneyness contributes6.0; these may preserve attention ordering but
are not evidence quality, conviction or return probability. The Terminal can sort/filter
by the score and labels the feed SIGNALS with an ELITE preset, while accepted OA source
law limits the score to Attention/Salience.

## Precise package/retention limits

A sweep-like flag means at least three prints on one contract, at least two exchanges and
at most two seconds. It does not establish a second leg or parent-order identity. Conversely,
a package can exist without either leg meeting that sweep predicate. Volume exceeding prior
OI requires some opening turnover at some point but does not establish overnight retention,
alert-side opening intent or beneficial-owner motive. Settled OI confirmation remains a
later campaign revision with its own availability clock.

The historical field guide reports98.3% swept in its SPY2022–2023 tape-reconstruction
cohort. If the current `swept -> MULTI_LEG` mapping were applied to that exact cohort, it
would direction-discount98.3%. This is a deterministic cross-source diagnostic only; the
current public R2 artifacts were not successfully inspected and no current prevalence is
claimed.

## Current state and continuation

OA-1T-Macro remains BUILT_NOT_PROVEN: #6585 is merged as
`dbd654edb0fb47449b969b7dcb4fbafc2e0fe3ef`, but controlled adoption on the scheduled
source and one natural RTH event-to-existing-consumer proof remain owed. This discovery
does not reopen OA-1T-Terminal or OA-1C, authorize a production patch, or lower the natural
proof requirement.

The eventual minimal repair keeps the producer's sweep evidence, adds a derived package
association over existing event/campaign IDs with single-leg/package-candidate/resolved/
unresolved states, preserves later OI as a correction-safe update, and renames/limits any
fixed heuristic to attention. Missing NBBO/OI/baseline/moneyness must be visible as missing
rather than positive evidence. Real browser proof is required before claiming the existing
Terminal journey is repaired.

AD-1T2, OA-1C, OA-3 exact-option outcomes, OA-4 statistical promotion and OA-5 Issue Desk
integration retain their current gates. No competitor login/API collection, source writer,
service, runtime Job, model flag, generated Agent OS state, worker commission or trade
changed. Repository-wide Agent OS validation, hosted CI, independent review and production
acceptance are not claimed until their actual receipts complete. Keep #7027 draft.
