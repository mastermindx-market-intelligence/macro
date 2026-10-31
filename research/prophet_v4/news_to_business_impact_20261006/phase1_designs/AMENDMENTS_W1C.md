# Phase 1 design amendments — wave w1c

Ruling: `DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS` (2026-10-13). This file amends the frozen
A-design packets A1–A7 instead of editing them.

**How to read a frozen packet.** Read the packet with this file beside it. Where a row below
names a line, this file wins; every other part of the packet stands as written. Line numbers
refer to the packets as committed in PR #9067. No row touches the frozen
`news_impact_event.v1` contract (sha256 prefix `3edc7139`).

Machine-readable overrides of frozen worked fixtures live in `AMENDMENTS_W1C.cases.json`
next to this file. A test that consumes an overridden fixture must load that overlay and fail
closed when it is missing.

## C5 — cost cascade (`A5_cost/A5_cost.md`)

| Where | Frozen text | Amended rule |
|---|---|---|
| §4.4 escalation table, lines 230 and 234–235 | First match wins; `material_issuer_relative_change` (234) is listed before `disputed_high_consequence_fact` (235) | `disputed_high_consequence_fact` is evaluated first. Its predicate contains the material-change predicate, so under the frozen order it could never fire. |
| `stop_not_material_delta`, lines 128, 136 and 165 | A reachable routing disposition | It stays in the closed enums for v1 but is unreachable: no v1 path emits it. The `audit_stratum` weight at line 263 therefore samples an empty stratum, and its slots fall through to the leftover rule. |
| §4.5 audit reserve, line 248 | `n_audit_target = floor(rate * review_capacity)` | `n_audit_target = ceil(rate * review_capacity)`, computed exactly as `math.ceil(Fraction(str(rate)) * review_capacity)`. The starvation and leftover-slot clamps are unchanged. This reproduces the packet's own Q6 default at line 584 (12% of 24 = 3), which floor cannot. |
| W4 worked example, line 471 | The arithmetic closes only with an implied usage snapshot | The example binds to the usage snapshot `9.9998`, stated as an explicit input. |

Code repair: `engine/news_impact/cascade.py` `select_audit_reserve` (wave w1c lane C5_reserve).

## X4 — transfer and observation (`A4_transfer_obs/A4_transfer_obs.md`)

| Where | Frozen text | Amended rule |
|---|---|---|
| Matched window, line 275 (same duration and session type) | The worked values offset the outcome by three calendar days | Counted in trading sessions of the injected `TradingCalendar`. The anchor is the session containing the information cutoff (inclusive), or the next session when the cutoff is outside regular hours. Both outcome endpoints shift back by the same whole number of sessions, so that the matched end lands in the k-th session strictly before the anchor. k defaults to 1 and must be an int in [1, 10]; anything else raises `BAD_MATCHED_WINDOW_SESSIONS`. Each endpoint keeps its ET wall-clock time on the shifted date. A candidate counts only if both endpoints fall inside their shifted sessions and its UTC duration equals the outcome's; otherwise the search steps one session further back. After 10 candidates it raises `MATCHED_WINDOW_NO_SESSION`. |
| Landmark outcome end (implementation, found at integration) | — | When a landmark cutoff is outside regular hours and a later bar exists, the outcome ends at the close of the session containing `outcome_start`. The W3 code used the session after it, so an early-close Friday (2026-11-27) produced an outcome ending at the 2026-12-01 close. |
| §4.7(h) coincident events, line 278 | The prose leaves the interval bounds open | The interval is `[first_admissible_feed_receipt, outcome_end]`, inclusive at both ends, as the `W_obs_coincident_ambiguous` fixture already encodes. |
| `W_obs_1600_landmark` worked values, lines 907–908, and `cases/W_obs_1600_landmark.json` lines 23–24 | Matched window `2026-09-26T13:30:00Z` → `2026-09-26T20:00:00Z`, a Saturday | `2026-09-25T13:30:00Z` → `2026-09-25T20:00:00Z`, applied through `AMENDMENTS_W1C.cases.json`. The case file stays byte-frozen. |

The `W_obs_0935_at_origin` and `W_obs_coincident_ambiguous` matched windows already land on
Friday 2026-09-25 and do not change.

Code repair: `engine/news_impact/observation.py` `compute_window_geometry` (wave w1c lane
X4_matched_window).

## M2 — mechanisms (`A2_mechanisms/A2_mechanisms.md`)

| Where | Frozen text | Amended rule |
|---|---|---|
| Case C `rule_ids`, line 445 | Listed in prose order | Fired rules are recorded in the library's ascending `priority` order, which is the evaluation order at line 181 and in the pseudocode at line 319. |
| T2 rows, lines 210–212 | `T2-AWARD` (200), `T2-OPTION-CEIL` (230) and `T2-BRIDGE` (400) as library rules | Retired names. The bridge is a post-sweep step, not a rule. An option ceiling never feeds a term, which the `V_NO_SUM_T2` validator already enforces. The library rule for awards is `T2-AWARD-POLICY`. |
| `mapping_status`, line 84 | — | A mechanism the library cannot express is set to `strategic_review` and recorded as a v2 candidate. It is never improvised. |
| Driver bridge | `form=range` has no mapping | `form=range` maps to `interval`. |

No code change.

## E3 — eval receipt and grading (`A3_eval/A3_eval.md`)

The committed schemas are the v1 contract that CI validates, and they win. These five
conflicts between design and schema are disclosed as v2 candidates and change nothing in v1:

1. `threshold_crossing = "disputed_dependence"` (line 341) has no slot in the receipt schema.
2. `two_way_cluster_cgm` (interval-method enum, line 166) has no receipt field for the two-way interval.
3. `success_on_subset` (`contracts/news_impact/endpoints.v1.json` line 187): the design reads it as a partial pass, while the registry leaves it null.
4. `net_return_horizon` (line 404): the design pools the 1d/5d/21d horizons, while the schema keeps them separate.
5. `null_reason` stays machine-only and is never rendered into `display_text`.

Grading case 3, line 608 (routing miss, TAM read as earnings demand): where the prose and the
pseudocode disagree, the pseudocode wins (line 247). A TAM routing miss is graded
`wrong_absence`.

No code change.

## T1 — thesis store (`A1_thesis_store/A1_thesis_store.md`)

| Where | Frozen text | Amended rule |
|---|---|---|
| Canonical bytes, line 248 | "`canonical_json_bytes(a) == canonical_json_bytes(b)` (contracts.py:127-140)" | "The same parameters as `engine/company_intelligence/contracts.py`, minus the trailing newline." Ruling W3-R2 stands: `sort_keys`, compact separators, `ensure_ascii=False`, no trailing newline. No consumer outside `engine/news_impact` compares these hashes. |
| Live set, line 233, and Case 4, lines 678–680 | "Index by `fact_key`" | The live identity of a fact is `(fact_key, polarity)`. A contrary record on a supporting fact's key is a separate live record, which is what the `contradiction` trigger at line 199 needs. |
| Case 1 hashes, lines 291–495 | Literal sha256 values | Placeholders, as line 495 already says. Tests derive these values and never assert the literals. |
| §4.8 next observation, line 182 | — | The next observation index is the furthest observed index plus one, as the fixture encodes. |

No code change.

## P7 — Prophet adapter (`A7_prophet_adapter/A7_prophet_adapter.md`)

| Where | Frozen text | Amended rule |
|---|---|---|
| Code home, line 88 | `engine/news_impact/adapt_prophet.py` | `engine/news_impact/prophet_adapter.py`. It stays a leaf (ruling W3-R7) and is not wired into `engine/intelligence.py` before the w2 benchmark gate. |
| Forbidden slugs, `copy_templates.v1.json` line 17 | `WATCH` | Matched as a whole, case-sensitive token, so the ordinary word "watching" is not a hit. |
| `channel_hint` → `channel`, line 144 | The adapter records where `channel` came from | `channel_source` is deferred to `prophet_evidence.v2`, with the enum `[channel_hint, template_default, channel_mapping]`. |
| Case 5.1, line 234 | — | Span checks run over `action_span` only. |

No code change.

## L6 — labeler agreement (`A6_labeler/agreement_spec.md`)

| Where | Frozen text | Amended rule |
|---|---|---|
| Minimum agreement gate, line 97 | `exact_agreement` ≥ 0.90 on EVERY critical field | Unchanged, but enforced fail-closed. A critical field with `n_compared == 0` makes `usable` false, with the reason `not_evaluable`. |
| Kappa gate, line 98 (`n_both_present ≥ 20`) | — | A null kappa (only one category observed) makes `usable` false, with the reason `kappa_undefined_single_category`. |
| `kappa_note`, line 54 | — | At n = 0 it lists the full category enum. |
| `span_only_divergence`, line 39 | — | Accepted as built. Abstentions are recorded as metadata, also as built. |

Code repair: `engine/news_impact/agreement.py` `evaluate_minimum_agreement` (wave w1c lane
L6_gate).
