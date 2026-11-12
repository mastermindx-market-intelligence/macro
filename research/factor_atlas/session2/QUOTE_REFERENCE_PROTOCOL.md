# Session 2 — Quote-reference microstructure protocol (research-only)

**State:** controlled-fixture implementation, no qualified equity print/quote source, no provider traffic, no production signing replacement, no customer signal or actionable trade authority.

## Why this exists

LIQN-style one-minute BVC infers a buyer fraction from prices, volume and a fitted empirical scale. Its sign is not an observed aggressor classification or institutional allocation flow. This finite offline comparator is a separate *reference estimate* against which to evaluate BVC on a genuinely licensed and owner-admitted synchronized tape. It must never be described as an exchange aggressor flag.

Canonical sign/calibration implementation remains Macro `engine/flow_signing.py` (Git blob `bc012baeeeedda73d90d15521c63df3853202f11`). This module does not alter that owner, the options signing gate, source capture, any provider client or the Options Superintelligence platform. Six ordinary-price scalar cases are checked against the incumbent quote-rule primitive. They test equivalence of the basic midpoint method, not actual signing accuracy.

## Pure interface

`prototype/quote_reference.py` exports `TapeTrade`, `TapeQuote`, `QuotePolicy`, `TapeDetail`, `TapeResult`, and `classify_tape(trades, quotes, policy, cutoff_ns, mode)`. Inputs are **already** condition/correction/rights/basis qualified and source-clock-received by the incumbent owner; the interface only checks structural contradictions. Caller-supplied strings cannot confer source rights or historical availability.

Trade and quote prices, quote sizes and **decimal_size** are decimal strings. Accounting uses `Decimal`, not integer `size` or binary-float notional. SIP timestamps and owner first-seen clocks remain integer **UTC nanoseconds**. A quote is usable only when `quote.sip_ns < trade.sip_ns`, the clocks, security, ET date, phase and basis agree, both observations are known at the evaluation cutoff, the stated quote age is not exceeded, and the quote has valid positive bid/ask/size with bid < ask. Equal source-clock quotes are ambiguous; they do not silently fall back to a previous quote. A newest invalid/locked/crossed/stale quote also does not silently fall back to an older one. No newer quote is used by nearest-neighbor interpolation. Quote and trade sequence numbers are **not** treated as one common sequence.

For an eligible, quote-referenced print, a price above the midpoint is buyer-inferred; below is seller-inferred. Equality is UNKNOWN by default. Explicit `midpoint_policy='tick'` can use the strictly prior eligible same-session price change as an independently labeled fallback, without zero-tick carry; equal-time prints cannot supply a prior tick. All such signs are model references, not tape truth. A research-default maximum quote age of **1s** is not empirically established; 0.1s and 5s are preregisterable sensitivities.

TRF prints remain eligible **unsigned unknown** until execution/reporting-clock alignment is independently established. Unknown conditions, unresolved corrections and canceled prints are diagnostic observed gross **excluded from eligible gross**; they are not silently zeroed or treated as current executions. A genuinely later cancellation may require reconstructing earlier available and later corrected versions through the incumbent revision selector. This prototype makes no retrospective revision selection and rejects duplicate trade or quote identities.

## Accounting and interpretation

For source-qualified eligible observed prints:

    E = B + S + U
    signed_net_covered = B - S
    classified_share = (B + S) / E   (null when E=0)
    full_net_if_unknown_only = [B-S-U, B-S+U]

B and S are quote-/tick-inferred gross notionals; U includes every eligible unsigned print. The range only bounds **the observed eligible tape**, never unobserved prints, incomplete feeds or true institutional holdings. Separately emit `observed_gross = E + excluded_or_unqualified_gross` for source-diagnostic activity, not for a publishable eligible-turnover denominator.

For `as_observed`, no selected trade/quote may carry an availability time after cutoff, and a classified print's `known_at_ns` cannot precede either underlying receipt. For `corrected_history`, derived historical first-observed receipt must stay **null**, even when event geometry is reconstructable. No source segment/market-hours calendar or signed-pressure publication authority is inferred from input labels.

All `may_publish/may_rank/may_alert/may_size/may_trade` flags are false, regardless of computed signs or market-data entitlement. No customer raw tape, beneficial-owner identifier or new live ingestion may be emitted.

## Source and falsifier gates

The historical 2026-08-08 Massive entitlement probe and enterprise licensing record are not current capture/quote-age evidence. Before any actual tape comparison, S2-P1's incumbent Terminal/Macro source owners must establish source rights, availability, corrected trade conditions, quarter/venue/auction scope and source/reader clock semantics. Assess quote age, eligible notional coverage and compute/storage footprint on a **small admitted sample**; preserve a no-data/not-estimable result.

The primary falsifier remains that quote signing does not offer the needed coverage/accuracy/cost in the intended universe, or that BVC reproduces vendor mathematics but fails to recover the active side. Unknown/unsupported is an acceptable outcome. `test_quote_reference.py` covers source-clock and volume accounting, deliberately stale/equal/invalid quotes, correction/TRF exclusion, exact decimal size, midpoint/tick cases, future cutoff, DST-relevant ET session binding and non-authority. The native tests are **synthetic**, not an empirical reference-label validation.
