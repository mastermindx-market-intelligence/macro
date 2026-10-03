# Concrete repair and qualification briefs for incumbent owners

**Status:** ready for current-owner reconciliation and scoped implementation review. No dispatch, source repair or production action is performed by this document. These briefs refine W1/W2 in [ROADMAP_AND_HANDOFF.md](ROADMAP_AND_HANDOFF.md). They preserve the current four C0 owners, Terminal #599 coordination and existing carrier custody.

## B1. Correct gamma-regime orientation

**Problem:** Macro `_gamma_flip` assigns long above/short below the nearest zero crossing. A descending crossing makes that regime disagree with the same producer's net-gamma curve at actual spot. The [executed witness](options-mechanics-witness.md) demonstrates both wrong-sign cases, with ascending and no-crossing controls.

**Source:** [engine/gex_engine.py at 6f5e78e](https://github.com/mastermindx-market-intelligence/macro/blob/6f5e78e94e8808582a650cdfa0fc3357040a179c/engine/gex_engine.py). Before editing, reconcile current Macro pricing/FS-5 #8313 and conditional producer #7306 scope and exact heads; do not assume the census pin is still the current worktree.

**Requested behavior:** determine current regime from the net gamma evaluated at current spot under the same inventory, IV, time and unit conventions as the profile. Keep nearest-crossing location as a distinct descriptive level. Preserve all crossings/orientation when the accepted schema supports them; do not silently extend a strict consumer payload. Define near-zero, no-data, out-of-domain and failed-model behavior with the current consumers. Do not convert the assumed-sign profile into an observed-dealer claim.

**Meaningful acceptance:** the supplied descending chain returns a local sign consistent with its own curve at S98 and S101; ascending and no-cross controls retain correct behavior. Include multi-root and near-zero examples, input permutations and a numerical tolerance tied to the declared units. Confirm current consumer compatibility for any state vocabulary change. Production incidence remains a separate bounded data audit; the synthetic finding alone does not quantify affected records.

**Scope:** fix-free research wrapper/witness exists here; production implementation belongs to the incumbent producer. No new position store, pricing engine or activation gate is needed.

## B2. Separate strike distribution from finite hedge change

**Problem:** Terminal `hedgeProfile` accumulates snapshot Greek rows by contract strike while source wording gives a stronger spot-travel hedge interpretation. The current UI retains a per-unit caption. Equal snapshot-Gamma input tables can require different endpoint hedge trades, so no relabelling of the numeric cumsum as a finite transaction can make the information sufficient.

**Sources:** [marketStructure.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/a049d46fa2415d3949aae5efc0ee515b6667c7a0/terminal/lib/marketStructure.ts) and [HedgingCards.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/a049d46fa2415d3949aae5efc0ee515b6667c7a0/terminal/components/msc/HedgingCards.tsx). Reconcile #723/#768 and the Macro conditional producer before editing.

**First useful implementation:** retain the useful cumulative exposure distribution, name its horizontal dimension contract strike and its units sensitivity per declared shock, and remove any assertion that it is the total trade required as spot travels. Preserve current per-unit disclosure. A second view for actual scenario hedge change should consume the incumbent Macro repricer with full qualified book inputs; avoid a separate client-side economic model.

**Scenario contract:** one hedge underlying/currency, stated signed inventory, scenario spot/IV/time rule, complete/partial coverage and model version. B=-sum n m Delta; H=S*×(B*−B0), positive underlying buy notional. This is an endpoint rehedge convention, not path cash/turnover or observed order flow. Market impact needs an additional model/evidence.

**Meaningful acceptance:** unchanged spot/IV/time gives zero hedge change; down/up moves and long/short positions have correct directions; positions on both sides of spot contribute; matched-Gamma/different-maturity and different-IV books remain distinguishable by repricing; small shocks converge to the whole-book local approximation. Preserve unknown Greeks and partial totals. Exact tests and inputs are in the witness script/JSON.

## B3. Make chain proxy and measured flow distinct

**Problem:** `build_chain_heat` reconstructs `ask_share` as .80/.20/.50 from `~buy/~sell/mixed` and premium-weights it. Measured `microstructure.at_ask_share` is a different quantity. The source labels remain soft/display-only, but downstream names/lean labels can invite a stronger interpretation. Soft signing also lacks the measured block's future/locked/crossed-quote checks.

**Source boundary:** [Macro census §4](options-macro-census.md) identifies `engine/live_flow.py`, `engine/flow_signing.py`, `scripts/build_chain_heat.py`, `engine/options_structure.py`; the Terminal census identifies ChainHeat and legacy score consumers. Reconcile active intraday source/signing/quarantine work before proposing a duplicate parser.

**Requested behavior:** publish and consume separately named, versioned proxy versus measured fields. Preserve the old display contract during migration, without silently changing its numbers into a new estimator. Measured shares retain source/valid denominators and unknowns. A proposed inferred sign includes method, causal quote selection, age and condition policy, package ambiguity and abstention reasons. Any sign probability requires labelled calibration.

**Meaningful acceptance:** fixtures distinguish same premium with different quote locations from identical side-category proxies; midpoint/unknown remains unknown; future/locked/crossed/stale/condition-ineligible observations get explicit outcomes under the chosen policy; no measure becomes a customer/opening/dealer label. Existing measured-parser arithmetic guards remain intact. Do not infer market-wide coverage from selected notable events.

**Additional bounded qualification:** verify the feed-specific sequence and correction contract before changing watermark logic. Same-response duplicates, late arrivals and cancel/replacements need source-certified cases and current custody; a new independent amendment ledger is outside this brief.

## B4. Audit the actual GEX/Prophet contribution

**Problem:** the committed stock-score GEX gate is false, but the separate C1 fusion path conditionally admits `gex_confirm_verdict` in F5_FLOW_POSITIONING. An evaluation using today's Prophet as an “options-free” baseline would misstate its information set. Source presence does not establish influence on a particular published run.

**Source boundary:** `scripts/build_stock_library.py` → `engine/us_board_rank.py` → `engine/us_prophet_fusion.py`, with `engine/gex_confirm.py`; exact lines are in [Macro census §5](options-macro-census.md). AD1's empty GEX map and stock-score gate remain separate paths.

**Requested evidence:** through the existing owner, choose one already published board/run and retain exact code/input/model/publication references. Record non-null coverage, within-pool variation, member admission, duplicate-vector collapse, family aggregation and final ranking. A fit-free research comparison with the GEX member excluded can quantify that run's sensitivity if the source receipts support reproduction. It is not a production disable or a predictive-validation result.

**Acceptance:** a traceable answer to whether the member was admitted and changed scores/ranks in the inspected run, or a specific unavailable-input state. The empirical protocol records B0 options-free research comparator, B1 actual incumbent and B2 incumbent plus the proposed new family, together with the cohort's selection lineage. No blanket global-gate claim survives the source evidence.

## B5. Preserve Greek and artifact availability provenance

**Problem:** current real trade collectors retain important clocks/conditions, while EOD/OI/Greek projections remove detailed source/underlying clocks and model inputs. Input availability alone also cannot establish when an exact feature artifact reached the candidate consumer.

**Source boundary:** `collectors/thetadata.py`, `engine/thetadata_store.py`, current poller/publication and candidate revision receipts. Use the existing AD/intraday/OA owners and the current candidate strict schema; no auxiliary store is needed.

**Requested behavior:** preserve or reference source time, effective OI session, acquisition/publication time, underlying observation, model/rate/dividend/IV/TTE/unit provenance and exact artifact revision. Pin vendor matching/version parameters after actual capability qualification. Represent captured-PIT versus reconstructed history explicitly. Availability chain includes artifact publication and consumer admission, not just a recomputation timestamp.

**Acceptance:** current retained trade fields survive round trip; OI effective date differs correctly from availability; historical backfill cannot pass a captured consumer-PIT gate; strict candidate schema migration is explicit; quote-to-contract money scale and product clocks match reference data. Use the joint fixed/refitted-IV witness plus real qualified fixtures before selecting a Greek adapter.

These five briefs are implementation inputs for the current owners. They do not authorize new scores, candidate actions, fills/P&L claims, process starts or publication effects. The larger Fable commission should carry their accepted source heads and integration receipts, with already-completed work excluded.
