# One real SEC filing through the existing local native source route

Read-only feasibility review, 2026-10-09. Requested by the principal while source delivery for Macro PR #8667 continues. This lane invoked **no collector, source factory, retention writer, credential factory, Git mutation, remote publisher or runtime admission**. It inspected source and exact configuration presence only. The example below is unexecuted orchestration of existing APIs, not a new collector, store or production pipeline.

## Decision

**A technically concrete existing local route is available.** The principal can capture one real SEC document through the native Fundamental Forensics collectors, retain it through their native writers, create an immutable native `ffsecsrc_…` snapshot in the already implemented `LocalStore`, and read it with the exact `PinnedSourceAuthority` consumed by the implemented adapter. This can be an authorized next private execution step under the Chairman's end-to-end instruction. It does not require production R2 credentials or an existing production snapshot pointer.

The result must be labeled **`LOCAL_NATIVE_REPLAY`**: a real network capture retained and replayed in a task-owned local instance of the existing native format. It is not production reader custody, an institutional attestation, independent SEC authorship authentication, native relationship admission, historical served evidence or product deployment. The prior statement that no existing production reader/pointer was available at the checked roots remains true.

The important distinction in the prior seam document is scope. Its prohibition on constructing `LocalStore` applied to that lane's **read-only adapter review**, because the constructor creates a directory. The same document explicitly names the existing collector → retention → source-sync route when a real capture is absent. The later end-to-end instruction authorizes useful reversible local execution; it does not require inventing an owner or bypassing a missing production credential. This lane remains read-only and has not exercised that authorization on the principal's behalf.

Protected custody is inherited from the principal at Mastermind `732cf7be88e7159b4995a8885fbd381cd1484e3e`. The inspected execution source head was Macro `2a00eff6125d07cc2303b1edbafa00ba1d50d4a5`. The relevant owner blobs are unchanged from the prior seam's `c503c2ca…` source pin. The source explicitly restricts `source_sync` to an operator/collect lane, outside normal render and the public site; this proposed isolated operator action fits that surface. No held carrier, dataset registry, rights registry, current product route or source ownership needs modification.

## Existing native interfaces

All links in this section are pinned to the actually inspected Macro revision.

| Native interface | Exact usable contract | Consequence for this witness |
|---|---|---|
| [Owner SEC configuration helper](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/collectors/edgar_forensics.py) | `_user_agent(root: Path) -> str` reads existing `config.yml` → `edgar.user_agent`; absent configuration raises | Reuse the existing configured application/contact identity; do not invent or print it. Presence-only inspection found the file and nonempty value and passed the native basic `@` check. That is not an independent validation of contact ownership. |
| [SEC JSON collector](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/collectors/edgar_forensics.py) | `SecForensicsCollector(raw_root: Path, *, user_agent, min_interval_seconds=0.12, timeout_seconds=30.0, max_response_bytes=None, session=None)`; `retrieve_current(cik, endpoint, *, max_response_bytes=None) -> (bytes, transport_metadata)` | Use the existing exact endpoint, streamed body cap, redirect refusal, source URL equality, response close and native retry behavior. `retrieve_current` itself does not persist or publish a pointer. |
| [Native raw retention](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/collectors/edgar_forensics.py) | `persist_response(raw_root, *, cik, endpoint, url, content, retrieved_at, etag=None, last_modified=None, publish_latest=True) -> RetrievalReceipt` | Pass only the actual bytes and metadata returned by the native collector; use the actual completed-response clock and `publish_latest=False`. This is the native writer, not a hand-built receipt. Keep source and receipt outside Git. |
| [Manifest and one-filing selector](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/engine/fundamental_forensics/sec_document_spine.py) | `build_filing_manifests(submissions, *, cik=None, ticker=None, recorded_at) -> tuple`; `select_periodic_comparables(manifests, *, form, ticker=None, as_of=None, count=2) -> tuple` | `count=1` is supported by this selector. It operates on real retained Submissions, requires acceptance/report clocks, and preserves native amendment/period selection. This is current selection from the retained response, not a claim that the system held that response historically. |
| [One exact archive fetch](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/collectors/sec_document_spine.py) | `SecFilingArchiveCollector(cache_root, *, user_agent, min_interval_seconds=0.12, timeout_seconds=30.0, max_attempts=4, max_document_bytes=None, session=None, ...)`; `fetch_document(document, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None) -> ArchiveReceipt | missing_receipt` | Supply the exact native selected document. Omit `retrieved_at` and `expected_sha256` on the first real acquisition: the native collector samples the completed HTTP observation and computes its actual digest. Refuse missing, redirects, oversized responses and transport failures. A later replay can assert the actual observed digest. |
| [Primary-document convenience](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/collectors/sec_document_spine.py) | `fetch_primary_document(manifest, *, retrieved_at=None, expected_sha256=None, max_document_bytes=None) -> dict` | Existing convenience combines native document fetch and `with_document_retrievals`. The example uses the underlying exact-document method to sample final manifest construction after the capture; neither approach requires a new fetcher. |
| [Receipt binding and retention](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/engine/fundamental_forensics/sec_document_spine.py) / [native writer](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/collectors/sec_document_spine.py) | `with_document_retrievals(manifest, receipts_by_document_id) -> dict`; `retain_filing_manifest(cache_root, manifest) -> (storage_key, retained_manifest, minted)` | The writer preserves a prior content-identical manifest and its original clocks. The example uses a fresh task-owned root; it never resets or rewrites an incumbent cache. Its bounded content lookup is confined to one CIK/accession directory. |
| [Existing local backend](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/engine/fundamental_forensics/source_sync.py) / [backend implementation](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/engine/research_vault/r2_store.py) | `build_private_source_store(*, local_dir=None) -> StrictConditionalWriteStore`; `LocalStore(root)`; `get_bytes_strict_bounded(key, maximum_bytes)` and native conditional writes | A nonempty **explicit** `local_dir` selects `LocalStore` before any environment or R2 path. The factory explicitly documents local dry-runs/tests. `LocalStore` implements the required strict read and conditional write protocols. It is an existing implementation; no new wrapper/backend is necessary. |
| [Native immutable local snapshot](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/engine/fundamental_forensics/source_sync.py) | `sync_source_roots(*, raw_root, archive_root, store, snapshot_at, max_files=…, max_file_bytes=…, max_total_bytes=…, publish_latest=True, skip_objects_in_latest_manifest=False) -> SourceSnapshot` | Set `publish_latest=False`, `skip_objects_in_latest_manifest=False` and lower finite limits. The function creates content-addressed immutable objects and a manifest by create-only writes with exact bounded readback. It neither deletes sources nor prunes local files. Its walk must cover only the two new isolated roots, never an incumbent cache or repository. |
| [Strict native read](https://github.com/mastermindx-market-intelligence/macro/blob/2a00eff6125d07cc2303b1edbafa00ba1d50d4a5/engine/fundamental_forensics/filing_attestation.py) | `PinnedSourceAuthority(*, store, snapshot_id)`; `read_file(*, kind, relative_path, maximum_bytes)`; `read_archive_document(*, storage_key, expected_receipt, maximum_bytes, maximum_stored_bytes=None)` | The exact existing class loads the native strict manifest. Full manifest/receipt-sidecar/gzip/raw replay can then be exercised against the returned local pin. No synthetic authority or institutional-ownership assertion is needed. |

### Why the broad CLI is the wrong executable for this bounded case

The existing `scripts/run_fundamental_forensics_wave2.py` CLI supports `--local-store`, explicit roots and `--acquire`, `--sync`, `--restore`, `--build-projections`. It is an authentic owner operator route. However, its `--acquire` calls `acquire_bounded_filings`, which explicitly requires **exactly two comparables per form** and may fetch two 10-K and two 10-Q documents. Reducing that acquisition API's `max_documents_per_form` to one raises `AcquisitionError`. The CLI exposes no `publish_latest=False` option; its combined sync uses the supplied `recorded_at` as snapshot time. Do not change or weaken those contracts for this witness. Use the existing lower-level single-document interfaces and separately sample the post-capture snapshot clock.

## Unexecuted bounded one-filing example

This is a reviewable example for the principal, not proof of execution. It uses candidate target NVIDIA CIK `0001045810`; it obtains the actual accession and document identity from a real SEC response. It selects the latest eligible 10-K family comparable **within that captured response** and preserves whether the native result is amended. It never invents a 2026 accession, foundry name, document body, expected digest or receipt.

Before executing, the principal must verify current SEC fair-access guidance, the owner configuration and the existing collector's operating context. Use a new task-owned non-symlink directory under the established private task cache, private permissions, one sequential capture and no background/scheduled acquisition. This example's pacing does not certify the aggregate rate of other SEC clients.

```python
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from collectors.edgar_forensics import (
    SecForensicsCollector, _user_agent, persist_response,
)
from collectors.sec_document_spine import (
    ArchiveReceipt, SecFilingArchiveCollector, manifest_storage_key,
    retain_filing_manifest,
)
from engine.fundamental_forensics.sec_document_spine import (
    HARD_MAX_FILING_MANIFEST_BYTES, build_filing_manifests, canonical_cik,
    manifest_from_json_bytes, select_periodic_comparables,
    with_document_retrievals,
)
from engine.fundamental_forensics.source_sync import (
    SOURCE_SYNC_PREFIX, build_private_source_store, sync_source_roots,
)
from engine.fundamental_forensics.filing_attestation import (
    PinnedSourceAuthority, gzip_stored_byte_ceiling,
)
from engine.fundamental_forensics.models import parse_utc
from engine.research_vault.r2_store import LocalStore
from engine.company_intelligence.relationship_candidates import MAX_SOURCE_BYTES


def now_utc():
    # Actual execution wall clock, never an issuer filing DATE or a backdate.
    return datetime.now(timezone.utc).isoformat()


def one(items, label):
    values = list(items)
    if len(values) != 1:
        raise RuntimeError(label)
    return values[0]


def capture_one_native_sec_filing(*, code_root: Path, task_root: Path):
    # Call only after the principal's bounded capture preflight.
    # Parent directory must already be the authorized private task cache.
    if task_root.exists() or task_root.is_symlink():
        raise RuntimeError("a new task-owned cache directory is required")
    user_agent = _user_agent(code_root)  # Never print this value.
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    raw_root = task_root / "raw"
    archive_root = task_root / "archive"
    store_root = task_root / "source-store"  # Sibling, not inside either tree.
    cik = "0001045810"
    submissions_limit = 8 * 1024 * 1024

    collector = SecForensicsCollector(
        raw_root, user_agent=user_agent, min_interval_seconds=1.0,
        timeout_seconds=30.0, max_response_bytes=submissions_limit,
    )
    content, transport = collector.retrieve_current(
        cik, "submissions", max_response_bytes=submissions_limit,
    )
    submissions_captured_at = now_utc()  # After native body consume and close.
    submissions_receipt = persist_response(
        raw_root, cik=cik, endpoint="submissions", url=transport["url"],
        content=content, retrieved_at=submissions_captured_at,
        etag=transport.get("http_etag"),
        last_modified=transport.get("http_last_modified"),
        publish_latest=False,
    )
    submissions = json.loads(content)
    if canonical_cik(submissions.get("cik")) != cik:
        raise RuntimeError("returned Submissions issuer does not match target")
    manifests = build_filing_manifests(
        submissions, cik=cik, ticker=None, recorded_at=now_utc(),
    )
    selected = one(select_periodic_comparables(
        manifests, form="10-K", count=1, as_of=submissions_captured_at,
    ), "no unique eligible 10-K family filing")
    accession = selected["filing"]["accession"]
    primary = one(
        (d for d in selected["documents"] if d["role"] == "primary"),
        "no unique primary document",
    )

    # Separate native clients do not share their _last_request_at value.
    # This explicit sequential gap covers this tiny invocation only.
    time.sleep(1.1)
    archive_collector = SecFilingArchiveCollector(
        archive_root, user_agent=user_agent, min_interval_seconds=1.0,
        timeout_seconds=30.0, max_attempts=1,
        max_document_bytes=MAX_SOURCE_BYTES,
    )
    archive_receipt = archive_collector.fetch_document(
        primary, max_document_bytes=MAX_SOURCE_BYTES,
        # No caller-supplied retrieved_at or invented expected_sha256.
    )
    if type(archive_receipt) is not ArchiveReceipt:
        raise RuntimeError("native capture did not return a stored document")

    # Construct the retained manifest after actual archive capture completes.
    # Preserve the exact accession/document selected before seeing its text.
    retained_recorded_at = now_utc()
    final_declared = one(
        (m for m in build_filing_manifests(
            submissions, cik=cik, ticker=None, recorded_at=retained_recorded_at,
        ) if m["filing"]["accession"] == accession),
        "selected accession no longer unique",
    )
    final_primary = one(
        (d for d in final_declared["documents"]
         if d["document_id"] == primary["document_id"]),
        "selected document no longer unique",
    )
    if final_primary["archive_url"] != primary["archive_url"]:
        raise RuntimeError("selected source URL changed")
    materialized = with_document_retrievals(
        final_declared, {primary["document_id"]: archive_receipt.to_dict()},
    )
    manifest_key, retained_manifest, minted = retain_filing_manifest(
        archive_root, materialized,
    )

    # Explicit local_dir selects the existing native LocalStore before env/R2.
    store = build_private_source_store(local_dir=store_root)
    if type(store) is not LocalStore:
        raise RuntimeError("expected the native local backend")
    snapshot_at = now_utc()  # After raw, archive, sidecar and manifest retention.
    for prior_clock in (
        submissions_captured_at, archive_receipt.retrieved_at,
        retained_manifest["clocks"]["recorded_at"],
    ):
        if parse_utc(prior_clock) > parse_utc(snapshot_at):
            raise RuntimeError("capture clock is later than snapshot clock")
    snapshot = sync_source_roots(
        raw_root=raw_root, archive_root=archive_root, store=store,
        snapshot_at=snapshot_at, max_files=16,
        max_file_bytes=8 * 1024 * 1024,
        max_total_bytes=24 * 1024 * 1024,
        publish_latest=False, skip_objects_in_latest_manifest=False,
    )
    latest = store.get_bytes_strict_bounded(
        f"{SOURCE_SYNC_PREFIX}/latest.json", 64 * 1024,
    )
    if latest is not None:
        raise RuntimeError("unexpected local snapshot latest pointer")
    if (raw_root / cik / "submissions" / "latest.json").exists():
        raise RuntimeError("unexpected local Submissions latest pointer")

    authority = PinnedSourceAuthority(store=store, snapshot_id=snapshot.snapshot_id)
    manifest_read = authority.read_file(
        kind="archive", relative_path=manifest_key,
        maximum_bytes=HARD_MAX_FILING_MANIFEST_BYTES,
    )
    verified_manifest = manifest_from_json_bytes(manifest_read.content)
    if manifest_storage_key(verified_manifest) != manifest_key:
        raise RuntimeError("canonical manifest key mismatch")
    document = one(
        (d for d in verified_manifest["documents"]
         if d["document_id"] == primary["document_id"]),
        "selected retained document no longer unique",
    )
    verified = authority.read_archive_document(
        storage_key=document["storage_key"],
        expected_receipt=document["retrieval"],
        maximum_bytes=MAX_SOURCE_BYTES,
        maximum_stored_bytes=gzip_stored_byte_ceiling(
            document["retrieval"]["byte_length"],
        ),
    )
    # The principal may now inspect the actual held body privately and annotate
    # one exact supported span. Do not print it or put it in a Git receipt.
    return {
        "evidence_class": "LOCAL_NATIVE_REPLAY",
        "authority": authority, "snapshot": snapshot,
        "manifest_key": manifest_key, "document": document,
        "verified_read": verified,
        "submissions_receipt": submissions_receipt,
        "retained_recorded_at": retained_recorded_at,
        "retained_manifest_minted": minted,
    }
```

The returned objects are private runtime inputs, **not a serializable public receipt**. In particular, `verified_read` contains source bytes. This example must not be used with `json.dumps(result)` or a blanket object dump. Root should construct an allowlisted metadata-only receipt from exact observed fields, after separately inspecting the native read result attributes. It must not print the user agent, source body, chosen passage, local secrets or a serialized authority/store object.

## Joining the real capture to PR #8667

The implemented adapter is API-only:

```python
inspect_pinned_candidate(
    candidate,
    authority=authority,
    snapshot_id=snapshot.snapshot_id,
    manifest_key=manifest_key,
    document_id=document["document_id"],
    maximum_bytes=MAX_SOURCE_BYTES,
    include_support_text=False,
)
```

Build the candidate **only after reading the actual retained body** and selecting its exact UTF-8 span. Use native `receipt_for_char_span` for coordinates and hashes. Candidate document fields must be exactly `document_id`, `version="sha256:<actual raw digest>"`, `source_ref=<exact native archive URL>`, and `published_date=None`. Preserve native filed/report DATE fields separately. `dataset_id=None`, `temporal_row=None`, unresolved canonical identity and null economic magnitude remain appropriate for this utility.

For the NVIDIA case, no foundry relationship is established by this feasibility study. A real passage listing named foundries can fit the current `supplier_roster` / `listed` class, whose disposition is **roster observation only**. An unnamed supplier or customer belongs to `anonymous_counterparty` and must not be resolved by inference. The current vocabulary does not implement a general admitted supplier economic edge. Do not call a generic foundry dependency `product_integration` merely to obtain a stronger disposition. Named relationships do not establish capacity share, exclusive supply, volume, price, bargaining power, current termination status or revenue attribution.

After a real current positive, run a real cutoff refusal without a registered historical profile. A correct `AS_OF_REGISTRY_REQUIRED` result with null source witness/current semantic views is useful paired evidence. It remains a missing registered historical context, not proof of historical eligibility. A bytes-only mismatch probe may be run on a task-owned copy or candidate receipt; never tamper with the held native source to manufacture a refusal.

## Capture, retention and stop conditions

1. **Primary access policy remains a capture preflight.** This lane did not browse SEC policy or contact SEC. Native code validates an application/contact user agent, uses bounded streamed responses, refuses redirects and exact-URL mismatches, paces each client and has bounded retries. Those implementation controls do not constitute a current legal/license determination or an aggregate SEC request budget. The principal should verify current SEC fair-access terms before real acquisition and keep the existing configured identity. No evasion, rotated identity, alternative host or retry storm after blocking is acceptable.
2. **Scope is one current response and one exact archive document.** The sample's default Submissions collector has a native bounded retry loop; the archive call is capped at one attempt. A selected filing unavailable in the captured current response is an explicit gap. Do not follow historical shards, enumerate a universe, fetch CompanyFacts, collect archive indexes or expand exhibits without a new bounded need. A size refusal should stay a refusal; do not increase the candidate's 4 MiB cap to obtain a positive.
3. **No new credentials or remote writes.** The explicit local backend needs no R2 configuration. Never omit `local_dir` or fall back to a default environment-selected store. Do not invoke the attested-history credential factory, remote source restore, source publisher, observation/projection build or current owner scheduler. Source-sync's immutable writes are confined to the new local store and `publish_latest=False` is mandatory.
4. **Keep all capture bodies outside Git.** SEC-hosted issuer filings are not automatically granted every reuse purpose by their public availability. Native byte retention, a source hash and the GMI unknown-family internal-only tuple do not grant display, redistribution, training, embeddings or evaluation rights. The proposed action is private bounded source inspection using the existing owner path. Any broader downstream use remains purpose-specific and unresolved. Do not export the filing or copied passage to the PR.
5. **Keep source clocks literal.** Sample the Submissions capture after HTTP completion, let the archive collector sample its default completed-response clock, construct the retained manifest at an actual wall clock, and sample the snapshot after the retained objects exist. Preserve SEC acceptance instants and filed/report dates exactly. Do not convert a filing date to `known_at`, backdate this 2026 capture, or relabel a supplied local timestamp as institutional ingestion evidence.
6. **Refuse incomplete integrity.** A 404 missing receipt, transport/denial error, source URL mismatch, unsafe path/symlink, over-budget document, invalid UTF-8, ambiguous selector, bad sidecar, bad gzip/raw hash/length, noncausal clock, local-store failure or snapshot mismatch ends the positive path. Preserve an honest metadata-only failure receipt and stop the bounded capture; do not substitute synthetic bytes, a current issuer web page or a manually forged native manifest.
7. **No product promotion follows.** Successful native replay may close a previously untested *local real-source* aspect of WP03. It does not close the production retained-runtime gap, fact/dataset/profile/identity/rights adoption, graph projection, conditional propagation, product route, reference-set precision, causal experiment or predictive promotion gates. Preserve #7870/#8245/#7891, held #6514, micro-membership, Terminal #796 and incumbent source ownership.

## Receipt required if root executes

Publish only an explicit metadata allowlist: evidence class `LOCAL_NATIVE_REPLAY`; exact executed source head and code digests; real task cache custody scope; requested CIK; actual selected accession/form/document ID/archive URL; Submissions URL/digest/length and completed capture instant; manifest ID/key/recorded instant; native archive receipt ID/digest/length/retrieval instant; immutable local snapshot ID/key/clock; all bounded read witness keys/digests/lengths; verified sidecar equality; current inspector disposition and no-authority/null-admission fields; historical refusal code and null views; native no-latest checks; actual process exit; and precise remaining production/rights/identity/PIT gaps. An optional source span digest and coordinates can be retained without the copied passage. Audit every manual annotation before Git publication because `include_support_text=False` does not sanitize annotations.

The receipt must distinguish **real capture**, **native-format local replay**, **manual semantic annotation**, and **production owner admission** as separate propositions. Record failure honestly if the SEC response or chosen passage does not support a valid candidate. Nothing in this memo is a completed runtime receipt.

## Inspected source provenance

The following file SHA-256 values were computed from the inspected native workspace at head `2a00eff6125d07cc2303b1edbafa00ba1d50d4a5`; Git blobs were read from that exact head. No source was imported or executed by this lane.

| Path | Exact Git blob | File SHA-256 |
|---|---|---|
| `collectors/edgar_forensics.py` | `5f6057fc07fb8d481d481749dc464de668dbbeae` | `8e153f35b1d9f243790c2df16749207243168c42676802f1f0e5a886537a9a29` |
| `collectors/sec_document_spine.py` | `7e787d0fb6406becab938e05835cfdc22c1ab5a1` | `50f5e14533069fa061bcc2c721e461633acf7bacc7510ce987bbb296e27b0b35` |
| `engine/fundamental_forensics/sec_document_spine.py` | `54987bc3557d4bd5e7c7e0ec893b39b42ad988a6` | `7a329e58bc975205d2b55f7ffb2c13a59298636bc1592aa25253d4becd1a1795` |
| `engine/fundamental_forensics/source_sync.py` | `1fc246978a13f9bbac203e9de565d5875ac003b1` | `73ddb5ac6ed910b1f4d9a7d76a944063f3251011e7b2af96d7fbb8306f46776a` |
| `engine/research_vault/r2_store.py` | `8aec6ca9ce727146e970f055692edd993c5f3245` | `7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd` |
| `engine/fundamental_forensics/filing_attestation.py` | `76a17ed1f4eb49a4cbcf7812eb84c063f0e55e65` | `5feb4f77614c4b90df31c65527f866caea3e6598be006574498d8551c8dd5645` |
| `scripts/run_fundamental_forensics_wave2.py` | `905b5a4797c031863d9db7e487a9822bc2516d63` | `93859774a13491bee10aa6cd7657547415d9af84a898fc1443d836ca5ef41f26` |
| `collectors/fundamental_forensics_acquisition.py` | `6ff076a4ed3042844afc932e2adc12ea8117acda` | `fba28cca50d8f8fe249c12bb8f6b9d29dd7e41dd439f32210908fb7869d97216` |
| `engine/company_intelligence/pinned_relationship_candidates.py` | `75ed75f83ff1fa550ce58012ef7eb00ebefb1f77` | `1000497dcfef316f1ad0726c08bcba7ba12dbe305175887e191d6f96512649bd` |
| `engine/company_intelligence/relationship_candidates.py` | `126bd3ad9be95f7d228742eb8699b64e5e92b990` | `27543f4a37202820f34071607b5cbdb1e48a04c30577a876ba1f803e1c41891d` |

Also read: the existing `NATIVE_SOURCE_ADAPTER_SEAM.md`, `EXECUTION_FRONTIER_ADJUDICATION.md`, relevant `EXECUTION_STATUS.md`, owner operator source and existing synthetic local/pinned test definitions. No tests or real-source acquisition ran in this review. The only configuration observation was presence and the native basic user-agent shape check, with no value output. The principal owns the next execution decision and any concrete capture.
