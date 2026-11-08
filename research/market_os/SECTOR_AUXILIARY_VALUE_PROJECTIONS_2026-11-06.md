# Captured auxiliary values and shared calibration

Status: source-qualified, not activated. Base `84f1b7287c8f7298e502eb67949f01ee7c40ef1e`.
Governing [Macro #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779);
source carrier [#10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780);
protected Mastermind law `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

## Existing owners retain their calculations

| Owner | Explicit captured-value entry | Preserved behavior |
|---|---|---|
| Basket score | `market_concentration_from_inputs` | Actual aggregate breadth tape; daily and 3/5/21-row summaries; existing present-data failure behavior |
| Theme | `earnings_calendar_from_inputs` | Panel-date comparison, original 14-calendar-day rule, uppercase ticker projection and whole-calendar failure fallback |
| Cycles | `risk_calibration_from_document` | Original artifact clamp, scalar/dict cells and whole-map fallback when any cell is malformed |
| Cycles | `risk_size_mult_from_inputs` | Original family aliases and missing-cell multiplier 1.0; no cache load |
| Cycles | `effective_entry_settings_from_inputs` | Six documented source defaults and original float/int coercions |
| Volatility | `published_snapshot_from_documents` | Nonempty site snapshot first, then regime mirror; no timestamp arbitration |
| Volatility | `overlay_gate_from_document`, `overlay_config_from_inputs` | Original closed gate, default configuration and explicit empty-map semantics |
| Theme / Narrative | `signal_calibration_from_document`, `sizing_calibration_from_document` | Verdict and sizing projections from one basket-calibration document, including explicitly malformed nested null/list values |
| Central | `fusion_calibration_from_inputs`, `fusion_calibrations_from_inputs` | Existing key derivation, beta lookup, risk-family lookup, deduplication and independent failure defaults |

Legacy acquisition delegates to the same mathematical bodies. No source freshness
is inferred merely because a supplied document can be projected. The full adapter
must bind actual bytes, preserve source dates and distinguish resolved absence from
unbound dependencies.

The concentration input is `data/breadth/breadth.parquet`, a separate aggregate
tape. It is not reconstructed from constituent close panels. Its original malformed
present-data behavior is preserved.

Earnings remain display-only. The new value entry requires an explicit panel date
and an absolute ISO source vintage, so words such as “today” cannot invoke the wall
clock. The legacy wrapper retains its original timestamp parser. The existing
14-day arithmetic, including its treatment of future-dated vintages, is preserved;
source admission owns any stricter provenance policy.

## Deliberate configuration freshness correction

Previously `acquire_calculation_inputs` read current configuration but used
import-time `_EG_*` values as fallbacks. If a process imported a setting of 20 and
the current configuration subsequently removed it, the captured input retained 20
instead of the source default 25.

The acquisition now resolves its effective settings against the six source defaults:
25, 80, 62, 30, 2 and -10 for the existing respective entry thresholds. Explicit
invalid values still fail conversion. Unbound legacy calculations continue using
their import-time globals; this change does not silently make that path dynamic.
A regression executes the literal prior acquisition and demonstrates the old 20
versus the corrected 25 with the same current empty setting.

## Fusion and volatility coherence

The optional `SectorDocumentContext.fusion_macro_beta_table` selects the captured
source path. The composer derives Central's actual lookup keys from the computed
cycle spine and uses the exact normalized risk calibration supplied to that cycle
calculation. It refuses a simultaneous populated manual calibration map. Existing
explicit-map callers remain compatible; the future complete capture adapter must
select the captured-table path.

The real-engine composer fixture produces byte-identical five-document output
through this new derivation when given the same values. No second cycle calculation
or replacement sizing formula is introduced.

Volatility sizing must receive `overlay_gate=` explicitly, even when its snapshot
is unavailable. Use the same captured gate for sizing and `regime_caution_scored`.
An older nonempty site snapshot still wins over a newer regime mirror, and
`available: false` still prevents sizing rather than selecting the mirror.
These are the existing owner semantics.

## Verification

The two focused new suites passed **97 tests**. The final 13-suite affected run
passed **447 tests**, with **two existing Narrative real-cache smoke tests skipped**
because regional and real price caches are unavailable in this workspace. Their
exact skip reasons were read back separately. Earlier earnings/concentration
qualification passed 110 tests; counts overlap.

Literal prior owner functions are retained in seven fixtures. Their function hashes
are verified against the exact base commit. Tests cover malformed calibration cells,
independent beta/risk defaults, source-priority edge cases, invalid settings,
resolved absence, no ambient loaders, cache nonmutation, original acquisition order,
the real composition path and ambiguous-source refusal.

[Exact source hashes, commands and receipts](SECTOR_AUXILIARY_VALUE_PROJECTIONS_SOURCE_REVIEW_2026-11-06.json).

Remaining: bounded actual auxiliary source capture, protected sponsor holdings,
complete composition-input binding, resolved MarketState/alpha provenance, updater
barrier implementation and first-adoption proof, CI/release, application/native
binding and authenticated beta generation acceptance. No runtime activation is claimed.
