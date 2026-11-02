# Exact Plan expiry payoff and quote context — source preparation

Root `01a10340-ddc1-7e41-9b42-9c8543c28c3d`; bounded integration owner
`01a16c6c-f91e-7bd2-9b0e-734172a3dd7d`. Source-only, unmounted. No provider
request, entitlement check, runtime install, enrollment, database or retained Plan
write occurred. Existing W0b/Q02, Exposure/Theta writer and IW2 boundaries remain.

## Decision and consumer interface

`engine.options_plan_expiry.prepare_plan_draft_expiry(draft, contexts, spots,
known_by=..., payoff_basis=...)` accepts the existing `options_plan_draft.v1` shape from Terminal
PR1166. The durable Plan owner still validates and stores the complete original
draft; this function does not create a persistence successor or modify that payload.
Ordered contexts must bind each pinned root/right/expiry/strike to the incumbent
exact OSI contract shape. Explicit conflicting pin terms or adjustment hints are
unpriced. Original nullable source clocks and stale state remain visible in
`source_pins`; neither receives a substitute observation clock. Snapshot row mid,
last, IV and quote context are never an entry assumption.

Each ordered context contains exactly `contract` and `reference_observation`.
A genuine exact-single receipt or bounded same-root/expiry list receipt is supported.
The list path selects exactly one matching ticker from at most100 rows and calls
incumbent `massive_reference_terms(observation,root,contract=selected)`. Missing,
duplicate, foreign or inconsistent rows stay unpriced. Original list endpoint,
response digest, selection parameters and capture clock are never rewritten into
fictitious single-endpoint provenance.
The explicit top-level `payoff_basis` is exactly
`{kind:hold_to_expiry_intrinsic, expiration:YYYY-MM-DD}`. Supplied spot values are
hypothetical underlying prices at that contractual expiry. This is a conditional
model assumption, not an observed fixing, physical-exercise reconstruction or
realized outcome. Early exercise, assignment and fees are excluded. An actual
fixing/settlement basis, legacy settlement_context or unknown context field is
explicitly unsupported, never silently interpreted as this model.

The lower-level `prepare_expiry_payoff(legs, spots, known_by=..., payoff_basis=...)` uses the existing
`massive_reference_terms` and `ordinary_etf_terms` interpretation only for standard
SPY/QQQ. It does not broaden the historical SPY identity service. Supported terms
are USD premium multiplier100, American, physical100 underlying shares, no reported
additional deliverables and no conflicting CFI. The policy interpretation and
source references are retained. Missing multiplier/deliverable evidence and
adjusted baskets remain unpriced, rather than using the engine's partial per-unit
output. No fixing timestamp or observed price is required for this symbolic curve.

All legs require the same underlying and expiry date, equal to the explicit
conditional-model expiry, before `engine.options_payoff.expiry_payoff` runs. Mixed
expiry calendars and mixed roots cannot accidentally share a single spot curve.
No second pricing formula, BS model, Greek, rate or volatility is introduced.
Entry uses the existing `{kind:user_assumption,premium_per_unit,currency:USD}`
object, with separate buy/sell side and positive integer contract quantity. A
zero premium is valid. Missing entry withholds the whole curve. Output is a
conditional expiry intrinsic payoff, excluding unknown fees, early exercise and assignment;
entry is an assumption, not a fill. `max_loss` retains the incumbent engine's
signed worst outcome convention; `UNBOUNDED` remains a string sentinel.

## Quote context is separate

`engine.options_plan_quote_context.normalize_massive_plan_quote(raw_bytes,
contract=..., origin=..., path=..., observed_at=..., http_status=...)` decodes one
bounded exact-contract snapshot into labeled reference context. It binds the
origin/path, ticker, right, expiry and decimal strike; an inconsistent supplied
underlying is refused. It retains the raw-byte digest/length, decimal price
strings, nullable sizes/venues/condition codes, exact integer `last_updated`,
vendor timeframe and separately supplied observation clock. It does not relabel
snapshot time as SIP time, convert an unverified clock to UTC, or refresh the
event clock from receive time. Duplicate keys, nonfinite JSON, oversized bytes
and unbounded decimal expansions are refused or typed unavailable.

Absent quote access stays `NO_QUOTE`/`ACCESS_UNVERIFIED`; there is no day.close,
last_trade, midpoint or FMV fallback. Delayed stays delayed after fresh retrieval.
One-sided, zero price/size, missing size, locked and crossed states are explicit.
Source authentication, clock, session, firm conditions and current access are not
established by this decoder. `current_quote_eligible` therefore remains false.
It does not prevent authored-entry expiry payoff when actual terms qualify.

The official [Massive exact snapshot documentation](https://massive.com/docs/rest/options/snapshots/option-contract-snapshot)
documents optional quote access and delayed/realtime plan recency; that does not
verify our account access. Its sample exposes `last_updated` separately from
last-trade `sip_timestamp`, so this initial decoder preserves clock identity.
The [Massive contract reference](https://massive.com/docs/rest/options/contracts/contract-overview)
reports shares and optional extra underlyings; shares alone are not a universal
premium multiplier. The incumbent narrow policy also cites
[OCC ETF specifications](https://www.theocc.com/clearance-and-settlement/clearing/etf-options).
[Theta snapshot documentation](https://thetadata.net/docs/operations/option_snapshot_quote.html)
permits latest quotes from the last seven calendar days and prior-session values
outside market hours. A new Theta adapter is not added while its actual owner is
editing EOD acquisition. The existing W0b full-chain first-order vendor snapshot
is not a current NBBO reader and is untouched.

## Executed checks and exact next evidence

Affected checks: **68 affected new checks passed in 1.69s** after the conditional-model correction using the existing B binding-venv Python:
`pytest -q --disable-warnings --basetemp=.pytest-plan-expiry
tests/test_options_plan_expiry.py tests/test_options_plan_quote_context.py`. The unchanged incumbent payoff tests previously passed in the 92-check source run. New
economically discriminating long call, debit/credit vertical, unbounded short
call, explicit zero premium and all-leg withholding cases. Contract/model-basis/pin
conflicts, missing entry/multiplier, adjusted cash/share baskets, unknown clocks,
old event vs new receive clock, delayed access and malformed bounded bytes are
covered. These tests are not provider, browser or mounted Plan proof.

Next real qualification is two separate obligations:

1. For an authored-entry curve, retain one genuine supported standard exact-series
   reference observation known by the Plan cutoff, joined to the pin and explicit
   hold-to-expiry intrinsic basis. An observed official-close fixing is not a
   prerequisite for this model. Standard ETF exercise is American and physical
   delivery follows exercise; trading hours do not establish universal cash fixing.
   Actual exercise, assignment, fixing and realized outcome need separate evidence.
2. For current quote display/eligibility, the existing authorized source owner must
   qualify one genuinely unattempted exact snapshot capture and its access, event
   clock, product session and condition semantics. No such request was made here.

Root owns integration into the eventual Plan API/view, Paper parity and IW2 durable
save/reopen. There is no mounted UI, fake Save, new cloud store, service, queue,
producer or activation switch. Source acceptance does not clear any held effect.
Four failed Ryan/Qwen runs remain on their original carriers with no quality
verdict. The verified existing diagnostic owner is investigating; no fifth task,
forced pool or cooldown-based replacement was submitted for this slice.


## CI integration correction

The existing `flow-surface` payoff step now runs both new suites alongside
`tests/test_options_payoff.py`; no new job or pack was created. Its exclusive path
scope includes both modules/tests plus `engine/options_nbbo_cohort.py`. Existing
`engine/session_digest.py` and `lib/*` already cover the imported session/calendar
closure. The manifest loads 355 jobs and the affected flow-surface inferred closure
contains 1173 paths with zero uncovered paths. Every other manifest field is retained.

Root corrected the initial mandatory official-close/fixing seam before readiness.
That earlier design is superseded by the explicit conditional-model basis described
above; it is not a live source requirement. Existing engine math is unchanged.


The returned result exposes the actual supplied `known_by`, contract expiration
list and New York calendar-date relation. A date before the known-by date is
explicitly `EXPIRY_DATE_BEFORE_KNOWN_BY_DATE`; same-day data does not imply an exact
expiry instant. Historical first availability is not established by this bridge.
After adding this provenance, 42 expiry tests passed in 1.63s; unchanged quote tests
retain their accepted run above. A root-provided retained reference also composed
locally with an after-capture cutoff, while a prior historical cutoff withheld math.
Only compact provenance/result is retained outside Git; no paid payload is committed.


Consumer compatibility increment:52 affected expiry tests passed after adding exact
selection from genuine list receipts, including duplicate/missing/mismatched row,
foreign scope and oversized-list refusal. No acquisition or reader registration is
part of the bridge. Consumer API/source-reader owner retains the actual source grant.
