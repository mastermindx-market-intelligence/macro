# Bounded catalogue consistency review

**Reviewer:** theta_audit. **Date:** 2026-10-03. **Scope:** all 40 human formula rows in /tmp/options-signal-catalog.md; complete OIF01/OIF04 JSON contracts and complete field differences for OIF19/OIF22/OIF13/OIF35 against the shared contract; shared model definitions/evaluation rules; MASTER_PLAN.md, CONTRACTS.md and RESEARCH_PROTOCOL.md under /workspace/scratch/304dc2fae6f2/options-research.

**Disposition:** No additional fatal formula, sign, unit, PIT or proxy-versus-observed defect found in the bounded review. Resolve the P3 naming/forecast-interface ambiguity below before describing these as exact harmonized contracts. The two other known cross-document collisions were already corrected in the catalogue during the review. This is a research-design consistency review, not numerical execution, source/data acceptance, model validation or release authority.

## 1. Material remaining clarification: P3 is a volatility-valued feature for a variance-forecast task

Catalogue JSON /features[id=OIF19]/formula is:

    VolResidual = sigma_ATM(T_H) - sqrt(vhat_P,H)

The shared physical model forecasts annualized realized **variance** through a positive log-HAR/smearing candidate. Its square root is a volatility-scale forecast transformation. It is not generally the conditional expectation of realized volatility: sqrt(E[V]) and E[sqrt(V)] differ. The current title “Implied-versus-expected realized-volatility residual” invites that ambiguity even though the formula itself is clear.

**Recommended exact harmonization:**

- Catalogue OIF19 title: **“ATM implied volatility minus square-root physical-variance forecast.”** Units: decimal annualized volatility; percentage-point display is ×100 once.
- MASTER_PLAN P3: name OIF19 as the primary volatility-valued residual; retain matched-20-session **variance forecasting** as the primary empirical task.
- CONTRACTS analytical table: retain two separately named rows—OIF19 volatility residual as above, and **OIF20 queued ATM-implied variance residual**, sigma_ATM(T_H)^2 − vhat_P,H, in annualized variance units.
- RESEARCH_PROTOCOL P3: **“Does a frozen positive variance forecast augmented with OIF19 reduce matched-horizon out-of-time QLIKE versus the actual incumbent forecast? The augmented forecast model/link and its fit/freeze rule must be specified before evaluation. OIF20 is a separately counted queued variant.”**

This does not require inventing a fitted coefficient or model in the current research PR. It makes the remaining preregistration obligation explicit. A possibly negative VolResidual is a feature, **not** a valid positive variance forecast supplied directly to QLIKE; “baseline plus residual” must mean an explicitly defined model augmentation, not addition of a volatility number to a variance number.

For positive IV and forecast variance:

    VarResidual_ATM
      = VolResidual * (sigma_ATM(T_H) + sqrt(vhat_P,H))

That identity does not make the two feature definitions interchangeable. Their units and observation-specific scaling differ; normalization, ranks and fitted-loss comparisons may consequently differ. Preserve their IDs and pilot roles rather than relabelling OIF19 as a variance gap. Relevant locations: catalogue model_definitions.physical_variance_forecast; pilot_families.P3; OIF19/OIF20; governing CONTRACTS §4; MASTER_PLAN §4; RESEARCH_PROTOCOL §3 and §6.

## 2. Known collisions addressed during this review

The close check confirms OIF13 now uses:

    H = -(S_0 + deltaS) * sum h_i*m_i*(Delta_i_star - Delta_i_0)

Its units now say endpoint hedge notional at scenario spot, positive for modeled purchases, with path cash excluded. This agrees with CONTRACTS §5's H=S_star*(B_star−B_0). Vanna/charm/pure-aging cases with zero spot shock retain the same spot factor. Keep common model-definition prose consistent with that endpoint convention; the earlier initial-spot convention was valid as a different quantity but could not share this H definition.

Maturity keys are now M0–M4, avoiding the governing protocol's B0/B1/B2 baseline vocabulary. These are naming repairs, not new operational states or additional pilot families.

The root is also harmonizing proposed primary endpoint/horizon selectors with the catalogue. Preserve the distinction between a concrete proposed selector and the final owner-reviewed dataset/endpoint freeze; no additional empirical run is implied.

## 3. Checks with no further blocker

- **OIF01:** q*m divided by same-underlying share volume is a coherent turnover ratio for compatible stock/ETF deliverables. Index/ETF denominator substitution is explicitly disallowed. It measures attention, not bullishness.
- **OIF04:** signed long-option delta, negative puts, inferred aggressor sign and separate unknown dollar-delta mass are coherent. Strictly prior eligible quotes, package uncertainty, source/model availability and final-hour model gates are explicit. Unknown model/deliverable cases cannot silently gain known exposure.
- **OIF19:** positive physical forecast, matched actual consumer-time endpoints, annualization and training-label maturity rules are consistent. Future realized variance remains an outcome. The remaining issue is the naming/positive-forecast interface above.
- **OIF22:** raw/adjusted differences have the same IV units; OI weighting and a training-only borrow projection are explicit. Missing/stale borrow makes the adjusted value unavailable. A statistical residual is not identified private information or an exact academic replication.
- **OIF13:** full repricing, scenario inventory, fixed surface policy, seconds-to-years conversion and unqualified expiry-crossing exclusion are explicit. Scenario hedge demand is not observed dealer trading or identified price impact.
- **OIF35:** relative spread is dimensionless and uses valid positive-size quotes; quoted friction and simulated markouts are not represented as proven fills or self-validated execution costs.

The wider human rows correctly distinguish gamma turnover from positions, gross OI exposure from signed scenario inventory, vega/vanna percentage-point scaling, calendar-charm sign, variance from volatility, total-variance slope from IV slope, matured markouts from decision-time inputs, and fixed versus same-price-refitted-IV diagnostics. Existing blocked benchmark labels and edition boundaries were retained; I did not reopen source research.

No input files were edited. No searches, agents, repository code execution, runtime probes or tests were used. Only this review note was written.



## Principal integration disposition — 2026-10-03

The catalogue writer and principal implemented the reviewed corrections: OIF13 uses endpoint spot for hedge notional; maturity labels are M0–M4; OIF19 is ATM IV minus the square-root physical-variance forecast, distinct from expected realized volatility and from OIF20; QLIKE requires a separately frozen positive variance forecast; matched ACT/365F annualization/conversion is explicit. The positive augmented mapping is deliberately still an empirical preregistration dependency, not an implemented model. Root structural checks confirm 40 IDs, six primary records and the corrected formulas/names.

The dedicated near-expiry specification now shares the catalogue 60-session/minimum40 RZ convention, explicit derivative time scaling and B0/B1/B2 baseline distinction. Its additional windows/shocks remain named diagnostic proposals.

| Integrated file | SHA256 |
|---|---|
| options-signal-catalog.md | `a7556061d98c74a36c3d6e21de3568c03cd4f1ed40e2e304d5143e4422bc2f79` |
| options-signal-catalog.json | `03f6e951dd838cc348472159d96a9eefe1c328879e720b09a2f4021aa57f7a82` |
| options-near-expiry-spec.md | `1bf7dd8412f035a7a3b2f02c91ba32eca1ea6d8ae1c02519e524e5bf83ecf2ec` |
