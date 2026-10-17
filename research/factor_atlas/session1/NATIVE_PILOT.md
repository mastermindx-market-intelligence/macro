# Factor Atlas Session 1 — native read-only candidate

**State: BUILT_NOT_PROVEN.** This native candidate is separate from the preserved research v0 schema/oracle. It is implemented in Macro and runs without a dashboard. It does not publish a feed or grant source/consumer acceptance.

## What now exists

`engine/factor_atlas_read.py` computes a source-referenced long-only USD basket from explicit owner projections. `engine/factor_atlas_sources.py` binds incumbent membership observations, `VendorAliasTable`, `Resolved` prices and existing US calendar/session rules. `contracts/factor_atlas_read.v1.schema.json` fixes the output envelope. `scripts/factor_atlas_read.py` validates bounded local inputs, calculates, checks the output schema/identity/digest and emits JSON to stdout only.

The initial method is equal target weights at a **fixed construction inception** and subsequent month-end closes, with weight drift and constituent-total-return reinvestment between rebalances. It is a gross descriptive index, not a funded trading strategy. The requested start date is a display/measurement window: it does not reset the basket or erase the earlier construction history.

Current-roster and strict-PIT requests remain distinct. Missing held prices withhold the return and break the global index chain; a later qualified rebalance can restart local return observations but cannot invisibly reconnect the original NAV. The output includes advance breadth, count/weight coverage, end-weight HHI/effective number, concentration, contributions, exact-window returns, volatility/downside deviation and drawdown, with explicit unavailable values.

## Run the native fixture examples

From an admitted Macro workspace, with its normal dependencies:

```bash
python3 scripts/factor_atlas_read.py \
  --input tests/fixtures/factor_atlas/monthly_round_trip.json

python3 scripts/factor_atlas_read.py \
  --input tests/fixtures/factor_atlas/pit_fallback_refusal.json

python3 -m pytest \
  tests/test_factor_atlas_read.py \
  tests/test_factor_atlas_sources.py \
  tests/test_factor_atlas_contract.py -q
```

Both fixtures are **SYNTHETIC_FIXTURE** inputs. Their three invented securities are not a real Magnificent Seven population, even where a fixture reuses a basket-shaped identifier. The round-trip example yields 0% over the full window under drifting weights. Moving the display anchor to the intermediate close yields -25% over the remaining interval, rather than incorrectly resetting to equal weights and showing -16.6667%. The strict-PIT fallback example returns `UNAVAILABLE`, with `CURRENT_ROSTER_FALLBACK` and null returns.

The CLI takes exactly `request` and `owner_inputs`. Duplicate JSON keys, NaN/Infinity, malformed shapes, unknown authority overrides and inputs above 16 MiB are rejected. Output above 4 MiB is refused rather than truncated. A shell redirect may save an explicitly chosen private evidence artifact; the runner itself has no source-write, publication or collection path.

## Source and construction contract

A request names the basket, history mode, requested window, measurement cutoff, internal-research purpose and the currently supported equal/monthly method. The owner projections must include a separate immutable `construction` reference and inception, plus every calendar/price interval from that inception through the requested end. The native calendar must agree with existing US sessions, including holidays, daylight-saving time and early closes. An omitted session is not removed from the denominator or replaced by a zero observation.

For each rebalance, strict PIT needs the exact membership query, snapshot date, complete population, effective interval and precise known-at cutoff. Current-roster mode freezes one explicit observation and does not claim that roster was selected historically. Per-decision alias observations preserve native effective/knowledge intervals. Historical membership symbols are not assumed to be current price-store keys; the incumbent alias owner resolves both spaces separately.

Price input is the incumbent `Resolved`/`PriceEvidence` contract. The bridge carries the same-read encoded-object receipt when that owner supplies it. Unknown adjustment vintage, session, venue, observation clock or corporate-action reference stays unknown. The bridge does not infer USD currency, rights or corporate-action qualification merely from a ticker or file hash; those bindings remain explicit owner-supplied inputs.

**Reference integrity is not source admission.** The result always says `CANDIDATE_NOT_ADMITTED` and `REFERENCE_CHECKS_ONLY_NOT_RECEIPT_AUTHENTICATION`; ranking, gating, sizing, trading, escalation and publication capabilities are false. A consistent digest detects accidental mutation but does not authenticate an authorized source or a legal entitlement.

## Tests and remaining proof

The native tests include integration with actual incumbent membership and price reader code over isolated synthetic fixture stores. They verify qualified fixture returns, preservation of absent native metadata, no source changes during the read, no network calls, immutable-input behavior, exact calendar boundaries, alias/store-key separation, output mutation rejection and byte-identical CLI results under different hash seeds.

They do **not** prove actual house-basket data rights, complete live PIT history, production corporate-action metadata, source publication, independent review or an authenticated Terminal consumer. The first real-data candidates remain `mag7`, `ai_infra` and `defense` after each input is qualified; no live history is fabricated to satisfy the pilot.

The existing Terminal gateway and chart components have not been changed. Their accepted feed/type binding and real consumer proof remain a separate dependency. No code in `research/factor_intelligence/`, `engine/theme_graph/`, incumbent basket/style calculations, membership stores or portfolio decisions is modified.

Current implementation evidence and next action: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md). Research publication receipt: [PUBLICATION_RECEIPT.json](PUBLICATION_RECEIPT.json). Source carrier: Macro PR #8680, under issue #8676.
