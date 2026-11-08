# 08 - F4 producer outage diagnosis and recovery gate

Status: bounded source diagnosis complete; production recovery not yet executed.
Observed protected procedure: Mastermind 5b244a2bbe4c2a94ec25a887eb4a0d8fafe1ea2f / Skillpack 1.0.1.
Observed Macro main during diagnosis: a74e44fd55120b4e87c35716803d566e5708fe15.
Effect: documentation only. No MarketDesk profile, LaunchAgent, R2 object, workflow dispatch, credential, or production host state was modified.

## Proven outage boundary

The Research Vault publication engine is not the September 24 failure. Git history shows repeated data/research_vault/catalog.json publication through October 4 while source population stopped growing.

Catalog growth stopped sharply on September 24:
- 09:27 generation: 2,769 rows
- 09:57 generation: 2,771 rows
- 10:12 generation: 2,772 rows
- 10:42 generation: 2,773 rows
- 11:57 generation: 2,777 rows
- 12:12 generation: 2,778 rows
- later generations: still 2,778 rows
- latest source published_at: 2026-09-24T09:28:05Z

Later commits advance publication time only. Therefore the failure is upstream of hourly Research Vault ingestion: MarketDesk producer/runtime -> private research_inbox.

## Prior incidents strongly constrain the cause

Issue #6862 had the same external failure shape: hourly Research Vault kept republishing while the real Mac13,1 MarketDesk producer had become unauthenticated. Recovery required stopping the single-writer daemon, authenticating the existing persistent profile, and restarting the same LaunchAgent. It closed PROVEN_LIVE after natural row growth.

Issue #7297 then proved MarketDesk healthy again on September 18 after M1 OOM recovery, with com.mastermindx.research-trickle running, SQLite quick_check OK, fresh downloads/vaults, and successful ingest triggers. The current September 24 cutoff is therefore a new later producer/runtime failure.

## Recurrence gap in current source

Current code correctly detects MarketDesk SessionExpired. After expiry it sets the account to unauthenticated and keeps the daemon alive. The loop then skips discovery and downloads forever. The dead-driver watchdog does not fire because no download attempts occur.

The existing feed watcher only checks whether a marketdesk trickle process exists. A parked auth-expired producer therefore looks alive. marketdesk status reports DB counts and last_successful_run, not live authentication state. The Research Vault source-freshness guard catches the consequence only after its source deadline.

## Current trigger owner

Issue #6949 final closure proves com.mastermindx.research-feed is the current PROVEN_LIVE immediate ingest trigger owner. It reads the canonical external STORAGE database through the bounded read-only feed_probe and triggers the existing research-ingest.yml. Natural feed cycles and a natural one-report ingest were accepted on September 15.

F4 must preserve this trigger unless a separately reviewed migration replaces it.

## PR #7226 ruling

PR #7226 is a legitimate but never production-activated alternative that would retire the feed watcher and move immediate GitHub dispatch into the collector. Its own September 27 checkpoint states that source merge would still not prove production activation.

Treat #7226 as stale/unactivated alternative trigger architecture, not current production authority. Do not merge it wholesale into F4. Salvage only its useful release-lineage work after current-main reconciliation.

## Source-lineage prerequisite

Current collectors/marketdesk_extractor/tools/install_runtime.py freezes the September recovery manifest hash and requires the current source manifest to match the original recovered packet. That preserves historical provenance but means any legitimate edit to trickle.py, feed_probe.py, runtime/feed.sh or other source-owned extractor files makes the canonical verifier reject the release.

Before F4 source modification, establish the accepted split:
- historical recovery manifest/import receipt = immutable provenance
- current release manifest/release receipt = evolvable accepted source

#7226 contains an earlier dual-manifest/release-receipt implementation, but it is thousands of commits behind current main and must be ported selectively. Do not weaken or delete the original recovery receipt.

## Recurrence repair after the release-lineage gate

Reuse incumbent owners only:
1. Persist typed producer authentication health in the existing MarketDesk SQLite meta table: AUTHENTICATED or AUTH_REQUIRED, with UTC timestamp and a non-secret typed reason.
2. Extend existing read-only feed_probe to return that typed state with vault watermark/count.
3. Make existing feed.sh return a visible nonzero result on AUTH_REQUIRED without opening MarketDesk, dispatching duplicate work, or attempting automated login.
4. Expose the same typed state in marketdesk status.

No new daemon, queue, scheduler, bucket, workflow, profile, auth service, or health database is permitted.

## Human production gate

Current MarketDesk source explicitly states that expired-session recovery needs a human: stop the daemon because the profile is single-writer, run marketdesk auth against the existing profile, then restart the same daemon.

Production recovery must therefore prove, in order:
- exact Mac13,1 and canonical external STORAGE database;
- current auth/log evidence;
- stop exactly com.mastermindx.research-trickle;
- authenticate the existing persistent MarketDesk profile;
- restart the same LaunchAgent;
- new discovery after the September 24 cutoff;
- one new real report downloaded and vaulted;
- incumbent feed/hourly ingest admits it;
- canonical PDF, catalog, corpus/full-text and receipt advance;
- source freshness returns healthy without weakening the deadline.

## Current lane state

F4 diagnosis: COMPLETE.
F4 root-cause class: HIGH-CONFIDENCE recurrent auth/runtime failure.
Exact live cause on host: UNPROVEN until host log/profile inspection.
Production recovery: HUMAN HOST GATE.
Recurrence source repair: BLOCKED on source-release-lineage prerequisite.
New production effects from this diagnosis: NONE.

This does not block F1, F2, F8, or other path-disjoint Research Vault AI Fabric work.