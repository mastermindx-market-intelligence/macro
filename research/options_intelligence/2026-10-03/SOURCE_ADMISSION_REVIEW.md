# Independent B3/B5 source-admission reference review

**Verdict: PASS for the proposed synthetic research reference at the exact digests below.** No remaining blocking defect was found in this bounded review. This is not source certification, candidate admission, production integration, a schema migration or evidence of predictive efficacy.

Review operation: options-intelligence-deep-research-20261003-astra-001. Reviewer was separate from the reference author. Review began 2026-10-03 10:34:32 UTC. No production/provider/M2 action, new agent, application source change, PR mutation or external write occurred. The initial review wrote this document and temporary runner/receipts. A separately authorized reproducibility addition now preserves the runner as the offline research checker described below; author reference, fixtures and specification remain unchanged.

## Exact reviewed inputs

| Reviewed file | SHA-256 |
|---|---|
| [source-admission-reference.py](source-admission-reference.py) | c935d56729043c20692e6bc0bfddb9592cbde07328932d750fd36a945b72441c |
| [source-admission-fixtures.json](source-admission-fixtures.json) | 2e5fc497bb0ffb13625ae4661365ee0ce5252e7cae10a0f5b1468950f407b8eb |
| [SOURCE_ADMISSION_SPEC.md](SOURCE_ADMISSION_SPEC.md) | 3f1388a76ac438b83552dcd79eeb77c217d8a71ec4dc4d7ffdf8f973dbfff1f7 |

All three digests were rechecked at 2026-10-03 10:44:30 UTC.

The retained strict-v1 candidate schema was also inspected directly: SHA-256 **04f0d87772ab28e6b9fe6ecb15981132f6f6dbecb83deb9826bddfc9f1bc5290** at the previously retained #8310 source. Its root and candidate both have additionalProperties=false. That older schema is a compatibility boundary, not proof of the currently commissioned v2 design or deployment.

## Executed validation

- **73 literal author fixtures:** zero failed cases or assertions.
- **Ten forbidden mutations:** all killed; zero failures after restoring the original functions. This reproduces the author's final suite result rather than relying on its statement.
- **47 independent adversarial cases:** zero failures. The reviewer loaded the exact source bytes once, hashed those bytes, then executed that immutable in-memory snapshot; expected monetary values and acceptance outcomes were supplied independently. Every case also checked unchanged inputs and deterministic repeated output.
- **Six independent CLI cases:** a valid synthetic envelope exited 0; malformed JSON, duplicate keys, NaN, an extra envelope key and a non-object envelope each exited 2. All retained source_certified_accepted=false and emitted no stderr.
- The reviewed evaluate function performs no I/O. CLI operations read supplied JSON/fixture inputs and print results; no publisher, provider client, network operation, source write or candidate adapter exists in these files.

Reproduction of the shipped suite:

```bash
python -B source-admission-reference.py --self-test --mutation-check
```

Passing fixture or mutation counts do not establish completeness over all possible market inputs. Initial test-first development claims in the specification were not independently replayed against earlier author implementations.

## Findings fixed during this review

The initial 62-fixture implementation passed its suite but admitted the following counterexamples. They were reported promptly; the author supplied bounded repairs and literal regressions. The reviewer reran independent counterexamples against the final digests.

| Finding | Independent counterexample and original result | Final disposition |
|---|---|---|
| Producer classification could precede its inputs | Set the base producer_classified_at to 11:59:00Z, before the noon trade, or 12:00:00.075Z, before input availability at .100Z. Both acceptance booleans were true. | Refused. The classifier's whole-record and contract-reference dependencies must precede classification. Feature-only OI/Greek references may arrive later, before computation; a positive case preserves that legitimate ordering. |
| Malformed timezone offset was silently normalized | Quote timestamp 2026-10-02T13:38:59.500+00:99 normalized to the baseline quote instant and fully passed. | Refused before datetime parsing. A legal +01:30 representation of the same instant still passes; sub-millisecond precision is refused. |
| Sequence spelling bypassed economic identity | Two records with different record IDs, same contract/session, sequences 7 and 07 produced a complete USD 400 denominator and passed. Unicode digits also passed. | Canonical ASCII sequence syntax is required. Unqualified scope/syntax blocks cohort admission and leaves the complete economic denominator null; it cannot merely drop one quote and retain a falsely complete denominator. |
| Quote and contract-reference evidence were not fully bound | An explicitly different quote contract and an explicitly unretained contract-reference receipt each passed. | Same-contract quote binding and contract-reference retention are now required for their respective synthetic checks. Retained booleans remain assertions, not authenticated custody. |
| Incomplete category denominator needed its own refusal | An otherwise usable category proxy could omit an unqualified premium from its weighted subset. | The proxy claim now refuses an incomplete economic denominator. Raw known mass remains diagnostic and is not relabeled complete turnover. |

No author file was edited by the reviewer. The author also hardened typed/nonblank Greek and label identities; those were checked in the final review.

## Independent coverage and literal results

The separate review exercised the following checks beyond simply rerunning the author's harness:

| Area | Independent checks and result |
|---|---|
| Monetary arithmetic and observation versus inference | Baseline price 2 × contracts 2 × multiplier 50 = USD 200. Midpoint retains observed at-ask share 0, inside share 1, unknown sign and USD 200 unknown mass. An upper-half inside print has inferred positive USD 195; an outside print retains outside location and abstains from signing. |
| Unequal premiums and missingness | USD 200 with a qualified ask quote plus USD 600 missing quote yields source USD 800, covered USD 200, print coverage .5 and premium coverage .25. Conditional at-ask share remains 1 without becoming population coverage 1. An ask USD 200 plus bid USD 600 yields shares .25/.75 and signed premium −USD 400. |
| Unknown economic denominator | Invalid price, boolean quantity, deliverable mismatch, unresolved correction, duplicate economic identity, leading-zero sequence or mixed unknown sequence scope cannot fabricate a complete premium denominator. Null is preserved; known raw mass is separately labeled. |
| NBBO policy | Future/equal-time, stale-beyond-boundary, locked/crossed, zero-size and wrong-contract quotes are refused. Exactly 1,000 ms age remains admitted under the proposed inclusive synthetic policy. This does not validate that threshold or conditions for a real feed. |
| Classification, feature and consumer time | Inputs after classification, contract reference after classification, feature input after computation, publication after consumer, admission after candidate decision and revision mismatch are refused. Feature-only Greek availability between classification and computation passes. Reconstructed and real-unqualified inputs cannot claim the captured synthetic check. |
| Proxy and population boundaries | Honest category proxy remains separate from NBBO location; it cannot satisfy the measured claim. Unknown proxy premium is not hidden. A selected notable-event subset cannot be relabeled market-wide. |
| Artifact/date-only collision | Same date and metadata except row counts 69 versus 62 fail. Equal counts with a different revision also fail. An exact identity positive control passes. The parent's real metadata fixture is an identity-refusal witness, not an independently fetched or joined economic dataset. |
| Outcome independence | A zero label stays pending before actual availability and becomes available with value 0 at the boundary. Nontext label identity stays unavailable. A non-object outcome_reference is malformed research input and refuses the whole packet; a malformed label dictionary instead returns an unavailable outcome without admitting its value. This input-shape distinction should remain explicit when consuming the reference. |

The specification correctly states that captured_pit_eligible describes only the simulated receipt/clock portion. It may be true while another measurement rule refuses synthetic_contract_pass. These flags must not be collapsed into one production eligibility signal.

## Strict-v1 and implementation boundary

The reference emits a separate research evidence object, retains source fields by deep copy, and declares candidate_boundary=separate_evidence_reference_no_candidate_fields_appended. It does not modify or serialize the incumbent strict candidate schema. Nothing here permits adding options_context or the reference's NBBO/proxy fields directly to v1. Existing IDs, authority flags, publisher, event/correction owners and the separately commissioned v2 work remain authoritative.

The specification explicitly distinguishes synthetic condition tokens, sequence scope, receipt assertions and age policy from provider-qualified rules. Actual quote-arrival evidence, clock uncertainty, correction/cancel semantics, multiplier/deliverable transforms, OI availability, Greek numerical correctness and real immutable publication/consumer receipts remain owner qualification work. No numerical_accuracy_qualified or source_certified_accepted flag becomes true.

The reference is suitable as a reviewable contract example and regression packet for existing owners. It is not an adapter or deployable gate.

## Review evidence record

Temporary independent review artifacts, not production/source files:

| Artifact | SHA-256 |
|---|---|
| /tmp/source-admission-independent-review.py — independent 47-case runner | 3ad5c9d8340bb85a015c279da29e5ec181cdcaad9205c60e52d12deba96fe516 |
| /tmp/source-admission-independent-final.json — exact-source assertions and suite/mutation results | b11890f4d7dad3d62d9fc65f5cf5a9346858ff892d1225a26055171185d4c393 |
| /tmp/source-admission-independent-cli.json — six CLI receipts | 179dc2f4366a1883b5465c4a30eb49d3a12328fa679c64cdc6432967ec85e5f0 |

The independently constructed cases are grouped above with their literal controls and expected outcomes. They were not generated from evaluator outputs. Earlier failing probes were retained temporarily in /tmp/source-admission-independent-initial.json; their exact inputs and initial behavior are described in the fixed-findings table. Source/fixture bytes at evaluation were the digests in this document, not an unfixed earlier implementation.

## Portable reproducibility addition

The exact executed 47-case construction/assertion block is now preserved in [source-admission-independent-check.py](source-admission-independent-check.py), SHA-256 **50edc65b99f717c3ac872c3935b9e8d06bc20e1faa8018268f418a86b969f8a6**. The original temporary runner existed and was read directly; this is not a reconstruction from remembered results. Text equality verified that its 47-case block was retained unchanged (block SHA-256 **f8a744c7797fe164a883b44db7430c82156522df108cd1caf5ed46182823b5b8**).

The portable edition makes three explicit changes: locate inputs beside the checker instead of at an absolute workspace path; require the exact reviewed reference/fixture hashes before evaluation; and print all results to stdout instead of writing a temporary receipt. It also faithfully preserves the six CLI payloads and expected return values from the separately executed CLI snippet. Those CLI checks now call the same main/parser with in-memory stdin/stdout/argv, with restoration in finally, rather than launch subprocesses. This transport adaptation is disclosed; it is not represented as byte-identical to the original subprocess snippet.

Run from any directory with the three adjacent files retained:

```bash
python -B /path/to/options-research/source-admission-independent-check.py
```

The checker uses only Python's standard library, reads its two pinned local inputs, and executes the exact source snapshot in memory. It makes no network or external-process call, writes no file, and returns 1 on check failure. A source or fixture hash mismatch refuses before evaluation. This remains a research checker, not a production gate or adapter.

The preservation run exited **0**: **47/47 independent cases, 73/73 author fixtures, 10/10 mutations killed, zero post-restoration failures, and 6/6 CLI cases**. Captured stdout SHA-256 was **f192d33d2fe62adbc112302ad261d3722d0d890dae36f9cb24001f91c25ac3f2**; the shell redirected stdout to a temporary review receipt, and the checker itself performed no writes. The exact reference and fixture digests still match the table above. The PASS verdict is unchanged.

No blanket approval of production source, current owner liveness, historical capture, a natural data sample or market efficacy follows from this finite review.
