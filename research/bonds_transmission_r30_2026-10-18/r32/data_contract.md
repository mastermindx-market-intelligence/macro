# R32 — case, event and receipt state extension

Read with the pinned [R31 owner bindings](../r31/source_bindings.json). These are UI/reference requirements, not new registered production schemas. Existing Investigation, Alerts, macro and capital-structure owners remain authoritative.

## Case additions

The local reference retains a stable key, kind, title, source, origin, reporting period, typed payload and relevant borrower/instrument/horizon context. Context admission precedes mutation. A conflicting addition leaves the original items and edited form intact. Reapplying a key replaces it rather than appending another vote.

An incompatible retained item remains visible with `needsReview`; its original payload stays inspectable. Effective rule, shape and hedge inputs derive from active additions. Undo restores both metadata and owned effective inputs. Pending main-page inputs and unapplied tool forms are independent from the applied case and from retained research.

The reference’s memory is not a new canonical research store. Production resolves supported typed references through Investigation v2. Unsupported charts, scenarios and rules must not be serialized into generic text to evade its admission rules.

## Observations and evaluation

The deterministic fixture represents `cutoff`, `sessionNo`, yield, funding and a frozen 12-peer cohort. Inputs carry value, quality, eligibility and release time. The fixture’s flags are declared test inputs, not proof of production freshness or entitlement.

An eligible input must be current and released by the decision cutoff. Peer aggregation requires complete unique membership and finite values. Known fresh invalidators are checked before the aggregate. Explicit null remains missing; zero remains a value. Display rounding does not control boundaries.

The evaluated rule retains the authored confirm, invalidate and peer-mean thresholds. Waiting, paused, expired and terminal results keep copied rule snapshots where applicable. A fifth close is evaluated before expiry; a session beyond the window cannot reopen it. Closed-event evaluation returns the original outcome.

Later continuation review requires a later observation cutoff and the original event’s declared review level. Earlier evidence remains historical context. Correction review uses the frozen original rule, preserves the original event and creates a separate revised evaluation without retrospective notification. Receipt storage must additionally bind exact source versions and an authoritative receipt/publication clock in production.

## Sensitivity compatibility

Benchmark and credit-spread shocks remain separate. All-in corporate yield plus an additional spread shock is rejected. A curve shape requires the compatible complete sensitivity vector for each affected exposure. The Treasury vector cannot be reused for corporate credit; the corporate shape result is unavailable until its own vector is bound.

Sensitivity identity must include instrument/position, valuation cutoff, curve basis, node/bump/interpolation method and relevant currency. A scalar convexity number does not supply a cross-tenor convexity matrix. Price approximation excludes undeclared carry, roll, FX and financing effects.

## Cash and flow provenance

Reported annual principal buckets preserve date precision and legal obligor. They do not generate invented payment dates. Current coverage requires amended obligations, cash-pool restrictions, draw eligibility, settlement cutoffs and permitted transfers. The Parent A cash fixture is separate from CoreWeave; no cross-borrower attachment is allowed.

Holder reconciliation preserves market-value basis, holder/asset/currency scope, observation period, transactions, price revaluation, FX and other changes. Missing components do not become zero. Net buying, gross selling and the source of funding are different quantities. Quarterly data cannot establish a same-day switch.

## Retained scope and operation identity

The offline question-only receipt includes its explicit scope, subject, question, next check, horizon, revision, operation ID, exact-read status, exclusions and simulation marker. Reopen derives content from that payload. Local excluded evidence is shown separately.

An uncertain operation keeps its original ID and payload for receipt recovery. A conflict preserves the submitted question/check and the case draft. Exact-revision failure never substitutes latest. Neither a demonstration receipt nor an admitted real question-only save establishes full-case retention or active monitoring.

## Forecast admission

The interface exposes conditional paths while empirical qualification is absent. Model probability remains null/unavailable until an approved owner supplies the exact target, horizon, model/data version, point-in-time admission, effective sample, out-of-time performance, calibration, uncertainty and abstention evidence. The number of correlated displayed indicators cannot fill these fields.
