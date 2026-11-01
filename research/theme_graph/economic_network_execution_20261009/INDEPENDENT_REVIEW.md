# Independent review — GMI economic relationship candidate inspector

## Status and review scope

**Final recommendation: PASS — safe to merge the reviewed implementation and delivery additions at private candidate-utility scope.** All three original P2 findings were repaired and independently re-tested. The follow-up review of the README, source-case metadata, actual-CLI replay harness, appended regression, and uniquely named CI job found no additional blocker. This supersedes the initial REQUEST_CHANGES recommendation while preserving the original findings and evidence below. No production, Graph1, identity, rights, historical-system, or economic admission is assessed or granted by this review. Actual CI selection/hosted execution and the principal's pending execution-status/handoff documents remain outside this review's proof.

Review date: 2026-10-09 UTC. Reviewer route: independent, read-only adversarial review. The reviewer did not author or modify the candidate source, allocate a workspace, publish source, merge, or deploy anything. Only the requested review artifact is written locally. Review used Mastermind Craft common/reviewer methods and the parent-provided protected-procedure grounding. Independent protected-source bootstrap was not repeated; this does not authorize any modifying company action.

Bound source:

- Workspace: `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-execution-20261009-pro-001`.
- Operation: `gmi-economic-network-execution-20261009-pro-001`.
- Branch (parent-provided): `sol/web-gmi-economic-network-execution-20261009-pro-001`.
- Observed Git HEAD: `1f9fb63fec63aaaee17ec0094f4d319dc63d24a5`.
- Initial `engine/company_intelligence/relationship_candidates.py`: SHA-256 `77036bcf3ea30dd9863c509decb507488c806fc8b714cafe7e5c6c66507ebecd`, 380 lines, untracked.
- Initial `tests/test_company_relationship_candidates.py`: SHA-256 `8261f7c657123b3cfcddb50c4ca95f8784d8b765caeb071c1a06431d68c33c91`, 430 lines, untracked.
- **Final reviewed module:** `engine/company_intelligence/relationship_candidates.py`, SHA-256 `27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d`, 444 lines.
- Intermediate repair-reviewed tests: `tests/test_company_relationship_candidates.py`, SHA-256 `14442d220e166ee0a528fa8f5aed7cac1fd06a50fad38c7c6d8d6c4b1c77c07f`, 581 lines.
- **Final reviewed tests:** `tests/test_company_relationship_candidates.py`, SHA-256 `0a8c73d5e5b968fd3795fed1e08305597f9c254cc5702b9946b702b8f31bdbd4`, 599 lines. The original 581-line prefix was independently hashed and is byte-identical to the previously reviewed 106-test file.

Final delivery-addition hashes:

| Repository-relative file | SHA-256 |
| --- | --- |
| `research/theme_graph/economic_network_execution_20261009/README.md` | `6ed926db17bc3fe7c990ef105c1f65623c881b398a34c079294dd92b514d20d2` |
| `research/theme_graph/economic_network_execution_20261009/MICRON_SOURCE_CASE.json` | `dd72d31afce12ca727a171e6f635d7085c8c2d6bff6bea2750f9c29a04fe101b` |
| `research/theme_graph/economic_network_execution_20261009/replay_micron_witness.py` | `69da2f393711923be68f05b1da563dbbcb736761fa60a8bf5ea4aa6cbf9f1830` |
| `.github/ci/legacy-jobs.yml` | `55f0291487afaa5c7bb878f8151ada51056a6db1eec249bac9748f9fa59ee174` |

CI review covers the appended `company-relationship-candidates` definition; the manifest digest identifies its containing file and does not imply a new full review of incumbent jobs.

The useful scope is a manually supplied assertion plus original UTF-8 body and native flat receipt, yielding a current analyst inspection through Python or the CLI. The code expressly marks semantic adjudication as not performed and keeps every decision-authority axis false. It does not produce a relationship dataset or an economic graph.

## Original findings and verified resolutions

### P2 — Unauthenticated document annotations appear as source provenance

**Location:** initial module lines 277–281, together with validation at lines 111–123.

**Reproduction:** start with `make_candidate()` from the synthetic test module. Replace `candidate['document']['source_ref']` with an invented SEC-shaped URL and `published_date` with `1900-01-01`. Keep the source and native receipt unchanged. Call `inspect_candidate(candidate, source=SOURCE)`.

**Observed:** the result remains `INSPECTABLE`. `source_provenance` echoes the invented locator and date alongside the correctly replayed source-body hash. There is no field distinguishing unauthenticated document labels from matched supplied bytes. `NOT_ADMITTED` and semantic-adjudication disclaimers remain present, but neither specifically identifies the provenance annotations as unauthenticated.

**Consequence:** a downstream analyst or consumer can read an issuer or SEC URL and publication label as established provenance when the utility has only proved consistency against a supplied body.

**Smallest adequate repair:** explicitly identify locator, date, version, and document identifier as untrusted caller annotations; independently state that the hash matched the supplied body. Do not claim issuer authentication or fetched-URL binding. This bounded repair has been accepted by the principal.

**RESOLVED:** final module lines 190–199 and 340–347 add result-wide annotation trust and explicit provenance markers. The original fake-locator/date/version reproduction remains inspectable as manual input, with `metadata_authenticity=caller_supplied_not_authenticated`, `source_hash_status=matched_supplied_bytes`, and `source_credibility=not_verified`. The response no longer implies that supplied-body consistency authenticates the document labels. Native regression: `test_fake_sec_metadata_is_echoed_untrusted_despite_body_hash_match`.

### P2 — Default support-field omission is not a guarantee of no source prose

**Location:** initial module lines 292–300; CLI flag/help at lines 347–349.

**Reproduction:** start with `make_candidate()`. Set `candidate['assertion']['product_scope'] = candidate['receipt']['value_text']`. Call `inspect_candidate(candidate, source=SOURCE)` without enabling support text.

**Observed:** the complete synthetic supporting sentence appears in `current_candidate_view.assertion.product_scope`. The dedicated `support.replayed_value_text` field is absent. The result remains `INSPECTABLE`.

**Consequence:** the interface cannot promise quote-free output merely because the support-text option is false. Caller annotations may themselves contain source prose; the same issue can occur in document or identity annotations.

**Smallest adequate repair for this private utility:** state the actual guarantee in machine-readable output, docstring, and CLI help: the option controls the machine-replayed support field; caller annotations are echoed and may contain prose. Explicitly retain that neither form authorizes public export, retention, training, or any other rights. A brittle sentence detector is not required and would not establish rights. The principal accepted this scope clarification, which is adequate if consistently reflected in output and tests.

**RESOLVED by the accepted interface clarification:** final module lines 8–12, 190–200, 317–325, 356–358, and 410–414 make the content boundary explicit. In both original sentence-in-scope reproductions, `quote_free_payload` and `public_safe_payload` are `NOT_CERTIFIED`, and `public_export` is `NOT_AUTHORIZED`. The dedicated support marker accurately reads `OMITTED` by default and `INCLUDED` with the opt-in. Manual, document, and identity annotations are explicitly unauthenticated. Independent API probes and the CLI regression verified that the sentence is still echoed with these truthful labels. This is a private inspection contract, not a content-sanitization or rights-grant mechanism.

### P2 — Malformed required temporal fields pass as-of inspection

**Location:** initial module lines 235–242, before `as_of_filter` at line 245.

**Reproduction:** use `with_temporal()` and the corresponding `synthetic_registry(profile)` from the synthetic test module; preserve candidate/document/version/source-hash bindings and valid required instant clocks. Inspect at `2024-02-27T00:00:00Z`. Each of these independently returns `INSPECTABLE`:

| Profile | Malformed supplied values |
| --- | --- |
| `BARS` | `period_start=[]`, `period_end=False` |
| `REVISABLE_RELEASE` | `period_end={}`, `revision_seq=False` |
| `INTELLIGENCE` | valid `computed_at` and `served_at`, with `code_version=False`, `input_cutoffs=False`, `data_cutoff_at=False`, `expires_at=False` |

**Observed:** the required-field check only excludes `None`. Interval-clock fields are exempt from `utc()` and receive no structural validation. The native filter checks `known_at`, so these malformed fields reach an as-of semantic view.

**Consequence:** presence of an arbitrary JSON value is treated as fulfillment of a required native-profile obligation. This is distinct from the acknowledged lack of authenticated history. No authority is granted, but the claimed structural temporal eligibility is overstated.

**Smallest adequate repair identified in the initial review:** reject invalid required-field shapes before constructing the relation view, preferably through an existing native row validator. Preserve valid DATE/interval labels as labels without inventing timezone-bearing instants. Do not introduce a competing temporal profile owner.

**RESOLVED:** final module lines 218–225, 232, and 253–292 explicitly describe and implement a bounded supplied-row input probe. No existing native row-shape validator or actual alternate `input_cutoffs` representation surfaced in the bounded owner-code search. The wrapper therefore checks exact nonnegative integer revision sequences, nonempty string code versions, nonempty named-input maps with native valid instant cutoffs, native valid cutoff/expiry instants, and valid ISO DATE or offset-bearing interval labels. Other native row formats remain the responsibility of their owning readers.

The three original malformed profile cases now return `REFUSED` with no view: BARS uses `AS_OF_INTERVAL_LABEL_INVALID`; REVISABLE_RELEASE and INTELLIGENCE use `AS_OF_REQUIRED_FIELD_INVALID`. A reviewer-installed in-memory replay sentinel was called **zero times** across those cases and the malformed DERIVED case, proving these refusals precede semantic receipt replay. Inputs remained unchanged. Native `assert_pit_readable` runs before the narrower row checks, so DERIVED still returns `NATIVE_TEMPORAL_REFUSAL`. Valid DATE and offset-bearing interval labels remain unchanged and inspectable.

## Independent repair validation

The full repaired candidate suite was independently run with the same bounded command shown below. **Observed result: exit 0; 106 passed, 8 warnings in 2.43 seconds; stderr empty.** The warnings remain the same unrelated old pytest temporary-directory cleanup warnings. The additional tests cover the exact provenance/prose reproductions, malformed required temporal fields, valid interval preservation, supported cutoff maps, and native DERIVED refusal ordering.

The final real Micron CLI was also re-run in both current and historical modes. Current inspection returned exit 0 and `INSPECTABLE`, with explicit untrusted metadata and matched-supplied-bytes markers. The historical cutoff again returned exit 2 and `AS_OF_REGISTRY_REQUIRED`, with relation, support, and provenance all null. Both retained `NOT_ADMITTED`, all decision-authority axes false, `graph1_projection=null`, and the explicit content-boundary labels. No original source body was printed or copied into this report.

## Final delivery-addition review

**Recommendation: PASS; no new findings.** Native source files remained read-only throughout this follow-up. No Git command or `run_ci_pack --execute` was used.

### README and source-case metadata

The README accurately distinguishes structural replay from semantic adjudication, caller metadata from source authenticity, supplied-row cutoff inspection from historical system replay, and dedicated support omission from source rights. It explicitly states that display, redistribution, retention, embedding, training, and evaluation rights are not granted. It also describes exact-capture dependence and refuses silent hash refresh when the public URL later changes.

The case JSON contains the source URL, retrieval instant, date-only publication label, hashes, byte/character addresses, concise manual assertion, and false admission/replay flags. It contains no source body or receipt passage. Its coordinates and hashes match the private witness already replayed during the core review. The reviewer did not independently recreate the original HTTP retrieval; the recorded retrieval metadata is a supplied research receipt, not authentication supplied by the inspector.

### Actual-CLI harness and changed-capture refusal

The 119-line harness was read in full. It pins its repository root from its own file path, reads at most the native source limit plus one byte, checks the complete body digest and length before constructing a receipt, verifies UTF-8 round-trip and the native span address/hash, and invokes the actual module CLI with argument arrays. It makes no network request, registry modification, publication call, or admission decision. Temporary candidate material is scoped to a temporary directory.

The positive harness was independently executed from `/private/tmp` with the original private Micron source. **Observed:** exit 0, empty stderr, harness `PASS`, current `INSPECTABLE`, and historical `AS_OF_REGISTRY_REQUIRED`. Both results remained unadmitted with all authority false and Graph1 null. The harness explicitly emitted `production_admission=false` and `served_product_proof=false`. The reviewer compared the held cited span and its normalized native text to captured stdout without printing either; **neither appeared in the output**. Current support contained only coordinates, hashes, structural/semantic status, and schema metadata.

The appended `test_research_witness_refuses_changed_capture_from_foreign_directory` uses an invented replacement capture from a foreign working directory. It passed with exit 2, empty stderr, a bounded `exact_held_source_capture_or_span_unavailable` refusal, `NOT_ADMITTED`, no historical replay, and no CLI outcome/semantic view. Receipt construction occurs only after the exact-capture checks, so replacement bytes cannot mint the expected witness receipt.

The final native suite was independently run: **107 passed, 8 warnings in 1.74 seconds; exit 0; stderr empty.** The same unrelated old pytest cleanup warnings remain. No source body was copied into the repository or this report by the reviewer.

### Appended CI definition

An independent YAML parse found exactly one `company-relationship-candidates` job. It is on the `code` gate and configures Python 3.12, installs `pytest` and `pyyaml`, and runs only `python -m pytest tests/test_company_relationship_candidates.py -q`. The reviewed definition has no ingestion, production, publishing, or admission step.

This is the legacy job-definition manifest consumed by the canonical CI pack selector. The reviewer did not execute the pack runner or independently certify its inferred path selection. The principal separately owns the reported validate-only result, current scope-selection probe, and actual hosted CI execution. The manifest's definition alone is not execution proof.

## Evidence that passed

### Native receipt and API/CLI boundaries

The complete module and test file were inspected, along with relevant functions in `engine/earnings_release/receipts.py`, `lib/dataos/temporal.py`, and `lib/dataos/registry.py`.

The existing native suite was independently executed with bytecode and pytest cache writes disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider tests/test_company_relationship_candidates.py
```

**Observed result:** exit 0; **76 passed, 8 warnings in 1.71 seconds**. The warnings are pytest cleanup failures concerning an old temporary Chromium runtime directory, outside these two candidate files; stderr was empty. No assertion was weakened and no test was changed by the reviewer.

The suite exercises UTF-8 and CRLF coordinates; complete-body revision mismatch; repeated identical spans with discordant character/byte offsets; normalized text and hash replay; unsupported labels; null-only quantities; taxonomy dispositions; source binding; DATE/naive cutoffs; unavailable, duplicate, and unrelated registry contracts; DERIVED refusal; future-known exclusion before semantic replay; corrections; authority flags; malformed/deep/duplicate JSON; and default CLI replay-field omission.

Additional reviewer probes:

- `include_support_text` values `1`, `None`, `'false'`, `[]`, and `{}` all returned typed `INPUT_INVALID` refusals.
- A matrix of 320 scalar/structure mutations across candidate, document, assertion, receipt, and revision fields produced **no uncaught exception, input mutation, or authority escalation**. This is bounded evidence, not a claim of exhaustive fuzz coverage.
- A supplied current identity annotation is echoed during a supplied-row as-of inspection, but canonical identity remains null and annotation status is explicitly `UNTRUSTED_NOT_RESOLVED`. This is a limitation of manual annotations, not an authenticated historical-identity result.

### Real-source witness

The private Micron witness supplied by the principal was run through the actual `python -m engine.company_intelligence.relationship_candidates` CLI. Its original source body was neither copied into this report nor published.

- Input candidate: `/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009/micron-manual-candidate.json`.
- Original source-body identifier: SHA-256 `a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e`.
- Replayed span SHA-256: `f79bce81f656e826b3aa74380eb9a2b63bf74fc0e60376dc2b40c64600eb890a`.
- Character coordinates: `370876:371258`; byte coordinates: `370936:371320`.
- Current call: exit 0, empty stderr, `INSPECTABLE`, dedicated support-text field absent.
- `--as-of 2024-02-26T12:00:00Z`: exit 2, empty stderr, `AS_OF_REGISTRY_REQUIRED`; current view, provenance, and support all null.
- Both calls: `NOT_ADMITTED`, all five authority axes false, `graph1_projection=null`.

The principal corrected the private fixture's document version to the required string before this independent run. The earlier integer-version input failure is not assessed as an economic defect.

## Scope limits and merge judgment

Reversing the manual parties, applying a manual category to names-only text, or asserting an unsupported lifecycle meaning can remain structurally inspectable because the utility does not adjudicate economic semantics. The output explicitly says `manual_review` and `semantic_adjudication=NOT_PERFORMED`. These results must remain manual candidates. Receipt agreement alone proves neither the relationship nor publication authenticity.

No actual historical native dataset or as-of issuer-identity path has been established. A supplied synthetic registry tests mechanics only; it does not prove a registered production dataset, authenticated history, historical system replay, source rights, Graph1 readiness, propagation, theme membership, forecast performance, or economic magnitude. Current PG publishers, held K3D work, and active unrelated workstreams are outside this review.

**Merge judgment:** the reviewed module, tests, README, case metadata, harness, and appended CI definition are safe to merge as a private analyst candidate utility at the final hashes above. No additional source repair is requested by this review. The supported result is structural receipt consistency and explicitly manual candidate inspection; it remains unadmitted and must not be consumed as verified economic truth, authenticated provenance, source rights, historical system output, or decision authority.

**Next action:** the principal may proceed with the existing source-publication workflow after its remaining canonical CI-selection/execution and status/handoff evidence is reconciled. Those operational results must be reported from their actual owners, not inferred from this source review. Production admission remains with its owner and is outside this recommendation.
