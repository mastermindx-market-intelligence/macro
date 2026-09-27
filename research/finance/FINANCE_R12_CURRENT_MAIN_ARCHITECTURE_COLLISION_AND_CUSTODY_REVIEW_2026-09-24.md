# Finance R12 — current-main architecture, collision and custody review

Date: 2026-09-24 UTC.
Operation: gmi-finance-sector-research-20260923-sol-001.
Carrier: Macro PR #7786 / sol/finance-sector-research-20260923.
State: RESEARCH / INTEGRATION PRE-FLIGHT / DRAFT-HOLD.
Mission complete: false. Product implemented: false.
Protected procedure: Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157, Skillpack 1.0.1/bootstrap 1.
Current-main pin: macro@9573cd4d134804fb4cd8c3801ad62a697c3de6d2.
Direct principal reason: PRINCIPAL_JUDGMENT.

R1–R11 established the Finance research, rerating laws, global/local semantics, basket architecture and product design. R12 determines what a later Fable implementation may safely own without forking or colliding with live company systems.

## 1. Executive ruling

PR #7786 is a research/design evidence carrier, not the implementation base.

At this review:
- Finance research head before R12: 9ca6f5b14c33e80ac388771c62405707a84b6270.
- Its merge base remains 668237947e016f679782e41e61c91c9133a5ea99.
- Current Macro main is 9573cd4d134804fb4cd8c3801ad62a697c3de6d2.
- The research branch has diverged materially while adding research-only artifacts.

Implementation law:

1. keep #7786 Draft/HOLD as the research packet;
2. start the implementation carrier from then-current main;
3. consume accepted research by exact path/SHA;
4. reconcile shared interfaces and active writers immediately before first implementation writes;
5. never merge #7786 merely to make its research accessible to implementation.

## 2. Current-main capability map

### Theme Graph evidence exists; Finance curation payload does not

Current main contains the closed Theme Graph evidence schema, append-only/bitemporal store, rights engine and source-family registry.

Current main does not contain:
- contracts/theme_graph/curation_assertion.v1.schema.json
- engine/theme_graph/curation_assertion.py

Finance must not create a finance-specific assertion contract or evidence ledger.

### Shared curation assertion has an active implementation owner

Semiconductor Theme Intelligence B, PR #7870 at 545ece0c7177a56627204e77302cd9c2d4d03f3e, records Fable custody for first authorship of the shared theme_graph.curation_assertion.v1 contract.

Its ruling is compatible with Robotics:
- one shared assertion contract;
- source-scoped business/product assertions;
- no second Theme Graph;
- full-fidelity current payload private;
- rights/retention and identity remain with their owners.

Finance disposition: consume the accepted shared revision or coordinate with its incumbent writer. Do not fork.

### Sector dossier outer contract has an active owner

PR #7777, feat(sector-intelligence): add governed dossier contract, is OPEN/non-draft at 4122e3b7e1524482216fb156f201f8229c14011b.

Its sector_dossier_read_model.v1 candidate models:
- identity;
- headline;
- dimensions;
- material changes;
- children;
- connected themes;
- participation;
- concentration;
- conflicts;
- watch conditions;
- freshness and quality;
- input receipts;
- authority caps.

The contract is not on current main at this pin.

Finance disposition: if #7777 or accepted successor lands, use it as the outer Financials sector dossier. Do not create a parallel finance_sector_dossier truth object.

A deeper Finance-specific object is permissible only as a read-only child projection under the accepted Sector Intelligence owner. It must own no source, identity, price, expectation, valuation, basket, lifecycle or publication truth.

### Financial Intelligence is useful but is not a global identity master

Current main contains the Financial Intelligence packet contract with strong source provenance, periods, revisions, disclosure changes and as-of semantics.

Its entity grammar is SEC/CIK shaped and cannot silently become global Finance identity.

Use Financial Intelligence for supported facts; preserve source-native unresolved identity for international records until the canonical identity/security owner supports them.

### Global identity remains incomplete

Current sector-intelligence ownership law says:
- one writer required;
- duplicate writer hard fail;
- generic company identity is partial ticker context, not PIT identity;
- security identity is bootstrap/incomplete, not a complete global security master.

Therefore global research may display attributed source-native businesses with explicit unresolved binding, but no new global admitted historical basket may fabricate identity or PIT history.

## 3. Source-custody matrix

| Interface | R12 state | Active owner/collision | Finance disposition |
|---|---|---|---|
| templates/state_of_themes.html.j2 | live main | #7870 plans shared Theme Research mount | consume accepted mount or coordinate |
| scripts/build_state_of_themes.py | live fixed seven-leg model | #7664 OPEN/non-draft touches it | avoid Finance semantic changes |
| engine/theme_graph/store.py | canonical append-only owner | #7462 OPEN/draft; #7870 freezes its proposed column | no Finance direct edit |
| shared curation assertion files | absent main | #7870 claimed first authorship | consume, never fork |
| templates/basket_detail.html.j2 | live | custody disagreement below | not critical-path for Finance dossier |
| site/theme.css + templates/theme.css | live global design system | #7849 OPEN/non-draft | consume accepted tokens; scoped Finance assets |
| sector dossier contract | absent main | #7777 OPEN/non-draft | consume if accepted |
| regional sector detail templates | moving | #7797 OPEN/non-draft | reference pattern only |
| config/theme_crosswalk.yml | 18 canonical themes | GMI vocabulary owner | do not mint Finance theme |
| data/baskets/membership.json | incumbent broad baskets | baskets owner | no R11 admission without owner review |
| basket/us_sector_financials.html | broad equal-weight price context | sector/basket surface | retain; owner-compatible launch only |
| Financial Intelligence packet | live | corporate/financial intelligence owner | reuse facts, not global identity |

## 4. Disagreement ledger

### D1 — basket-detail custody

Semiconductor #7870 states templates/basket_detail.html.j2 is frozen pending #7669.

A fresh GitHub file-list read of #7669 at 2c28d950aa9448fc878bb64d92b228a8f1952bde does not list that path.

Ruling: path custody is unresolved at this observation. At implementation pickup, perform one fresh path-specific reconciliation. Do not infer free custody or continued ownership from either stale statement.

This does not block Finance because its primary dossier is not designed around basket-detail mutation.

### D2 — Theme Tracker has multiple moving owners

#7664 touches scripts/build_state_of_themes.py while #7870 plans a templates/state_of_themes.html.j2 mount.

Ruling:
- prefer accepted generic mounts and authenticated projections;
- avoid changing lane classification or the seven-leg Theme Tracker semantics;
- do not derive Finance state in browser code.

### D3 — planned shared infrastructure is not current-main truth

Not yet on current main:
- curation assertion;
- shared Theme Research route/assets;
- governed Sector Dossier contract.

Final implementation must name these as dependency/custody gates, not assumptions.

## 5. Ownership boundary

Finance consumes existing owners for:
- canonical themes and evidence;
- source rights;
- company/financial facts;
- earnings/guidance/revisions;
- market prices;
- rates/macro/credit;
- broad baskets;
- sector context;
- company identity;
- security/listing identity;
- authenticated private publication.

The only new Finance-specific responsibility should be a deterministic read projection.

Conceptually:

finance_intelligence_projection =
accepted owner reads
+ Finance slice grouping
+ deterministic conflict labels
+ display composition

It may own:
- view objects;
- grouping of 52 research slices;
- layout ordering;
- deterministic conflict presentation;
- links from slices to accepted owner references.

It may not own:
- raw source facts;
- canonical identity;
- expectation history;
- valuation truth;
- price history;
- basket membership;
- Theme Graph lifecycle;
- trading/rank state.

## 6. Route and page boundary

Subject to current-owner reconciliation:

Outer sector projection:
- accepted sector_dossier_read_model.v1 or successor for Financials.

Deep Finance projection:
- authenticated read-only route under Sector Intelligence.
- candidate route: GET /api/sector-intelligence/financials/finance/v1.
- exact route/name remains proposal until owner review.

Page:
- dedicated Finance Intelligence shell;
- Theme Tracker and Financials context link into it;
- do not force full dossier into Theme Tracker, basket detail, stock detail or regional templates.

The shell may be public/static, but current full-fidelity research data must use the accepted authenticated/private/no-store path. No full current payload in public Git, static HTML, localStorage, IndexedDB or service-worker caches.

## 7. First implementation vertical

Retain Financial Rails & Market Infrastructure.

Money Movement:
- Card Networks
- Merchant Acquiring / Processing
- Issuer Processing

Securities Infrastructure:
- Exchanges & Trading Venues
- Custody & Asset Servicing
- Market / Reference Data
- Ratings / Credit Information
- Indices / Benchmarks / ETF Plumbing

Clearing/CCP/CSD may join once listed-issuer/security binding and publication boundaries are clean.

Required existing research witnesses:
Visa, Mastercard, Fiserv, FIS, CME, ICE, Nasdaq, BNY, State Street, S&P Global and Moody's.

They are research witnesses, not an admitted portfolio.

## 8. Vertical acceptance

A signed-in reader can:

1. enter Financials from Theme Tracker or Sector Intelligence;
2. open Finance Intelligence;
3. select Money Movement;
4. distinguish network, issuer, acquirer/processor and software roles;
5. inspect source-backed operating metrics with denominators;
6. see operating → earnings → expectations → valuation → price;
7. see honest NO_HISTORICAL_CONSENSUS when appropriate;
8. open evidence with exact clocks;
9. switch to Securities Infrastructure;
10. distinguish venue, custody, data/index/rating roles;
11. inspect conflicts instead of a fused score;
12. return to existing stock/basket/sector routes.

Negative acceptance:
- no universal Finance theme;
- no Finance attractiveness score;
- no duplicate basket;
- no guessed global identity;
- no public full-fidelity evidence payload;
- no browser-side signal calculation.

## 9. Implementation carrier law

When Fable begins:
- create a fresh implementation carrier from then-current main;
- use a distinct implementation operation linked to #7786;
- record pickup and START separately;
- preserve one implementation carrier;
- reconcile exact incumbent writers before overlapping paths;
- consume/wait on started shared dependencies instead of replacing them;
- use bounded workers only after Fable freezes owned file sets and acceptance.

Do not convert #7786 into the implementation carrier.

## 10. R12 completion

R12 freezes:
- implementation-base law;
- owner map;
- shared-dependency map;
- source-collision matrix;
- global identity limitation;
- outer-sector/deep-Finance projection boundary;
- first vertical;
- witness set;
- initial acceptance shape.

R13 remains:
- exact implementation waves;
- dependency gates;
- file/task ownership packets;
- test and review plan;
- browser/production proof;
- final Fable CEO handoff.

Do not merge #7786 automatically.
