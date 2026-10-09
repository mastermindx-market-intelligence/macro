# Independent review — pinned native relationship-candidate adapter

## Verdict

**PASS — safe to merge the reviewed adapter and tests at private candidate-utility scope. No blocking findings or source repair requests remain.**

The later CI integration follow-up at the end of this report records an observed hosted packing defect, a rejected intermediate curation, and the independently verified 68-input repair. The source verdict is unchanged. The earlier CI definition review was a structural checkpoint, not hosted integration proof.

This recommendation covers exact retained-byte integrity relative to a supplied native strict reader, bridged into the already reviewed manual candidate inspector. It does not establish production-reader ownership, SEC authorship, economic truth, source rights, canonical identity, registered historical eligibility, historical served output, or Graph1 admission. **No real retained-store positive was available or executed.** All positive archive fixtures used in this review are explicitly synthetic.

Review date: 2026-10-09 UTC. Route: independent, read-only adversarial review. The reviewer applied Mastermind Craft common/reviewer methods, read the completed source only after receiving its final hashes, and performed bounded native tests and synthetic probes. No native source edits, Git commands, credentials/configuration changes, discovery, production reads, publication, or `run_ci_pack --execute` occurred. This report is the only new reviewer artifact.

## Exact scope and source identity

Workspace: `/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-execution-20261009-pro-001`.

Operation: `gmi-economic-network-execution-20261009-pro-001`.

The principal supplied draft/unarmed PR #8667 and branch base `d68678701b0e58924ae9dd5cf1b7f45b1c598538`, integrated with `c503c2caabc45b10524c006fbddc571a8608019a`. These Git identities are parent-provided; the reviewer did not query Git during this assignment. Protected-procedure custody remains with the principal at `732cf7be88e7159b4995a8885fbd381cd1484e3e`.

| Reviewed file | Lines | SHA-256, checked before and after verification |
| --- | ---: | --- |
| `engine/company_intelligence/pinned_relationship_candidates.py` | 235 | `1000497dcfef316f1ad0726c08bcba7ba12dbe305175887e191d6f96512649bd` |
| `tests/test_company_pinned_relationship_candidates.py` | 409 | `3c85ace77022c2b37c8abfab915ae8bf97ee711a8f315ea9e3b6f27d01872406` |

The established inspector and 107-test file remained unchanged:

- `engine/company_intelligence/relationship_candidates.py`: `27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d`.
- `tests/test_company_relationship_candidates.py`: `0a8c73d5e5b968fd3795fed1e08305597f9c254cc5702b9946b702b8f31bdbd4`.

The reviewed seam report was `/workspace/scratch/9fd3d58c239a/lanes/NEXT_NATIVE_ADAPTER_SEAM_20261009.md`, verified SHA-256 `8eb3934edabadbeb0322afec787a2c5df076d10e5b9d6b49fafc3b948b8817a5`. The implemented API and two assigned paths supersede that report's earlier optional CLI/path suggestions; this increment has no CLI or store factory.

## Findings and design assessment

**No actionable defect was found within the reviewed scope.** The following boundaries were verified against the completed source and native owners.

### Authority and exact source selection

Adapter lines 98–125 validate the application limit and selectors, require the exact `PinnedSourceAuthority` type, compare the explicit snapshot pin, and reconstruct the authority over the same supplied store. The adapter does not trust caller-mutated cached snapshots, clocks, or instance reader overrides.

The manifest is read through the native pinned reader, parsed by `manifest_from_json_bytes`, and compared to the native `manifest_storage_key` result. Exact-one document selection is enforced. This additional check matters because the native filing-manifest validator checks individual document identity and canonical order but does not itself reject duplicated document IDs. No name fallback, primary-document substitution, latest-pointer selection, or filing fan-out occurs.

The native `source_sync` reader reloads the immutable snapshot manifest before each positive file read and verifies the outer object's length and SHA-256. This prevents forged session mappings from redirecting an object claim. A self-consistent reader/store can still be caller-controlled; the output explicitly limits custody verification to that supplied reader and leaves its production ownership unauthenticated.

### Complete archive replay, bounds, and error distinctions

Adapter lines 126–146 check the selected receipt's exact integer raw length against the application cap, delegate stored-gzip bounds to `gzip_stored_byte_ceiling`, and use native `read_archive_document`. The native archive reader independently loads the retained sidecar, requires equality with the complete expected receipt, verifies its storage binding, performs bounded gzip decompression, and checks the original body length and hash. The adapter additionally checks returned length/hash and strict UTF-8 round-trip before using the text inspector. No document transformation is passed off as original source.

Errors remain typed and do not reflect source text, object keys, or host details. Genuine native missing-object/path branches map to `PINNED_SOURCE_MISSING`. Access failures, unavailable readers, typed/recognized bounded-read failures, manifest corruption, archive replay failures, snapshot contract failures, and unknown reader failures remain distinct. The suite exercises both same-length corruption and object-length overflow, avoiding a false conclusion that every damaged object is merely missing.

### Candidate binding, clocks, and historical output

Adapter lines 147–161 require exact candidate document ID, canonical native archive URL, digest-based string version, and `published_date=null`. Native `filed_on` and `report_date` remain separate date metadata. Their values are never converted to publication instants.

Native manifest recording and document retrieval clocks must not postdate the selected snapshot. These are source-capture causality checks, not a new DataOS knowability rule. The established inspector still owns registered-profile cutoff filtering and DERIVED refusal.

Source reads and capture-causality checks precede the inner inspector's registry-dependent historical filtering. The independent probe confirmed **seven bounded native reads** for a valid aware cutoff without a registry, followed by `AS_OF_REGISTRY_REQUIRED`. The returned native binding, inner relation view, provenance, and support were all null. Invalid DATE and naive cutoffs refused before any new source read. This ordering performs current source I/O but exposes no inadmissible current semantic/provenance view on the refused request and makes no historical replay claim. It is not proof that historical requests avoid all I/O or that response timing is an access-control boundary.

`native_source_binding` is added only after the inner result is `INSPECTABLE` (lines 164–193). It remains null for refusal and `NOT_KNOWN_AS_OF`. The future-known supplied-row test verifies exclusion without current witness leakage.

### Meaning, rights, and corrections

Successful output leaves the established inspector's caller metadata unauthenticated and adds a separate native custody witness. The native issuer/filing labels remain source-local; canonical issuer/counterparty IDs and economic exposure fields are not resolved or populated. Source amendment lineage is copied as native metadata without rewriting the candidate's correction relation or treating an omission as termination.

All outer and inner admission and authority restrictions remain intact. The default synthetic result contains neither the complete body, raw cited span, nor normalized supporting sentence. Explicit support replay is still a private content option; it grants no source-purpose right. The response does not certify quote-free or public-safe annotations. No `ffatt_` seal, dataset admission, rights grant, or Graph1 projection is manufactured.

## Independent verification

The completed adapter and test file were read in full. Relevant primary owner implementations were also inspected:

| Native owner | Decisive contract inspected |
| --- | --- |
| `engine/fundamental_forensics/filing_attestation.py` | Exact native authority; fresh reconstruction; verified source records; complete receipt-sidecar equality; bounded archive reads |
| `engine/fundamental_forensics/source_sync.py` | Strict pinned snapshot load; canonical immutable manifest; authoritative reload on each read; missing versus propagated reader errors |
| `engine/fundamental_forensics/sec_document_spine.py` | Canonical manifest parser and identity; exact document/receipt binding; original clocks and amendment lineage |
| `collectors/sec_document_spine.py` | Native manifest key; canonical retained receipt decode; bounded raw gzip replay |
| `engine/fundamental_forensics/filing_package.py` | Existing exact-authority reconstruction and source-capture causality pattern |
| `engine/research_vault/r2_store.py` | Strict bounded reader protocol and its authoritative-absence semantics |

### Test result

**153 passed, 8 warnings in 3.61 seconds; exit 0; stderr empty.** This comprised 43 new adapter tests, the unchanged 107 inspector tests, and three targeted existing native source-reader adversarial tests. The warnings are the same old pytest temporary Chromium-directory cleanup warnings previously observed; they do not concern the adapter assertions.

Executed from the bound workspace, with bytecode and pytest cache writes disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -q -p no:cacheprovider \
  tests/test_company_relationship_candidates.py \
  tests/test_company_pinned_relationship_candidates.py \
  tests/test_fundamental_forensics_source_sync.py::test_pinned_strict_reader_fails_closed_for_missing_tampered_and_too_small_reads \
  tests/test_fundamental_forensics_source_sync.py::test_pinned_strict_loader_rejects_duplicate_kind_path_before_any_source_read \
  tests/test_fundamental_forensics_source_sync.py::test_pinned_file_read_reloads_manifest_and_ignores_forgeable_session_mapping
```

The new fixtures use the actual native manifest/receipt writers, snapshot sync, strict pinned reader, and archive replay in temporary synthetic stores. Their reader spy denies writes, discovery, and unbounded reads during adapter execution. Fixture construction is not live source acquisition, and no fixture is represented as a production capture.

### Additional independent counterexamples

| Probe | Observed result |
| --- | --- |
| A native-valid canonical manifest containing the selected document twice, with a newly derived manifest ID and key | `DOCUMENT_NOT_UNIQUELY_SELECTED`; no native binding, inner relation, provenance, or support |
| Forged cached snapshot object and snapshot clock, with both instance reader methods overridden | Original pinned snapshot reloaded successfully; zero overridden-method calls; original pin/clock recovered; candidate unchanged |
| Subclass of the native authority | `EXACT_NATIVE_AUTHORITY_REQUIRED`; zero additional reads |
| Support option values `1`, `None`, and `'false'` | Typed `INPUT_INVALID`; zero additional reads |
| DATE-only and naive historical cutoffs | `NATIVE_TEMPORAL_REFUSAL`; zero additional reads and no views |
| Aware historical cutoff without a native registry | Seven bounded reads, then `AS_OF_REGISTRY_REQUIRED`; all native/current views null |
| Default positive synthetic output | No body or raw/normalized cited passage echoed; `NOT_ADMITTED`, all authority false |

The tests additionally cover canonical manifest aliases, cross-document substitution, complete sidecar metadata mismatch, current/over-budget/binary bodies, corrupt and oversized gzip objects, post-snapshot capture clocks, unavailable members, permission/network/unknown failures, future-known exclusion, source lineage preservation, source-body hash mismatch, malformed candidates, and authority injection.

## Proof limits and next action

**Real retained-store replay remains UNVERIFIED.** The principal's seam report records bounded absence checks for the declared owner data/configuration paths beneath the operation workspace and canonical primary root, plus absence of the dedicated reader configuration in the checked process. Those observations do not establish that deployed runtimes or private buckets lack captures. The reviewer did not broaden that search, enumerate a store, inspect secrets, invoke a reader factory, acquire a document, or create an actual source snapshot.

A real acceptance witness requires an existing owner-managed strict reader and an exact retained snapshot/manifest/document pointer. It must replay the native manifest, receipt sidecar, outer gzip object, original bytes, and candidate span with metadata-only evidence. That future result must be labeled separately from the synthetic proof here. Registered relationship datasets, source-purpose entitlements, canonical/historical identity, and incumbent downstream transport remain their owners' separate gates.

**Next action:** the principal may proceed with the existing delivery workflow for these exact reviewed source hashes, while separately validating its CI/docs changes and reporting actual hosted execution. No source repair is requested by this review. Neither a merge nor this PASS should be described as live retained-source, served-product, or production admission proof.

## Earlier delivery-addition review — before hosted CI integration findings

**PASS — no new findings.** The final bounded review of the updated unique CI job and delivery documentation completes the source-level CI/docs review named above. The adapter and dedicated tests remain at the exact previously passed hashes. No unchanged tests were rerun; no native files were modified and no Git or pack-execution command was used.

### Exact reviewed delivery hashes

| Repository-relative file | SHA-256 |
| --- | --- |
| `research/theme_graph/economic_network_execution_20261009/PINNED_SOURCE_EXECUTION.md` | `b9cff5d9adb4afb69b4a8d6211d971a92ea689744d4b7e2208ca55a236d2b33e` |
| `research/theme_graph/economic_network_execution_20261009/README.md` | `c90f49b5e28094269b8da0193aad644f04cc897c8d822f967552d2faa0a5718a` |
| `research/theme_graph/economic_network_execution_20261009/EXECUTION_STATUS.md` | `d4b4d19822dce0cd42371d28e1849d1e0ffda4a6c0b1867379d40beba13f6e15` |
| `research/theme_graph/economic_network_execution_20261009/NATIVE_SOURCE_ADAPTER_SEAM.md` | `8eb3934edabadbeb0322afec787a2c5df076d10e5b9d6b49fafc3b948b8817a5` |
| `agentos/decisions/DEC-GMI-ECONOMIC-RELATIONSHIP-CANDIDATE-EXECUTION.md` | `6e5ae5515302e801fa39f0131dda60847cca1f99da9683703c508225f53c674f` |
| `.github/ci/legacy-jobs.yml` | `e05bf4bdeb85e04554ef6360398d2314ad6dfdb652ee300e32c477f34534c85f` |

The README's original 179-line prefix was independently hashed and remains byte-identical to its earlier reviewed version (`6ed926db17bc3fe7c990ef105c1f65623c881b398a34c079294dd92b514d20d2`). The native seam memo is an exact copy of the source report already read at the same `8eb3934e…` digest. Prior-stage verification and review receipts intentionally retain their original hashes and proof scope; the continuation text explicitly prevents treating those receipts as coverage of later source additions.

### Documentation and operational claims

`PINNED_SOURCE_EXECUTION.md` was read in full. The appended README, execution-checkpoint continuation, and decision continuation agree with the reviewed code and evidence:

- The API consumes an existing native authority and explicit selectors; it introduces no store factory, acquisition route, latest-pointer discovery, credential manager, or publisher.
- Successful custody replay remains relative to the supplied reader. Class identity and a self-consistent synthetic store are not institutional custody or SEC-authorship proof.
- The candidate metadata binding, 4 MiB raw cap, complete native sidecar/gzip checks, source-capture clocks, and source-witness suppression match the implementation.
- Historical source I/O is described accurately, including the observed seven-read missing-registry case and its null native/current output views. No retained snapshot or DATE field is relabeled as registered knowability.
- The stated 150 focused tests are supported by the independent 153-test run above, which adds three native reader tests. Synthetic pinned fixtures remain separate from the real Micron current file-input witness.
- Neither the two known-root/process absence checks nor the lack of a supplied pointer is broadened into a claim that deployed runtimes or private buckets have no captures. Real retained-store replay is expressly not run and unverified.
- No historical replay, legal-party identity, source-purpose right, relationship dataset, Graph1, predictive promotion, or production work-package completion is claimed.
- Earlier checkpoint publication facts are dated separately from the final extension's exact-source hosted checks and release receipts. The documentation does not claim that the pending final head has already passed hosted CI or merged.

The GMI rights statements were cross-checked against the primary native files during this delivery review. `config/theme_sources.yml` explicitly limits its registry to GMI emissions and excludes retroactive gating of pre-existing owner products. `engine/theme_graph/rights.py::licensing_for_family` returns the restrictive readable tuple `(True, False, False)` for unknown families; public-emission and family guards remain separate. The delivery notes correctly avoid interpreting that tuple as a general retention, training, embedding, evaluation, or publication grant.

### CI definition and evidence boundary

An independent YAML parse found exactly one `company-relationship-candidates` job, on the `code` gate with no exclusive scope override. It uses Python 3.12, installs `pytest pyyaml requests`, and runs precisely:

```sh
python -m pytest tests/test_company_relationship_candidates.py tests/test_company_pinned_relationship_candidates.py -q
```

The job contains no ingestion, admission, publisher, or production-control step. The final containing-manifest digest matches the principal's supplied `e05bf4bd…` digest. This review covers the owned job definition, not a new review of every incumbent job in the shared manifest.

The principal separately reported validate-only exit 0, 28 inferred source/dependency paths with conservative fallbacks retained, and byte-for-byte conservation of the upstream manifest after removing the owned appended job. Those are principal-owned operational receipts. The reviewer did not rerun selection, execute the CI pack, or query Git to recreate the conservation check. Actual hosted CI and final publication remain separate execution evidence.

**Delivery recommendation:** proceed with the existing final source-publication workflow for these reviewed hashes and preserve the distinct stage receipts. No additional repair is requested. This document's source/fixture PASS does not supply the still-missing real retained-source acceptance, downstream owner admission, or hosted release result.

## CI integration follow-up — final curated scope

**PASS — the final 68-input curation repairs the independently reproduced underselection and excludes the three unrelated packing probes. No further repair is requested for the reviewed job.** This is a source and native-selector verdict. A fresh exact-head hosted contract-delta result remains required before merge; this local check did not execute the full CI pack or measure every incumbent job.

### Resolved findings and the evidence that changed the earlier assessment

**P2 — introduced over-selection violated existing hosted packing ceilings.** The principal reported that initial head `d68678701b0e58924ae9dd5cf1b7f45b1c598538`, hosted run `37873602283`, failed contract-delta job `113636962816`. The newly added `company-relationship-candidates` job was selected through broad inferred runtime-input fallbacks for all three unrelated probes:

| Probe | Principal-reported selected jobs | Existing ceiling |
| --- | ---: | ---: |
| `templates/index.html` | 136 | 135 |
| `scripts/build_free_content.py` | 135 | 134 |
| `engine/prophet/plan_book.py` | 130 | 129 |

The principal subsequently reported that `ci-pack-0` failed only `test_exclusive_curation_narrows_ordinary_code_prs` for those same three violations, while the other 11 packs passed. These hosted observations are principal-provided; the reviewer did not query the hosted run. The reviewer independently read the current native `PACKING_PROBES` declaration and confirmed the same three paths and job ceilings. No ceiling increase is part of the repair.

The earlier definition review checked the unique job, dependencies, command, and declared evidence boundary. It did not run native selection and did not establish packing integration. The hosted failure demonstrated that its non-exclusive inference was too broad for this entrant. This later finding supersedes the earlier CI recommendation for that configuration; it does not invalidate the unchanged inspector/adapter tests.

**P2 — the first exclusive repair omitted real initialization dependencies.** At manifest SHA-256 `3408fd7697fb9a6a1234e8124ea52a86971add4fee3d2751534ceec6b0d0e41b`, the proposed job declared 36 paths. Those paths covered the native selector's 28 named dependencies, the exact witness JSON, and several package/configuration inputs, but did not cover the dependencies of the imported package initializers or the applicable shared pytest setup.

The reviewer reproduced the defect with native `load_legacy_jobs` and `select_jobs`: changing any of `engine/company_intelligence/contracts.py`, `health.py`, or `views.py` selected zero copies of this job, although `engine/company_intelligence/__init__.py` imports those modules unconditionally. The same false-negative selection occurred for `engine/fundamental_forensics/normalize.py`, `pipeline.py`, and `disclosure_diff.py`, and for the existing `tests/__init__.py` marker. Expected behavior is selection of `company-relationship-candidates` when an actual initialization input changes.

The principal accepted the finding. Independent source inspection bounded the additional coverage as follows:

| Additional group beyond the rejected 36 | Count | Why included |
| --- | ---: | --- |
| Package initialization closure and test package marker | 10 | The three Company Intelligence imports; six additional named Fundamental Forensics inputs, including its disclosure-diff configuration; and `tests/__init__.py` |
| Applicable shared autouse-fixture imports | 20 | The GDELT, breadth-divergence, master-brain, and marketing fixtures plus their module-level import dependencies |
| Sparse-checkout collection hook and package marker | 2 | `scripts/worktree_sparse.py` and `scripts/__init__.py`, imported by the applicable pytest collection hook |

The 20 fixture inputs are `engine/{basket_breadth_divergence,catalyst_tone,desk_ledger,gdelt_client,master_brain}.py` and `engine/marketing/{__init__,accounts,authority,chart_render,charter,claims,cmo,departments,economics,events,ledgers,logo_cache,opportunity_bus,publication,state}.py`. These are bounded source dependencies, not a blanket marketing or engine directory scope.

Shared `tests/conftest.py` imports and patches these fixtures even for the focused candidate suites, with dependency guards around some optional imports. Its stamp/cache/override operations are redirected or stubbed. The inspected module initialization and fixture paths do not read additional repository data/configuration bodies. The sparse hook's executed `missing_dirs`/`remedy_line` path observes checkout metadata and directory presence; it does not call `load_profile`. Therefore the dormant `config/sparse_worktree.json` body read and the helper's unrelated traversal/checkout operations were not added. The reviewer inspected those paths without invoking the Git-reading hook. This is a bounded dependency analysis, not a claim that every conservative named configuration input is read in every test run or that a whole-runtime file-access trace was captured.

### Exact final repair identity

| Reviewed file | SHA-256 |
| --- | --- |
| `.github/ci/legacy-jobs.yml` | `195921e289363a9ecc6036c9b53fbcbb6c991df8ad8d08138b51fe23b63f2d64` |
| `research/theme_graph/economic_network_execution_20261009/PINNED_SOURCE_EXECUTION.md` | `294958b47fc384673048d9c6512ac46380ee938abfff10fae2e106f4968f2797` |
| `research/theme_graph/economic_network_execution_20261009/EXECUTION_STATUS.md` | `184dd300d4531fd57ecadc4e39851c0db8e2ef0c644e2dec9b4725c5ceb13247` |

The reviewer rehashed all four inspector/adapter source and test files and confirmed the exact hashes already recorded above. The README, native seam memo, and decision document likewise remain at their previously reviewed hashes. The unchanged 153-test result remains the applicable independent source/fixture evidence; no unchanged source tests were rerun for this CI-only repair.

The complete owned job occupies 3,818 appended bytes, SHA-256 `a82338f3851cfa30b9f4e79be8ef076d753d0fdf8af78ea33a6cd8e327808eaa`. Independent in-memory removal of that suffix produced prefix SHA-256 `dc8577417f3e95bad895317d6abfad961ef845dbfa0bd12a5b1ad5d4f6d6ce9d`, matching the principal-supplied upstream manifest digest. The principal associates that digest with upstream `cdbcd143dcfa419ab0637bc11dd4c80368143e2e`; this review confirms byte conservation against the supplied digest without independently resolving the Git ref. The test command, Python 3.12 environment, dependency install, and code gate remain as reviewed earlier. There is no added admission, ingestion, publisher, or production-control step.

### Independent native selector proof

The final job was loaded through native `scripts.run_ci_pack.load_legacy_jobs` and passed through `infer_job_scopes`. A separate counterfactual inference with exclusivity and declared paths removed derived the original 28 named dependencies. The reviewer separately assembled the package initializer closure, existing initialization/configuration inputs, exact witness JSON, and source-inspected shared fixture/hook inputs. This independently constructed set equals the final 68 declared paths exactly.

The native probe ran with bytecode writes disabled and exited 0. The manifest digest was checked before and after the probe.

| Check | Independent observed result |
| --- | --- |
| Final mode | `exclusive=true` |
| Native inferred fallback list | Empty |
| Original native named dependency closure | 28 files; none uncovered |
| Independently expected and declared inputs | 68 each; exact set equality |
| Missing, unexpected, or nonexistent declared inputs | None |
| Each of the 68 inputs passed separately to native `select_jobs` | The candidate job selected every time |
| `templates/index.html` passed to native `select_jobs` | Candidate job excluded |
| `scripts/build_free_content.py` passed to native `select_jobs` | Candidate job excluded |
| `engine/prophet/plan_book.py` passed to native `select_jobs` | Candidate job excluded |
| Native own-job semantic manifest invalidation | Candidate job selected |

The negative checks measure this entrant's selection, not the total selected jobs, aggregate weights, pack count, or every curated job's closure. The relevant native rules were inspected: `scope: exclusive` replaces inference; manifest loading requires nonempty paths and command-path coverage; native curation requires named closure coverage; and `select_jobs` retains global/semantic invalidation. The repair uses these existing mechanisms without modifying the selector, the contract-delta helper, the three packing ceilings, or unrelated jobs.

### Updated documentation and final recommendation

The changed CI paragraph in `PINNED_SOURCE_EXECUTION.md` and the appended CI integration section of `EXECUTION_STATUS.md` were read against the final job and probe evidence. They record the hosted over-selection, the rejected 36-input intermediate scope, the final 68-input repair, and the requirement for fresh hosted verification. Earlier non-exclusive descriptions remain expressly dated stage history. No new live source, historical, rights, admission, or production claim is introduced.

**Recommendation: proceed with the existing source-publication workflow for the reviewed bytes, retaining the fresh exact-head hosted gate before merge.** The local CI curation repair is PASS and the private candidate-utility source recommendation remains PASS. This report supplies neither the pending hosted result nor the still-missing real retained-source acceptance, downstream owner admission, or production completion.
