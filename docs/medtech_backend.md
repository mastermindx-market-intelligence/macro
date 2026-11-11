# MedTech R14 backend: official outcomes and source changes

## User job and ownership

The backend supports finding an official FDA outcome, understanding its exact device/submission scope, opening its source, and reviewing later record changes. It supplies the Watchdesk and Event views in the [R14 Paper design](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1K-0).

Macro owns FDA acquisition, evidence, normalization, revision history and the read projection. Terminal owns personal watches and review state in its existing Supabase account database. The existing Macro authentication and subscription boundary remains authoritative. Company/issuer identity and economic rights remain with the existing company-intelligence owners.

No prospective FDA dates, commercial outcomes, issuer assignments, CMS coverage, safety notifications or delivery claims are inferred from these records. The API reports those capabilities as unsupported.

## Verified source contract

| Source | Native identity | Supported meaning |
| --- | --- | --- |
| [510(k) API](https://open.fda.gov/apis/device/510k/) | k_number, including observed DEN identifiers | Explicit substantially-equivalent clearance for SESE; observed De Novo DENG decisions remain separate grants |
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

The M2 source qualification acquired October 1–5, 2026 decisions: **37 510(k) records and 20 PMA records**, 57 baseline records total. Both acquired datasets reported `last_updated` 2026-10-05. These establish the initial reference baseline; they are not evidence of 57 newly announced catalysts.

The initial acquisition completed at 2026-10-19T01:56:25.002631Z. On October 20, the retained raw pages were replayed into a separate schema-2 database using their original observation clocks. All 57 normalized state hashes and observation times remained unchanged. Atomic publication, read-back, list/detail/health responses and stale-generation refusal passed using an explicit local authentication override. The [sanitized receipt](evidence/medtech-r14-retained-source-20261020.json) records the raw-page digests, historical cutoff and exact public generation.

Raw receipts and both private qualification databases stay outside Git in `reports/medtech-r14-runtime/`; the original acquisition remains untouched. Synthetic fixtures are confined to isolated tests and never promoted as real records. Local authentication overrides do not establish production paid-account access.

Run a bounded acquisition using the normal source worker:

```sh
python3 scripts/medtech_worker.py \
  --state-db /private/operator-selected-path/events.sqlite3 \
  --public-root /separate/operator-selected-path/public \
  --start 2026-10-01 --end 2026-10-05 --max-records 2000
```

The private and public paths must be disjoint. No source timer is installed or enabled by this CLI. API deployment alone cannot establish a collector refresh schedule.

Local regression command: `python3 -m pytest tests/test_medtech.py tests/test_medtech_deployment.py -q`. The dedicated MedTech contract workflow includes their complete source and deployment input closure and runs them with the shared conftest guards.

The October 20 composition with protected main `f54eeb09f3473e091ea55416a8dcad9196603e60` passed **85 focused tests and 31 subtests** on M2. This includes MedTech contracts and deployment refusals, repository import precedence, the API restart import closure, cross-worker configuration isolation, and curated CI input closure. The [deployment qualification receipt](evidence/medtech-r14-deployment-qualification-20261020.json) binds the result to exact file hashes and records independent source review. This isolated macOS qualification does not claim a full repository-suite pass, actual Linux mount activation, or a live paid-account request; hosted CI and production readback are separate release gates.

### Recovered 2026 decision-range qualification

The retained October 20 acquisition covers decision dates January 1–October 20, 2026 and contains **4,323 baseline records**: **2,571 from the 510(k) endpoint and 1,752 from PMA**. Both datasets report `last_updated` October 5, 2026. The 510(k) response includes **26 observed De Novo records**; these are identified by native `DEN` numbers and DENG grants, with links to the official De Novo record. This is complete for the verified bounded queries, not a comprehensive standalone De Novo denominator or a current announcement feed.

The recovery preserves those original observations and reacquires no FDA data. The [local production-scope receipt](evidence/medtech-r14-production-scope-local-qualification-20261020.json) binds the retained generation and current source files, verifies 4,323-record listing, health, exact De Novo/legacy-PMA/supplement detail, history and watch subjects, private cache headers and stale-generation refusal. The recovered candidate passes **94 focused tests and 31 subtests**. A shared CI failure was repaired by declaring `engine/medtech/__init__.py` in the 13 jobs already declaring its modules; the ancestor-dependency ratchet passes with its original ceiling unchanged. Hosted checks remain separate.

The acquisition uses 250-record pages to stay within response-size bounds; retained earlier acquisitions keep their recorded page size and original request evidence. Parser identity advances to `medtech_openfda_v2`. Terminal #1084 aligns gateway, exact watches and SQL validation with the observed native identifiers; application-family watches stay P-number-only.

## Research expansion, tied to user value

1. **Who benefits:** consume the existing issuer registry and filing/disclosure owner. Applicant-name similarity can produce a review candidate; it cannot establish a listed issuer's territorial economic rights. Require explicit subsidiary, acquisition, license or distribution evidence with an accession/document passage and dates. [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) provide issuer metadata and filings; company facts alone do not prove device-level rights or revenue.
2. **Useful upcoming milestones:** qualify the actual parameter/response schema for [CMS national coverage APIs](https://api.coverage.cms.gov/docs/release_notes), then separate NCA process deadlines, proposed determinations, final coverage and effective dates. Do not guess Swagger parameters. Local coding-detail license tokens are outside this initial adapter.
3. **Safety developments:** use [FDA device recalls and early-alert communications](https://www.fda.gov/medical-devices/medical-device-safety/medical-device-recalls-and-early-alerts) for actual public notices and revisions. Keep early alerts distinct from confirmed recalls. The [openFDA recall](https://open.fda.gov/apis/device/recall/) and [enforcement](https://open.fda.gov/apis/device/enforcement/) feeds explicitly warn against direct public-alert/lifecycle use; use them for identity/scope enrichment.
4. **De Novo:** observed `DEN` records returned by the existing 510(k) endpoint are now qualified and linked to the [official database](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm). Comprehensive standalone extraction and coverage remain unqualified; no undocumented openFDA De Novo endpoint is invented.
5. **Delivery and saved briefs:** use existing account/outbox ownership when these consumers are implemented. A current event URL is not a preserved historical brief; the saved object must retain an accepted revision/generation or a frozen content projection.

## Deployment and scheduled refresh

The canonical API deployment provisions only the dedicated `macro-medtech` identity and empty `/srv/medtech/private` and `/srv/medtech/public` anchors before reviewing or restarting the API. Existing symlinks, unsafe owners/modes, shared identities and orphaned trees are refused without adopting or recursively repairing them. Existing Market Memory, Company Intelligence, BioCatalyst and Ticker News guards remain in place.

The reviewed API fragment first runs the same fixed provisioning helper through a privileged `ExecStartPre`. Its separate process runs outside the API mount namespace and must succeed before the application starts. This covers first adoption when the canonical updater installs its successor but continues executing its predecessor. The application command keeps its normal sandbox. The fragment sets `MEDTECH_PUBLIC_ROOT=/srv/medtech/public`, mounts that publication root read-only, and makes the private root inaccessible. Both mounts are mandatory. Before each refresh, a fixed root-only inspection checks the running API's exact installed fragment, lack of drop-ins/reload drift, stable process/invocation/mount namespace, actual mount flags and directory identities, and its effective publication-root environment. Unrelated system mount stacks do not affect the MedTech decision.

Acquisition runs as the dedicated nonroot account with no capabilities. The oneshot service uses the existing checkout and Python environment, explicit credential-path exclusions, a 15-minute timeout, 512 MiB memory ceiling and CPU/task/I/O bounds. It has no automatic retry. Its fixed command covers the configured start date through the current UTC day, capped at 10,000 records per endpoint. The example start date is 2026-01-01; this scope is explicit and does not claim all FDA history.

The worker checks for at least **5 GiB available on each storage filesystem before opening the store or acquiring sources**. Low space records a failed attempt and preserves the previous publication. This check does not reserve space or delete retained evidence. The CLI's zero default remains available for isolated qualification.

The existing API update/setup paths do not install or activate this source timer. After the reviewed source is merged and deployed, the release owner uses:

1. `bash /opt/macro/app/deploy/medtech-setup.sh` to validate and install the service/timer without enabling or starting either.
2. On the first installation, install the reviewed `medtech-environment.example` as root:root mode 0600 at `/etc/macro-medtech.env`. Review an existing file rather than overwriting it. Only `MEDTECH_START_ON` is accepted.
3. Run `/usr/bin/python3 -I /opt/macro/app/deploy/medtech-api-boundary.py`, then explicitly start `macro-medtech.service` and inspect its exit status and the API's published generation/health.
4. After the first refresh is accepted, enable `macro-medtech.timer`. Its daily schedule is 06:10 UTC with up to 20 minutes of jitter.

The installer refuses active/enabled units or drop-in adoption. Future source changes continue through the existing Git and deployment owners; an installed timer alone is not proof that a refresh succeeded.

## Release acceptance

Keep source qualification, authenticated API test overrides, production account proof, SQL catalog proof, and actual scheduled refresh proof distinct. Do not label a design fixture or a local TestClient override as a production paid-user success.

The fresh read-only VPS check at 2026-10-20T03:40:41Z found **36,907,368,448 bytes available and 56% usage** on the root filesystem. It supersedes the October 19 disk-full observation; no cleanup was required. Capacity, actual API mount readback, the first complete source refresh and paid-account consumer behavior must still be checked at activation.
