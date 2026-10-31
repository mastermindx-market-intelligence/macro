# Phase 1 design packets — Prophet news-to-business-impact

Status: **DESIGN — seat-accepted, not a ratified build spec.** Every packet here was produced by a
bounded GLM design lane (wave 2, 2026-10-11/12) under Meta-CEO seat `0e739467` and accepted by
artifact review: every `*.schema.json` passes `Draft202012Validator.check_schema`, no schema key
matches the closed forbidden vocabulary (confidence / probability / score / price_target /
fair_value / contagion / sentiment), and each design was checked against the standing kills it
sits next to. A later phase builder **re-freezes** the relevant packet against the then-current
contract (`contracts/news_impact/news_impact_event.v1.schema.json`, sha256 prefix `3edc7139`)
before writing code; nothing here is executed, wired, or authoritative.

Lane line numbers cite the lane clone HEAD named in each packet (`57f3041e22` or `295e76c6a0`);
main has moved since, so expect small line drift (spot-checked at about ten lines on 2026-10-13).

| Packet | Masterplan home | Answer first | Seat verdict |
|---|---|---|---|
| `A1_thesis_store/` | §5 thesis memory | Thesis view = pure fold F(fact_log, owner_snapshot, as_of); the only clock-bound field is next-observation status. Append-only fact log chosen; a mutable "thesis lobe" is rejected (DNR:KILL-THESIS-LOBE). | ACCEPT |
| `A2_mechanisms/` | §4 mechanism / channel library | Seven closed channels, 29 deterministic mapping rules; `market_only` is forbidden for T1/T2/T3 schemas; `channel_hint` is display-tier, never a mapping input. | ACCEPT |
| `A3_eval/` | §9–§11 evaluation | 6 metric families / 27 metrics / 5 baselines / 6 ablations; thresholds PROPOSED-OWNER-FREEZES; QA-only vs prospective_primary named per family; "zero unsupported supplier assertions" is undecidable at N=600 (needs ~3,000 independent clusters); nulls printed, never hidden. | ACCEPT |
| `A4_transfer_obs/` | §8 transfer + observation windows | One-hop transfer needs a two-party source span; abstention (`transfer_absence.v1`) is the default; expected two-party-span reject rate 70–80% is a design expectation, not a measurement. | ACCEPT |
| `A5_cost/` | §10 cost cascade | Nine-stage cascade; ceilings are PROPOSED_NOT_AUTHORIZED; capacity routing stays with the Mastermind Model Router (DEC-EXECUTIVE-CAPACITY-FABRIC). | ACCEPT |
| `A6_labeler/` | §3.5 labeled benchmark | 12 critical fields per template; `novelty` is the field most likely to split two labeler families; agreement spec is pre-registered (per-field exact agreement, Cohen kappa, third-family adjudication). | ACCEPT |
| `A7_prophet_adapter/` | §12 Prophet consumer | First consumer is `engine/intelligence.py` `build()` with an unblended `news_impact` facet after `_brain()`; output `prophet_evidence.v1` is `authority: context_only`, every `prophet_flags` value false. | ACCEPT |
| `C2_owner_census/` | owners for Phase 2 | No general article-body fetch owner exists; the rights registry exists only as the benzinga-scoped `qbus.news_rights_receipt.v1` — Phase 2 builds a body re-fetch owner on that receipt pattern and mints no second registry. | ACCEPT (census) |
| `C3_gap_census/` | promise ledger | 112 masterplan promises classified (22 PRESENT / 30 PARTIAL / 29 ABSENT / 27 FROZEN-IN-PHASE-0 / 4 EXCLUDED); gaps #1 (contract placement, closed by #8873) and #2 (`engine/news_impact/` leaf, closed by the Phase 1 integration PR) head the critical path. | ACCEPT (census) |

Disclosed by the census and still open: no article-body fetch (no byte-replayed news spans yet),
no multi-source rights registry, the §4 mechanism layer is design-only, and the propagation
contract stays excluded while PR #6514 holds.
