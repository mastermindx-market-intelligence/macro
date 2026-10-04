# Finance R11 — product and visualization architecture freeze

Date: 2026-09-23 / 2026-09-24 UTC.  
Operation: `gmi-finance-sector-research-20260923-sol-001`.  
Carrier: Macro PR #7786 / `sol/finance-sector-research-20260923`.  
State: RESEARCH / UX ARCHITECTURE FREEZE / DRAFT-HOLD.  
Mission complete: false. Product implemented: false.  
Current-main compatibility read for this freeze: `macro@da092e5d4a64dbb7c3958826f8cd60d7cbd02cc5`.  
Protected procedure: `Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`.

## 1. Core UX ruling

Finance must be integrated into Themes research without pretending that the entire financial system is one canonical theme.

The current Theme Tracker is a canonical-theme glance surface built around a fixed seven-leg asymmetry model, including `bottleneck_tightness`. That is appropriate for its existing theme engine but not as the primary Finance sector model.

Therefore:

- **Theme Tracker remains the canonical-theme router.**
- **Financials remains a sector/system lens.**
- **Fintech & Payments remains its existing canonical theme.**
- **The Finance Intelligence dossier is a read-only composition over existing owners.**

Do not place 52 Finance slices into the Theme Tracker lane system.

## 2. User journey

Preferred user journey:

```text
Research navigation
  → Theme Tracker / Sector Intelligence
  → Financials system lens
  → Finance Intelligence dossier
  → domain
  → subtheme / research slice
  → company exposure
  → source evidence
  → existing stock / basket / sector workflow
```

Two valid entry points:

1. **Theme Tracker** — small non-canonical “Sector deep dives” affordance for Financials, clearly separate from canonical theme lanes.
2. **Sector Intelligence / Financials equal-weight detail** — the primary Financials entry and price-participation context.

Fintech & Payments should link into the relevant Finance payments domain, not claim ownership of the entire Finance dossier.

## 3. Theme Tracker integration

### What to add

Add a compact optional **Sector deep dives** module outside the canonical theme lanes.

Finance card contents:

- Financials / Finance Intelligence;
- research coverage state;
- evidence freshness;
- number of mapped semantic slices;
- currently important system changes, when source-backed;
- “Open Finance Intelligence” action.

### What not to add

Do not:
- increment the canonical theme count;
- place Finance into Watch/Broadening/Re-rating/Accelerating lanes;
- compute the seven Theme Tracker asymmetry legs for Finance;
- manufacture a Finance bottleneck score;
- use “working now” or “hidden opportunity” as the sector-level Finance verdict.

The card is navigation/context, not a stage/rank.

## 4. Financials price-context integration

The existing `basket/us_sector_financials.html` remains the broad US Financials participation gauge.

It should gain a compact **Finance Intelligence** launch module showing:

- broad Financials price context;
- existing XLF leg context;
- existing broad baskets: regional banks, payments/fintech, insurance;
- top research domains;
- current evidence horizon;
- link into the deeper dossier.

It must retain its existing truth:
- equal-weight S&P 500 Financials participation;
- not a buy list;
- not an exposure-pure Finance basket.

## 5. Finance Intelligence dossier

The dossier is the main research surface.

Preferred information hierarchy:

### Tier 1 — What changed
At the top:
- material new observations;
- affected domains/slices;
- event clock;
- operating implication;
- evidence freshness;
- conflict badges.

No overall Finance score.

### Tier 2 — Rerating map
This is the primary Finance visual.

For selected slice:

```text
driver / new information
→ operating variable
→ earnings / book / FCF / capital
→ expectations
→ valuation anchor
→ price recognition
→ falsifier
```

Each node can show:
- observed;
- inferred;
- missing;
- conflicting;
- stale;
- regime-break.

### Tier 3 — System / flow map
Selectable views:

1. contractual money/risk flow;
2. regulated infrastructure/access;
3. public-equity economics.

Do not merge them into one network.

### Tier 4 — Subtheme atlas
Browse the 52 semantic slices by six domains:

- Banking & credit
- Markets & infrastructure
- Payments
- Asset/wealth/private markets
- Insurance
- Software/trust/disruption

Every slice indicates one of:
- semantic only;
- broad existing context available;
- research candidate cohort;
- candidate ready for owner review;
- admitted price basket, if one eventually exists.

### Tier 5 — Company exposure matrix
Rows = companies/businesses.  
Columns = selected slices / workflows / economics.

Cells show:
- relationship role;
- measured exposure basis;
- materiality state;
- retained risk;
- current evidence date.

A cell never contains a hidden score.

### Tier 6 — Macro/regime matrix
Rows = Finance slices.  
Columns = macro drivers:

- policy rates;
- yield curve;
- deposit/funding conditions;
- credit growth;
- losses/defaults;
- housing;
- equity levels;
- volatility;
- issuance/M&A;
- catastrophe/reinsurance;
- regulation/capital;
- FX;
- liquidity.

Cell state describes mechanism and lag, not positive/negative stock verdict.

### Tier 7 — Constraint map
Optional and subordinate to rerating economics.

Show:
- regulatory permission;
- capital;
- funding/liquidity;
- network access;
- settlement/record finality;
- data/benchmark control;
- distribution;
- integration/switching;
- trust/identity;
- resilience.

Every constraint must link to an economic effect. No “important bottleneck → good stock” shortcut.

### Tier 8 — Evidence drawer
Reuse the site's established drawer interaction pattern.

Required fields:
- publisher/source;
- source family;
- exact locator;
- publication/observation/effective clocks;
- business scope;
- metric definition;
- numerator/denominator;
- unit/currency;
- statement mode;
- reported/derived state;
- limitations;
- correction/supersession;
- rights state.

## 6. Slice detail contract

Every slice page/state answers:

1. What economic job does this slice perform?
2. How do companies make money?
3. What risk do they retain?
4. What drives earnings/book/FCF per share?
5. What are the leading operating indicators?
6. Which indicators lag?
7. What valuation anchor applies?
8. What would justify a higher/lower multiple?
9. What appears to be expected, if dated expectations exist?
10. Is price confirming, leading or conflicting?
11. What would falsify the thesis?
12. Which companies/businesses are direct/diversified/enablers/proxies/at-risk?
13. Is there an admitted price basket?
14. How fresh and complete is the evidence?

## 7. Company detail behavior

Do not create a second company identity or generic Finance-company database.

From the matrix, clicking a company should use the existing company/stock route.

Finance-specific context may appear as a read-only panel:

- business roles;
- relevant slices;
- exposure metrics;
- revenue mechanism;
- retained risk;
- rerating bridge;
- latest conflicts;
- evidence.

The company owner remains canonical.

## 8. Conflict view

Finance users need disagreements surfaced, not averaged.

High-value conflicts include:

- `EARNINGS_UP / P_E_DOWN`
- `BOOK_UP / P_B_DOWN`
- `NII_UP / CREDIT_WORSE`
- `CAPITAL_COST_UP / GROWTH_STILL_STRONG`
- `REGULATORY_RATIO_DOWN / REGIME_BREAK`
- `VOLUME_UP / REVENUE_MATERIALITY_UNPROVEN`
- `PRICE_UP / CAUSAL_EVENT_EFFECT_UNPROVEN`
- `PLAN_DISCLOSED / EXECUTION_PENDING`
- `POLICY_SUPPORT / NIM_PRESSURE`
- `TAIL_RISK_DOWN / CURRENT_EARNINGS_WEAK`

Conflicts should be visually first-class.

## 9. Visual grammar

### Color
Do not encode “good/bad stock” through color.

Use semantic categories:
- observed / complete;
- watch / partial;
- caution / conflict;
- missing;
- stale;
- non-comparable/regime break.

Price direction continues to follow existing locale/theme semantics.

### Rerating map
Horizontal on desktop; vertical stepper on mobile.

Each stage:
- label;
- one primary metric;
- state;
- clock;
- evidence action.

### System map
Progressive disclosure:
- show 5–8 workflow nodes at first;
- expand branch/detail on interaction;
- never show 100-node hairball by default.

### Exposure matrix
Desktop:
- sticky row/company;
- sticky slice headers;
- sortable/filterable;
- role icon/text + materiality.

Mobile:
- company/slice cards;
- no wide table dependency.

### Basket panel
When a price cohort exists:
- state clearly whether it is existing broad context, research candidate or admitted;
- show membership count;
- PIT status;
- weighting basis;
- overlap;
- price basis;
- freshness.

## 10. Missing/degraded states

Required visible states:

- `NO_HISTORICAL_CONSENSUS`
- `EXPOSURE_NOT_SEPARATELY_DISCLOSED`
- `CURRENT_MEMBERSHIP_ONLY`
- `PIT_MEMBERSHIP_INCOMPLETE`
- `IDENTITY_UNRESOLVED`
- `PRICE_BASIS_UNQUALIFIED`
- `SOURCE_STALE`
- `SOURCE_RIGHTS_HELD`
- `REGIME_BREAK_NOT_COMPARABLE`
- `VALUATION_ANCHOR_UNAVAILABLE`
- `CAUSAL_EFFECT_UNMEASURED`

Never collapse these into blank cells.

## 11. Accessibility and mobile acceptance

Minimum implementation acceptance:

- 1440 desktop and 390 mobile;
- light/dark;
- EN/ZH;
- keyboard navigation;
- visible focus;
- no meaning conveyed by color alone;
- reduced-motion mode;
- no page-level horizontal scroll at 390;
- flow diagrams usable as text/step sequence;
- evidence drawer traps/restores focus correctly;
- source links usable without precision hover;
- tables expose labels to screen readers;
- long Finance terms wrap without clipping.

## 12. Browser-proof matrix

Before user-facing acceptance, prove:

1. Theme Tracker with Finance sector-deep-dive entry.
2. Financials sector page with Finance Intelligence launch.
3. Finance dossier populated.
4. semantic-only slice with honest no-basket state.
5. candidate-basket slice.
6. missing-consensus state.
7. regime-break state.
8. stale-source state.
9. company exposure drill.
10. evidence drawer.
11. mobile flow map.
12. EN/ZH parity.
13. light/dark parity.
14. keyboard-only journey.

Screenshots are product proof only when rendered from the real implementation path, not from a static mockup alone.

## 13. Data composition law

The dossier is a projection over owners:

```text
GMI identity/evidence
+ Financial Intelligence / company facts
+ existing baskets and sector context
+ revisions/expectations owner
+ valuation owner
+ market price owner
+ macro/rates/credit owners
+ regional regulatory facts
→ Finance Intelligence read model
```

Do not create a second:
- identity master;
- source archive;
- revisions engine;
- valuation engine;
- price history;
- basket owner;
- theme graph.

## 14. Current-main compatibility observations

Against `macro@da092e5d4a64dbb7c3958826f8cd60d7cbd02cc5`:

- Theme Tracker is a dedicated `build_state_of_themes.py` + `templates/state_of_themes.html.j2` pipeline.
- Its seven-leg model includes supply bottleneck, stale consensus, cyclical dislocation, entry cleanliness, crowding, falsifier clarity and orthogonality.
- The board already declares itself context-only and not a trade signal.
- Financials already has an equal-weight sector basket page linked back to Sector Intelligence.
- The canonical theme crosswalk includes `fintech_payments`; `regional_banks` remains an unmapped macro/rates basket.
- Existing basket detail and evidence interactions are reusable presentation patterns.
- The existing Financial Intelligence packet contract is source/provenance rich but its entity contract is SEC/CIK oriented and must not be silently reused as a complete global Finance identity contract.
- The registered market/security identity plane is not a complete global PIT security master.

These observations constrain the implementation plan.

## 15. Freeze

R11 visualization/product architecture is frozen unless a current-main collision materially invalidates it.

Next: R12 current-main architecture/collision/custody review, then R13 final Fable CEO implementation master handoff.
