# Prophet Cycle Equity V1 — funding path and original-shareholder capture

**BUILT_NOT_PROVEN / MISSION_COMPLETE:false. B17/Q08 source implementation; no live rank, sizing, policy, trade, or portfolio authority.**

Branch: `sol/prophet-cycle-equity-v1-20261001`
Source base at implementation start: `origin/main@f38a77de6ab59c2b13d2400e4baebcfdb4fceb21`
Protected procedure: Mastermind `bdf2a972e68a70270c24d4b5d61a4d60edc4f288`,
Skillpack 1.0.1 / bootstrap major 1.

## Outcome

Before this wave, B17/Q08 was a specified-but-unbuilt question:

> Can the issuer survive until recovery, and does the original shareholder
> capture value after financing?

The new `engine/prophet_cycle_equity.py` answers that question deterministically
for a source-bound starting balance sheet plus an explicit dated financing path.
It is deliberately separate from the Cycle (a) macro diagnostic in PR #7868 and
its ALFRED source producer in #7871.

The implementation reuses existing native owners:

- `capital_need.v1` for validated cash / disclosed debt context;
- `capital_structure.share_count_observation.v1|v2` for observed common shares;
- the existing Capital Structure owner for future source-qualified financing and
  claim facts.

It creates **no** collector, financing database, share-count store, lifecycle,
price feed, evaluator, portfolio store, or policy engine.

## Implemented mechanisms

### 1. Dated funding-path survival

`build_funding_path` processes only events whose information was available by
the decision cut. It distinguishes observed facts from scenario assumptions and
orders events by their effective date.

Supported event semantics are:

- operating cash change;
- cash obligation;
- restricted-cash release;
- equity raise;
- debt draw;
- debt repayment;
- debt conversion.

Every equity raise carries both proceeds and newly issued shares. Every debt draw
carries both cash and the new debt claim. Debt conversion adds shares and removes
debt but creates no cash. Original-cohort participation in a new issue requires
an explicit additional cash contribution.

The path checks the operating-cash floor **after each dated event**. A later
financing event does not erase an earlier shortfall.

A claim that the issuer is funded through the modeled recovery date is withheld
unless:

1. starting cash is available;
2. the disclosed debt ladder is complete;
3. restricted-cash treatment is established;
4. the funding schedule is explicitly complete through the recovery date; and
5. the path has no cash-floor breach.

Unknown restricted cash is not silently zero.

### 2. Business recovery versus original-share recovery

`recovery_scenario` maps an assumed operating enterprise value through ending
cash, debt, senior claims, and ending common-share count.

For a continuing common security it exposes:

- common-equity value;
- ending value per common share;
- original-cohort terminal value;
- total original-cohort capital contributed;
- scenario return on total contributed capital;
- enterprise value required to recover the original purchase; and
- enterprise value required to recover all modeled cohort contributions.

These are scenario identities, not fair value, expected return, calibrated
probability, or entry permission.

### 3. Original-security cancellation / reorganization

A canceled old security is **never** spliced into replacement-security
performance.

Without an explicit distribution, terminal old-share value is unavailable, not
zero. An explicit cash/new-share distribution can be evaluated separately.
Legacy scenario fixtures without an evidence clock are retained only as
`scenario_assumption`; they are not upgraded to observed restructuring facts.

### 4. Inventory-versus-sales cycle counterexample

`inventory_sales_diagnostic` prevents a common false recovery inference:
inventory can fall while sales fall even faster. The implementation evaluates the
inventory/sales ratio and emits
`INVENTORY_DOWN_SALES_DOWN_FASTER` when the apparent destocking is not demand
confirmation.

### 5. User-facing evidence explanation

`cycle_equity_brief` consumes only an already-built Cycle case and emits:

- supporting facts;
- counterevidence;
- explicit unavailable inputs;
- one of `FUNDING_GAP`,
  `RECOVERY_WITH_MATERIAL_EQUITY_RISK`,
  `EVIDENCE_INCOMPLETE`, or
  `SCENARIO_REACHES_ORIGINAL_COMMON`.

It explicitly keeps current market/portfolio permission, recovery probability,
financing probability, fair value, position size and averaging-down permission
unestablished.

## Discriminating example — recovery can still lose money

Hypothetical assumptions, not an issuer recommendation:

- original shares: 100 million;
- original purchase: $2/share;
- starting accessible cash: $0;
- starting disclosed debt: $400 million;
- new equity: $200 million gross at $1/share;
- issuance fees: $10 million;
- recovery investment: $190 million;
- assumed recovered operating enterprise value: $900 million.

The raise creates 200 million new shares and $190 million net cash; the modeled
investment consumes that cash. Ending common shares are 300 million, debt remains
$400 million and common-equity value at a $900 million operating EV is $500
million.

Therefore:

- ending value/share = $1.6667;
- original-cohort value = $166.67 million;
- original purchase cost = $200 million;
- scenario return on original contributed capital = **−16.67%**;
- enterprise value required merely to recover the original $2 purchase =
  **$1.0 billion**.

This is the central B17 distinction: a recovering business is not automatically
a recovered stock.

The same fixed $200 million raise produces different recovery hurdles solely from
the financing price:

| New-equity price | New shares | EV required to recover original $2 purchase |
|---:|---:|---:|
| $0.50 | 400m | $1.4bn |
| $1.00 | 200m | $1.0bn |
| $2.00 | 100m | $0.8bn |

No probability is attached to any row.

## Existing source capability and the exact gap

The current repository already has useful, separately governed finance truth:

- `engine/cash_runway.py`: SEC Companyfacts cash / OCF / capex;
- `engine/capital_need.py`: validated `capital_need.v1` cash + maturity
  composition;
- `engine/capital_structure/share_count_truth.py` and materializer paths:
  immutable share-count observations;
- the Capital Structure event/document/covenant planes.

However the current public-safe Capital Structure projection explicitly withholds
`cash_runway`, `fully_diluted_shares`, active instruments, remaining
capacity, financing probability and normalized terms until those owners exist.
Repository search at this source base found no native exact
`gross_proceeds + issue_price + shares_issued` financing consumer and no
restricted-cash join for B17.

Therefore this engine **does not fabricate those facts**. Funding events remain
scenario assumptions unless an existing source owner supplies exact admitted
records.

The next source integration should be narrow:

1. select one issuer with existing `capital_need.v1` and share-count truth;
2. bind exact source-qualified financing / obligation terms already retained by
   the Capital Structure owner, if available;
3. prove restricted-cash semantics or keep that field unavailable;
4. compile the B17 case and brief;
5. carry it through the existing Prophet / D5 / product presentation path;
6. obtain authenticated served proof and correction/history proof.

Do not create another financing store to make this easy.

## Verification

Local affected battery:

```
python3.12 -m pytest
  tests/test_prophet_cycle_equity.py
  tests/test_capital_need.py
  tests/test_cash_runway.py -q
```

Result: **292 passed / 4 unrelated pytest cleanup warnings / 0 failures**.
Final test-log SHA256:
`b59584053f07278a52f69d8a6ac02c2c3eb92da5ca625804e2b7fdb3f55854f9`.

The new Cycle suite contains 45 focused tests, including one direct consumption
of an actual `assemble_capital_need(...)` output.

Three deliberate source mutants are caught by intended assertions and original
source bytes are restored:

1. drop equity proceeds while retaining dilution;
2. erase an interim funding-floor breach;
3. ignore total ending shares in the purchase-recovery hurdle.

Mutation receipt:
`research/prophet_v4/cycle_equity_v1/fault_discrimination.json`.

The test suite is registered into the existing render/engine guard lane; no new CI
job or dependency was introduced.

## Capability boundary

This wave establishes deterministic financial mechanics and a bounded explanation.
It does **not** establish:

- financing availability;
- a probability of recovery;
- a probability distribution of enterprise value;
- a validated Cycle stock-selection edge;
- a price forecast;
- sizing;
- entry permission;
- market-risk permission;
- automatic averaging down;
- a production user experience.

Those remain separate owners/gates.

The correct scientific next question is not “does this model look sensible?” It is
whether source-qualified funding/per-share evidence improves Cycle selection and
risk discrimination **on the same eligible population**, including failed firms,
diluted firms, canceled securities, reorganizations and never-funded recoveries.
Protected H1/Cycle outcomes are not opened by this implementation wave.
