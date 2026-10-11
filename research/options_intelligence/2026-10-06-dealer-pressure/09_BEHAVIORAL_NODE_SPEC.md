# Behavioral node specification

**Status: SPEC_ONLY.** Nodes are derived summaries of a continuous, uncertain pressure/liquidity field. Large OI strikes remain structural concentrations unless a behavioral mechanism earns a stronger label.

## 1. Do not confuse damping with attraction

Let `B(S)` be the modeled target hedge. For fixed inventory, `∂B/∂S=−Σh m Γ`. Negative slope means target hedge changes oppose an exogenous spot move. This is a **damping response**; it does not by itself identify a unique price attractor. A long-gamma book can damp motion at many prices without creating a force toward one strike.

An attractor requires a defined conditional future flow or drift field. Let `F_t(s)` be the projected signed incremental execution over a specified horizon, conditioning on an anchored hedge state, future vol/time, inventory and hedge policy. A candidate stable equilibrium `s*` requires `F(s*−ε)>0`, `F(s*+ε)<0` and a robust inward slope, under the relevant price-impact mapping. A root of absolute hedge holdings or net gamma is not automatically that equilibrium.

The label remains 'modeled attractor candidate' until the close/hold/touch studies establish calibrated usefulness. The expiration-clustering literature supports conditional mechanisms, not a guaranteed max-pain target [R09].

## 2. Behavior taxonomy

| State | Required mechanism | What invalidates it? |
|---|---|---|
| Absorption candidate | Perturbation induces material countercyclical target/execution response; qualifying liquidity supports the interpretation | Inventory/surface sign reversal, demand too small, liquidity evaporates |
| Attractor / pin candidate | Robust inward conditional flow on both sides for a stated horizon | Drift loses inward sign, equilibrium leaves domain, expiry transition, external-flow dominance |
| Neutral | Response remains inside registered numerical/economic near-zero band with adequate coverage | Newly material response; missingness is not neutral |
| Acceleration candidate | Incremental hedge demand reinforces movement and increases materially after breach | Countercyclical response, weak execution propensity, replenishment |
| Transition / flip | Qualified sign/stability change with orientation and uncertainty band | Disappears with refinement or plausible inventory/surface model |
| Liquidity reservoir | Independently observed or lag-trained replenishment/execution evidence | Withdrawal, depletion, correction, stale book; options OI is insufficient |
| Fragile void | Thin executable capacity plus procyclical response under matched horizon | Improved depth/refill or nonmaterial options flow |

One zone may have separate options and liquidity tags. Do not collapse contradictory mechanisms into an averaged bullish/bearish score.

## 3. Extraction algorithm

1. Freeze anchor inputs, admissible scenarios, instrument coordinate, horizon and evaluation grid. Store the exact price band and input revision.
2. Evaluate whole-book pressure and relevant derivatives with error tolerances. Refine grid around near-zero crossings, strong gradient changes and liquidity discontinuities.
3. Extract connected price intervals satisfying the behavioral predicate. Root-find only on genuine brackets; tangencies require a separate local-extremum check. No root means no transition, not a synthetic root at spot.
4. For each candidate interval, calculate center/range, boundary slope, integrated response, min/max across scenarios, numerical stability and options materiality. Report scenario survival fraction as robustness, not calibrated probability.
5. Combine adjacent candidates only if their mechanism, horizon and uncertainty bands overlap under a predefined rule. Split competing behavioral states. Cap the displayed number by a registered information-density policy, while preserving the complete candidate set in the machine record.
6. Rank display relevance by distance, horizon, materiality, uncertainty and current evidence maturity. This is an attention ordering, not a trading or Prophet ranking.
7. Publish node lineage. A moved range or changed mechanism creates a new version; old decision snapshots remain unchanged for evaluation.

## 4. Topology, optimization and clustering

Use topology first: connected components, crossings, turning points and stability under grid refinement are interpretable. Persistent features across spot/vol/time slices are stronger candidates for attention but have no automatic forecast probability. Optimization is useful for locating extrema of hedge-response elasticity subject to a bounded domain. Density clustering can combine nearby supported strikes or prints; it must not fabricate economic behavior from density alone.

Choose a minimum spatial resolution based on tick size, numerical error, quote staleness and inferred location dispersion. A printed '5,982.25' from a coarse model is false precision. Express broad bands when inventory uncertainty moves the transition substantially. Sensitivity to the strike lattice, round-number effects and grid spacing is a required placebo.

## 5. Node record

`node_id`, `version`, `source_snapshot_id`, `instrument_coordinate`, `basis_mapping_id`, `formed_at`, `available_at`, `valid_until_condition`, `horizon`, `low`, `high`, `mechanism`, `flow_sign_below`, `flow_sign_above`, `target_units`, `expected_execution_range` where qualified, `pressure_gradient`, `materiality_definition`, `materiality_range`, `inventory_scenario_set`, `surface_model_set`, `numerical_error`, `model_disagreement`, `liquidity_evidence`, `invalidation_conditions`, `adjacent_nodes_by_direction`, `evidence_class`, `forecast_model_id` if any, `null_reason`.

`next_node_if_broken` is an adjacency relationship under the frozen scenario, not a price forecast. Supply a conditional transition probability only from a calibrated model. Do not connect a graph edge across an unevaluated domain or a different product coordinate.

## 6. Stability and refresh

Use separate thresholds for appearing and disappearing to reduce visual flicker, with values selected on training data. Retain raw state changes so smoothing cannot hide a genuine sign switch. Freeze published forecast nodes at decision time for labels; subsequent recomputation starts a new forecast record. Conditional state history is visible in replay through existing history and correction owners.

## 7. Validation

Compare against equally wide static-OI, current GEX, round-strike, VWAP and randomly shifted placebo zones. Match distance-to-spot, time-of-day, width, volatility, eligible sample and number of zones. A wider or denser grid touches more often mechanically. Report touch and conditional hold separately; a day that closes above a support level after a large intraday breach is not necessarily a successful hold.

Key falsifiers: node behavior disappears after width/distance matching; gamma-only labels perform as well as full field; apparent pinning is a strike-lattice artifact; topology changes under small credible inventory changes; effect vanishes after price/liquidity baseline. Failed nodes may remain descriptive structural overlays but lose behavioral/predictive language.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[R09]: https://www.sciencedirect.com/science/article/pii/S0304405X05000577
