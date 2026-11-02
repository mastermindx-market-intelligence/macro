# OA-3 retained exact-option evaluation

The offline command consumes two already-retained quote responses and an original
expression receipt through the frozen OA-3 ruler. It performs no quote collection,
activation, publication, ledger append, training admission or trading. It emits the
existing `options.oa3_exact_option_outcome_fixture/v1` record to stdout.

```sh
python3 scripts/evaluate_options_alpha_exact_option_outcome.py --input /private/oa3/input.json
```

The input is a local handoff document with exactly `expression`, `entry` and `exit`.
The expression has `raw_path` and `upstream_digest_sha256`. Each quote role has:

```text
contract, boundary_at, query_end_at, query, raw_path, endpoint,
request_started_at, response_observed_at, retrieval_observed_at, computed_at
```

`raw_path` identifies the original response bytes relative to the input document's
directory. Absolute paths, parent traversal and symlink escapes are refused. Keep the
input and source responses host-private. The command reads bounded regular files;
it never rewrites the source. It accepts whitespace variations without replacing
raw-byte hashes with hashes of reserialized JSON.

The caller supplies the upstream expression digest, exact query, endpoint and all
source clocks from existing retained evidence. Every clock must include a timezone.
The command does not create missing receipts, compute an upstream digest, infer a
clock from file modification time or use the current time as source availability.
Both quote captures are required. If one does not yet exist, wait for the existing
producer to retain it; do not manufacture an empty response to obtain `pending`.
A real captured empty JSON array or malformed response remains evidence for the evaluator's
explicit unavailable path.

A syntactically valid handoff is not authentication of the producer or independent
proof of its asserted clocks. The evaluator checks immutable expression identity,
upstream digest, exact query windows, source-byte bindings and clock causality.
Economic rules, fixed fees, maturity states and authority flags come from the
existing evaluator; the wrapper adds no eligibility rule or outcome status.

An evaluated result exits zero even when its status is `pending`, `unavailable`,
`invalid` or `excluded`. A malformed handoff exits two with no result on stdout.
Use the returned status and authority flags rather than interpreting process
success as scientific acceptance.

## Remaining real-path gate

This command closes the local retained-evidence consumer gap. It does not prove
that a real expression was selected prospectively or that a natural entry/exit
lifecycle has been captured. The preregistration still requires an accepted active
expression-selection contract, a durable OA-3 activation receipt, and an expression
first formed after both forward fences. Pre-fence data can diagnose the code path
but cannot be promoted into prospective research outcomes.

The remaining end-to-end path is the existing producer's frozen expression, actual
entry ask or explicit source unavailability, H+60 maturation, actual exit bid or
explicit unavailability, immutable outcome under the existing owner, and a current
consumer. Retain source-event, decision, availability, request, response, retrieval,
computation and publication clocks separately. Do not import the competitor cohort's
identity, registry, coverage or 600-second live-availability rule into OA-3.

The controlling ruler and forward fence remain in
[the OA-3 preregistration](../../research/options_estate/OPTIONS_ALPHA_EXACT_OPTION_OUTCOME_PREREG_2026-09-19.md).
