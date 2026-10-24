# Private conditional Plan consumer

`POST /api/options/plan/expiry` accepts only `options.plan_expiry_request/v1`:
`schema`, the existing `options_plan_draft.v1` `draft`, `spots` (1–1001 bounded
hypothetical expiry prices), and exact `payoff_basis` `{kind:
"hold_to_expiry_intrinsic", expiration: "YYYY-MM-DD"}`. The server derives the
incumbent six-field exact contract identity from each pin, validates the math
before acquisition, and never accepts source contexts, observations, endpoint
URLs, credentials, hashes, clocks or source grants from the caller.

The endpoint is explicitly private even though it is nested in the existing hub
router. `app.options_auth.resolve_entitled_options_principal` reuses the same
uncached configured Supabase authentication and billing read as the existing
Options use consumer. `_fresh_product_allowed` contains that existing predicate
once: `terminal_live_options`, unlimited tier, or the existing operator overlay.
Anonymous, missing/invalid subject, expired session, denied entitlement and billing
outage remain closed. No OptionUseRequest, matrix admission or rights receipt is
fabricated. Every explicit HTTP success/error uses private, no-store headers.

The source seam reuses RestProber's incumbent bounded selected-expiry profile
and BoundedRequestBudget(max_gets=1). It constructs one fixed-origin reference
list request for SPY/QQQ, one common expiry and the selected strike interval,
limit 100. It rejects pagination, redirect, oversize/malformed/failed response,
and stops the process's source lane after failure without a request/API reset.
It does not call the retired options snapshot route, retry, fall back to R2,
write source data, or create a registry/store/scheduler. A genuine list receipt
retains its actual query/path, response digest and capture clock. PR10146's
bridge uniquely selects each requested ticker from that original receipt.

`as_of` is the earlier of server New York calendar date and contractual expiry;
it selects reference semantics and never backdates the observation. Capture is
known-by, with historical first availability false. The response distinguishes
server-observed terms from caller-supplied discovery snapshots. A matched source
reference does not authenticate the DOI/Hot snapshot, prove a current listing,
provide an executable quote or prove a fill.

Activation uses ordinary `OPTIONS_PLAN_REFERENCE_ENABLED=1` runtime configuration
after actual source/access/budget qualification and the principal's independent
review of this auth boundary. It is disabled by default. No provider request or
runtime change occurred during source implementation/tests. Named-provider
commercial rights are already approved by Chairman attestation; this is not a
new licensing gate. Real endpoint denial, unsettled acquisition and human consent
remain on their original carriers. Production enrollment and Paper Plan journey
are separate from the source tests.

The output reuses `engine.options_payoff.expiry_payoff`, including authored side,
quantity and premium per unit, qualified ordinary SPY/QQQ terms, one root and one
expiry. It is a conditional intrinsic payoff over hypothetical underlying prices.
Early exercise, assignment and fees are excluded. It is not mark-to-market,
settlement/fixing, trading authority or an actual outcome. No Save implementation
is added; the Investigation owner keeps the unchanged Plan payload.
