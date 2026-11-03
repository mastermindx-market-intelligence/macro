# Research Desk: October 15 intake outage

Observed October 21, 2026 Central / October 22 UTC. This is incident evidence and a recovery checklist, not a new publication policy or a declaration of recovery.

## Outcome and scope

MarketDesk intake is stopped by rejected browse and metadata responses. The adapter incorrectly treats every malformed feed response as an expired session and parks the account indefinitely, even while other authenticated endpoints work. A separate missing browser dependency was found and repaired. Downstream Research Vault publication remains held under the existing recovery owner. The public catalog is stale; source and display corrections alone do not establish restored intake or released publication.

The existing owner and unresolved-effect record remain [Research Vault #8438](https://github.com/mastermindx-market-intelligence/macro/pull/8438#issuecomment-6199947153). This October 15 intake failure does not invalidate the previously accepted source import or the October 11 recovery.

Source baseline for this incident workspace: Macro `d5d0be27e245833245b792f7e86c437a09be9180`. Governing Mastermind pin: `c9cbee5569ba50e30e28715d930809061a169517`.

## Direct observations

| Boundary | Evidence |
| --- | --- |
| MarketDesk session | M1 producer DB reports `AUTH_REQUIRED`, reason `NO_AUTHENTICATED_PROFILE`, required since `2026-10-15T13:13:17.654204+00:00` (8:13 a.m. Central). |
| Exact initiating error | M1 log at `2026-10-15T06:13:18-0700`: discovery received a JSON object `{'success': False}` where the authenticated API contract requires an array; the daemon logged `SESSION EXPIRED` and parked the profile. |
| Last intake | Last discovered `2026-10-15 12:45:38`; last downloaded `13:08:14.681200Z`; last vaulted `13:08:15.902897Z`. The existing feed watermark matches the last vaulted timestamp. |
| Producer inventory | 2,956 COMPLETE, 7,386 DISCOVERED, 1,560 SKIPPED_EXCLUDED, 1 SKIPPED_UNSUPPORTED. DISCOVERED is a pending inventory, not a promise that every record is downloadable or eligible. |
| Process and storage | The sole `com.mastermindx.research-trickle` launch agent remains present and repeatedly logs `NOT AUTHENTICATED — skipped`. External volume free space was 365.56 GiB against the configured 100 GiB floor; historical storage-guard errors are not the current blocker. |
| Feed bridge | Runs every 900 seconds and logs `AUTH_REQUIRED`, followed by `nothing new`; its watermark has not advanced. A live process and an exit-zero feed tick do not prove an authenticated producer. |
| Publisher | Workflow ID `319072296` (`research-ingest.yml`) is `disabled_manually`, last updated October 19. Re-enabling it is not part of the display fix. |
| Public API | At `2026-10-22T02:15:53Z`, `/api/research/catalog` returned HTTP 200 with `private, no-store`, 2,960 reports, `generated_at=2026-10-19T08:48:02.670798Z`, `stale=true`, and `catalog_health.reason=age_exceeded`. |
| Source distinction | The newest public preview is an internal Mastermind Research report dated October 19. The next two MarketDesk items are dated October 15. An internal addition does not prove MarketDesk recovery. |
| Existing alert | [Heartbeat run 39702926705](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39702926705), job `119576165538`, failed at 00:58 UTC with `PRODUCER_STALE` (newest overall report 73 hours old). Neither `RESEARCH_VAULT_SOURCE_OUTAGE_ACK` nor a custom maximum age variable was set. |

The initial DB inspection used SQLite read-only mode and query-only. Subsequent controlled profile diagnostics, browser dependency installation and restoration of the existing launch agent are recorded below. No report rows, watermark, credentials, workflow state, canonical catalog or corpus were manually changed.

## Immediate display repair

When the selected catalog is stale, Research Desk must retain its known archive count and its saved report cards, suppress the three figures presented as weekly activity, and say:

- EN: **Research updates are delayed. Showing the saved catalog.**
- ZH: **研报更新延迟，正在显示已保存的目录。**

The existing status line owns the actual saved timestamp. The unavailable state, fresh catalog behavior, entitlement preview limits, report selection, and PDF access gates remain on their existing paths. The copy must not expose local host or authentication internals.

The open first-paint PR [#8871](https://github.com/mastermindx-market-intelligence/macro/pull/8871) remains held under its own conditions. This incident does not release or supersede that PR.

## Fresh M1 diagnosis and controlled recovery

Canonical installation: `~/mastermind-research/marketdesk_paper_extractor`; existing profile: `/Volumes/STORAGE/MastermindX/marketdesk/browser_profile`. All profile checks used one owner: unload the existing launch agent, confirm its daemon/driver/browser exited, run a bounded diagnostic, close that diagnostic, then restore the same production plist. No cookies, credentials, DB rows, watermark, quota or disk floor were reset.

The initial `AUTH_REQUIRED` record was a latched classification, not a fresh request on each tick. Reading the original October 15 log established `latest=25 picks=250 saved=0` immediately before `browse/current` returned `{"success": false}`. The original "session expired" text alone did not establish whole-session expiry.

### Missing browser dependency repaired

At `2026-10-22T02:54:14Z`, the supported `trickle --once --dry-run` diagnostic failed before any authentication request: Playwright 1.61.0 could not find its required `chromium_headless_shell-1228` executable. The daemon's broad exception handling had also labeled this startup failure as unauthenticated.

The matching browser was installed through the **existing** runtime interpreter:

```bash
cd "$HOME/mastermind-research/marketdesk_paper_extractor"
.venv/bin/python -m playwright install chromium
```

No Python package upgrade or alternate browser/profile was used. Installation completed successfully. A second supported dry-run at `02:55:58–02:56:01Z` reported `session ready`, quota 70, used-in-24-hours 0, and closed without a remaining profile owner. This proves the saved profile could authenticate; it does not prove discovery or publication.

A normal restart at `02:57:06Z` again read latest/picks successfully and failed at browse. No new report was discovered, downloaded or vaulted.

### Endpoint-specific rejection reproduced

A bounded same-context read at `03:01:09–03:01:15Z` produced:

| Request | Result |
| --- | --- |
| POST `/api/mobile/latest/latest`, before browse | HTTP 200, JSON array of 25 IDs |
| GET `/api/mobile/library/browse/current` | HTTP 200, `{"success": false}` |
| POST `/api/mobile/latest/latest`, after browse | HTTP 200, JSON array of 25 IDs |
| GET one returned item's `/path` | HTTP 200, `{"success": false}` |
| Authenticated `/library/browse` HTML | HTTP 200, MarketDesk application shell |

The current authenticated frontend still calls the same browse and metadata endpoints. A request without the session returned `{"success": false}` from latest, confirming that the positive controls depend on authentication.

Further bounded reads through `03:06:58Z` established:

- Latest pages 0, 1 and 2 each return 25 distinct IDs. This is more capable than the July API note, but does not prove date coverage.
- POST `items/provision` rejects two returned IDs with `{"success": false}`; explicit JSON encoding and the same-origin header do not change the result.
- GET one returned item's metadata also returns `{"success": false}`.
- GET `/api/user/limits` returns `previews=true` and `downloads=true`. These booleans are not proof of either remaining quota or a reached cap. The current frontend applies `previews` to an `active` CSS class and only assigns `downloads`; its observed consumers do not establish entitlement semantics.
- Adding a JSON content-type header does not repair browse. No speculative header patch or latest-only fallback is justified.

These observations establish selective rejection of authenticated data requests. They do **not** distinguish an account-specific provider restriction from an upstream service defect. A valid ID feed without metadata cannot restore research intake. A new login has not been shown to be necessary.

### Normal routing initialization checked

The current authenticated frontend races image loads from `ts1` through `ts5` and posts the selected host to `/api/user/preferences/ts/<host>`. A single controlled reproduction used only those five observed hosts, validated each JPEG by successful image decoding, and selected `ts2`. The one JSON preference POST returned HTTP 200 with `success=true`. Latest still returned 25 IDs before and after; browse and provision still returned `success=false`. The normal routing update was acknowledged but did not restore data access. No other host update or ambiguous-write retry was attempted.

The same frontend's desktop-width bootstrap was read without executing it: the server had already rendered desktop preference `d`, matching the collector's desktop viewport. No device-width preference update was needed. The initial image-validation attempt stopped at an unavailable optional decoder import before any service or account effect; the actual attempt used the existing macOS image decoder.

Each diagnostic closed before restoring the canonical launch agent. After the final frontend read, the sole daemon was PID 24007. The old code still parks on the provider response; process presence is not recovery.

### Adapter corrections and acceptance

The source repair distinguishes an unexpected endpoint response from a freshly confirmed negative authentication check. A positive control keeps the account eligible for the existing discovery cadence while surfacing the endpoint error. It never converts a rejected response into an empty or successful discovery. Negative controls retain the existing conservative expiration path; a negative boolean can still reflect transport failure. Unexpected post-start probe/client-construction exceptions also retain the legacy unauthenticated fallback. This repair does not make every possible `AUTH_REQUIRED` observation definitive proof of cookie expiry.

Browser-entry failure must report `UNKNOWN / BROWSER_START_FAILED` through the existing metadata and dry-run plan. Partial entry must close any created context and stop its driver while preserving the original error. No new scheduler, health database or authentication ceremony is introduced.

Source installation follows the existing post-merge installer/readback contract. Matching browser installation and a supported sole-owner dry-run are runtime readiness checks; source-byte verification and import smoke alone cannot prove readiness. Intake is recovered only after metadata hydration succeeds and an actual eligible report advances through discovery, download and vault publication.

### Ready MarketDesk evidence request

For the existing account, reproduce the application's browse/report-opening behavior and ask the provider to investigate the authenticated sequence above. Supply UTC timestamps, endpoint paths and the nonsensitive response shapes. Ask whether browse/item/provision access is valid for the account and whether these endpoints are experiencing a service fault or require an updated documented request contract. Do not supply cookies, passwords or bearer tokens.

The connected browser interface was unavailable, so actual interactive MarketDesk UI behavior has not been verified. No support message was sent. Keep this boundary open until the data endpoints return usable report metadata and intake proof advances.

## Separate publication recovery gate

The existing hold identifies original run [38517760919](https://github.com/mastermindx-market-intelligence/macro/actions/runs/38517760919), attempt 1, job [115700308577](https://github.com/mastermindx-market-intelligence/macro/actions/runs/38517760919/job/115700308577).

Independent read-only reconstruction bound it to Macro `72f8c6ac333fc243b825e7c8f2d07e3b8b16b02d` on `mac-builder-3` / `m2studio`, invoking `python -m scripts.ingest_research --require-store` from 05:39:21 through cancellation at 05:54:56 UTC on October 14.

The retained backfill marker at 05:42:02 reports zero candidates/rows. There are no provider request IDs, authenticated intent/outcome journal, final phase timing, or completion summary. The source used unconditional boto3 PUTs with adaptive retries. Silence after the marker cannot prove later publication stages were never issued.

Potential write classes are:

| Object class | Original behavior |
| --- | --- |
| `research_vault/<id>.pdf` | Unconditional per-document promotion |
| `research_vault/corpus.sqlite` | Unconditional checkpoint/final corpus publication |
| `research_vault/catalog.json` | Unconditional visibility publication after a successful logical corpus call |
| `research_inbox/_processed/<id>.json` | Unconditional processed receipts after a successful logical catalog call |
| `research_vault/fulltext/v1/...` | Potential create-only derivative writes |

The source path contains no delete, copy, managed multipart or generation-adoption operation. Later successful workflow runs and present object reads do not provide the missing original-attempt outcomes.

Current generation recovery requires a real retained generation journal and cannot adopt this legacy run. Current reader/writer contracts also have no supported independent-namespace transition: catalog, corpus, receipts and downstream consumers still bind the same canonical keyspace. Do not substitute a prefix wrapper or a manually asserted qualification flag.

### Ready provider evidence request

Through the existing authenticated Research Cloudflare account, request attributable outcomes for all potentially accepted R2 PUT attempts from the exact run/window/keyspace above, including delayed completion after cancellation. Request IDs were not retained, so the provider may need verified account, bucket, credential identity, source IP, user agent, key and size to distinguish concurrent callers; no secret value is needed in a report.

If historical records are unavailable, ask for an authenticated provider-supported closure or fencing determination that establishes whether any already accepted request from this execution can still commit. Blocking future authentication alone is not proof about previously accepted requests.

Cloudflare's [R2 consistency documentation](https://developers.cloudflare.com/r2/reference/consistency/) explains why an uncertain write is not settled by a subsequent read. [R2 Data Access Logs](https://developers.cloudflare.com/r2/buckets/data-access-logs/) require prior enablement, cannot backfill, have seven-day retention, and are best-effort; absence of a log is not proof of absence.

Cloudflare's [bucket-lock documentation](https://developers.cloudflare.com/r2/buckets/bucket-locks/), updated October 20, provides a real prospective fence: after a successful rule update, protected existing objects cannot be overwritten, including completion of earlier uploads. It does not prevent creation of absent keys and would also block the intended publisher's updates. The documentation does not establish permanent rejection after removing a lock. This is a candidate for canonical-owner containment review, not evidence that the present hold is already cleared.

Ask the provider specifically whether an applied-and-later-removed lock permanently rejects already admitted requests, and what covers creation of previously absent keys. Require the scope, effective timestamp and attributable evidence before treating it as settlement. No lock was applied.

Provider access was not available in this diagnostic surface. No support message was sent. The original request remains unresolved.

After supported settlement, use the existing owner's release procedure: qualify the exact producer and all current admitted attempts, reopen the same noncanceling workflow once, consume that execution, and verify the resulting exact report identities through catalog, search and authenticated PDF opening. No replacement scheduler, replay or duplicate canary is authorized by this note.

## Acceptance before calling this incident fixed

- The same M1 profile passes a fresh authentication control, and browse/provision return usable report metadata.
- At least one newly discovered post-October-15 MarketDesk report reaches the existing inbox under the quota policy.
- The original publisher uncertainty is settled by supported evidence, or the canonical owner has accepted and proven a containment transition.
- The existing publication workflow completes with acknowledged outputs.
- That report's exact identity appears in the real Research Desk catalog and is discoverable; an entitled user can open its PDF.
- Source freshness is checked specifically against MarketDesk intake as well as the overall catalog clock.
- The existing heartbeat no longer reports `PRODUCER_STALE`; no outage acknowledgment or threshold relaxation is used to manufacture success.

Until those conditions are met, the incident remains open. The display repair is a bounded improvement, not end-to-end recovery.

## Display validation

Integrated onto refreshed main `a1ff21e17ab43872758d653e4295f9a805fca350`; the affected app and page-test source were unchanged from the initial baseline. The local page suite passed **36 tests**, including **seven actual-function Node VM cases** for stale live data, saved fallback, unavailable data, fresh aggregates, missing preview aggregates, known zero, and language change during initial loading. Independent review required the loading no-op before the stale branch; it is included. The existing page suite invokes the Node regression, so it remains inside the established Research Vault CI owner. The only overlap with held #8871 is an appended test function; its existing changes and hold are preserved.

The browser plugin returned `Connection closed`, so these are source/runtime regression results, not a rendered-browser or authenticated product-path proof. Publication and live served-byte verification must be recorded separately. The read-only Fabric audit's excerpt-artifact and unsupported themes-count suggestions were rejected; the implementation contribution was reviewed and tested before scoped acceptance.


## Adapter and package validation

The integrated repair adds 65 cases to the existing test files: 46 cover endpoint/provision response classification and failed discovery behavior; 19 cover startup classification, aggregate auth health, reopen, dry-run output and partial browser cleanup. The failed-later-provision-chunk case was first reproduced against the old source, which returned partial success without raising.

On the actual checkout:

- The full standalone extractor suite passed **412 tests**.
- The installer/lineage and Research Desk page suites passed **61 tests** (25 lineage plus 36 page tests, including the existing wrapper around seven Node VM cases).
- The current source verifier passed before and after tests: exactly **58 payload files**, no missing, extra, mismatched or symlinked payloads.
- Current release: `marketdesk-endpoint-auth-discrimination-20261022-v1`; current manifest SHA-256: `9808e50683c65728c73fed5d40f7d3f358994b01a22160de2e446249c3d60132`. The immutable recovery manifest and historical import receipt were preserved.

The paid implementation contribution was a three-file blueprint validated only against excerpt-derived fixtures. Its returned inline diff contained a joined-line formatting defect and did not include its claimed test-file bytes. The parent integrated the functions against the real files, added the approved provision discriminator, and supplied the real regression tests above. No fixture-only pass is treated as checkout or runtime evidence.

The first PR CI run, [39712669527](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39712669527), failed only the logical `admin-js-no-undef` check: both the candidate and its differential base timed out after 180 seconds while invoking the pinned `eslint@8.57.1` through `npx`. The runner was GitHub-hosted `ubuntu-latest` (`GitHub Actions 1000386442`). This identifies a tooling timeout, not a confirmed network cause or an adapter regression. The updated head must pass ordinary CI on its newly allocated runner; no guard bypass is used.
