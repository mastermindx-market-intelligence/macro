# X0a transaction-reconciliation gold fixtures (SPEC_X0 §4)

Every file here is a **hand-built adjudicated-gold record**, not extracted filing
text and not a fabricated filing. Each observation and each binding carries
`origin: adjudicated_gold` with a `decided_at`, which is what SPEC_X0 §2/§3 admit
for an owner decision over retained bytes; nothing here claims
`canonical_extraction`, and no file pretends to be SEC document text.

The deterministic extractor that produces `canonical_extraction` observations
from retained filing bytes is X0b (SPEC_X0 §10), a later lane.

Shape: `paths` are the registration-path facts X0a reads (`path_id`,
`registration.file_number`, `origin.sec_accepted_at`); `observations` and
`coverage` are named records; each entry of `cases` names the records it uses, an
`as_of`, and the `expected` exact values the test asserts. Every amount is an
exact decimal string in USD — there is no float anywhere in these files.
