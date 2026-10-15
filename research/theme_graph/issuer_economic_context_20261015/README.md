# Issuer-level native economic context — single-pass composition

This extends the accepted per-fact GMI projection (#9423) into an issuer entry
point. An authenticated host supplies an incumbent issuer ID, native owners,
read-only store factory, purpose and audience. No ticker-to-fact mapping, source
acquisition, identity allocator, relationship ranking, graph publisher or HTTP
endpoint is added.

## Reuse the existing native selector, not another authority

The original `read_issuer_selection` already reads and validates each selected
fact before returning reference metadata. Calling a per-fact reader afterward
would unnecessarily reread every artifact. The new
`read_issuer_disclosure_bundle` factors that EXISTING transaction into one native
implementation. It retains its request-local verified read results only after
all original selection, identity, source, revision-chain and final admission
checks succeed. The existing metadata-only response is constructed unchanged
from that same result. No external response gains a cached permission token.

The request-local bundle is not a credential or portable admission. Its
SelectionOwner and DisclosureAuthority are still injected trusted host
boundaries. Every invocation requalifies the actual owner; no graph-reference
string or caller-supplied dictionary is accepted in place of it.

The GMI consumer `read_issuer_economic_context` uses that one native bundle and
the same private renderer as `read_economic_context`. It opens the artifact
store at most once and reads each selected fact once, exactly as the original
metadata selector. All rows must have every required field granted BEFORE
constructing the store. Missing field permission is a consumer restriction,
never an additional grant. Existing metadata callers keep their original field
requirements and response schema.

## Result and failure behavior

`theme_graph.native_issuer_economic_context/v1` is a current subject/disclosing-
issuer view. Available results contain the native issuer binding, generation,
usage, selection-scoped coverage, and the existing per-fact context records.
The count refers only to that owner's current selection, not all company
relationships. A qualified empty selection is available with an empty list and
requires no artifact store; an unavailable selection is a typed refusal.

A revoked grant, changed selection/generation, missing identity attestation,
corrupt later fact, failed last admission recheck, or invalid field grant returns
`context: null` for the WHOLE issuer result. No partial earlier positive, fact
reference, requested identity, raw source or exception string is returned.
The store-factory failure is sanitized without retry. The original native
sixteen-selection bound and deterministic ordering remain unchanged.

Subject and object, planned product/platform scope, source publication date and
nullable instant, edition-known and fact-known clocks, native generation and
qualified audience/purpose remain intact. No supplier relation, fulfilled
shipment, present plan, economic share, prediction or trading authority is
inferred. No historical/counterparty/ticker query is manufactured.

## Tests and compatibility

The tests use actual native validation and read code over synthetic state. They
also use CurrentDisclosureOwner and ReadOnlyLocalObjects through the existing
isolated test publication harness. No live C01 generation is read or republished.

Single- and two-fact call counters match the existing metadata reader; each
fact is read exactly once. Multi-row tests prove that a missing grant on a later
row blocks ALL artifact I/O and late revocation or corruption suppresses the
entire issuer response. The exact old metadata response and all existing HTTP
API regressions are retained. Four in-memory fault injections check the new
field gate, final selection check, final admission check and duplicate reads.
The original per-fact mutation controls remain applicable to its fact renderer.

## Source and ownership

Parent source: #9423 at a474d289db007117d12e32f421ae7c46bcc163e8. This is a
stacked source increment on `gmi-issuer-economic-context-20261015-sol-001`.
It does not edit the parent controller-owned workspace. All native classes,
owner validation, permissions, publication and identities remain with Company
Intelligence; GMI owns the consumer view. No API, source cache or deployment
files are modified. The active F04 cache PR#9216 has disjoint implementation
paths. Native-owner review/adoption and ordinary CI/release remain required.

The original F04/E20 source/runtime/API/Terminal work and effect uncertainties
are not retried or transferred. C01 generation040b stays immutable. The blocked
ownership-release#8793 is unaffected. This increment cannot be called a live
user journey until its existing host consumer is installed and proven.

## Executed acceptance and release dependency

575 native cases passed, including51 new issuer-context tests. All90 existing
private disclosure HTTP API cases passed separately (five existing framework
deprecation warnings). Two CI scope checks passed. Four new and four existing
per-fact fault controls were detected. No source or test body is changed by
fault injection. Exact native validation/gate order and legacy response AST
are preserved; the per-fact renderer AST is also conserved.

Measured one-fact and two-fact runs use exactly the same owner calls, admission
checks, artifact reads and one store construction as the old metadata reader,
with zero read-time writes. This is I/O-count parity, not a production latency
claim or proof that the existing EdgeOne timeout is repaired.

This source PR is stacked on #9423. The existing workflow intentionally runs
PR checks only for main, so the stacked review has local proof only until its
parent lands and the child is retargeted through the ordinary source process.
No workflow filter is changed and no missing hosted check is called a pass.
