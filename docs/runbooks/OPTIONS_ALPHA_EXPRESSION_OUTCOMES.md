# Exact-expression research outcomes through the campaign owner

The incumbent `engine.options_signal_campaign.run` accepts an optional sequence
of native `ExpressionOutcomeEvidence` objects. This is an explicit local input
interface, not a runtime capture path or a receipt of source admission. Its
ordinary nightly lane, lock, original ledger paths, immutable appends and
checkpoint-last writes remain the only write owner. No caller is wired into the
scheduler and no real ledger is changed by preparing this source.

Each input must contain the exact private publisher readback, the caller's actual
OA-3 `ExpressionReceipt`, independent entry and exit `QuoteEvidence`, and the
actual observation clock. The composition does not create these receipts, set a
selection fence, select quotes or borrow candidate availability. It resolves the
original expression bytes and its first publication commitment through the
existing sealed local state. Missing original intent bytes, missing explicit
contract terms, a wrong candidate/campaign revision, pending evidence and invalid
causal clocks refuse preparation before any append.

The unchanged OA-3 evaluator supplies the exact-option math. A terminal record is
stored as `options.signal_campaign_expression_outcome/v1` in the EXISTING
`data/options_signal_campaign/outcomes.jsonl`. Its semantic key is the explicit
namespace `exact_option_expression` plus expression ID, frozen OA-3 policy SHA256
and `h60`. Legacy rows retain their original `(campaign_revision_id, horizon)`
keys. No existing stock-anchored option-unavailable block is rewritten, and no
second outcome ledger or quote store is introduced.

A mixed physical ledger uses `options.signal_campaign_checkpoint/v3`, recording
both namespaces, physical populations and the native correction binding. Pure
legacy histories keep their existing v1/v2 checkpoint bytes. After an interrupted
append, the owner verifies the old checkpoint's recorded physical prefixes and
validates the tail, then seals the same immutable rows. A replay with identical
input is a no-op; different bytes for an occupied expression key refuse.

The existing correction policy and its exact activation receipt continue to gate
any history covered by that policy, including v3 continuation. This source does
not activate that correction or satisfy the separate #9677 review boundary.
Quarantine bytes, physical ordinals, row hashes and occupied underlying keys are
preserved. Expression outcomes cannot enter or replace the old quarantine.

The private `read_expression_outcomes` consumer rebuilds the incumbent effective
view from its original raw snapshot and actual correction receipt, then returns
only validated expression rows with original physical identities that were
observed by the consumer's explicit observation clock. It never exposes future
outcome observations to an earlier consumer clock. The legacy v2
candidate enrichment continues joining underlying outcomes only. Neither path
turns an expression commitment into public expression distribution.

All authorities remain literal false, `training_eligible` remains false, and
records explicitly declare `local_retained_evidence_not_source_admission`.
Fixture clocks, synthetic terms and synthetic quote receipts prove composition,
not a natural prospective lifecycle. Production readiness still requires lawful
positive per-series terms evidence, actual prospective selection/admission,
original publisher availability, permitted retained quotes and the existing
campaign/runtime correction gates. Historical quote reharvesting cannot replace
these obligations.
