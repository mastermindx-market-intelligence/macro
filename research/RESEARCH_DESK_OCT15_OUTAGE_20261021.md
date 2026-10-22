# Research Desk: October 15 intake outage

Observed October 21, 2026 Central / October 22 UTC. This is incident evidence and a recovery checklist, not a new publication policy or a declaration of recovery.

## Outcome and scope

MarketDesk intake is stopped by an expired persistent browser session. Downstream Research Vault publication is separately held under the existing recovery owner. The public catalog is stale. Repairing the page's stale-state presentation does not restore intake or release publication.

The existing owner and unresolved-effect record remain [Research Vault #8438](https://github.com/mastermindx-market-intelligence/macro/pull/8438#issuecomment-6199947153). This new October 15 authentication failure does not invalidate the previously accepted source import or the October 11 recovery.

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

DB inspection used SQLite read-only mode and query-only. These observations did not change the database, profile, watermark, credentials, launch agents, workflow state, catalog, or corpus.

## Immediate display repair

When the selected catalog is stale, Research Desk must retain its known archive count and its saved report cards, suppress the three figures presented as weekly activity, and say:

- EN: **Research updates are delayed. Showing the saved catalog.**
- ZH: **研报更新延迟，正在显示已保存的目录。**

The existing status line owns the actual saved timestamp. The unavailable state, fresh catalog behavior, entitlement preview limits, report selection, and PDF access gates remain on their existing paths. The copy must not expose local host or authentication internals.

The open first-paint PR [#8871](https://github.com/mastermindx-market-intelligence/macro/pull/8871) remains held under its own conditions. This incident does not release or supersede that PR.

## M1 authentication recovery

Canonical installation: `~/mastermind-research/marketdesk_paper_extractor`; existing profile: `/Volumes/STORAGE/MastermindX/marketdesk/browser_profile`.

The installed `marketdesk auth --help` confirms `--timeout`. Source `auth.py` deliberately opens a headed persistent Chromium context and waits for the user to log in; it never stores a password. `cmd_auth` returns zero only after the API returns an authenticated array response.

This procedure requires the operator at the M1 desktop. Do not start a second browser against the profile while the trickle daemon owns it. Do not clear cookies, create a replacement profile, reset the DB or watermark, or lower the disk floor.

1. Stop the one existing `com.mastermindx.research-trickle` launch agent and verify that its browser/profile owner has exited.
2. In Terminal on the M1, from the existing installation, run:

   ```bash
   cd "$HOME/mastermind-research/marketdesk_paper_extractor"
   .venv/bin/marketdesk auth --timeout 600
   ```

3. Complete MarketDesk login in the window it opens. Require the terminal to print `Authenticated.` and return zero. A window opening alone is not success.
4. Resume only the existing launch agent using its existing production plist after the auth command has closed its browser.
5. Verify the producer's own DB metadata changes to `AUTHENTICATED` with a new observation, discovery advances past October 15, and a real eligible report progresses through download and vault publication under the existing quota policy.
6. Keep the downstream workflow disabled until the separate publisher gate below is settled. Local intake into the existing inbox is not permission to publish the canonical catalog.

The agent can handle stopping, resuming and verification when the operator is present; the login itself requires user interaction. No authentication ceremony was started during the diagnostic pass.

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

Provider access was not available in this diagnostic surface. No support message was sent. The original request remains unresolved.

After supported settlement, use the existing owner's release procedure: qualify the exact producer and all current admitted attempts, reopen the same noncanceling workflow once, consume that execution, and verify the resulting exact report identities through catalog, search and authenticated PDF opening. No replacement scheduler, replay or duplicate canary is authorized by this note.

## Acceptance before calling this incident fixed

- The same M1 profile is authenticated and its current metadata proves it.
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
