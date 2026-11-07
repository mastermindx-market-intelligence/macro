# Factor Atlas S3 — Native options research capability (source-only)

This code adds an original, deterministic and display-only factor-options
research capability to the incumbent Options Hub and Factor Atlas. No chain
store, customer portfolio database, dealer-sign authority, source publisher,
scheduler, Prophet or position-sizer has been created.

The public source at engine/options_basket_aggregation.py models a
constituent-IV summary and a distinct, covariance-conditioned 30-calendar-day
expected move. Only independently qualified source, basket and correlation
receipts can support complete-basket numerical outputs. Euler marginal and
component risk attribution remains display-only.

The pure history leaf engine/options_basket_history.py implements distinct
252-session min/max constituent-IV Rank and empirical midrank Percentile. All
source sessions and compatible house-basket identities are required. It
never claims directly traded synthetic-basket options.

The modules under research/factor_atlas/session3/*.py are pure retrospective
research and read-only original-source adapters. Their private input manifests
must be supplied from separately authorized existing source files. No actual
original vendor quotes, vendor year-file hash lists, private research results,
signed licensing data or customer portfolio records are shipped here.

Tests under tests/test_factor_options_*.py and tests/test_options_basket_*.py
use original synthetic fixtures. These methods do not certify historical
quote known-at, EOD pricing, licensed redistribution, calibrated probability,
trade P&L, risk-neutral implied correlation or model alpha.

Reproduce the existing code CI tests against Macro's approved test runtime:

    python -m pytest -q tests/test_options_basket_aggregation.py       tests/test_options_basket_inputs.py tests/test_options_basket_ci.py       tests/test_options_basket_risk_attribution.py       tests/test_options_basket_iv_history.py       tests/test_factor_options_retrospective.py       tests/test_factor_options_retrospective_io.py       tests/test_factor_options_retro_calibration.py       tests/test_factor_options_retro_outcomes_io.py       tests/test_factor_options_iv_retro_history.py       tests/test_factor_options_iv_retro_history_io.py       tests/test_factor_options_iv_error_sensitivity.py       tests/test_factor_options_extended_backtest.py       tests/test_factor_options_extended_backtest_io.py       tests/test_factor_options_raw_eod_provenance.py

Source-specific private research receipts and file hashes are preserved
separately by the original author, not published to the public Macro repo.
Original PR remains Draft/HOLD until registered guarded publication, exact
head hosted CI and independent code review. Customer-facing release needs
source timing, pricing method, data-use rights and authenticated path proof.


## Source-continuity and data-quality review

The 252-session constituent-IV history leaf refuses a mixed source cohort
even if all 252 rows contain numerical observations: basket definition,
member weights, **source coverage policy version and thresholds**, and
per-member 30-day IV calculation method must remain compatible. A changed
admission policy or an exact-tenor/interpolation method transition needs a
separately accepted continuous source history before a rank or percentile
can appear. No mixed cohort is silently recomputed into a valid history.

The read-only original EOD audit distinguishes actual missing numeric values
from non-numeric parsing failures and rejects nonfinite/infinite prices or
Greeks even if both source/archive representations contain the same invalid
token. This is *numeric reproduction* only, not quote-age or legal-use proof.

Both obligations are covered by original, synthetic test fixtures in
\`tests/test_options_basket_iv_history.py\` and
\`tests/test_factor_options_raw_eod_provenance.py\`, respectively. They do
not grant source rights, historic known-at, publication or trading authority.


## Original report and underlying mark clocks

The read-only raw EOD Greek provenance audit additionally compares the
original option and **underlying mark** source timestamp dates with the
declared EOD session. Inconsistent underlying-mark session dates,
non-ISO8601/numeric-epoch clocks, and unparseable timestamps are not
converted into falsely source-reproduced observations. The audit still
reports only original contract-count/field-disagreement diagnostics,
never restricted vendor values.

Passing that numeric audit is a necessary reproduction check, but is
not independent evidence of original quote availability, pricing-model
fitness, distribution rights or point-in-time known-at. These
limitations also apply to the historical ranking and retrospective
outcome research.


## Market session and availability are separate

The owner-qualified `Member` input can now carry an explicit `source_session`
date. The aggregate preserves that label on each member and reports a common
session only when every positive-weight member supplies the same date.
It never derives an exchange session from the date portion of `observed_at`,
`known_at` or the envelope's evaluation `asof`.

The history leaf requires that explicit common session and matching member
sessions before assigning an observation to the existing owner-supplied cash
calendar. Missing, malformed or duplicate session identity is refused;
a constituent session mismatch makes the point unqualified. Evaluation and
availability checks remain independent and unchanged: a later EOD receipt
cannot be used before its true receipt time. Different source sessions may
honestly share a capture/evaluation timestamp without collapsing into one day.
Equivalent timestamp offsets cannot move the market session.

The incumbent calendar/source owner must supply the actual observation
sessions eligible at the evaluation cutoff. Eligibility is not inferred from
UTC date equality. A history assembled from information available at query
as-of is not automatically a historical point-in-time reconstruction.

Current constituent-IV descriptors remain available under their existing
source/coverage policy when a common history session is unknown. A null common
session identifies an as-of member snapshot without claiming a synchronized
market-session measurement. Historical ranks remain withheld. Missing covariance
continues to withhold modeled risk without suppressing an otherwise qualified
constituent descriptor.
This is a source-contract repair, not a new calendar, collector, source
certificate, redistribution grant or historical known-at reconstruction.

Synthetic regression cases cover later EOD delivery, batch receipt, timezone
offsets, unavailable/mismatched session identity and duplicate sessions.
The change does not rerun or replace any previously completed original
ThetaData historical-source repair.
