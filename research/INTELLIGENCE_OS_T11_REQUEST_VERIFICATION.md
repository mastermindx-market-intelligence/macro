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

The native executor now consumes its actual subscriber resolver output while the
request owns it. Both gateway modes supply the existing compiled-context request
ID, then use that same ID for the existing internal response log. The verifier
result stays on the internal execution object; it is absent from the public
receipt, chat response, stream events and persisted assistant-message metadata.
A verifier failure cannot change the already resolved answer or invoke a model.

The existing response-log writer accepts only the closed internal verdict shape.
It rejects a missing/false internal-only marker, malformed or unknown codes,
non-integer counts, excess/duplicate/malformed references and inconsistent success
claims. It does not normalize defective proof into success. Extra narrative,
source values and keys are dropped by explicit projection. The existing operator
log reader retains this field; no new persistence service or public badge is added.
A recorded verdict does not self-admit source context to the offline scorer.

This is a bounded source composition, not completion of T11. Installed execution
and actual same-request log consumption must be qualified after lawful release.
The twelve-file follow-on probe binds the direct caller/checker/log sources and
`app/deploy/update.sh`, but its two CLI observations do not establish live
numeric-verifier execution. After the normal updater installs the qualified
release, separately verify the installed updater copy and the actual
`macro-api.service` and `admin.service` processes. An installed source hash or an
admin PID alone does not prove that the native caller loaded the new source.
Correlate one actual native request with its internal log row and existing
operator-reader consumption. Follow the source-binding and observation procedure
in `research/evidence/eval-os-tier-query-20261014/release-probe/README.md`.
General model narratives remain outside the exact native renderer subset. The
earlier authenticated native browser observation demonstrates one real receipt/
answer path; it does not independently bind installed source or supply historical
values to this checker. A1 still has no admitted numeric input and must preserve
that explicit gap.
