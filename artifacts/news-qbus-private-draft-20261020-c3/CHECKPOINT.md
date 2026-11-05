# Integrate News Intelligence — checkpoint 2026-10-20 17:32 UTC

## Shipped and verified

Primary Macro PR [#9846](https://github.com/mastermindx-market-intelligence/macro/pull/9846) merged at 17:06:32 UTC as `1298ed4281362329c682a1f7c038b932e4ccbb64`, from reviewed candidate `b82af8dae3b05e7eaea198cfe49d61fb9b8ce595`. Binding CI [39453623427](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39453623427) and the main-target authority/fence checks concluded green. Fresh-main integration and post-merge blob checks retained all 110 owned paths; only the deliberately integrated CI manifest differed. The primary remote branch is deleted.

The normal updater installed the merge and restarted the API and the existing sole news writer. Its exit 1 recorded the independently frozen W2C lane after the news deployment steps completed; that lane was left under its existing owner.

Publisher operation `news-publisher-activation-20261020-c3` applied once at 17:23 UTC. Reviewed operation SHA-256: `4f6b515ad32295b3b2ba6a896801cb32afbac5904ed8de9d30585720cda84428`. All 31 installed critical source pins matched, the actual service-environment check qualified three publishers and 503 universe members, and both services restarted successfully. The existing credential was retained only in the writer environment; the API received receipt paths. No entitlement, public editorial release, or trading authority was created.

At 17:26:29 UTC the canonical read-only store census proved 201 active Zacks reports, 123 Motley Fool reports, and 96 GlobeNewswire reports. Health was live, the additional poll was available with 420 accepted reports, and no catchup failure or unresolved gap was present. New groups use `qbus_news_cluster.v3`; legacy groups retain their recorded provenance. The authenticated AAPL News panel displayed the new sources after a fresh page load. See `publisher-activation-live.json` for the separate activation and live receipts. Do not replay the activation: the existing private phase carrier is under `/var/lib/macro-ticker-news/news-publisher-activation-20261020-c3/`.

## Current owned work

The private Press consumer is in the separate managed workspace/branch `news-qbus-private-draft-20261020-c3` / `sol/web-news-qbus-private-draft-20261020-c3`. At this checkpoint it is qualified locally and being committed; it has not yet been published as a PR. Its original base is b82; merge current main into this private carrier before publication so the already-squashed primary integration is not presented again.

The final four-suite managed run passed **252 tests, one existing skip** at 17:24:35 UTC. It exercised the real writer and canonical dispatcher with an isolated external client; no live provider was invoked. Final test SHA-256: `5827148fc6e899c191a5a8dca562103f3df909498eb749e164dba1c1ae367cc3`. Independent source/test review is retained beside this checkpoint.

Source-change CI is bound through the existing `ticker-news-qbus` job with the Press run/writer suites and their dependencies. The canonical closure added 74 derived paths plus the two suites, changes only that job, and introduces no closure or ancestor blind spot. The ancestor ratchet stays non-vacuous: 339 inherited rows become 336. Final pre-main manifest SHA-256: `cae6e9acf19b8ac6489b59b0c7b111fd2b9b2312a391131d16abc2ba485526cd`. Do not replay the earlier broad ancestor experiment; it was removed before commit.

The normal covering render [39463170560](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39463170560) was still pending at 17:25 UTC. The shared runner was serving an older engine render whose actual post-pull source predates the integration. The stock-page panel remains awaiting a covering generated commit and served-page proof. Preserve the shared queue; do not cancel or duplicate it.

## Next three steps

1. Commit the private carrier, integrate current main, run the full news/Press job and differential contract audit, then publish its PR and bind fresh review/CI before expected-head merge and normal deployment.
2. Follow the existing covering render through its actual post-pull `from` ancestry, ticker dossier guard, generated push, normal updater and live stock-page verification.
3. Rerun the unchanged offline ordinary Press planner after normal input refresh. Make one admitted private draft only when an original current-day slot with exactly one explicit qualified company ticker exists.

## Exact remaining input and coordination

The ordinary planner currently returns a macro research slot with no ticker; Brief has no slot. Production staging is empty, and no current-day hosted Press staging artifact was found. The private live draft is `waiting_for_eligible_ordinary_company_slot`. The precise needed input is an untouched eligible current-day ordinary planner slot, or an independently retained full original staging record with provenance. Do not insert a ticker, relabel a date, replay a publication-ledger row, or alter planner ranking/caps to manufacture a demo. No authentication or permission request is pending.

Dashboard PR #9612, terminal sidebar PR #1081, and sector holds #8697/#7982/#8057 remain separate owners. Terminal compatibility #1088 remains previously merged/deployed. No Slack/email messages were sent.
