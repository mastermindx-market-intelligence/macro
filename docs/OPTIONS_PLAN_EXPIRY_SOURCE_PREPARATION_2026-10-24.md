# Exact Plan expiry payoff and quote context — source preparation

Root `01a10340-ddc1-7e41-9b42-9c8543c28c3d`; bounded integration owner
`01a16c6c-f91e-7bd2-9b0e-734172a3dd7d`. Source-only, unmounted. No provider
request, entitlement check, runtime install, enrollment, database or retained Plan
write occurred. Existing W0b/Q02, Exposure/Theta writer and IW2 boundaries remain.

## Decision and consumer interface

`engine.options_plan_expiry.prepare_plan_draft_expiry(draft, contexts, spots,
known_by=...)` accepts the existing `options_plan_draft.v1` shape from Terminal
PR1166. The durable Plan owner still validates and stores the complete original
draft; this function does not create a persistence successor or modify that payload.
Ordered contexts must bind each pinned root/right/expiry/strike to the incumbent
exact OSI contract shape. Explicit conflicting pin terms or adjustment hints are
unpriced. Original nullable source clocks and stale state remain visible in
`source_pins`; neither receives a substitute observation clock. Snapshot row mid,
last, IV and quote context are never an entry assumption.

Each context contains `contract`, `reference_observation` and
`settlement_context`. The latter has exactly `contract`, `economic_expiry_at`,
`available_at`, `fixing_ref` and `fixing_basis=official_close`. It is a caller-owned
integration seam requiring an exact contract, offset-aware fixing instant and
content-bound authoritative source reference known by the supplied cutoff. It
does not issue or authenticate evidence. A valid-looking URL/hash does not prove
that a source was retrieved or that its fixing is correct. Actual consumer source
qualification remains required; all positive fixtures are controlled and synthetic.

The lower-level `prepare_expiry_payoff(legs, spots, known_by=...)` uses the existing
`massive_reference_terms` and `ordinary_etf_terms` interpretation only for standard
SPY/QQQ. It does not broaden the historical SPY identity service. Supported terms
are USD premium multiplier100, American, physical100 underlying shares, no reported
additional deliverables and no conflicting CFI. The policy interpretation and
source references are retained. Missing multiplier/deliverable evidence and
adjusted baskets remain unpriced, rather than using the engine's partial per-unit
output. An expiry date alone does not provide an exact fixing instant.

All legs require the same underlying, expiry date, actual fixing instant and
compatible fixing basis before `engine.options_payoff.expiry_payoff` runs. Mixed
expiry calendars and mixed roots cannot accidentally share a single spot curve.
No second pricing formula, BS model, Greek, rate or volatility is introduced.
Entry uses the existing `{kind:user_assumption,premium_per_unit,currency:USD}`
object, with separate buy/sell side and positive integer contract quantity. A
zero premium is valid. Missing entry withholds the whole curve. Output is a
conditional expiry intrinsic payoff, excluding unknown fees and early exercise;
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
It does not prevent authored-entry expiry payoff when actual terms/fixing qualify.

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

Affected checks: **92 passed in2.89s** using the existing B binding-venv Python:
`pytest -q --disable-warnings --basetemp=.pytest-plan-expiry
tests/test_options_plan_expiry.py tests/test_options_plan_quote_context.py
tests/test_options_payoff.py`. This includes incumbent payoff tests and new
economically discriminating long call, debit/credit vertical, unbounded short
call, explicit zero premium and all-leg withholding cases. Contract/fixing/pin
conflicts, missing entry/multiplier, adjusted cash/share baskets, unknown clocks,
old event vs new receive clock, delayed access and malformed bounded bytes are
covered. These tests are not provider, browser or mounted Plan proof.

Next real qualification is two separate obligations:

1. For an authored-entry curve, retain one genuine supported standard exact-series
   reference observation plus authoritative exact fixing/settlement binding known
   by the Plan cutoff. This source seam is currently unfilled by the source-only
   test fixtures. No open/realtime market is required for this calculation.
2. For current quote display/eligibility, the existing authorized source owner must
   qualify one genuinely unattempted exact snapshot capture and its access, event
   clock, product session and condition semantics. No such request was made here.

Root owns integration into the eventual Plan API/view, Paper parity and IW2 durable
save/reopen. There is no mounted UI, fake Save, new cloud store, service, queue,
producer or activation switch. Source acceptance does not clear any held effect.
Four failed Ryan/Qwen runs remain on their original carriers with no quality
verdict. The verified existing diagnostic owner is investigating; no fifth task,
forced pool or cooldown-based replacement was submitted for this slice.
