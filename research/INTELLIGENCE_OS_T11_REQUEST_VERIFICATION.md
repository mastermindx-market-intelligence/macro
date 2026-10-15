# T11 — request-scoped native numeric verification

The existing `engine/neuralweb/response_eval.py` accepts an explicit, ephemeral
`native_source_context` in `score_response`. The context contains the receipt,
request and source-request IDs, admitted symbol, and subscriber resolver envelopes
from that same request. It is never inferred from a persisted response-log row.
The caller owns actual request correlation, symbol admission and subscriber rights;
matching caller-supplied IDs is a consistency check, not authentication or a grant.

`verify_native_numeric_response` compares the canonical native answer and receipt
with those source envelopes. It reuses the existing semantic fingerprint,
subscriber packet projection and native renderer. The supported subset is one to
twelve available, finite numeric security fields. Unknown, unavailable, blocked,
non-numeric or malformed evidence remains `not_assessed`. Observed disagreements
are `mismatch`. Duplicate, missing or extra fields/clauses and added narrative
cannot earn a successful exact native-answer verification. Entity, unit, clocks,
source and field identity remain distinct even when two values happen to agree.
No tolerance, historical reconstruction or arbitrary prose parser is introduced.

The result contains only status, reason, checked count and field/fingerprint
references. It is internal QA telemetry. It grants no evaluation tier, public
badge, financial authority or historical access. No value cache, registry, rights
policy, rubric or failure taxonomy is added. The source context is not passed to
the model judge or returned in the verification result.

When the caller explicitly requests this check, `score_response.passed` requires
both the existing quality conditions and a `verified` source result. An LLM score
cannot override a mismatch or missing source assessment. Calls without explicit
source context retain their existing behavior; the numeric result is a separate
field and does not change the judge's score or frozen rubric axes.

This is a bounded source composition, not completion of T11. The normal production
caller still needs to pass genuine same-request resolver output, and installed
execution must be qualified after lawful release. General model narratives remain
outside the exact native renderer subset. The earlier authenticated native browser
observation demonstrates one real receipt/answer path; it does not independently
bind installed source or supply historical values to this checker. A1 still has no
admitted numeric input and must preserve that explicit gap.
