# R9 — First real Atlas scope admission: full house catalogue, no fake cap

**Status: RESEARCH RULING / IMPLEMENTATION STILL HELD.**
Parent: existing Chairman-commissioned Finviz / Sector / Theme / Cycle Intelligence programme.

## 1. Decision

R7 required a rights-safe real Atlas scope with complete catalogue and capitalization before the first
shared Grid / Clusters / Bubbles / table implementation. R8 invalidated one hidden assumption in that
sequence: the available capitalization reference covers only 500 of 702 selected source keys, has five
whole groups with zero matches, and is dated one day later than the P1 observation. Making capitalization
a prerequisite for every representation would either erase valid house groups or stall useful non-cap views.

**R9 therefore separates scope admission from cap-sized encoding admission.**

The first real shared scope is `house_us_49.p1`. It retains all 49 house-curated US groups, all 1,020
group-member appearances and all 702 distinct source member keys. Grid, table, member-count Clusters and
non-cap Bubbles may use that same population after the P1 publication gate. **Market-cap-sized area, cap
tiers and cap filters remain unavailable** until the existing cap/identity owners supply an accepted
complete-enough input with explicit clocks and null behavior.

This narrows only R7's implicit coupling of “first real scope” to “cap available for every member.”
It does not reduce the destination: real cap sizing, broader/lower-cap coverage, rotation intelligence,
economic/regime context and separately validated Prophet contribution remain owed.
## 2. Evidence pins

- Protected Skillpack: Mastermind `320f586126b7c82c843ef17612f12d40d20a42e0`, v1.0.1.
- Current Macro rights authority inspected at `c3d4b81acee75081138c9e40aba8d7589aa341e3`.
- P1 source carrier remains #7252 at `e6795e1ae34c84e32ae9092779d358660ae8e5f5`.
- P1 real input: observation date `2026-09-16`; frozen R8 source/result hashes remain controlling.
- Current Terminal protected master inspected at `2f7ea43669503225325156594b7388b3415b15e7`.
- Discover route blob: `5100b5595e9694de74d3338cd7c6049b8e11ff69`.
- Exact R9 evidence root:
  `/Volumes/Mastermind/agent-evidence/sector-cycle-atlas-admission-r9-20260917-sol-001`.

No production source, data, service, queue, model or publisher was changed by this study.

## 3. Membership rights are actually clear

All 49 P1 groups report:

- `group_kind = curated_basket`
- `source_membership_ref = data/baskets/membership.json`

The current rights authority `config/theme_sources.yml` declares `mastermind_curated` as
`rights_class: direct_display_ok`, `auth_class: house`, with a source route including
`data/baskets/membership.json` and an explicit note that the 49 US curated baskets are house content.
`engine/theme_graph/rights.py` maps `data/baskets/` to `mastermind_curated`. Executing that current
authority against the exact P1 membership reference produced
`family=mastermind_curated`, `rights_class=direct_display_ok`, `auth_class=house`,
`licensing=(internal=true, display=true, redistribution=true)`; the public-emission gate passed.

This closes the **membership-structure** rights question for the 49-group house scope. It does not grant
rights to Finviz or THS membership structures. `finviz_themes` and `ths_concepts` remain unresolved
under the same registry and are excluded from this first Atlas scope.

## 4. Measurement-rights boundary is narrower

The theme-source registry adjudicates theme structure, not every paid market-data contract. Current
repository rights records still describe Polygon/Massive-derived display or redistribution rights as
not fully evidenced for arbitrary **new public-tier expansion**. R9 therefore does not infer a vendor
license conclusion from house-owned membership.

The first interactive Atlas must:

1. consume only already accepted Group Pulse / P1 derived measurements;
2. add no raw provider fields, raw bars, market-cap values or vendor theme structure;
3. stay on the signed-in Terminal Discover member surface for the new interactive experience;
4. use the existing Macro group/detail owner for evidence drill-through;
5. fail closed if a later source-rights authority disallows a selected derived measurement.

This is a conservative product boundary, not a legal opinion. Current Terminal source confirms
`/discover` is signed-in-only: non-fixture requests resolve Supabase claims and guests receive
`SignupGate`.
## 5. Compact real read-model candidate

A research-only compact projection was built directly from the frozen P1 companion and house basket
metadata. It retains every group and only two accepted aggregate measurements:

- `strict_trend_50`
- `strict_trend_200`

For each measurement it carries the existing recipe, basis, window, minimum, numerator, denominator,
value, null reason and cohort digest. It also carries group membership identity/digest, member count,
member keys and the existing detail path.

It deliberately contains no market capitalization, raw-return group aggregation,
benchmark-relative-return group aggregation, inferred issuer/security IDs, rankings, recommendations,
gates, sizes or trade authority.

Executed conservation checks:

- 49 / 49 groups retained;
- 1,020 group-member appearances retained;
- 702 source member keys retained;
- all groups are `curated_basket` from one accepted membership source;
- strict-50/200 values, numerators and denominators equal their P1 source objects;
- no cap, return-aggregate or identity field was synthesized.

The candidate is **68,421 bytes**, versus **2,602,709 bytes** for the full P1 companion (2.63%).
That is payload-shape evidence, not latency or production-budget proof.
Candidate SHA-256:
`921c5da0b4768db64b597373e7ebd1045295a11cb5ce7e4a6bba33a8bc86e498`

Input-manifest SHA-256:
`6cac9bf691ded5157dfefcb72a45e19fd3fcd06f6a870fd98b302859971bf89e`

The candidate is **not an accepted persisted schema**. It proves a compact projection can be produced
without inventing analytical semantics. Production implementation must remain with existing owners.

## 6. Representation contract for the first slice

Every representation consumes the exact same 49 group rows and the exact same measurement objects.

- **Grid:** one group per equal-area cell; color = selected strict-50 or strict-200 measurement.
- **Clusters:** group by house category; circle area = member count; color = selected strict metric.
  Proximity carries no statistical, economic or causal meaning.
- **Bubbles:** X = strict-50 participation; Y = strict-200 participation; size = member count; color =
  house category or selected accepted measurement. No cap axis/size/filter until cap admission passes.
- **Table:** strict-50, strict-200, member count, observation date/status and evidence/detail link.

Member count is labelled **membership breadth**, never market capitalization. Search, category and
representation switches are display-only unless an explicit measured rescope is requested. Null groups
remain present as unavailable. False and zero remain observed values.

## 7. User journey and ownership

Primary first host: **Terminal Discover → Heatmap/Atlas**, a signed-in member surface.

Required journey:

`Atlas overview → same group → existing complete-member evidence → company → return with scope preserved`
The existing Macro group/detail surface remains the evidence owner. The first Terminal implementation
must adapt or consume it; it must not create another membership store, Group Pulse engine, ThemeState,
identity plane, source-rights registry or publication scheduler.

A compact producer is acceptable only as an existing-owner **projection** with a real Terminal consumer
in the same vertical. A schema or artifact without that consumer is not capability completion.

## 8. What remains blocked

R9 does not release implementation. Still required:

- exact-head hosted execution for P1 #7252;
- incumbent #7211 current-invocation validation, publication integration and deployed proof;
- accepted source custody for the first compact producer/Terminal consumer vertical;
- any additional market-data subscriber-display ruling required by the current rights owner;
- real-cap input qualification before cap-sized representations;
- issuer/security identity before cross-group union breadth or independence claims;
- authenticated EN/ZH/responsive/browser proof for the real shared journey;
- temporal rotation, economic/regime work and separately validated Prophet contribution.

The shared `ci-linux` executor remains externally starved under #6351. R9 does not rerun, cancel,
reprioritize or replace that queue.

## 9. Exact next implementation after gates

After P1/publication acceptance, build **one** vertical:

1. existing Macro P1 owner emits or exposes a compact immutable projection of `house_us_49.p1`;
2. signed-in Terminal Discover consumes that same projection;
3. Grid + table + member-count Clusters/Bubbles switch representation without changing population;
4. every group opens the matching existing evidence page/receipt;
5. EN/ZH + responsive + keyboard evidence proves the full journey;
6. cap-sized encoding stays visibly unavailable until its separate input gate passes.

This is the smallest real capability slice that preserves the full Atlas destination. It is not
permission to rebuild the R6 synthetic renderer or copy the Finviz catalogue.
