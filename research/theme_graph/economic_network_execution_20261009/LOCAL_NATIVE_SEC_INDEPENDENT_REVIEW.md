# Independent review: actual local native SEC relationship witness

Review completed: 2026-10-09 04:00 UTC

Reviewer: `/root/real_native_witness_review`

Disposition: **PASS for LOCAL_NATIVE_REPLAY. No source-code correction required.**

This review independently reproduced the real retained-document inspection and its refusal cases from the exact existing native local store. It supports an actual local native source replay, including a source-grounded manual roster observation. It does not establish production reader ownership, native fact admission, historical served state, purpose-specific rights, canonical entity resolution, a served product, or prediction authority. The parent project remains incomplete.

## 1. Reviewed identities and custody

The principal identified code head `037a23cf0fb232012bcb1a85f9cb714973782194`. I verified the current bytes of every native code dependency listed in the capture receipt against that receipt, and independently verified both candidate modules against their previously reviewed digests.

Native code root:

`/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-execution-20261009-pro-001`

Existing retained-source task root:

`/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009/nvda-sec-local-native-20261009`

The replay used `LocalStore` over this task root's existing `source-store` directory and the actual `PinnedSourceAuthority`. It did not invoke the capture script, create a source root, invoke an R2 factory, inspect credentials, acquire network data, publish a pointer, modify Git, or contact another person. The native LocalStore constructor's directory operation was allowed only after verifying the entire existing root chain consisted of real directories with no symlink in that chain. Task and store directory identities and modification times remained unchanged.

| Artifact | Independently verified SHA-256 |
|---|---|
| Capture receipt, `nvda-sec-local-native-capture.json` (5,781 bytes) | `3671954fc8d02dc2b58e68e705e249c6919ddaacfd8fad1a5e5af7a6620901b1` |
| Relationship witness, `nvda-sec-local-native-relationship-witness.json` (24,607 bytes) | `bd3edbbe0c4fef9b85657b8aaf07b3f65cf271828ec8982eb8393ed29dc3a5cd` |
| Private capture harness, `capture_one_native_sec_filing.py` | `4979788caa3a4d3eb039dfe8e5410f9c2cb87a57da0b52e4f8c05a1d35342b0b` |
| Private inspection harness, `inspect_nvda_local_native_witness.py` | `d1584bd88f3b9bd22b4c93f723bdb6e84273cb8ee619b0427dff580dc5b834db` |
| Candidate inspector | `27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d` |
| Pinned candidate adapter | `1000497dcfef316f1ad0726c08bcba7ba12dbe305175887e191d6f96512649bd` |

The retained snapshot is:

`ffsecsrc_520d816415a2d1dbde1fcf348abef2cbfdd8b28b88b4bf847a549613002d02ee`

Its native snapshot descriptor has SHA-256 `d9fd6566dfbecfc1b9de60c604fcb71c2f52f48ddaf3543c5279c89c698414b4`. The descriptor contains exactly two retained raw entries and three retained archive entries: Submissions gzip, Submissions receipt, filing manifest, primary-document gzip, and archive receipt. I used these explicit entries rather than discovering additional files or snapshots.

## 2. Independent source selection and exact object replay

I read the pinned Submissions response through the native gzip replay API and verified its independently retained receipt. The raw Submissions body is 159,785 bytes, SHA-256 `0b3ce6a0cd78c43d69b19b7efb9effcd79d0c6bd4c43606aac84d0f872cc9c73`. Its retained receipt SHA-256 is `11e52abbae6f18ae49c01f43a54e780cff8c00bb9ea0f1d5a4d2ce925b1510f7`.

Running the existing `build_filing_manifests` and `select_periodic_comparables(form="10-K", count=1, as_of=<actual Submissions capture>)` over those actual retained bytes independently selected the same single filing and primary document:

| Field | Verified value |
|---|---|
| Source-local issuer CIK | `0001045810` |
| Source-local issuer name | `NVIDIA CORP` |
| Accession | `0001045810-26-000021` |
| Filing form | `10-K` |
| Report date | `2026-01-25` |
| Primary document ID | `sec_document_5b75587074cf7849d010ec05a7ae7a18d305326a50418897d5d0bc75423bb26a` |
| Source URL | `https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm` |

The exact selected filing manifest key is:

`manifests/0001045810/0001045810-26-000021/ffsec_manifest_f050d1fb989d8f840c4291c5eb8b12788f1110bea58bf3b5b4ce239c8a771a61.json`

Native manifest parsing and canonical-key reconstruction agree. The selected document is unique, primary and stored. The fully decoded selected document equals the capture receipt's document object.

| Retained object | Bytes | Independently verified SHA-256 |
|---|---:|---|
| Filing manifest | 2,257 | `d4aed1a554bf7f208752591994fd854f6c2fe879e2b2d8eae77b3324040f9524` |
| Primary filing gzip | 166,203 | `1131e65e38c5e8a87c6d49a1cf56f22bf47ab88d3debaba8791ca4e7f8f9430a` |
| Primary archive receipt sidecar | 701 | `52dc92ce41b106dfee5a8f10a2c09d75112d2274dc2aa562439617e6c1547f6a` |
| Inflated primary filing body | 1,967,931 | `94f539316ae2a9ff625357cf01008cb77b930d1a6a228326f04a3ce5f5a56d2e` |

I independently used `PinnedSourceAuthority.read_file`, the native canonical manifest parser, and `read_archive_document`. The sidecar deserializes to exactly the selected document's declared retrieval receipt; its canonical storage key agrees. Gzip and sidecar witness lengths and digests agree with the actual bytes. Inflated raw bytes agree with the raw receipt, including strict UTF-8 round trip. This is relative custody proof through the supplied local native reader; a consistent local receipt is not independent cryptographic authentication of SEC authorship or production ownership.

## 3. Actual passage and manual semantics

I privately inspected the actual retained support span and regenerated the native character-span receipt directly from the raw body. Its boundaries are:

| Span field | Verified value |
|---|---|
| Character start / end | `243494` / `243668` |
| UTF-8 byte start / end | `243494` / `243668` |
| Length | 174 characters and 174 bytes |
| Span SHA-256 | `13a4750ac1264fdc31b6a3569e9a0c1672d0bffb798ff11539b8c289d6665b48` |
| Occurrences of exact span in retained body | 1 |

The regenerated receipt exactly equals the private candidate's supplied receipt. The passage identifies a foundry roster containing TSMC and Samsung and a semiconductor-wafer scope. The accepted candidate deliberately uses only the exact source-local labels `We`, `TSMC`, and `semiconductor wafers`.

The resulting inspection preserves:

- `kind=supplier_roster`, `lifecycle=listed`, `disposition=roster_observation_only`, `scope=named_roster_only`.
- `bilateral_candidate=false` and both canonical entity IDs null.
- Null magnitude, economic weight, revenue, shipments, theme membership and identity annotations.
- No automated selection or original erasure for revision metadata.

The separately retained filing issuer is NVIDIA. This witness does not resolve the pronoun `We` to a canonical legal entity, infer an exclusive bilateral contract, prove a current shipment, quantify any supply dependence, or admit an edge into Graph1. TSMC appears in a roster that also includes another foundry; no exclusivity or purchase share follows from this passage.

The principal's initial annotation used an issuer name, a joined object label and a paraphrased product scope that were not exact source-local labels in the support span. I read the separately preserved initial private candidate and independently reproduced `SOURCE_LOCAL_LABEL_UNSUPPORTED`. Correcting the annotation to exact labels without changing code was the appropriate response. The initial refusal remains part of the empirical record.

## 4. Independent execution and refusal results

The principal's capture and inspection scripts were inspected as source. They were not rerun. My separate read-only Python invocations reconstructed the native reader from the existing store and called the actual public adapter API.

The main independent inspection replay (native PID 4589) completed with exit code 0. All five complete output objects exactly equal the saved witness, not merely their status strings. The independent Submissions selection and additional boundary replay (PID 9243) completed with exit code 0. Both invocations used Python `-B` and an audit hook blocking network operations and filesystem mutations after existing LocalStore construction. Tracked source, receipt and private-candidate bytes, sizes and modification times remained unchanged in the main replay.

| Probe | Independent result |
|---|---|
| Current exact candidate | `INSPECTABLE`; `NOT_ADMITTED` |
| Historical request at `2026-02-26T00:00:00Z`, no registry | `AS_OF_REGISTRY_REQUIRED` |
| Candidate raw-version digest deliberately mismatched | `CANDIDATE_SOURCE_METADATA_MISMATCH` |
| Missing selected document ID | `DOCUMENT_NOT_UNIQUELY_SELECTED` |
| Unsupported source-local labels | `SOURCE_LOCAL_LABEL_UNSUPPORTED` |
| Preserved original private candidate | `SOURCE_LOCAL_LABEL_UNSUPPORTED` |
| Explicit as-of after actual capture, still no registry | `AS_OF_REGISTRY_REQUIRED` |
| Raw-byte limit one byte smaller than actual retained filing | `SOURCE_RAW_SIZE_OUTSIDE_LIMIT` |

Every output retains `admission=NOT_ADMITTED`, null Graph1 projection, and false rank/gate/size/trade/prediction authority. Every refusal suppresses native source binding. The historical output additionally has null current candidate view, source provenance and support. The post-capture as-of probe confirms that a recent capture does not substitute for an adopted registry contract.

## 5. Clock evidence and absence of publication

I independently checked that the actual retained clocks are monotone in the following order:

| Event | Retained instant |
|---|---|
| Principal capture started | `2026-10-09T03:53:31.343521+00:00` |
| Submissions body captured | `2026-10-09T03:53:31.726239+00:00` |
| Primary filing retrieved | `2026-10-09T03:53:33.185441Z` |
| Retained manifest recorded | `2026-10-09T03:53:33.214726+00:00` |
| Native source snapshot | `2026-10-09T03:53:33.331285Z` |
| Principal capture completed | `2026-10-09T03:53:33.344870+00:00` |
| Principal candidate inspection | `2026-10-09T03:56:29.839534+00:00` |

The native filing metadata separately retains accepted-at `2026-02-25T21:42:19.000000Z`, filed-on `2026-02-25`, and report date `2026-01-25`. The candidate's `published_date` is null. None of those filing dates or the HTTP last-modified header was converted into a system capture, registry known-at, or historical served-state claim.

The capture source explicitly calls both native Submissions persistence and source synchronization with `publish_latest=False`. I independently verified absence of the exact native snapshot latest key and the exact task-local Submissions latest path. The snapshot descriptor itself contains only the five immutable retained entries described above. This is an isolated local native capture and replay; it is not a production pointer publication.

## 6. Export boundary and size discrepancy

The 24,607-byte witness does not contain the actual support sentence, the full source body, an HTML body, or a `replayed_value_text` field. Its source annotations still contain short source-derived labels. The adapter accurately retains `quote_free_payload=NOT_CERTIFIED`, `public_safe_payload=NOT_CERTIFIED`, and `public_export=NOT_AUTHORIZED`. The review does not turn metadata omission into a license grant.

The private inspection harness and private candidate do contain source text required for exact replay. They must remain distinguished from the checked metadata receipt; this review makes no public-export finding for those private artifacts.

The commissioning principal reported a separately observed SEC web-index declared size of **1,967,816 bytes**. My direct retained-body observation is **1,967,931 bytes**, a difference of **115 bytes**. These must remain separate observations. I did not acquire the web index or recapture the document under this read-only assignment, so I do not independently attest the index-size observation or explain the discrepancy. There is no demonstrated byte equality to that index listing. Exact replay of the observed captured body is independently established by the native receipt and digest. The unresolved size difference does not change that bounded result, but it prohibits claiming the two size observations agree.

## 7. Required disposition

**No source-code correction is required for this witness.** The completed finding may be reported as: an actual retained SEC filing was inspected through the existing native local snapshot, canonical manifest, archive sidecar and gzip reader; a manually annotated roster observation and explicit refusals reproduced independently.

Reporting and subsequent execution must preserve four limits:

1. Use `LOCAL_NATIVE_REPLAY`, with production custody and admission false. The independent test established behavior relative to the supplied local reader and inspected capture evidence; it did not independently observe the original HTTPS session or authenticate institutional reader ownership.
2. Keep the initial annotation refusal, corrected exact labels and roster-only interpretation. Do not upgrade the candidate to a bilateral, quantified, exclusive or canonical relationship.
3. Keep the 115-byte index/capture discrepancy unresolved. Cite each observation according to who actually observed it.
4. Keep production owner custody, native relationship fact/dataset admission, point-in-time registry, canonical identity, purpose-specific rights and served-product proof as separate unfinished gates. All predictive and trading authority remains false.

No broad source discovery, network requests, native cache writes, repository changes, commits, PR operations, credential changes, latest publication or production admission were performed by this reviewer. This scratch review is the sole new artifact created by this assignment.

---

Publication formatting note from the principal: two Markdown hard breaks were converted to paragraph separators for the repository whitespace check. The independent report text is otherwise unchanged. Original review SHA-256: `6d81040cf5718f32a59803badbaaae4e2bc85e8d324017df7bf2e3a21c1abad8`.
