# Healthcare R10 — reconcile with the shared implementation, not a second build

**Author-side compatibility amendment and bounded review packet. Not independent acceptance, shared-owner approval, a worker commission, or a product release.**

Date: 24 September 2026. Operation: `gmi-healthcare-deep-research-20260923-sol-001`. Research carrier: Macro #7788, branch `claude/healthcare-theme-research-20260923`. R10 pickup: `dee08ae9e6edba7da3f4e43cd3ce5a3f59ffb862`. Protected procedure: Mastermind `6ffb3389635a5344df91765689acc48cf5499f60`, compatible Skillpack 1.0.1/bootstrap 1. Read-only main pin: `c52d80a1cc7a6d770e44c9f263c900b40895e930`.

## 1. User outcome and the material change

The Healthcare investor must be able to explain a development, identify the economic mechanism and evidenced participants, see the strongest counterevidence, and identify the next discriminating observation. This still belongs in the existing `state_of_themes.html` and `basket/obesity_glp1.html` journey. The full twelve-family roadmap remains intact. A current-evidence explanation is not an underpricing claim or trade instruction.

Since R9 was prepared, a real shared implementation carrier has appeared: **Macro #7870**, operation `gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001`. It is open/draft/unmerged at the inspected head `45eb37bbf832e007e67ce2594674d6bfeeb3b880`. Its schema, native assertion module, admission classifier and fresh rights-snapshot functions are present on that branch. This is implementation source, not deployed behavior. The existing shared owner reports the storage-column and basket-template custody gates as still held and private full-body admission as not implemented.

This invalidates only R9's assumption that the shared contract and rights entry points are wholly future work. It does not invalidate the Healthcare economics research, authorize copying the shared code, prove private admission, or supply independent Healthcare review.

**Disposition for the Healthcare research plan:** consume #7870's exact shared implementation after its acceptance. Replace R9's conflicting algorithm/interface examples with the requirements below. Do not create another assertion module, private publication selection, route, auth client or source-rights owner. Shared amendments remain requests to the existing owner.

## 2. Exact source evidence and its limits

| Reference | Inspected identity | What it establishes |
|---|---|---|
| Shared PR #7870 | head `45eb37bbf832e007e67ce2594674d6bfeeb3b880` | Existing implementation carrier and changed paths; not release acceptance. |
| `contracts/theme_graph/curation_assertion.v1.schema.json` | blob `ff3928f0c54aa164ef8283d9da45af67e6a0d971` | Closed assertion envelope, eight predicates, exact observation enums and optional industrial extension. |
| `engine/theme_graph/curation_assertion.py` | blob `23a25614782b8b1cb76ce7e3f292b64d35bfb4f6` | Native revision algorithm, mint/decode behavior, non-negative numerical rule and grain semantics. |
| `engine/theme_graph/rights.py` | blob `758937246e9a07ac150ba65123ebfa876bbc66c0` | `load_registry_snapshot` and `assert_current_emission_allowed` exist on the candidate branch. |
| #7773 comment `5808307684` | shared-owner response, 24 September | Current owner-described contract, route direction and unresolved private binding. |
| #7780 comment `5807772681` | R4 private-binding decision request | Candidate existing-Research-Vault prefix, public-reference proposal, unresolved bucket/entitlement checks. |
| R9 implementation plan | blob `f58970d627a6334905bd42fa5994a25a2b00956a` | Exact earlier proposal reviewed; all eight tasks and 48 inherited acceptance cases remain traceable. |

Immutable source prefix for the three code files: `https://github.com/mastermindx-market-intelligence/macro/blob/45eb37bbf832e007e67ce2594674d6bfeeb3b880/`.

Owner discussion: `https://github.com/mastermindx-market-intelligence/macro/pull/7773#issuecomment-5808307684` and `https://github.com/mastermindx-market-intelligence/macro/pull/7780#issuecomment-5807772681`.

Selected source content was read through GitHub. A container attempt to retrieve full raw copies failed DNS; it was not retried and is not a GitHub write failure. The local R10 audit evaluates the hash-matched R9 fixture against explicitly transcribed selected constraints. It does **not** execute the complete shared schema or native module. The shared owner's reported independent reviews concern that shared candidate, not this Healthcare package.

## 3. Precise R9 compatibility corrections

### C1 — one revision algorithm

R9 T03 Step 3 prepends `gmi-curation-v1` plus a null separator before hashing and excludes additional fields. The implemented shared module does neither: it canonicalizes the validated payload excluding only `curation_revision`, hashes those bytes with SHA-256, and takes the first 32 hex characters after `gmirca_`.

**Replacement:** remove the R9 local hash helper from the future task. Call the native `curation_revision`, `encode_assertion` and `source_ref_for` functions. Request metadata belongs outside the closed payload. Unknown fields must refuse rather than being silently omitted from identity. Local algorithm comparisons in the audit are illustrations, not minted canonical evidence.

### C2 — compare equivalent mint stages

R9 T03's test compares `decode_assertion(encode_assertion(first))` to a fixture with a null revision. The shared encode path stamps that fixture, so the records intentionally differ. Appendix A's warning does not repair the contradictory assertion in the test.

**Replacement test requirement:** begin with a schema-valid synthetic candidate; mint/decode; compare every field other than the stamp with the original candidate; assert the stamp equals the native revision; assert a second encode/decode of the stamped object is identical; assert a stale stamp after a content change refuses. Do not modify the shared mint path to accommodate the old test.

### C3 — six fixture incompatibilities are not six new upstream bugs

The exact R9 Appendix A fixture carries six values outside the inspected shared schema:

| R9 field | Candidate value | Shared rule |
|---|---|---|
| Root `economic_right` | present | Not an admitted property. |
| `predicate` | `REPORTED_ECONOMIC_RIGHT` | Not one of the eight admitted predicates. |
| `observation.quantity_basis` | null | Closed non-null basis vocabulary. |
| `observation.gross_net_basis` | `net_sales` | `gross`, `net` or null only. |
| `observation.estimate_status` | `not_disclosed` | `reported`, `estimated` or `target`. |
| `observation.precision` | `qualitative` | `integer`, `decimal`, `range` or `approximate`. |

**Replacement:** keep the fixture as a rejected, proposed Healthcare extension until the shared owner accepts a closed branch. Do not change a royalty assertion into an operating measure merely to pass. Do not turn undisclosed into zero, or label a nonexistent numerical measurement approximate. Keep the payment denominator (`net sales`) in the economic-right branch rather than repurposing gross/net basis.

Request one branch-aware representation for non-numerical assertions. The owner may select an optional typed non-numerical observation alternative or compatible additive fields. In either case, legacy quantitative Robotics fixtures must remain valid, unknown terms need reasons, and all producer/reader/test paths must agree. Both `REPORTED_ECONOMIC_RIGHT` and `REPORTED_SUPPLY_STATUS` remain proposed, not enrolled.

### C4 — signed economic changes must not relax physical counts

The shared code refuses negative `observation.value` and `value_high`. That is coherent for component counts but cannot carry a negative pricing contribution, negative cash flow or other signed financial measure.

Materials has already raised the shared signed/exact-measurement requirement. Healthcare should join that one amendment, not define another decimal grammar. It must retain sign, unit, scale, period, consolidation scope, percentage-versus-percentage-point basis, and exact source precision. Preserve the legacy non-negative physical-quantity branch. No conversion of a negative financial change into a positive magnitude without explicit direction, and no guessed numerical rate for qualitative royalties.

### C5 — use actual shared rights functions

R9's proposed `read_policy_snapshot` is not a reason to implement a duplicate. Consume `load_registry_snapshot(path=None)` and `assert_current_emission_allowed(families, *, snapshot)` from the shared owner. The returned revision identifies the bytes actually parsed. The API must construct that snapshot itself, derive required families from admitted evidence, and reject unresolved required-family lineage; a caller-selected empty family list is not proof that a sourced statement needs no rights check.

The inspected loader reads the file without a byte bound; R9's bounded-policy requirement is therefore an amendment/qualification obligation, not a capability already proved. Carry the pre-response policy-change check into the real route; function existence alone does not prove warm-service revocation, field/use permission, or complete source-family lineage.

### C6 — route and publication names belong to the existing shared owner

R9 proposes `GET /api/themes/{theme_id}/research/v1`. The shared owner identifies the intended common transport as `POST /api/themes/v1/research/query` and `POST /api/themes/v1/research/evidence`. The inspected changed-file list does not establish that those routes are implemented yet.

**Replacement:** adapt the Healthcare profile to the accepted shared request/response contract; do not add the R9 GET route or a Healthcare-specific parallel client. Preserve read-only semantics, entitlement before data access, `private, no-store`, safe errors, request cancellation/identity, and the existing page mounts. The route method itself grants no write or trade authority.

R9 T04's proposed `private_evidence.py` generation API is also not an instruction to create another publisher beside the pending shared R4 adapter. Consume its actual accepted reader/publication binding and freeze signatures only after that return. K1 must reference the true physical accessor and immutable native identity, not an invented pointer.

## 4. Private-binding recommendation and important qualifications

Healthcare supports R4's **existing private Research Vault** approach in principle: one GMI-owned adapter, existing private storage primitives, registered `theme_graph_private/v1/assertions/<revision>.json` prefix, and no relocation of the global data root. This is Healthcare design feedback, not a unilateral ruling on the Semiconductor execution grant, source-writer custody or live admission.

Three qualifications are essential.

**Source permission is not publication tier.** A family marked `direct_display_ok`, including house-authored material, does not automatically make the current full-fidelity paid product public. Preserve legacy public receipts. New public examples need a deliberate object/representation-level public designation in the existing publication policy. Detailed current Healthcare assertions and synthesis remain protected even when they are original house prose. Do not launder upstream restrictions through a house wrapper.

**A nonexistent object's 404 is not proof of private storage.** The acceptance target must bind a valid positive object/read receipt and its exact key, actual bucket identity, and the relevant control-plane public-access configuration. Negative anonymous tests use that same known-existing object on the configured public/custom-domain/mirror paths. A wrong host, missing key or absent candidate proves nothing about the intended protected object. Keep credentials and private body contents out of GitHub evidence.

**Entitlement grace needs an explicit consumer ruling.** R4 raises an existing positive entitlement grace. Its acceptable duration for this new protected class has not been decided here. The shared paywall owner must state the exact outage/grace/revocation policy and test it; a general purpose grace is not permission to ignore source-rights revocation. Do not create Healthcare authentication to solve this. Missing accepted policy keeps live admission/release held while independent source work can advance.

## 5. Adversarial preservation requirements

These are plan-level counterexamples, not newly demonstrated production bugs.

**Cross-domain preservation.** With one shared publication selection, a valid predecessor check can still promote a Healthcare-only candidate and omit Robotics or Semiconductor records. If the accepted shared publisher uses a manifest/selector, form the next eligible set from the exact prior generation plus explicit admitted changes; preserve unaffected entries. Omission is not withdrawal. If it instead uses immutable per-assertion lookup plus an incumbent owner selector, enforce preservation there. Do not build a new selector to satisfy the test.

**Exact replay is not a second publication.** After a successful or ambiguous publication, prove the same candidate and current selector/receipt on the original carrier before deciding the effect. An already-current identical candidate is a reconciled no-op; a stale different predecessor conflicts; an unreadable result remains unknown. No automatic key replacement or retry.

**The FDA cache needs transactional writer custody.** A temporary file and atomic rename prevent partial-file exposure, not a stale read-modify-write replacement. T02 must consume the existing single-writer/fencing mechanism and demonstrate that an older acquisition cannot replace a newer qualified generation or remove its history. The refresh outcome and chosen source generation must refer to the same serialization point. No additional lock service or history plane is authorized.

**Structural profiles must not contain the paid current thesis.** Public configuration may define the Healthcare facets, field labels and deterministic layout. It must not contain today's private assertions, copied detailed company reasoning or precompiled current evidence payload. Current reviewed narrative content is admitted through the same accepted owner/private path. Public code is not a publication workaround.

**Text-safe output is not URL-safe navigation.** `textContent` protects the text insertion context; citation links additionally need a restricted URL policy. Accept reviewed HTTPS source URLs or exact same-origin routes, not script/data schemes, scheme-relative URLs, embedded credentials or caller-selected internal storage keys. Reject unsafe links without losing the surrounding factual limitation. If the server fetches a source URL, use the incumbent source-admission/fetch policy, not browser-provided arbitrary network destinations. OWASP's XSS prevention guidance distinguishes URL attributes from ordinary text sinks.

**D1 cannot depend on unbuilt D4 tests.** R9 T08's aggregate test command lists future suites and says missing files are not skips. Apply that to the complete candidate, not every early release. D1 uses T01/T02 tests and their existing integration regressions; D2 adds T03–T05; D3 adds T06; D4 adds T07; T08 checks the applicable dependency-closed release and final union. Future cases stay NOT_EXECUTED and outside the earlier release claim. They are never called PASS or silently discarded.

## 6. Twelve additional intended acceptance cases

All cases below are **NOT_EXECUTED** product specifications. The 48 R9 cases remain preserved.

| ID | Task | Discriminating requirement |
|---|---|---|
| R10-A01 | T03 | Native shared hash and source-ref identity are used without a vertical prefix or field-stripping fork. |
| R10-A02 | T03 | Unstamped candidate, minted record and stale-stamp rejection are tested at equivalent stages. |
| R10-A03 | T03 | Qualitative royalties use the accepted closed non-numerical branch; no unknown-to-zero or enum coercion. |
| R10-A04 | T03/T06 | Signed financial changes survive the one shared measurement extension while negative physical counts remain refused. |
| R10-A05 | T04/T05 | Actual policy bytes, complete source-family lineage, bounded reads and warm request behavior are verified at the shared route. |
| R10-A06 | T04/T07 | A publication/correction retains unrelated verticals and treats identical already-current input as a reconciled no-op. |
| R10-A07 | T02 | Existing writer fencing prevents an older FDA sweep or refresh outcome from overwriting a newer qualified generation. |
| R10-A08 | T04/T05 | Upstream display permission cannot publish protected house-authored current content; approved entitlement behavior is separate. |
| R10-A09 | T04/T08 | Privacy proof uses an exact known-existing object and actual bucket/domain controls, not a meaningless absent-key response. |
| R10-A10 | T05/T06 | Unsafe citation URLs refuse; protected current narrative cannot enter public profile/configuration or persistent browser caches. |
| R10-A11 | T08 | Each early release runs its dependency-closed proof set; future unexecuted tests neither falsely pass nor administratively block D1. |
| R10-A12 | T03/T05 | Healthcare uses #7870's accepted shared module and common transport; no rival hash, private selector, route or client is added. |

The five-part user explanation and second non-metabolic witness remain acceptance targets. Private infrastructure by itself is not completion. Differences between clinical success, paid access, company retained economics and market expectations remain visible.

## 7. Review request and return contract

Send the bounded shared dependency request to #7870, referencing the existing R4 request on #7780 rather than originating another R4. Request disposition on the two Healthcare meanings, non-numerical and signed measures (jointly with Materials), actual transport/publisher/reader signatures, source-policy and audience separation, and cross-domain preservation. Ask for the exact accepted source revision or an explicit unresolved owner action. Do not claim silence or a comment receipt is acceptance.

A separate genuinely independent Healthcare review must evaluate R7–R9 plus this narrow amendment and the 60 intended cases. The reviewer should not repeat sector research or implement code. Return findings with severity, exact clause/line, a counterexample, minimal correction, and an explicit distinction among author recommendations, accepted shared source and unproved runtime behavior. A shared-code review alone is not independent Healthcare-package acceptance.

No reviewer is assigned by this document. Preferred bounded review avenue: CTO Sol, due to closed-schema compatibility, source/privacy, publication concurrency and cross-owner semantics. WHY NOT FABLE for that review: it is a fixed read-only package; scarce Fable responsibility remains shared architecture/integration and later build orchestration. Actual placement/admission must use the existing owner. No unbound OPEN_PICKUP, raw provider spawn or background claim.

## 8. Verification, limitations and next action

`audit_r10_plan.py` verifies the complete local R9 plan against its recorded Git blob, extracts only its literal synthetic fixture, and checks selected shared constraints. It reports six shape/enum mismatches plus hash, mint-stage and signed-value conflicts: nine compatibility observations. These are not nine shared-code defects. It also includes simple control and set-preservation illustrations. No native module, application test, live API, production cache or cloud store is executed.

The source excerpts and native hashes above provide inspectable evidence. Whole shared files were not independently copied/hash-verified locally; do not promote this selected-constraint audit into an exact-runtime test. The audit's candidate hashes are unadmitted research illustrations, not canonical source objects. No new clinical, company financial or investment-return claim is made in R10.

This amendment supersedes only the named R9 helper/interface examples, contradictory fixture expectations, publication assumption and release-proof interpretation. R1–R9 files remain recoverable and unchanged; the README points here before execution. The original 48 cases plus the twelve additions remain unexecuted. Shared acceptance and independent review remain pending until actual returns exist.

Next action after sending the bounded request: consume the shared owner's exact response, update only affected interfaces/acceptance mappings, then obtain independent Healthcare review and issue the mature Fable orchestration handoff. No product implementation, live admission, merge, deployment or trading effect follows automatically from this research result.

## Sources for general technical reasoning

- OWASP, Cross Site Scripting Prevention Cheat Sheet: `https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html` — text and URL contexts require different handling.
- Python `os.replace` documentation: `https://docs.python.org/3/library/os.html#os.replace` — atomic replacement is not a complete multiwriter read-modify-write contract.
- The actual source/custody evidence remains the pinned Macro files and discussion references above, not generic cloud documentation or a claim about deployed configuration.
