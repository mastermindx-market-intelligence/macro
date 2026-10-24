# Factor Atlas Session 1 — native implementation frontier

Implementation owner: Sol under the current direct Chairman instruction to save the research and implement it. Implementation issue: **Macro #8676**.

## Source and custody

- Protected procedure: Mastermind `732cf7be88e7159b4995a8885fbd381cd1484e3e`, compatible Skillpack 1.0.1 / bootstrap major 1.
- Native base: Macro `d28a9fbe913846bff7d72a503d3951618a8a5b86`.
- Managed operation: `factor-atlas-s1-native-20261009-c1`.
- Branch: `sol/web-factor-atlas-s1-native-20261009-c1`.
- Installed `mmx-workspace acquire --repository macro` returned APPLIED with matching base/head and its operation lock. No prior modifying effect was unresolved.
- The Session 2 capital-pressure and Session 4 workspaces were observed and preserved. The Session 2 uncommitted research path is disjoint. This operation neither takes over their source nor duplicates their workers.
- The source-only workflow uses the existing Studio/managed-workspace and GitHub delivery owners. No Executive Job, provider worker or background reasoning is claimed.

## First verified native capability

`engine/factor_atlas_read.py::build_factor_read` is an additive read-only candidate over explicit incumbent-owner projections. It reuses Data OS security identifiers, UTC clock parsing, adjustment/session/venue vocabulary and the existing price owner's basis arbitration.

The bounded method is USD regular-session consolidated closes, monthly equal targets with drift between rebalances, constituent-total-return reinvestment and gross zero-cost returns. Current-roster and strict-PIT requests are distinct. Missing held valuation breaks the index chain; unavailable prices are not zero or renormalized portfolios. Breadth, end-weight concentration, horizon returns, volatility and drawdown retain declared denominators and missingness.

**This is not an admitted production feed.** Output says `CANDIDATE_NOT_ADMITTED` and `REFERENCE_CHECKS_ONLY_NOT_RECEIPT_AUTHENTICATION`; all ranking, gating, sizing, trading and publication flags are false. A supplied reference is not proof of entitlement or actual owner acceptance.

## Verification completed at the first native milestone

- Baseline: `python3 -m pytest tests/test_price_ladder.py tests/test_us_basket_membership_pit.py -q` — **52 passed, 4 skipped**. Skips are not passing coverage. Baseline emitted existing shared-pytest-temp cleanup warnings; subsequent task tests use operation-local basetemp.
- RED: `python3 -m pytest tests/test_factor_atlas_read.py -q --tb=short --basetemp=.factor-atlas-evidence/red-tmp` — **41 failed**, each on the explicit missing-native-adapter assertion, not import or dependency errors.
- GREEN: `python3 -m pytest tests/test_factor_atlas_read.py -q --tb=short --basetemp=.factor-atlas-evidence/green-tmp` — **41 passed**.
- `git diff --check` — no whitespace errors on the tracked diff at this milestone.

These are native tests over synthetic owner projections, not real-data PIT proof, independent review, CI acceptance, merge or deployment. Logs stay in the operation's uncommitted evidence directory; exact source is preserved by the carrying commit.

## Next in-scope actions

1. Preserve the full delivered Session 1 research package without rewriting its historical claims into current acceptance.
2. Add native schema validation, effective-time/alias checks, additional source-bound adapter tests and deterministic cross-process proof.
3. Exercise the incumbent owner-input seam, preserving unavailable rights, corporate-action vintages, collection clocks and identity coverage as explicit gates.
4. Complete exact-head review and CI before any release. Bind an accepted consumer interface before modifying the Terminal gateway or publishing a customer feed.

## Boundaries and DO_NOT_REDO

Do not edit `research/factor_intelligence/`, `engine/theme_graph/`, incumbent basket/style calculations, ranking, entry, portfolio or membership stores. Do not promote the old research's source counts to current live coverage. Do not replay previously refused host read batches, change permission configuration, or claim that a mode switch clears a refusal.

The current request authorizes this new source-only candidate workflow. It does not supply price redistribution rights, corporate-action attestations, historical collection completeness or consumer acceptance. Keep those gates separate from the independently implemented calculation layer.

## Native owner-bridge milestone

The original research is now committed and pushed at `24764ffea743bc4a8d29b36d983d63605ad59dc8` in PR **#8680**. `PUBLICATION_RECEIPT.json` verifies 23 original manifest entries byte-for-byte, with six raw logs explicitly omitted rather than pretending the source subset is the entire archive. `PUBLICATION.md` explains the original reports' retained historical status statements.

`engine/factor_atlas_sources.py` adds an invocation-scoped bridge over the incumbent `members_asof` output, native `VendorAliasTable`, native `Resolved` price type and US cash/session-calendar owners. It does not collect or write source data. Historical membership names and current price-store keys stay separate. Missing aliases stop binding instead of shrinking a cohort; duplicate price labels refuse; adjustment/action/knowledge/rights fields are never filled from the current time. Per-decision identity observations preserve effective alias intervals.

Further test-first changes close future/expired membership, exact as-of query, missing/expired identity interval, malformed shape, extreme numeric, missing calendar session, holiday and incorrect close-clock cases. Full-window NAV never reconnects after a missing valuation, even when local returns resume after a qualified rebalance.

Verification:
- Hardening RED: 18 failed, 46 passed; failures exposed the intended missing necessary checks.
- Hardening GREEN: 64 passed.
- Owner-bridge RED: 9 failed on the explicit missing native bridge assertion.
- Owner-bridge GREEN: 73 passed across calculation and bridge tests.
- Calendar/per-decision identity RED: 5 failed, 64 passed.
- Current combined GREEN: `python3 -m pytest tests/test_factor_atlas_read.py tests/test_factor_atlas_sources.py -q --tb=short --basetemp=.factor-atlas-evidence/calendar-green` — **78 passed**.

The bridge integration tests actually invoke the incumbent membership writer/readers and price resolver **only against isolated synthetic fixture stores**. They prove a 7% synthetic current/PIT return when fixture evidence is explicitly qualified and withheld returns when the native price evidence leaves its adjustment/session/observation fields unknown. They also prove no source-file changes during the adapter invocation and no network calls. They do not prove live rights, production source completeness or an accepted consumer feed.

Current next step: native v1 schema, executable read-only invocation and source-only project continuity; then exact-head validation/review and the separately gated real-input/consumer qualifications. PR remains DRAFT / HOLD-FOR-SOL.
