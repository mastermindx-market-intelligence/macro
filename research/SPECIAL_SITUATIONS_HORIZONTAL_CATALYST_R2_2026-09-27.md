# Special Situations Horizontal Catalyst Integration — R2 Research & Architecture

**Date:** 2026-09-27  
**Owner:** Astra Web CEO, Special Situations horizontal lane  
**State:** research/design source; DRAFT/HOLD; no production authority  
**Macro base:** `170456b0013bf833a952498daf6a44a2153d70c6`  
**Protected Mastermind procedure:** `429bf720788f8c68e76a576b7b3fedd8f8ad423a`  
**INDEX blob:** `94d1af402598894372858793a5b1931019c5fa77`, Skillpack 1.0.1 / bootstrap 1  
**Related source carriers:** Catalyst design PR #8061 at `902e63be2278ec76147885268c7f89152b8cee76`; F09 cash-deal repair PR #6793 at `ff71a149a7d8f61b072b563f16ca874f0ac08d9d`.

This document advances the existing Special Situations system. It does not create a replacement collector, event store, lifecycle plane, identity service, ranker, queue, recommendation service, or global Catalyst schema. Existing owners retain authority for identity/GMI, Company/Event/Earnings, Financial Intelligence/Capital Structure, expectations/options, recommendation/entry, publication, evaluation, portfolio, watchlist and alerts.

## 1. Executive result

The highest-value current defect is no longer theoretical. A single upstream take-private event for **The Marygold Companies, Inc. (MGLD)** is being projected into multiple USCF fund tickers as separate `Going-Private` Special Situations and then emitted as independent `special_situation` Alt-Data channels.

The SEC filings of USCF fund registrants state that:

- TMC entered the definitive all-cash transaction with Madison Dearborn Partners.
- TMC is the sole shareholder of USCF Investments.
- USCF Investments holds United States Commodity Funds LLC, which is the relevant fund general partner/sponsor.
- TMC, not the fund, is the public company that is expected to become private and delist.
- The fund is indirectly affected through control, consent and post-close USCF strategy.

Primary examples:
- USL Form 8-K: https://www.sec.gov/Archives/edgar/data/1405528/000207187626000222/i26397_usl-8k.htm
- UGA Form 8-K: https://www.sec.gov/Archives/edgar/data/1396878/000207187626000220/i26393_uga-8k.htm
- MDP/TMC announcement distributed via Business Wire: $2.00 cash per MGLD share, 100% premium to the unaffected 2026-09-24 close.

The M2 Special Situations store at the time of this investigation contained **48,057 rows** through 2026-09-25. The current owner code on main projects the USCF filings as `Going-Private`; current local generated consumers showed UNL, USL, BNO, CPER, UGA, UNG and USO each receiving a `special_situation` Alt-Data channel at weight 0.20. This is useful evidence of a real relationship, but it is not seven independent take-private events and must not count as seven independent confirmations.

### R2 architectural ruling

Represent the event once at transaction identity and attach typed affected relationships:

```
canonical transaction: MGLD / Madison Dearborn take-private
  target_security      -> MGLD common
  acquirer             -> MDP acquisition vehicle / owner-native identity when available
  controller_change    -> USCF Investments
  gp_control_change    -> United States Commodity Funds LLC
  affected_fund        -> USO / USL / UNG / UGA / BNO / CPER / UNL ...
  required_consent     -> owner-native change-of-control approvals when source-bound
```

The fund rows remain valid source observations and affected-case evidence. They do not become target-company merger-arb rows, target delisting events, or independent event-success confirmations.

## 2. Current estate audit

### 2.1 Discovery and classification

Current `collectors/special_situations.py` uses EDGAR daily-index discovery plus EFTS metadata enrichment. Structured forms pass through. For 8-K rows, an accession absent from an otherwise non-empty EFTS day is currently dropped; only an entirely empty EFTS day is retained as `items_unknown=True`.

**Ruling:** authoritative discovery and enrichment coverage are separate facts. A discovered accession with unavailable enrichment must remain a pending/unknown discovery denominator unless another owner-native negative observation establishes it is irrelevant. Partial enrichment is not a negative event classification.

### 2.2 Lifecycle

Current `engine/special_situations.py::lifecycle()` groups successful records by `(cik, category)`. It derives terminal flags at the issuer level:

- any Deal Terminations row for that CIK can set `terminated`;
- any Item 2.01 or Form 15 row can set `closed`;
- the resulting flag is then applied to all deal-arc rows for that issuer/category.

This can incorrectly close or terminate a different transaction for the same issuer.

**Ruling:** lifecycle attaches to the actual agreement/transaction identity. An unlinked terminal document may be displayed as evidence but must not terminalize another transaction.

### 2.3 Snapshot deduplication

Current snapshot merging uses approximately `(normalized ticker, category)`, and EDGAR can upgrade a digest row to “live” at that granularity.

**Ruling:** same ticker/category is not transaction identity. Cross-source confirmation requires a shared canonical event or a sufficiently strong owner-native relation to the same agreement. One press release, an 8-K and a specialist case can be three evidence records but one origin, not three independent confirmations.

### 2.4 Security projection

Current `mastermind_emit()` uses `by_ticker` and preserves only the latest event record for a ticker.

**Ruling:** a security may have multiple simultaneous corporate events. Preserve case references underneath one security-level investment exposure. The security projection can nominate a lead material case but must retain the other material cases, dependencies, and revision status.

### 2.5 Cash-deal math

PR #6793 contains a source-byte-bound F09 cash-deal observation design and repairs around exact price/date basis, but it is currently 3,198 main commits behind the present base and is not a safe wholesale recovery carrier.

**Ruling:** preserve F09 as incumbent specialized work. Reconcile/adopt bounded concepts through its owner; do not create a third premium/spread producer. Its per-share cash-deal schema must not be overloaded with aggregate divestiture proceeds, retained ownership, licensing economics, financing packages, or fund-control relationships.

## 3. Real-path vertical: MGLD → USCF funds

### 3.1 Observed source fact

The USCF filings are material to each fund because their general partner's ownership/control chain may change and specific change-of-control approvals may be required. That is a legitimate Special Situations relationship.

### 3.2 Current erroneous interpretation

The present classifier/category projection places the **fund registrant** into `Going-Private`, despite the source text stating that the parent TMC is becoming private.

Consequences observed in current local generated artifacts:

1. each fund can appear as a separate Going-Private situation;
2. category/stage historical priors are attached to the fund row even though the fund is not the take-private target;
3. technical “setup” features can be combined with that event family;
4. Alt-Data lights `special_situation` independently for each fund;
5. downstream systems may therefore count one source-origin event repeatedly unless they independently recognize the control relationship.

### 3.3 Target projection

For each affected fund, expose a relationship-aware context projection:

```json
{
  "security": "USO",
  "event_ref": "<existing owner-native canonical event reference>",
  "event_family": "going_private",
  "security_role": "affected_through_general_partner_control",
  "direct_target": false,
  "direct_offer_consideration": null,
  "affected_relationship": {
    "from": "MGLD",
    "via": ["USCF Investments", "United States Commodity Funds LLC"],
    "relation": "controller_change"
  },
  "materiality": {
    "status": "research_required",
    "known_impacts": ["change_of_control_consents", "post_close_strategy_change"],
    "unknowns": ["fund_fee_change", "adviser_or_gp_replacement", "product_changes"]
  },
  "source_origin_group": "<one transaction/source lineage>",
  "is_context_only": true
}
```

The exact persisted shape belongs to the incumbent semantic owners; this is a required semantic mapping, not a new canonical schema.

### 3.4 Consumer behavior

- **Special Situations desk:** show one MGLD transaction with an “Affected structures” expansion listing USCF funds.
- **Fund/security page:** show “Parent/controller change” context, not “this fund is being taken private.”
- **Alt-Data:** a fund may retain a context channel if policy admits it, but deduplication metadata must identify the shared source-origin group and prevent multi-counting as independent evidence.
- **Catalyst Intelligence:** invalidate/research only cases whose economics or operational assumptions depend on USCF control, fees, product continuity, capital support or management.
- **Recommendation owner:** no automatic stance change from relationship existence alone.
- **Evaluation:** score detection, affected-case mapping and any price/flow timing target separately from MGLD deal completion.

## 4. Event-family economics

Special Situations is horizontal because different corporate events change different economic state. No single “completion probability” is sufficient.

| Family | Required event states | Economic translation |
|---|---|---|
| Take-private / cash M&A | announce, competing bid, revise, vote, regulatory delay, close, terminate | target cash/stock consideration, break value, timing, taxes/costs, financing and optionality |
| Stock/mixed M&A | same plus exchange-ratio and hedge state | acquirer share distribution, collar/ratio terms, dilution, hedge basis |
| Divestiture / asset sale | announce, consent, close, retained stake/liability | cash received, taxes, debt paydown, stranded cost, earnings lost, retained liabilities, capital allocation |
| Spin-off | announce, Form 10, distribution, separation, post-spin | parent/remainco/spinco values, debt allocation, dis-synergies, one-time costs |
| Strategic review | initiated, narrowed, bidder/alternative, abandoned | probability-weighted alternatives only after calibrated evidence; otherwise research state |
| Activism | disclosure, demand, board settlement, proxy fight, exit | campaign mechanism and governance/capital-allocation paths; filer prior remains separate context |
| Restructuring / financing | amend, exchange, forbear, court process, emergence/failure | capital-structure waterfall, dilution, coupon/cash burn, maturity runway, recovery |
| Capital return | authorization, execution, completion | actual repurchases/dividends, share-count impact, funding source, opportunity cost |
| Licensing / rights | grant, milestone, royalty tier, amendment/termination | retained economics, pass-through obligations, milestone conditionality, territory/indication |
| Controller/adviser change | announce, consent, effective, replacement | fee/management continuity, product rights, governance, customer/asset retention |

Each assessed investment case must explicitly separate:
1. event occurrence/completion;
2. durable economic effect;
3. security total return over a stated horizon;
4. benchmark outperformance.

## 5. Evidence and clocks

Every event-family adapter must preserve, through existing owners:

- source-native document/accession identity;
- source publication time;
- first-known/system observation time;
- effective/contract date where distinct;
- analysis cutoff and model version;
- market/reference-price time and currency;
- correction/retraction/supersession lineage;
- source-origin grouping across repeated filings/press releases;
- identity confidence and unresolved relationships.

Never backdate later financial terms to the report period or legal effective date merely because they describe it. Historical evaluation uses what was actually knowable at the cutoff.

## 6. Affected-case invalidation

A corporate-event revision invalidates only dependent downstream calculations.

Example dependency graph:

```
source revision
 -> canonical event / relationship
 -> affected assets/programs/security exposures
 -> dependent economic assumptions
 -> dependent specialist outcome-to-equity translations
 -> accepted recommendation/policy review
 -> one coherent publication snapshot
```

Unrelated clinical probabilities, procurement-win probabilities, commodity-price models or sector facts do not change merely because the issuer has a new corporate event.

Old recommendations and old evidence snapshots remain immutable known-at-time records. The new publication shows the delta; it does not silently rewrite history.

## 7. Evaluation contract

The July Special Situations event study found no robust positive post-filing drift on the covered first-event-per-ticker panel. Preserve that contrary evidence. It does not prove all corporate-event strategies lack value, because:

- it measures post-filing drift, not announcement jump;
- it pools heterogeneous families;
- first-event-per-ticker discards subsequent transaction state;
- the economic question differs across merger arb, activism, spin-offs, restructurings and affected-controller relationships.

Future evaluation must therefore include:

- complete discovery denominator and missing-enrichment denominator;
- event-family × role × lifecycle state;
- transaction identity rather than ticker/category;
- source-known timestamp and market session;
- direct target vs indirectly affected security;
- simple baselines;
- outcome-blind frozen predictions;
- failed, delayed, withdrawn and unranked cases;
- overlapping/common-cause dependencies;
- after-cost security returns at matched horizons;
- calibration of each named probability target;
- incremental ablation for options/positioning/flow;
- prospective shadow evidence before promotion.

No fixed sample count, green CI result or single significant horizon qualifies a forecast.

## 8. Market-structure role

Existing options/expectations owners remain authoritative. For each Special Situations family, test separately whether options/flow/positioning adds information about:

- physical event outcome;
- market-implied expectations;
- short-term reaction;
- entry/exit timing;
- crowding/tail risk.

Measured trades, inferred aggressor direction, later OI, modeled dealer inventory and risk-neutral prices remain distinct. No-options names keep a useful fundamental path.

## 9. Product direction

The revamped Special Situations view is a research workspace and a contributor to the unified security-level investment experience.

First screen:
- lead material event or strongest prepared case;
- correct security role;
- event stage and next decision/window;
- economic consequence;
- what changed;
- prepared stance only if accepted by recommendation policy;
- primary failure/unknown.

Deeper views:
- transaction/relationship graph;
- event timeline and source revisions;
- event-family economics;
- affected securities/assets/programs;
- expectations/options context;
- decision history;
- source inspectors.

Required states: desktop/mobile, dark/light, keyboard/touch, loading, partial, stale, denied, source-missing, identity-unresolved, model-withheld, price-stale and review-pending.

Native Paper file is `01M2WGNCX9475G79JRKJTCM08P`. The guarded adapter was connected and confirmed the BioCatalyst page `p-K-0`, but the current Paper catalog hash `8cd27488...` was not accepted against expected `ca90a537...`; a later catalog call returned `UPSTREAM_UNAVAILABLE` with retry disallowed. **No Paper write was dispatched.** Native Paper remains blocked; do not switch carriers to bypass this admission failure.

## 10. Readiness

- **Research/design readiness:** PARTIAL but materially advanced. Existing architecture is recovered; first real relation bug is proven through stored event and generated consumers; method/product direction is frozen. Remaining: incumbent semantic-owner adjudication, real canonical event/relationship receipt, native Paper acceptance and served UI proof.
- **Forecast-promotion readiness:** NOT QUALIFIED. Current context/model holds remain.
- **Production acceptance:** NOT ACCEPTED / NOT CHANGED.

## 11. Next exact vertical

1. Resolve the owner-native canonical event/security/relationship identities for the MGLD transaction and the affected USCF funds.
2. Build a shadow relation-aware projection that keeps one transaction and multiple typed affected cases.
3. Trace it through Special Situations context, Alt-Data, Company Intelligence / Catalyst research and the recommendation review seam.
4. Prove that the correction changes the misleading fund classification while preserving the legitimate control-change evidence and the MGLD target economics.
5. Preserve old snapshots and unaffected cases.
6. Independently review the semantics and run real producer→consumer tests.
7. Only then consider adopting related F09 transaction-term work or user-facing rollout through the incumbent owners.
