# Foundation independent review: narrow source remediation

The original independent Fabric reviewer examined Macro PR #10055 at exact
head `e05fbe3cad8d6f314d2b4f7a108571724222726e` and returned
**CHANGES_REQUESTED**. The result was consumed and accepted as a *review
artifact* under original run
`market-navigator-review-e05fbe3-20261022`, digest
`fe88daa25b9ada22b1722cecfe9cfecc010a602fd6a1aa6ede226645b91695c3`.
This does not accept the code, close a protected review gate or authorize release.

The two actionable findings were repaired on the *original parent branch*:

1. **F1, material CI closure**: the exclusive Navigator job did not select
   changes limited to `tests/fixtures/market_navigator/*.synthetic.json`,
   despite the memory and CLI tests reading those files. Added the precise
   `tests/fixtures/market_navigator/**` path to the existing job only;
   no CI job, account, bypass, packing limit or ordinary-change ceiling
   was added or raised. Added an executable fixture-only selected-job
   assertion and counterexamples against the unrelated packing probes.
2. **F2, immutable authority flags**: a mutable shared `AUTHORITY` dict
   could be changed in-process before both composition and its projection
   equality check. The one process-wide constant is now
   `MappingProxyType` and the test asserts direct tampering is refused
   and every resulting public authority flag remains strictly false.

The reviewer also found lower-priority integration hardening questions:
the unbound production source-verifier contract, control characters in
internal source references, future-unavailable existence metadata and
synthetic screenshot repository size. These remain explicit, not
unjustifiably called solved. No Navigator live endpoint is wired and
`production_binding_proven` is still false.

Review reuse: any modified foundation head needs **new** semantic review.
The old result is not reused as approval. The pilot ci-authority context
was red at the original head; green unit/CI packs cannot override it.

Local test caveat: `test_curated_exclusivity_drops_only_the_opaque_fallback_tier`
raised a separate `ci-control-plane-contracts` owned-path discrepancy
on a sparse checkout; its failing selectors are unrelated to
`tests/fixtures/market_navigator` or `AUTHORITY`. Preserve the
failure as observed, not as an accepted baseline or a reason to loosen
job ceilings. Exact-hosted checks still govern integration.
