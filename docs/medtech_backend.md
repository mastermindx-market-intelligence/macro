# MedTech R14 backend: official outcomes and source changes

## User job and ownership

The first live backend supports finding an official FDA outcome, understanding its exact device/submission scope, opening its source, and reviewing later record changes. It supplies the Watchdesk and Event views in the [R14 Paper design](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1K-0).

Macro owns FDA acquisition, evidence, normalization, revision history and the read projection. Terminal owns personal watches and review state in its existing Supabase account database. The existing Macro authentication and subscription boundary remains authoritative. Company/issuer identity and economic rights remain with the existing company-intelligence owners.

No prospective FDA dates, commercial outcomes, issuer assignments, CMS coverage, safety notifications or delivery claims are inferred from these records. The API reports those capabilities as unsupported.

## Verified source contract

| Source | Native identity | Supported meaning |
| --- | --- | --- |
| [510(k) API](https://open.fda.gov/apis/device/510k/) | k_number | Explicit substantially-equivalent clearance where code SESE is observed |
| [PMA API](https://open.fda.gov/apis/device/pma/) | pma_number + supplement_number | The exact original/supplement action, with unknown codes retained |
| [PMA fields](https://open.fda.gov/apis/device/pma/searchable-fields/) | Supplement remains linked to parent | A supplement is not silently relabeled as a new original-device approval |

Both official overview pages document **monthly** API updates. These are reference feeds, not a real-time prospective decision calendar. `meta.last_updated` describes the acquired dataset; it is not an individual source publication timestamp. Individual publication time remains null.

Observed live PMA records included P150012/S191 and N970003/S311 with decision code OK30. This code was absent from the inspected [published PMA dictionary](https://open.fda.gov/fields/devicepma.yaml). The adapter retains it as unmapped and accepts non-P native identifiers. It never guesses that a 30-day notice is a new-device approval.

The [openFDA authentication page](https://open.fda.gov/apis/authentication/) publishes keyless limits of 240 requests/minute/IP and 1,000/day/IP. The bounded worker has no automatic retries or credentials; it pauses between pages, caps records/page size, refuses redirects and distinguishes a verified no-results response from an unavailable source. A production refresh policy must stay within the existing source budget.

## Evidence and publication

`collectors/medtech/openfda.py` captures raw response bytes and exact request URLs. It verifies every page's count, range, IDs, clock and pagination metadata again at the store boundary. Partial or inconsistent batches cannot commit.

`engine/medtech/store.py` holds private SQLite acquisitions, source-page SHA-256 digests, parser identity, sightings and append-only normalized observations. Unchanged recapture adds evidence without another product change. A → B → A produces three observations. Omission from a later query never deletes a known case. Historical queries use actual observation time, not a backfilled decision date.

Each public revision carries its own decision date and device name. Correcting a date later cannot retroactively turn an old backfill into a new-supplement development. Exact diffs expose only approved scalar product fields.

`engine/medtech/publication.py` validates a closed product payload, writes immutable content-addressed generations, and advances the current pointer last. The API never opens the private database. A failed refresh keeps the prior valid projection and reports refresh failure. File reads and payload sizes are bounded; symlink/digest/schema failures fail closed.

The current API only serves the **current generation**. A requested generation that has advanced returns 409. This prevents mixed list/detail or pagination results; it does not implement a retained saved-brief archive.

## Authenticated API

All endpoints use `/api/medtech`, require the existing verified user and paid-site gate, and return private/no-store responses.

| Endpoint | Purpose |
| --- | --- |
| GET /health | Availability, failed refresh, source clocks and supported capabilities |
| GET /events | Device/applicant/native-ID search; pathway, decision and dataset filters |
| GET /events/{event_id} | Exact current record, latest revision and source |
| GET /events/{event_id}/changes | Revision history, including explicitly labeled first observation |
| GET /subjects/{subject_type}/{subject_id} | Verify a watch subject and its supported triggers |
| GET /changes | Subject-scoped revisions after a subscription baseline |

List and change pages cap `limit` at 100 and require `snapshot_id` for continuation offsets. An optional exact `revision_id` supports validating a review acknowledgment without fetching every page.

Watch subjects are either one exact `event` or a `pma_application` identified by an exact P-number. The latter includes its supplements. Supported triggers are `record_changed` and, for a PMA application, `new_supplement`. A new-supplement item requires an initial observed decision date strictly after the subscription's calendar day; old backfills and ambiguous same-day ordering are suppressed. First indexing of an exact event is never a new-development alert.

## Bounded qualification

The M2 source qualification acquired October 1–5, 2026 decisions: **37 510(k) records and 20 PMA records**, 57 baseline records total. These are not57 newly announced catalysts. Both acquired datasets reported last_updated 2026-10-05.

The initial acquisition completed at 2026-10-19T01:56:25.002631Z. Raw receipts and the private qualification database stay outside Git in `reports/medtech-r14-runtime/`. Synthetic fixtures are confined to isolated tests and never promoted as real records.

Run a bounded acquisition using the normal source worker:

```sh
python3 scripts/medtech_worker.py \
  --state-db /private/operator-selected-path/events.sqlite3 \
  --public-root /separate/operator-selected-path/public \
  --start 2026-10-01 --end 2026-10-05 --max-records 2000
```

The private and public paths must be disjoint. No source timer is installed or enabled by this CLI. API deployment alone cannot establish a collector refresh schedule.

Local regression command: `python3 -m pytest tests/test_medtech.py -q`. The dedicated MedTech contract workflow runs these tests with the shared conftest guards.

## Research expansion, tied to user value

1. **Who benefits:** consume the existing issuer registry and filing/disclosure owner. Applicant-name similarity can produce a review candidate; it cannot establish a listed issuer's territorial economic rights. Require explicit subsidiary, acquisition, license or distribution evidence with an accession/document passage and dates. [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) provide issuer metadata and filings; company facts alone do not prove device-level rights or revenue.
2. **Useful upcoming milestones:** qualify the actual parameter/response schema for [CMS national coverage APIs](https://api.coverage.cms.gov/docs/release_notes), then separate NCA process deadlines, proposed determinations, final coverage and effective dates. Do not guess Swagger parameters. Local coding-detail license tokens are outside this initial adapter.
3. **Safety developments:** use [FDA device recalls and early-alert communications](https://www.fda.gov/medical-devices/medical-device-safety/medical-device-recalls-and-early-alerts) for actual public notices and revisions. Keep early alerts distinct from confirmed recalls. The [openFDA recall](https://open.fda.gov/apis/device/recall/) and [enforcement](https://open.fda.gov/apis/device/enforcement/) feeds explicitly warn against direct public-alert/lifecycle use; use them for identity/scope enrichment.
4. **De Novo:** the [official database](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm) exists. Its actual extraction contract still needs qualification. No undocumented openFDA De Novo endpoint is invented here.
5. **Delivery and saved briefs:** use existing account/outbox ownership when these consumers are implemented. A current event URL is not a preserved historical brief; the saved object must retain an accepted revision/generation or a frozen content projection.

## Release acceptance

Keep source qualification, authenticated API test overrides, production account proof, SQL catalog proof, and actual scheduled refresh proof distinct. Do not label a design fixture or a local TestClient override as a production paid-user success.

Before source activation, verify production disk capacity, provision disjoint private/public paths, and prove the API's read-only/deny filesystem mounts. The 2026-10-19 deployment preflight observed the VPS root volume at 99% usage with about 1 GB free; resolve the existing retention/capacity issue before introducing a persistent collector or build.
