---
key: OPTIONS-COMPARE-IN-RISK-DETAIL
question: Where should the cross-name options-cost and downside-protection comparison live on the Macro Dashboard?
answer: >
  Inside the existing Risk Detail dialog, immediately alongside the incumbent
  volatility diagnostics. Keep the established #regime-radar as the primary
  macro surface and link deeper work to the Options workspace.
rationale: >
  The current Macro Dashboard already reserves volatility diagnostics for Risk
  Detail to keep the primary scorecard glance-first, and the prior Chairman
  ruling removed a second standalone risk container for the same viewport-cost
  reason. The new comparison is options-risk context, not a new regime score or
  trading signal, so Risk Detail is the existing semantic and interaction owner.
alternatives:
  - option: Add a new full-width Macro Dashboard panel
    why_not: Reintroduces the duplicated first-level risk surface and vertical cost already rejected.
  - option: Put the comparison only in the Options workspace
    why_not: Loses the macro-risk glance while duplicating none of the existing options depth.
  - option: Fuse the two axes into Market State or Risk Radar scoring
    why_not: The skew owner remains display-only and unscored; a fused score would exceed its authority.
evidence:
  - research/DO_NOT_REBUILD.md HOLD-UD-B1-PRIMARY-MACRO-MIGRATION
  - agentos/decisions/DEC-RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL.md
  - engine/options_skew.py
  - templates/risk_envelope_live.js
  - templates/options_compare.css
  - tests/test_options_skew.py
  - tests/test_risk_envelope_radar_integration.py
affects:
  - templates/risk_envelope_live.js
  - site/risk_envelope_live.js
  - site/options_compare.css
  - scripts/build_site.py
  - templates/options_compare.css
  - engine/options_skew.py
  - scripts/build_options_skew.py
confidence: high
reversibility: easy
decided_by: chairman-chris
decided_at: 2026-10-07
---

The comparison remains display-only. "Fast" means unusually large five-session
movement inside the two-axis options-pricing map; it does not mean bullish,
bearish, actionable, validated, or promoted. The axes use the canonical skew
ledger's own-history observations and inherit its source/session limitations.

Integration repair, 2026-11-06: comparison-only styles use the existing paired
asset copy path and load once with the comparison data. The accepted early-warning
band CSS, dashboard template and visual receipt inputs remain byte-identical.
Weekends do not count toward the comparison's session minimum, ranks or trails;
the browser measures displayed age from the as-of date at read time.


Original-journey continuation, 2026-11-07 (Mastermind #2028, original #8578):
the numerical contract is options_compare.v2. A name needs 20 strictly prior
paired-valid same-source observations, and each rank uses up to 60 prior
observations with midpoint ties. Current is excluded from its baseline.
history_n continues to count prior plus current; prior_n names the denominator.
Every trail point applies those rules at its own historical cutoff.

Keep the deliberate 30-name bellwether/fallback display budget as this carrier's
product scope. The closed #8577 all-name prototype is not a separate obligation
to duplicate the map or claim complete-market coverage. Same-source exclusion,
weekend handling, complete-session selection and existing owner/emitter remain.

The selected-tenor one-standard-deviation IV percentage reference uses annual
fractional ATM IV times sqrt(actual calendar-day tenor / 365). It is a declared
pricing scale without physical-probability, forecast or trade authority.
The ledger lacks a qualified spot observation clock and price basis: retain
that absence and withhold the price-unit expansion, even when a numeric spot is
reported. Do not infer a spot timestamp from as_of, IV time or generation time.

The committed v1 seed remains historical and byte-unchanged. The renderer has
explicit separate v1 strict-less labels and v2 midpoint-tie labels; unsupported
contracts or malformed ranks do not become zero. Legacy rows do not acquire a
fabricated v2 pricing reference. Only the existing emit path can generate new
v2 data; synthetic tests are not served-data or production-generation proof.

The required new-stylesheet/hover CI hold, existing browser/capture refusals and
authenticated/live-market acceptance remain. This source continuation neither
relabels historical evidence nor releases that hold.
