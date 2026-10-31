# A4_transfer_obs — one-hop issuer TRANSFER + market OBSERVATION contracts

Lane: A4_transfer_obs · Seat: Fable 0e739467 · Wave 2 · 2026-10-12
WT HEAD: 57f3041e22 (clone of mastermindx-market-intelligence/macro)
Schemas: `transfer_edge.v1.schema.json`, `observation_window.v1.schema.json` (jsonschema Draft 2020-12, parse-checked).

## (1) ANSWER FIRST

The two-party-span rule will reject **about 70–80% of transfer candidates** that a ticker-or-tag expander would otherwise emit; the relationship type it rejects most often is **competitor / same-industry peer**.

That fraction is a design expectation, not a measured rate. It follows from three owner facts: (i) freeze §7 grades any edge without a cited span naming both parties as an unsupported ticker-to-supplier assertion (the §11 zero endpoint); (ii) the live Graph-2 generator is large (`MEMBER_OF` is what GMI actually emits — `engine/theme_graph/materialize.py:12-20`) while Graph-1 types `SUPPLIES` / `ENABLES` / `BOTTLENECK_OF` / `BENEFITS_FROM` are reserved and not emitted (`research/economic_propagation/D0_THREE_GRAPH_SEPARATION_MAP.md:51-70`); (iii) the tape's machine `customer_win` / `contract_award` yield is tiny (C1_tape Q6: 2 + 2 of 10,000 title classifications; event_log 6 feeder rows) and 97% of event_log centrality is incidental. A semiconductor label, MAG7 membership, or GICS peer almost never carries a span that names both legal issuers. Named customer/supplier/partner sentences survive; competitor and residual-market sympathy almost never do.

The design is two frozen, context_only contracts: `transfer_edge.v1` (one-hop, two-party span required, abstention default, plus `transfer_absence.v1` and `macro_shock_fanout.v1`) and `observation_window.v1` (at_origin vs landmark, explicit `information_cutoff`, six delayed-entry test arms, measurement windows that cannot see the outcome). Neither originates a signal. Model output may only describe, cite, and abstain.

---

## (2) Constraints (labelled)

### STATED (masterplan / freeze)

- S1. Consume the existing three-graph separation: economic relationships / fundamental-narrative comparability / residual market behaviour. Same theme is not a supply relationship; co-movement is not a cash-flow weight. (MASTERPLAN.md §8; D0 map §1.)
- S2. For each source-event → target pair record: target generator, role and direction, economic mechanism when supportable, exposure magnitude or UNKNOWN, timing, alternatives, graph provenance, and a cited span naming **both** parties. (MASTERPLAN.md §8; freeze §7 grading: an edge without one is an unsupported ticker-to-supplier assertion; §11 target zero.)
- S3. Pilot = direct issuer effects and source-backed **one hop**. A graph path is a research candidate, not authorization. No recursive score propagation, no cycles. (MASTERPLAN.md §8.)
- S4. One macro or industry shock touching many firms is analysed once, then fanned by exposure; no per-issuer frontier call. (MASTERPLAN.md §8, §10.)
- S5. Preselect peer sets by documented exposure, not by which set rallied. Leave the target out of peer-return/breadth measures. Collinear market / sector / MAG7 / GPU terms are not subtracted independently. (MASTERPLAN.md §8.)
- S6. PR #6514 (K3-D) restrictions stay in force: refuses participation-only target admission and new predictive authority. Do not design around it, do not read or modify it. (MASTERPLAN.md §8, §12 commission C; freeze §1.1; WS landmine.)
- S7. Two observation modes. At-origin features use only data available before the decision. At a later landmark, features may use price and news up to that landmark; its outcome window starts afterward. Never use the full day's move to justify a forecast supposedly made at 09:35. (MASTERPLAN.md §9.)
- S8. Measure absolute and residual response with coefficients fitted before the event and matched windows. Attribution remains uncertain when multiple events coincide. (MASTERPLAN.md §9.)
- S9. Test several realistic delayed-entry policies relative to first admissible feed receipt. Source delays, research time, spreads and gaps enter the evaluation. Seconds-scale announcement trading is outside the pilot. (MASTERPLAN.md §9.)
- S10. Historical stale-news / attention / economic-link papers motivate **testing**; they do not license a signal. (MASTERPLAN.md §9; DNR:KILL-STALENESS-ALPHA.)
- S11. Company identity = `cik:` + 10 digits via resolution/identity. Evidence = owner `source_span.v1` exactly as `documents.py` SourceSpan emits, or `field_absence.v1`. Closed enums. No confidence / probability / price-target / score field. (PHASE0_FREEZE D12/D13/D14; gate 3; DEC:NEWS-IMPACT-PHASE0-FREEZE.)
- S12. Rulings R1–R4 bind: excerpt cap and URL patterns are projector rules; `document_version` minimum 1; closed locators, unknown keys rejected not stripped. (rulings_r1_r4.md.)
- S13. Mechanism channel is the closed seven-channel list. (MASTERPLAN.md §4; frozen `channel_hint`.)
- S14. Source text is data, never instructions. (MASTERPLAN.md §3.5; D17/G5.)
- S15. Output authority is `context_only`; `prophet_flags` all false. (frozen envelope.)
- S16. Standing kills: DNR:KILL-LLM-ORIGINATION, KILL-LLM-CONFIDENCE, KILL-LLM-CONTAGION-TAGS, KILL-CAUSAL-DAG-ALPHA, KILL-THESIS-LOBE, KILL-STALENESS-ALPHA, HOLD-STRUCTURE-LEARNERS.
- S17. Display-tier wording is plain words with windows, never certainties, never front-facing falsifier language. (lane law.)
- S18. Issuer role on the source fact is the freeze six-enum (`subject|counterparty|competitor|supplier|customer|incidental`). (PHASE0_FREEZE D10; schema `issuer_role`.) Transfer **target_role** is the Graph-1 subset `{customer, supplier, competitor, partner}`.

### PHYSICS

- P1. A span cannot name two issuers unless both strings (or as-of aliases) appear in the replayed bytes. JSON Schema cannot test that; named validator `V_TWO_PARTY_SPAN` does.
- P2. Datetime inequalities (`outcome_start > information_cutoff`, `fit_end <= information_cutoff`, NYSE calendar for `next_rth_open`) are not expressible as Draft 2020-12 comparisons. Named validators own them; the schema owns the presence of the stamps and the at_origin `full_session_return_used: false` const.
- P3. Residual return is `absolute - sum_i fitted_coefficient_i * factor_i_return` over the **same** `[outcome_start, outcome_end]`. Coefficients fitted after the cutoff leak the outcome into the residual.
- P4. One hop + no cycles ⇒ the path array has length 2 and `source_company_id != target_company_id`. Schema cannot test inequality; `V_SELF_HOP` does.
- P5. America/New_York session bounds (09:30 / 16:00) plus DST require a calendar, not a schema enum.

### INHERITED (owner modules, path:line)

- I1. Three-graph owner document: `research/economic_propagation/D0_THREE_GRAPH_SEPARATION_MAP.md:14-47` (Graph 1 economic relationship / Graph 2 comparability / Graph 3 residual market) and `:51-70` (object assignment). Cited by MASTERPLAN.md §15 as R5.
- I2. GMI theme graph is the Graph-2 spine and assembles, never scores: `engine/theme_graph/__init__.py:1-16`. Live edge types built are only `MEMBER_OF`, `EXPRESSES`, `TRACKS`; no derived company→theme edge: `engine/theme_graph/materialize.py:12-20`.
- I3. Graph-1 GMI types `SUPPLIES` / `ENABLES` / `BOTTLENECK_OF` / `BENEFITS_FROM` are reserved enum, not emitted; `source_class=co_movement` on a `SUPPLIES` edge is named as a trap. D0 map `:51-70` and collapse table. Exposure axes `economic_share`, `trading_beta`, `attention_share` are reserved-null columns: `engine/theme_graph/store.py:55-63` and `RESERVED_EDGE_FIELDS` at `:127-129`.
- I4. Group Pulse is Graph 3, `authority: context_only`, `may_rank/may_gate/may_size` false, payload must not contain a fused score/rank/heat key: `engine/group_pulse.py:1-16`.
- I5. Target-out-of-peer-set already exists as an owner idiom: `engine/coiled.py:337` (self-exclusion) and `engine/cohort_metrics.py:369` ("Peer set = all covered members EXCEPT self").
- I6. Demand Desk spender lists are hardcoded, not PIT Graph 1: `engine/demand_chain.py:8-12` and `:44-49` (`ai_datacenter` spenders MSFT/GOOGL/AMZN/META/ORCL). D0 map collapse row: a list of six spenders is not Graph 1.
- I7. GR3 linked-outsiders never emit customer/supplier/partner/competitor: `engine/group_linked_outsiders.py:8-12`, `RELATIONSHIPS` `:207-218`, `FORBIDDEN_ROLE_LABELS` `:260`. Yield today is zero counterparties. A `supply_agreement` keyword is not a role. D0 map: Graph 1-candidate, never upgrade to customer/supplier.
- I8. Company id: `engine/company_intelligence/identity.py:50-58` `company_id_for_cik` → `cik:` + 10 digits (`cik:0000320193`). Freeze D12 ladder lives in resolution.
- I9. Evidence: `engine/company_intelligence/documents.py:307` `SourceSpan`; `:375` `text_span` (byte_replayed); `:435` `address_only_span`; `:72` `ABSENCE_REASONS`. Freeze D13/D14.
- I10. `DeclaredLocator.address` is an unconstrained mapping: `engine/company_intelligence/resolution.py:134`. R4: unknown locator keys reject at the news-impact boundary.
- I11. `company_event.v1` `EVENT_TYPES` has no `news` member: `engine/company_intelligence/events.py:93-99`. Transfer cites `source_fact_id` of a news-impact fact, not a forced CI event.
- I12. Frozen seven channels: `contracts/news_impact/news_impact_event.v1.schema.json` `$defs.channel_hint` (`revenue_demand` … `market_only`).
- I13. Frozen envelope `prophet_flags` all const false; `authority` const `context_only`.
- I14. `economic_propagation` owner is BLOCKED on #6514 (freeze §9 reuse matrix). This design consumes Graphs 1–3 and the news-impact fact; it does not reuse or wrap the held propagation contract.

### ASSUMED

- A1. ~70–80% two-party-span reject rate (ANSWER FIRST). Falsifier: commission-D indirect-transfer quota once labeled. Default until then: treat the rule as a hard gate, not a rate target.
- A2. Transfer `target_role` stays the four Graph-1 roles; `distributor` maps to `supplier`, `licensee`/`licensor` to `partner`. Widening is a versioned amendment.
- A3. A T2/T3 `counterparty_company_id` already on the source fact does **not** skip `V_TWO_PARTY_SPAN`; the same span may be reused if it already names both.
- A4. Residual factor set in v1 = `{market, documented_peer_residual}`. Sector / MAG7 / GPU legs are recorded as `unused_collinear_factors` absences (S5).
- A5. Session calendar is NYSE regular hours, timestamps stored as UTC `...Z`, displayed as America/New_York windows.
- A6. `macro_shock_fanout.v1` lives in the transfer schema file (one builder packet) and does not mint edges by itself.
- A7. `fitted_coefficient` is a pre-cutoff OLS number, not an originated signal. The field name is `fitted_coefficient`, never a banned token.
- A8. Display summaries are English, ≤500 chars, `text_safe`, window-stamped, no certainty verbs ("priced in", "will", "proves").

If A2–A6 are wrong, the schemas still parse; only enum membership and the fanout home change. A1 does not bind a builder.

---

## (3) Candidate designs

Mechanism-distinct (doctrine §4.3). Standard play named and quarantined (doctrine §4.4).

### C1 — Graph-walk expander (STANDARD PLAY for "transmission")

Walk GMI `MEMBER_OF` co-members, GR baskets, GICS peers and tagged tickers; emit a signed edge per neighbour; measure the full-session move as the effect.

Refutation test: an AMD semiconductor-label item emits an NVIDIA edge with no two-party span; a 09:35 record includes the 16:00 close as a feature. Both fire on C1. Killed by S2, S6, S7, I2, I4, DNR:KILL-LLM-ORIGINATION (the expander originates the link).

### C2 — Held propagation contract as the transfer object

Treat K3-D `economic_propagation.propagation_hypothesis/v1` as the v1 transfer record and add observation windows beside it.

Refutation test: the freeze reuse matrix lists that owner as `NO / BLOCKED` until #6514 lands (PHASE0_FREEZE §9); the lane law forbids reading or modifying it; K3-D refuses participation-only admission. C2 cannot be built inside this grant. Killed by S6, I14.

### C3 — Span-gated one-hop record + cutoff-gated observation (CHOSEN)

Two closed context_only contracts. A transfer edge exists only when a cited owner span names both issuers, role/channel are closed, hop_count=1, Graph-1 provenance, else `transfer_absence.v1`. A macro shock is one `macro_shock_fanout.v1` plus per-issuer roster rows. Observation is a typed window with `information_cutoff`, six delayed-entry **test** arms, pre-cutoff residual fit, target-excluded documented-exposure peer set, and coincident facts stored as `ambiguous_coincident`.

Refutation test that would kill C3: (a) an accepted `transfer_edge.v1` whose `claimed_quote` fails `V_TWO_PARTY_SPAN`; or (b) an `at_origin` row with `full_session_return_used: true` or `outcome_start <= information_cutoff`. Those are the tripwires in §6.

**Why C1 and C2 lose.** C1 collapses Graph 2/3 into Graph 1 and leaks the outcome into the decision. C2 is a held sibling with a participation-only refusal this program is forbidden to repair. C3 is the boring baseline that actually satisfies S2–S10: records and absences, not a new graph and not a predictor.

---

## (4) Frozen-spec draft

Builder implements these types with no further questions. JSON Schema files are the executable form; this section is the law the schemas encode plus the named validators the schemas cannot encode.

### 4.1 Shared envelope (every publishable object)

| Field | Type | Invariant |
|---|---|---|
| `schema` | const per type | closed |
| `authority` | const `context_only` | never another value |
| `prophet_flags` | object | `may_rank`, `may_size`, `may_gate`, `prophet_authority` all const `false` |
| `unsolicited_instruction_detected` | boolean | emitted edges/windows const `false`; if true, only `transfer_absence.v1` with `instruction_detected` |
| `observed_at` | UTC `YYYY-MM-DDTHH:MM:SSZ` | processing time of this record |
| `source_available_at` | same | first admissible feed receipt of the source item |
| `display_summary` | `text_safe` 1–500 | plain words with windows; no certainty; no front-facing falsifier language |

Identity: `company_id` = `^cik:(?!0{10}$)[0-9]{10}$` (freeze D12; `identity.py:50-58`). `fact_id` = `^fact_[0-9a-f]{24}$`. `transfer_id` / `absence_id` = `^xfer_[0-9a-f]{24}$`. `observation_id` = `^obs_[0-9a-f]{24}$`. `shock_id` = `^shock_[0-9a-f]{24}$`.

Evidence: `two_party_span` on an emitted edge is `evidence_span` (`claimed_quote` 1–500 `text_safe` + owner `source_span.v1` 12-key payload). Receipt/locator/version rules identical to the frozen event schema (R1–R4 projector applies). Absence uses `field_absence.v1` reason enum `{not_stated, stated_without_number, range_only, redacted_rights, parse_failed}` plus optional `owner_reason` from `documents.py:72`.

`additionalProperties: false` on every object. Every string `maxLength`d. `text_safe` injection not-patterns copied from the frozen event schema. Forbidden tokens as field names or meanings: confidence, probability, score, target, fair value, rating, contagion.

### 4.2 `transfer_edge.v1` (emitted one-hop)

Required fields:

| Field | Closed type | Notes |
|---|---|---|
| `transfer_id` | `xfer_` + 24 hex | stable id |
| `source_fact_id` | `fact_` + 24 hex | validated news-impact fact; never a raw article id |
| `source_company_id` | `company_id` | subject issuer of the source fact |
| `target_company_id` | `company_id` | second issuer; `V_SELF_HOP` forbids equality |
| `target_role` | `customer \| supplier \| competitor \| partner` | role of the **target** vs the source issuer |
| `edge_direction` | `source_to_target \| target_to_source` | who is the acting party in the cited sentence |
| `operating_effect_on_target` | `positive \| negative \| mixed \| unknown` | operating economics of the **target**, not a price call |
| `mechanism_channel` | frozen seven `channel_hint` | if `market_only` then `operating_effect_on_target` const `unknown` (this is observation territory; prefer abstention — see 4.4.25) |
| `exposure` | `measured {unit, value, evidence}` or `unknown` + `field_absence.v1` | UNKNOWN is a first-class form, not a guessed percent |
| `timing.lag_kind` | `immediate \| intra_day \| next_session \| next_quarter \| multi_quarter \| unknown` | |
| `timing.horizon_period` | freeze `fiscal_period` or `field_absence.v1` | |
| `alternatives` | 1–4 `{channel, claimed_quote}` or `field_absence.v1` | contrary channels named, not scored |
| `graph_provenance` | see below | emitted edges: `graph=economic_relationship`, `generator_kind=source_span_two_party`, `hop_count=1`, `path=[source, target]` |
| `two_party_span` | `evidence_span` | **the** authorizing object |
| `shock_id` | `shock_` id or null | set only when produced from a fanout roster |
| `supersedes_transfer_id` | `xfer_` id or null | non-null on a correction replay |

`exposure.unit` when measured: `percent_of_revenue | percent_of_cogs | usd | units | unknown`.

`graph_provenance.generator_kind` closed: `source_span_two_party | gmi_member_of | gmi_supplies_reserved | gmi_expresses | gmi_tracks | group_reads_basket | group_linked_outsiders | demand_chain_hardcoded | gics_peer | residual_comovement | tagged_ticker_list | shock_exposure_roster`. On an **emitted** edge the only legal generator_kind is `source_span_two_party`. Other kinds appear on absences as `refused_generator`.

Named validators (Phase 3, not schema):

- `V_TWO_PARTY_SPAN`: replayed bytes (or `claimed_quote` as the projector-side stand-in until bodies exist) contain tokens that resolve, via the D12 ladder at `source_available_at`, to **both** `source_company_id` and `target_company_id`. Aliases (GOOGL/GOOG) resolve to one CIK and count as one party.
- `V_SELF_HOP`: source ≠ target.
- `V_ONE_HOP`: `path.length == 2` and no ancestor transfer on the same `source_fact_id` lineage has this target as a source.
- `V_NO_CYCLE`: the undirected pair `{source, target}` plus `source_fact_id` is unique; a reverse edge requires its own two-party span (the shortage case is a different source fact, not a back-propagation of the capex edge).
- `V_SOURCE_FACT`: `source_fact_id` exists as an accepted news-impact fact; `novelty=corrected_fact` on that fact requires this transfer to carry `supersedes_transfer_id` or to be an absence `source_fact_superseded_stale_cite`.
- `V_CHANNEL_MARKET_ONLY`: `mechanism_channel=market_only` is rejected as an **edge** (abstain `channel_market_only_no_graph1`) even though the schema's if/then allows unknown effect — the named validator is the stricter law. Schema keeps the if/then as defense in depth.
- `V_COMPETITOR_CLAIM`: `target_role=competitor` requires the span to state a competitive relationship (displace, take share, rival product), not merely co-membership.
- `V_NEGATION`: a source fact with `negated=true` does not emit a positive-effect edge; it may emit an absence or a correction.

Correction: a later source fact with `novelty=corrected_fact` mints a new `transfer_edge.v1` with `supersedes_transfer_id` pointing at the prior edge (worked case W_correction). Consumers read the undirected latest `transfer_id` per `(source_fact_lineage, source_company_id, target_company_id)`.

### 4.3 `transfer_absence.v1` (typed non-edge)

Required: `absence_id`, `source_fact_id`, `source_company_id`, `candidate_target_company_id` (`company_id` or `field_absence.v1`), `abstention_reason` (closed enum below), `refused_generator` (`graph_provenance` or absence), `two_party_span` (`evidence_absence` or `field_absence.v1`), envelope fields, `display_summary`.

This is the default output. Silence is illegal; an examined candidate that does not meet §4.2 emits this object.

### 4.4 Abstention rules (no edge is emitted unless every gate passes)

Abstention is the default. Emit `transfer_absence.v1` — not an edge — under **any** of:

1. `no_two_party_span` — no cited span, or span does not exist.
2. `span_names_one_party_only` — `V_TWO_PARTY_SPAN` fails.
3. `target_identity_unresolved` — D12 typed absence (ETF tag, artefact `'Q'`, CN code without CIK, dead name).
4. `source_equals_target` — self hop.
5. `hop_exceeds_one` — candidate is a second hop (supplier of a supplier of the source fact's issuer).
6. `cycle_on_source_fact` — would close a cycle on this fact lineage.
7. `graph2_membership_only` — only fundamental/narrative comparability.
8. `graph3_residual_only` — only residual co-movement / pulse / sympathy.
9. `participation_only_refused` — target admitted only because it participated in a move.
10. `gmi_member_of_only` — sole generator is GMI `MEMBER_OF` (`materialize.py:12-20`).
11. `demand_chain_list_only` — sole generator is `engine/demand_chain.py` hardcoded spenders.
12. `linked_outsider_role_unlabeled` — GR3 `supply_agreement` / `disclosed_agreement` without a role-bearing two-party span in **this** source event (`group_linked_outsiders.py:8-12,260`).
13. `role_incidental_or_unknown` — mention is incidental; freeze issuer_role incidental/unknown is not a transfer role.
14. `channel_market_only_no_graph1` — market-only sympathy with no Graph-1 path.
15. `source_fact_not_validated` — source fact rejected, deferred, or quarantined.
16. `source_fact_negated` — the cited event did not occur.
17. `source_fact_superseded_stale_cite` — cites a fact that a correction superseded, without minting a superseding transfer.
18. `body_unavailable` — tape is headline-only (C1_tape Q1); body fetch failed. Counted, not dropped.
19. `rights_redacted` — rights registry refuses the source.
20. `parse_failed` — extractor could not bind the sentence.
21. `name_resolution_ambiguous` — D12 / GR3-style `ambiguous_tie` (two registrants, one title) and no CIK disambiguation.
22. `instruction_detected` — §3.5 injection in source text.
23. `llm_relatedness_tag_refused` — a model-originated related-ticker tag (DNR:KILL-LLM-CONTAGION-TAGS).
24. `structure_learner_refused` — DNR:HOLD-STRUCTURE-LEARNERS.
25. `causal_dag_refused` — DNR:KILL-CAUSAL-DAG-ALPHA.
26. `peer_selected_by_rally` — peer/target set chosen by post-event return.
27. `no_documented_exposure_for_shock` — macro fanout row without a documented exposure (two-party span or filing-backed concentration naming both).
28. `competitor_without_competitive_claim` — `V_COMPETITOR_CLAIM` fails.
29. `second_hop_refused` — explicit second-hop expansion request.
30. `k3d_participation_only_hold` — any attempt to admit a target under the held K3-D participation rule.

A Graph-2 or Graph-3 path may be recorded on the absence as `refused_generator`. It is never upgraded to an edge.

### 4.5 Macro / industry shock: analyse once, fan out by exposure

`macro_shock_fanout.v1` (same schema file):

| Field | Law |
|---|---|
| `shock_id` | one id per source fact that is a multi-issuer shock |
| `source_fact_id` | the single analysed fact |
| `shock_span` | owner `evidence_span` of the shock sentence |
| `analysed_once` | const `true` |
| `exposure_roster` | 2–64 rows `{company_id, exposure, transfer_ref}` |

Procedure: (1) classify the source fact once; (2) build the roster from **documented** Graph-1 exposure (two-party spans in this document, or prior filing-backed named customer/supplier concentration that still passes `V_TWO_PARTY_SPAN` against that filing span — not GMI membership); (3) for each roster row, either mint `transfer_edge.v1` with `shock_id` set or mint `transfer_absence.v1` with `no_documented_exposure_for_shock` / `no_two_party_span`; (4) **zero** per-issuer frontier calls. The expensive review packet, if any, is the shock packet plus the roster, matching MASTERPLAN.md §10.

### 4.6 Peer-set preselection (feeds observation, not transfer admission)

`peer_set` on `observation_window.v1`:

- `selection` const `documented_exposure` (the only legal selector in v1).
- `member_ids`: 1–64 `company_id`, unique, **must not contain** `excluded_target_id`.
- `excluded_target_id`: the observation target.
- `target_excluded` const `true`.

Illegal selectors (named validator `V_PEER_SELECTOR`): rallied-most, participation-only, GMI `MEMBER_OF` only, residual co-movement group, MAG7 membership. Those produce `field_absence.v1` on `peer_set` with reason `not_stated` and the observation still stores absolute response with `attribution_state=unmeasured` if no documented set exists.

This matches I5 (owner self-exclusion) and S5.

### 4.7 `observation_window.v1`

One type, `mode` discriminator.

#### (e) Two modes and the cutoff

| Mode | `information_cutoff` | Features admitted | Outcome window |
|---|---|---|---|
| `at_origin` | equals `entry_timestamp` (the delayed-entry stamp) | data with timestamps **< cutoff** (strictly before). Decision stamp may equal cutoff. | `outcome_start >= decision_timestamp` and `outcome_start > information_cutoff - 0` in practice: `outcome_start >= entry_timestamp` and **must not** include bars whose end is ≤ cutoff. Named validator `V_CUTOFF`: every feature `observed_at <= information_cutoff` for landmark, `<` for at_origin prices that print at the decision bar; `outcome_start >= information_cutoff` and the first return bar is the first bar **after** the cutoff. |
| `landmark` | equals `decision_timestamp` (the landmark) | price and news with timestamps **≤ cutoff** | `outcome_start` **after** the landmark (next RTH open if landmark is 16:00 ET; else next bar after cutoff) |

`first_admissible_feed_receipt` is T0: the earliest lawful feed timestamp at which the source item was available to this system (qbus `_crawled_at` when populated, else publisher `seendate` flagged `PUBLISHER_STATED` — C1_tape Q1). It is never the publisher's claimed happening-time if that precedes feed receipt.

`full_session_return_used`: const `false` when `mode=at_origin` (schema if/then). Using previous-close-to-close or open-to-close that **straddles** the cutoff as the outcome of a 09:35 decision is forbidden (S7). A landmark at 16:00 may **describe** the session that just closed as a **feature**, not as its own outcome; its outcome starts afterward (worked case W_obs_1600).

#### (f) Delayed-entry policies (exact stamps relative to T0)

All six are **test arms**, not alpha claims. `entry_timestamp` is computed from T0 = `first_admissible_feed_receipt`. `test_purpose` is schema-tied to the policy.

| `delayed_entry_policy` | `entry_timestamp` | `test_purpose` |
|---|---|---|
| `feed_receipt` | T0 | `none` |
| `plus_60s` | T0 + 60 seconds | `source_delay` |
| `plus_900s` | T0 + 900 seconds | `research_time` |
| `next_rth_open` | next NYSE regular-hours open **strictly after** T0 (09:30 America/New_York) | `gap_open` |
| `same_session_close_1600_et` | 16:00 America/New_York of the RTH session containing T0 if T0 < that close; else the next 16:00 ET | `session_close_landmark` |
| `next_rth_open_plus_one_session` | RTH open of the session **after** the session that contains T0 | `stale_news_treatment` |

`next_rth_open_plus_one_session` is the stale-news **test** arm (S10). It does not mint a staleness feature, a decay parameter, or a trading rule. DNR:KILL-STALENESS-ALPHA.

If T0 falls on a weekend/holiday, `next_rth_open` is the next session's 09:30 ET. Named validator `V_ENTRY_POLICY` checks the arithmetic against a frozen NYSE calendar file (existing owner; this contract does not create a calendar).

#### (g) Measurement windows

- **Absolute response**: simple or log return of `target_company_id` over `[window_start, window_end]` = `[outcome_start, outcome_end]`. Form `measured` or `unmeasured` + absence.
- **Residual response**: absolute minus `sum_i fitted_coefficient_i * factor_i_return` over the **same** window.
- **Residual fit**: `method` const `ols_trailing_pre_cutoff`; `fit_end <= information_cutoff` (`V_FIT_CUTOFF`); legs only `{market, documented_peer_residual}`; `window_bars` 2–2520. Sector, MAG7, GPU are `unused_collinear_factors` with `field_absence.v1` (S5). Coefficients are not a rank.
- **Matched window**: `[matched_window_start, matched_window_end]` has the same duration and the same session-type (RTH-to-RTH or intra-RTH) as the outcome window, and `matched_window_end <= information_cutoff`.
- **Full-day rule**: for a 09:35 at_origin decision, the outcome window is `[09:35, chosen_end]` (worked case: 16:00 same day) or a later delayed-entry stamp. It is **not** `[previous close, close]`, **not** `[open, close]`, **not** the print-to-close of a bar that opened before the cutoff. Schema: `full_session_return_used=false`. Named validator `V_NO_FULL_DAY` rejects an `at_origin` row whose absolute window starts at the session open or previous close when `decision_timestamp` is intra-RTH.

#### (h) Coincident events = ambiguous attribution

`coincident_events`: 0–16 `{fact_id, company_id, observed_at}`. A fact is coincident when it shares the target (or a documented-exposure peer used in the residual) and its `source_available_at` falls inside `[information_cutoff - 0, outcome_end]`.

If the array is non-empty, schema if/then forces `attribution_state=ambiguous_coincident`. Residual numbers may still be stored as measurements of the **window**; they are not assigned to one fact. There is no resolver, no DAG, no "primary" event picker. `unambiguous_single_event` is legal only when the array is empty. `unmeasured` when the tape/rights/fit is missing.

An abnormal residual is not causation. A flat residual is not proof of non-incorporation. Display summary states the window and the coincidence, nothing stronger (S8, S17).

### 4.8 What this contract refuses to be

- Not a predictive head, not an episode, not a B4 input (`prophet_flags` false).
- Not a fourth graph. Graph 1/2/3 stay with GMI / GR / pulse owners (I1–I4).
- Not K3-D. Participation-only admission is an abstention reason (S6).
- Not a structure learner, causal DAG, relatedness tagger, thesis lobe, or staleness-alpha.
- Not a rival span store: it embeds `source_span.v1` / `field_absence.v1`.

---

## (5) Worked cases

Eight schema-validated instances (7 required shapes + fanout). JSON is the payload a builder would persist.

### 5.1 Customer capex increase helping a supplier — EDGE EMITTED

`cases/W_customer_capex_supplier.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "transfer_edge.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "unsolicited_instruction_detected": false,
  "transfer_id": "xfer_d4d635d3fd7af11f42bc115b",
  "source_fact_id": "fact_678e8bf5a1906cc701210c40",
  "source_company_id": "cik:0000320193",
  "target_company_id": "cik:0001046179",
  "target_role": "supplier",
  "edge_direction": "source_to_target",
  "operating_effect_on_target": "positive",
  "mechanism_channel": "revenue_demand",
  "exposure": {
    "form": "unknown",
    "absence": {
      "schema": "field_absence.v1",
      "authority": "context_only",
      "reason": "stated_without_number",
      "subject": "exposure",
      "detail": "named foundry, no share figure",
      "missing_fields": []
    }
  },
  "timing": {
    "lag_kind": "next_quarter",
    "horizon_period": {
      "year": 2027,
      "quarter": 1,
      "calendar_end": "2027-03-31",
      "period_kind": "quarter"
    }
  },
  "alternatives": [
    {
      "channel": "market_only",
      "claimed_quote": "Same-session semiconductor basket moves are a separate market-only hypothesis."
    }
  ],
  "graph_provenance": {
    "graph": "economic_relationship",
    "generator_kind": "source_span_two_party",
    "generator_id": "span_gate.v1",
    "as_of": "2026-09-28T13:35:00Z",
    "belief_time": "2026-09-28T13:35:00Z",
    "hop_count": 1,
    "path": [
      "cik:0000320193",
      "cik:0001046179"
    ]
  },
  "two_party_span": {
    "claimed_quote": "Apple increased iPhone assembly capex and named TSMC as the foundry that will take the incremental wafer starts.",
    "span": {
      "schema": "source_span.v1",
      "authority": "context_only",
      "span_id": "span_8d4f69ef27da9b40ad67",
      "document_id": "doc_aapl_capex_20260928",
      "document_version": 1,
      "locator": {
        "kind": "text_span",
        "sub_kind": "transcript_segment",
        "segment_index": 0,
        "span_start_byte": 0,
        "span_end_byte": 112
      },
      "text_sha256": "ea6b7d0e18f87054e754daf0847ffcbd6988fd9a2a0cd5a9f3838418236425b4",
      "display_excerpt": "Apple increased iPhone assembly capex and named TSMC as the foundry that will take the incremental wafer starts.",
      "rights_profile": "rp_unknown_v1",
      "receipt_state": "byte_replayed",
      "receipt": {
        "source_sha256": "c8f2d0a816e5c9ecadd7895334eadbd11ed39f3605020f572051f182017c1648",
        "segment_index": 0,
        "segment_sha256": "ea6b7d0e18f87054e754daf0847ffcbd6988fd9a2a0cd5a9f3838418236425b4",
        "segment_bytes": 112,
        "span_start_byte": 0,
        "span_end_byte": 112,
        "text_sha256": "ea6b7d0e18f87054e754daf0847ffcbd6988fd9a2a0cd5a9f3838418236425b4"
      },
      "unreplayable_reason": null
    }
  },
  "shock_id": null,
  "supersedes_transfer_id": null,
  "observed_at": "2026-09-28T13:35:00Z",
  "source_available_at": "2026-09-28T13:32:14Z",
  "display_summary": "Over the next-quarter window, Apple's named foundry relationship with TSMC is the documented path for the capex increase; exposure share is not stated."
}
```
### 5.2 Semiconductor label, no shared end-market evidence — ABSTAIN

`cases/W_semi_label_abstain.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "transfer_absence.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "unsolicited_instruction_detected": false,
  "absence_id": "xfer_3216a5cf4ac25f0091271639",
  "source_fact_id": "fact_21fff50d62560d3c535fac04",
  "source_company_id": "cik:0000002488",
  "candidate_target_company_id": "cik:0001045810",
  "abstention_reason": "gmi_member_of_only",
  "refused_generator": {
    "graph": "fundamental_comparability",
    "generator_kind": "gmi_member_of",
    "generator_id": "theme_graph:MEMBER_OF:ai_semiconductors",
    "as_of": "2026-09-28T13:35:00Z",
    "belief_time": "2026-09-28T13:35:00Z",
    "hop_count": 1,
    "path": [
      "cik:0000002488",
      "cik:0001045810"
    ]
  },
  "two_party_span": {
    "schema": "field_absence.v1",
    "authority": "context_only",
    "reason": "not_stated",
    "subject": "two_party_span",
    "detail": "headline carries a semiconductor label only; no span names both issuers or a shared end market",
    "missing_fields": []
  },
  "observed_at": "2026-09-28T13:35:00Z",
  "source_available_at": "2026-09-28T13:32:14Z",
  "display_summary": "AMD and NVIDIA share a semiconductor basket label. No cited span names both parties or a shared end market, so no transfer edge is emitted."
}
```
### 5.3 Supplier shortage hurting a buyer — NEGATIVE CHANNEL

`cases/W_supplier_shortage_buyer.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "transfer_edge.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "unsolicited_instruction_detected": false,
  "transfer_id": "xfer_0d59c114009b178ceb2fa778",
  "source_fact_id": "fact_df49d7e9e9f7da48ed1b7e33",
  "source_company_id": "cik:0001046179",
  "target_company_id": "cik:0000320193",
  "target_role": "customer",
  "edge_direction": "source_to_target",
  "operating_effect_on_target": "negative",
  "mechanism_channel": "revenue_demand",
  "exposure": {
    "form": "unknown",
    "absence": {
      "schema": "field_absence.v1",
      "authority": "context_only",
      "reason": "stated_without_number",
      "subject": "exposure",
      "detail": "shipment cut named, volume not given",
      "missing_fields": []
    }
  },
  "timing": {
    "lag_kind": "intra_day",
    "horizon_period": {
      "year": 2026,
      "quarter": 4,
      "calendar_end": "2026-12-31",
      "period_kind": "quarter"
    }
  },
  "alternatives": [
    {
      "channel": "margin_cost",
      "claimed_quote": "A wafer cut can also raise Apple's unit cost if it buys spot supply."
    }
  ],
  "graph_provenance": {
    "graph": "economic_relationship",
    "generator_kind": "source_span_two_party",
    "generator_id": "span_gate.v1",
    "as_of": "2026-09-28T13:35:00Z",
    "belief_time": "2026-09-28T13:35:00Z",
    "hop_count": 1,
    "path": [
      "cik:0001046179",
      "cik:0000320193"
    ]
  },
  "two_party_span": {
    "claimed_quote": "TSMC said a tool outage will cut wafer shipments to Apple this quarter.",
    "span": {
      "schema": "source_span.v1",
      "authority": "context_only",
      "span_id": "span_fb2041e3526b45a3d8ea",
      "document_id": "doc_tsmc_outage_20260928",
      "document_version": 1,
      "locator": {
        "kind": "text_span",
        "sub_kind": "transcript_segment",
        "segment_index": 0,
        "span_start_byte": 0,
        "span_end_byte": 71
      },
      "text_sha256": "92c9daa36f867f0d405d0e62237bf63758af9668d754c6724bde8e12c89335ed",
      "display_excerpt": "TSMC said a tool outage will cut wafer shipments to Apple this quarter.",
      "rights_profile": "rp_unknown_v1",
      "receipt_state": "byte_replayed",
      "receipt": {
        "source_sha256": "18e86661c80406362922f6bf8f976399a0f9523c2be4af4caf8a187ebf90dfb6",
        "segment_index": 0,
        "segment_sha256": "92c9daa36f867f0d405d0e62237bf63758af9668d754c6724bde8e12c89335ed",
        "segment_bytes": 71,
        "span_start_byte": 0,
        "span_end_byte": 71,
        "text_sha256": "92c9daa36f867f0d405d0e62237bf63758af9668d754c6724bde8e12c89335ed"
      },
      "unreplayable_reason": null
    }
  },
  "shock_id": null,
  "supersedes_transfer_id": null,
  "observed_at": "2026-09-28T13:35:00Z",
  "source_available_at": "2026-09-28T13:32:14Z",
  "display_summary": "Over this quarter, TSMC's named shipment cut to Apple is a negative demand-path for the buyer; the volume of the cut is not stated."
}
```
### 5.4 Correction / supersedes — later statement withdraws incremental demand

`cases/W_correction_supersedes.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "transfer_edge.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "unsolicited_instruction_detected": false,
  "transfer_id": "xfer_c2e70e7efa3ae4153bfc98e8",
  "source_fact_id": "fact_9c4d47cde166501dfa2185ea",
  "source_company_id": "cik:0000320193",
  "target_company_id": "cik:0001046179",
  "target_role": "supplier",
  "edge_direction": "source_to_target",
  "operating_effect_on_target": "unknown",
  "mechanism_channel": "revenue_demand",
  "exposure": {
    "form": "unknown",
    "absence": {
      "schema": "field_absence.v1",
      "authority": "context_only",
      "reason": "not_stated",
      "subject": "exposure",
      "detail": "correction withdraws incremental demand; no replacement figure",
      "missing_fields": []
    }
  },
  "timing": {
    "lag_kind": "unknown",
    "horizon_period": {
      "schema": "field_absence.v1",
      "authority": "context_only",
      "reason": "not_stated",
      "subject": "timing.horizon_period",
      "detail": "",
      "missing_fields": []
    }
  },
  "alternatives": {
    "schema": "field_absence.v1",
    "authority": "context_only",
    "reason": "not_stated",
    "subject": "alternatives",
    "detail": "",
    "missing_fields": []
  },
  "graph_provenance": {
    "graph": "economic_relationship",
    "generator_kind": "source_span_two_party",
    "generator_id": "span_gate.v1",
    "as_of": "2026-09-29T14:10:00Z",
    "belief_time": "2026-09-29T14:10:00Z",
    "hop_count": 1,
    "path": [
      "cik:0000320193",
      "cik:0001046179"
    ]
  },
  "two_party_span": {
    "claimed_quote": "Apple later said the capex figure restated previously announced plans and is not incremental demand for TSMC.",
    "span": {
      "schema": "source_span.v1",
      "authority": "context_only",
      "span_id": "span_2a6417aa408f0e8e2d06",
      "document_id": "doc_aapl_correction_20260929",
      "document_version": 1,
      "locator": {
        "kind": "text_span",
        "sub_kind": "transcript_segment",
        "segment_index": 0,
        "span_start_byte": 0,
        "span_end_byte": 109
      },
      "text_sha256": "fe9ac6792173a7574c19d420cc57781d4016b8fbf94d4109d452f4bf91f70de8",
      "display_excerpt": "Apple later said the capex figure restated previously announced plans and is not incremental demand for TSMC.",
      "rights_profile": "rp_unknown_v1",
      "receipt_state": "byte_replayed",
      "receipt": {
        "source_sha256": "c2dc6f65478b0414bd6133f6d1b7195cb2fe5e04d11cff35aa20ac3d355f810b",
        "segment_index": 0,
        "segment_sha256": "fe9ac6792173a7574c19d420cc57781d4016b8fbf94d4109d452f4bf91f70de8",
        "segment_bytes": 109,
        "span_start_byte": 0,
        "span_end_byte": 109,
        "text_sha256": "fe9ac6792173a7574c19d420cc57781d4016b8fbf94d4109d452f4bf91f70de8"
      },
      "unreplayable_reason": null
    }
  },
  "shock_id": null,
  "supersedes_transfer_id": "xfer_d4d635d3fd7af11f42bc115b",
  "observed_at": "2026-09-29T14:10:00Z",
  "source_available_at": "2026-09-29T14:08:00Z",
  "display_summary": "Apple's later statement names TSMC and withdraws the incremental-demand reading of the prior capex item; this record supersedes the earlier transfer."
}
```
### 5.5 Coincident-events day — AMBIGUOUS ATTRIBUTION

`cases/W_obs_coincident_ambiguous.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "observation_window.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "unsolicited_instruction_detected": false,
  "observation_id": "obs_f7c6bb98eef2bc61332b6d99",
  "mode": "at_origin",
  "source_fact_id": "fact_678e8bf5a1906cc701210c40",
  "target_company_id": "cik:0001046179",
  "first_admissible_feed_receipt": "2026-09-28T13:32:14Z",
  "delayed_entry_policy": "plus_900s",
  "test_purpose": "research_time",
  "entry_timestamp": "2026-09-28T13:47:14Z",
  "information_cutoff": "2026-09-28T13:47:14Z",
  "decision_timestamp": "2026-09-28T13:47:14Z",
  "outcome_start": "2026-09-28T13:47:14Z",
  "outcome_end": "2026-09-28T20:00:00Z",
  "matched_window_start": "2026-09-25T13:47:14Z",
  "matched_window_end": "2026-09-25T20:00:00Z",
  "full_session_return_used": false,
  "absolute_response": {
    "form": "measured",
    "unit": "simple_return",
    "value": 0.018,
    "window_start": "2026-09-28T13:47:14Z",
    "window_end": "2026-09-28T20:00:00Z"
  },
  "residual_response": {
    "form": "unmeasured",
    "absence": {
      "schema": "field_absence.v1",
      "authority": "context_only",
      "reason": "parse_failed",
      "subject": "residual_response",
      "detail": "two source facts share the window; residual is stored, attribution is not assigned to one fact",
      "missing_fields": []
    }
  },
  "residual_fit": {
    "method": "ols_trailing_pre_cutoff",
    "fit_start": "2026-07-01T20:00:00Z",
    "fit_end": "2026-09-25T20:00:00Z",
    "legs": [
      {
        "factor_id": "market",
        "fitted_coefficient": 1.12,
        "window_bars": 60
      },
      {
        "factor_id": "documented_peer_residual",
        "fitted_coefficient": 0.41,
        "window_bars": 60
      }
    ],
    "unused_collinear_factors": [
      {
        "factor_id": "sector",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.sector",
          "detail": "collinear with market plus documented-peer residual; not subtracted",
          "missing_fields": []
        }
      },
      {
        "factor_id": "mag7",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.mag7",
          "detail": "collinear MAG7 term reserved unused",
          "missing_fields": []
        }
      },
      {
        "factor_id": "gpu_theme",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.gpu_theme",
          "detail": "collinear GPU term reserved unused",
          "missing_fields": []
        }
      }
    ]
  },
  "peer_set": {
    "selection": "documented_exposure",
    "member_ids": [
      "cik:0000937966",
      "cik:0000723125"
    ],
    "excluded_target_id": "cik:0001046179",
    "target_excluded": true
  },
  "coincident_events": [
    {
      "fact_id": "fact_592b59ae8da56136dbfd0608",
      "company_id": "cik:0001046179",
      "observed_at": "2026-09-28T13:40:00Z"
    }
  ],
  "attribution_state": "ambiguous_coincident",
  "observed_at": "2026-09-28T20:00:00Z",
  "source_available_at": "2026-09-28T13:32:14Z",
  "display_summary": "From 13:47:14Z to 16:00 America/New_York, TSMC's window return is stored. A second TSMC fact arrived at 13:40Z in the same window, so attribution stays ambiguous."
}
```
### 5.6 Observation: 09:35 at-origin (plus_60s from T0=13:32:14Z)

`cases/W_obs_0935_at_origin.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "observation_window.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "unsolicited_instruction_detected": false,
  "observation_id": "obs_466cb0049eac67f446ea3d94",
  "mode": "at_origin",
  "source_fact_id": "fact_678e8bf5a1906cc701210c40",
  "target_company_id": "cik:0001046179",
  "first_admissible_feed_receipt": "2026-09-28T13:32:14Z",
  "delayed_entry_policy": "plus_60s",
  "test_purpose": "source_delay",
  "entry_timestamp": "2026-09-28T13:33:14Z",
  "information_cutoff": "2026-09-28T13:33:14Z",
  "decision_timestamp": "2026-09-28T13:35:00Z",
  "outcome_start": "2026-09-28T13:35:00Z",
  "outcome_end": "2026-09-28T20:00:00Z",
  "matched_window_start": "2026-09-25T13:35:00Z",
  "matched_window_end": "2026-09-25T20:00:00Z",
  "full_session_return_used": false,
  "absolute_response": {
    "form": "measured",
    "unit": "simple_return",
    "value": 0.012,
    "window_start": "2026-09-28T13:35:00Z",
    "window_end": "2026-09-28T20:00:00Z"
  },
  "residual_response": {
    "form": "measured",
    "unit": "simple_return",
    "value": 0.004,
    "window_start": "2026-09-28T13:35:00Z",
    "window_end": "2026-09-28T20:00:00Z"
  },
  "residual_fit": {
    "method": "ols_trailing_pre_cutoff",
    "fit_start": "2026-07-01T20:00:00Z",
    "fit_end": "2026-09-25T20:00:00Z",
    "legs": [
      {
        "factor_id": "market",
        "fitted_coefficient": 1.12,
        "window_bars": 60
      },
      {
        "factor_id": "documented_peer_residual",
        "fitted_coefficient": 0.41,
        "window_bars": 60
      }
    ],
    "unused_collinear_factors": [
      {
        "factor_id": "sector",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.sector",
          "detail": "collinear with market plus documented-peer residual; not subtracted",
          "missing_fields": []
        }
      },
      {
        "factor_id": "mag7",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.mag7",
          "detail": "collinear MAG7 term reserved unused",
          "missing_fields": []
        }
      },
      {
        "factor_id": "gpu_theme",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.gpu_theme",
          "detail": "collinear GPU term reserved unused",
          "missing_fields": []
        }
      }
    ]
  },
  "peer_set": {
    "selection": "documented_exposure",
    "member_ids": [
      "cik:0000937966",
      "cik:0000723125"
    ],
    "excluded_target_id": "cik:0001046179",
    "target_excluded": true
  },
  "coincident_events": [],
  "attribution_state": "unambiguous_single_event",
  "observed_at": "2026-09-28T20:00:00Z",
  "source_available_at": "2026-09-28T13:32:14Z",
  "display_summary": "From 09:35 to 16:00 America/New_York on 2026-09-28, after a 60-second delay from first feed receipt, TSMC's residual return versus the pre-event market and documented-peer coefficients is recorded over that window. The full-session move is not used."
}
```
### 5.7 Observation: 16:00 landmark (outcome starts next RTH open)

`cases/W_obs_1600_landmark.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "observation_window.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "unsolicited_instruction_detected": false,
  "observation_id": "obs_1d640783f9ecc86a42a56a7e",
  "mode": "landmark",
  "source_fact_id": "fact_678e8bf5a1906cc701210c40",
  "target_company_id": "cik:0001046179",
  "first_admissible_feed_receipt": "2026-09-28T13:32:14Z",
  "delayed_entry_policy": "same_session_close_1600_et",
  "test_purpose": "session_close_landmark",
  "entry_timestamp": "2026-09-28T20:00:00Z",
  "information_cutoff": "2026-09-28T20:00:00Z",
  "decision_timestamp": "2026-09-28T20:00:00Z",
  "outcome_start": "2026-09-29T13:30:00Z",
  "outcome_end": "2026-09-29T20:00:00Z",
  "matched_window_start": "2026-09-26T13:30:00Z",
  "matched_window_end": "2026-09-26T20:00:00Z",
  "full_session_return_used": false,
  "absolute_response": {
    "form": "measured",
    "unit": "simple_return",
    "value": -0.003,
    "window_start": "2026-09-29T13:30:00Z",
    "window_end": "2026-09-29T20:00:00Z"
  },
  "residual_response": {
    "form": "measured",
    "unit": "simple_return",
    "value": -0.001,
    "window_start": "2026-09-29T13:30:00Z",
    "window_end": "2026-09-29T20:00:00Z"
  },
  "residual_fit": {
    "method": "ols_trailing_pre_cutoff",
    "fit_start": "2026-07-01T20:00:00Z",
    "fit_end": "2026-09-28T20:00:00Z",
    "legs": [
      {
        "factor_id": "market",
        "fitted_coefficient": 1.12,
        "window_bars": 60
      },
      {
        "factor_id": "documented_peer_residual",
        "fitted_coefficient": 0.41,
        "window_bars": 60
      }
    ],
    "unused_collinear_factors": [
      {
        "factor_id": "sector",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.sector",
          "detail": "collinear with market plus documented-peer residual; not subtracted",
          "missing_fields": []
        }
      },
      {
        "factor_id": "mag7",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.mag7",
          "detail": "collinear MAG7 term reserved unused",
          "missing_fields": []
        }
      },
      {
        "factor_id": "gpu_theme",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "residual_fit.gpu_theme",
          "detail": "collinear GPU term reserved unused",
          "missing_fields": []
        }
      }
    ]
  },
  "peer_set": {
    "selection": "documented_exposure",
    "member_ids": [
      "cik:0000937966",
      "cik:0000723125"
    ],
    "excluded_target_id": "cik:0001046179",
    "target_excluded": true
  },
  "coincident_events": [],
  "attribution_state": "unambiguous_single_event",
  "observed_at": "2026-09-29T20:00:00Z",
  "source_available_at": "2026-09-28T13:32:14Z",
  "display_summary": "At the 16:00 America/New_York landmark on 2026-09-28, features may include news and prices up to that stamp. The outcome window starts at the next regular-hours open and ends at that session's close."
}
```
### 5.8 Macro shock analysed once, fan-out roster without per-issuer edges

`cases/W_macro_shock_fanout.json` — jsonschema ACCEPT against the matching top-level oneOf.

```json
{
  "schema": "macro_shock_fanout.v1",
  "authority": "context_only",
  "prophet_flags": {
    "may_rank": false,
    "may_size": false,
    "may_gate": false,
    "prophet_authority": false
  },
  "shock_id": "shock_8c92aec324c8f70fa3ba98ba",
  "source_fact_id": "fact_678e8bf5a1906cc701210c40",
  "shock_span": {
    "claimed_quote": "A regional power curtailment hit several Taiwan foundry campuses on the same morning.",
    "span": {
      "schema": "source_span.v1",
      "authority": "context_only",
      "span_id": "span_b1c5944e5e06f7300a8d",
      "document_id": "doc_power_curtail_20260928",
      "document_version": 1,
      "locator": {
        "kind": "text_span",
        "sub_kind": "transcript_segment",
        "segment_index": 0,
        "span_start_byte": 0,
        "span_end_byte": 85
      },
      "text_sha256": "2cf2958582c6ed6baa3f3fe437c8d32e6fd11a56108656914b895ee8532d2ab8",
      "display_excerpt": "A regional power curtailment hit several Taiwan foundry campuses on the same morning.",
      "rights_profile": "rp_unknown_v1",
      "receipt_state": "byte_replayed",
      "receipt": {
        "source_sha256": "3f56cb140cc12433c5b9890ead69de78f656f2bb841236d551631bc446cc4215",
        "segment_index": 0,
        "segment_sha256": "2cf2958582c6ed6baa3f3fe437c8d32e6fd11a56108656914b895ee8532d2ab8",
        "segment_bytes": 85,
        "span_start_byte": 0,
        "span_end_byte": 85,
        "text_sha256": "2cf2958582c6ed6baa3f3fe437c8d32e6fd11a56108656914b895ee8532d2ab8"
      },
      "unreplayable_reason": null
    }
  },
  "analysed_once": true,
  "exposure_roster": [
    {
      "company_id": "cik:0001046179",
      "exposure": {
        "form": "unknown",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "exposure",
          "detail": "",
          "missing_fields": []
        }
      },
      "transfer_ref": {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": "not_stated",
        "subject": "transfer_ref",
        "detail": "no two-party span from this shock text to TSMC",
        "missing_fields": []
      }
    },
    {
      "company_id": "cik:0000937966",
      "exposure": {
        "form": "unknown",
        "absence": {
          "schema": "field_absence.v1",
          "authority": "context_only",
          "reason": "not_stated",
          "subject": "exposure",
          "detail": "",
          "missing_fields": []
        }
      },
      "transfer_ref": {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": "not_stated",
        "subject": "transfer_ref",
        "detail": "no two-party span from this shock text to ASML",
        "missing_fields": []
      }
    }
  ],
  "observed_at": "2026-09-28T13:35:00Z",
  "source_available_at": "2026-09-28T13:32:14Z",
  "display_summary": "The power-curtailment item is analysed once. Issuer rows are filled only from documented exposure; this roster records two foundry names without emitting edges because the shock text does not name them."
}
```

---

## (6) Failure modes and tripwires

| Failure | What it looks like | Tripwire |
|---|---|---|
| F1 Unsupported ticker-to-supplier | Edge with Graph-2 `MEMBER_OF` or a tagged ticker and a one-party span | `V_TWO_PARTY_SPAN` + schema `generator_kind` const on edges; freeze §11 count of `unsupported_transfer=yes` must stay 0 |
| F2 Competitor-by-label | AMD item → NVIDIA edge because both are "semis" | worked case 5.2 must ACCEPT as absence `gmi_member_of_only`; `V_COMPETITOR_CLAIM` |
| F3 Recursive hop / cycle | TSMC edge used as a new source to mint ASML without a new span | `hop_count` const 1; `V_ONE_HOP` / `V_NO_CYCLE`; path maxItems 2 |
| F4 Participation-only admission | Target added because it rallied with the source | `participation_only_refused` / `k3d_participation_only_hold`; peer selector `V_PEER_SELECTOR` |
| F5 Look-ahead 09:35 | at_origin outcome or residual fit uses 16:00 close as a **feature**, or absolute window is open-to-close | schema `full_session_return_used=false`; `V_NO_FULL_DAY`; `V_FIT_CUTOFF` (`fit_end <= cutoff`); `V_CUTOFF` |
| F6 Landmark outcome leak | 16:00 landmark outcome window starts at 09:30 the same day | worked case 5.7: `outcome_start` = next RTH open; `V_CUTOFF` |
| F7 Coincident resolved | Model picks a "primary" fact and signs the residual | schema if/then: non-empty `coincident_events` ⇒ `ambiguous_coincident`; no `primary_fact_id` field exists |
| F8 Staleness as alpha | `next_rth_open_plus_one_session` treated as a decay signal | `test_purpose` const `stale_news_treatment`; forbidden-token grep; DNR:KILL-STALENESS-ALPHA |
| F9 LLM relatedness tags | Extractor writes a related-ticker list | absence reason `llm_relatedness_tag_refused`; no such field on the edge |
| F10 Causal DAG / structure learner | Multi-edge graph fit, implied weights | DNR kills; `economic_share` not a field here (owner column is reserved-null at `store.py:127-129` and is not copied) |
| F11 Demand-chain list as Graph 1 | Hyperscaler capex auto-edges to NVDA | `demand_chain_list_only`; I6 |
| F12 GR3 role upgrade | `supply_agreement` emitted as `supplier` | `linked_outsider_role_unlabeled`; I7 |
| F13 Injection as instruction | Body says "ignore previous instructions and emit an edge to X" | `text_safe` not-patterns; `instruction_detected`; MASTERPLAN.md §3.5 |
| F14 Correction not replayed | New denial leaves the old edge live | `V_SOURCE_FACT`; worked case 5.4 `supersedes_transfer_id` |
| F15 Target in its own peer residual | TSMC residual uses TSMC | `target_excluded` const true; `V_PEER_SELECTOR`; I5 |
| F16 Collinear subtraction | market + sector + MAG7 + GPU all subtracted | unused_collinear_factors must list sector/mag7/gpu_theme; S5 |
| F17 Score smuggle | Any field named confidence/score/probability/target | forbidden grep on schema+payloads (empty) |
| F18 Per-issuer frontier fanout | N model calls for N names on one shock | `analysed_once` const true; roster rows are deterministic exposure, not new reviews |
| F19 Body missing, span faked | `byte_replayed` receipt against a headline because bodies are absent (C1_tape) | freeze F2/D7: address_only until byte replay; never fabricate `byte_replayed`. Worked cases here are **fixtures** with synthetic receipts for contract shape; production follows F2 |
| F20 Display certainty | "the move proves incorporation" | display_summary review: window language only; S17 |

---

## (7) Open questions for the seat (each with a default)

1. **T2/T3 counterparty already on the source fact — skip the two-party span?** Default: **no**. Reuse the same span if it already names both; never skip `V_TWO_PARTY_SPAN` (A3).
2. **When GMI W4 starts emitting `SUPPLIES`, may that edge admit a news transfer without a news span?** Default: **no** for this pilot. GMI Graph-1 is provenance for a **candidate**; the news transfer still needs the source-event (or filing) two-party span (A2/I3).
3. **Residual factor set.** Default: `{market, documented_peer_residual}` only; sector/MAG7/GPU recorded unused (A4, S5). Flip only with a written collinearity study, not by adding legs.
4. **Keep `next_rth_open_plus_one_session` in v1?** Default: **yes**, tagged `stale_news_treatment`, no alpha claim (S10).
5. **Widen `target_role` with distributor/licensee?** Default: **no**; map into `supplier` / `partner` (A2). Version the schema if a real owner caller needs the extra words.
6. **Fanout object home.** Default: `$def` in `transfer_edge.v1.schema.json` (A6), not a third contract file.
7. **At-origin inequality: `observed_at < cutoff` vs `<=`.** Default: prices use the last **completed** bar ending at or before cutoff; the decision bar's own close is **not** a feature for at_origin (it is the first outcome tick). Landmark may include the landmark bar as a feature. Write this as `V_CUTOFF` prose in the Phase 3 validator.
8. **May a GR3 `supply_agreement` 8-K span authorize a news-impact transfer?** Default: **only** if that 8-K span is attached as `two_party_span` **and** a separate role-bearing sentence exists in the **news** source fact or the 8-K; keyword `supply_agreement` alone stays unlabeled (I7). Do not mint `target_role=supplier` from the GR3 subtype.
9. **Fixture receipts vs production F2.** Default: contract tests may use internally consistent synthetic `byte_replayed` receipts (as the frozen event suite does). Production news URLs use `address_only` until byte replay exists (freeze F2/D7). Do not treat these worked-case hashes as production evidence.
10. **Commission D labeling of "indirect-transfer" rows.** Default: labeler marks `unsupported_transfer yes/no` per freeze §7; this contract's `transfer_absence.v1` is the machine form of `yes`. Do not add a parallel grade.

---

## Appendix A — schema files and validation receipts

- `transfer_edge.v1.schema.json` — oneOf `transfer_edge.v1` | `transfer_absence.v1` | `macro_shock_fanout.v1`. Forbidden-token grep empty after description rewrite.
- `observation_window.v1.schema.json` — oneOf `observation_window.v1`.
- Both `Draft202012Validator.check_schema` OK. Eight worked instances ACCEPT under the top-level validator.
- Named validators listed in §4.2 / §4.7 are Phase 3 (`engine/news_impact/` leaf), not this lane.

## Appendix B — three-graph consumption map (what a builder may read)

| Graph | Owner to read | May it admit a transfer edge? |
|---|---|---|
| 1 Economic relationship | Future GMI `SUPPLIES` et al. (reserved, I3); filing spans; this contract's two-party span | Yes, iff `V_TWO_PARTY_SPAN` passes |
| 2 Comparability | GMI `MEMBER_OF`/`EXPRESSES` (I2); GR baskets; Bio trial peers | No — absence `gmi_member_of_only` / `graph2_membership_only` |
| 3 Residual market | `group_pulse.v1` (I4); residual engines | No — absence `graph3_residual_only`; observation may **measure** it |
| Join | Held K3-D record | Out of scope (S6, I14) |

## Appendix C — clock worked arithmetic (fixtures, not live clock)

T0 `first_admissible_feed_receipt` = `2026-09-28T13:32:14Z` (09:32:14 America/New_York, EDT).
- `plus_60s` entry = `2026-09-28T13:33:14Z`; 09:35 decision uses this cutoff (case 5.6).
- `plus_900s` entry = `2026-09-28T13:47:14Z` (case 5.5).
- 09:35 ET = `2026-09-28T13:35:00Z`; 16:00 ET = `2026-09-28T20:00:00Z`.
- Next RTH open = `2026-09-29T13:30:00Z`.
No `datetime.now` / `time.time` in this lane's artifacts.
