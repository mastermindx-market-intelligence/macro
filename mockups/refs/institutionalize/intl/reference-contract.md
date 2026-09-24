# International Markets vNext — Reference Contract R2

**Status:** provisional design-authority revision after RIG pass-1 BLOCK.
**Reference id:** `intl-vnext-20260924`.
**Replaces:** the semantic content of commit `f3873dcb`; preserves its composition grammar.
**Primary question:** What is changing across world markets, why does it matter, and what stance is already warranted by the accepted engines?

## 1. Truth and authority rules

1. Every visible fixture value maps to a field already published by `scripts/build_intl.py`; the reference labels itself **REFERENCE FIXTURE**, never Live.
2. The only 0–100 headline scalar is the engine-owned World Risk Appetite score. It is never renamed confidence, risk budget, conviction, or probability.
3. Do not show invented confidence percentages, historical ranks, data-health scores, sensitivities, or thresholds.
4. Do not show Saved, Pin, Compare, Alerts, Generate brief, Export, Live Desk, or account state. Those capabilities do not exist on this static route.
5. Transmission language is conditional and descriptive: “observed with,” “associated pressure,” “if this persists.” Never state a causal chain.
6. Market cards use one selected horizon for every row and always show USD return, local return, and FX contribution together.
7. Rotation uses current rank plus accepted `rs20_pct`, `rs5_pct`, state, and stance. It does not invent rank history.
8. Turn states and RRG quadrant labels remain separate vocabularies and distinct visual treatments.
9. Slow fragility always shows threshold/source/cadence/base-rate context and an honest missing state.
10. Playbook content is a projection of existing stance fields only; it never originates, sizes, or recommends a trade.
