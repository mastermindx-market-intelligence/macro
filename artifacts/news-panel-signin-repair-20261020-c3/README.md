# Shared news panel sign-in repair

Owner operation: `news-panel-signin-repair-20261020-c3`.
Canonical starting main: `8128e4085d8aa346c969de186f05694afbbe6274`.

## Failure and bounded repair

The normal shared renderer [39439974736](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39439974736) completed unsuccessfully at 2026-10-20 19:51:34 UTC. Its actual post-pull source was `1a0a58907a670e55b66b8da2fc23fc0fda8ed672`, a descendant of primary integration merge `1298ed4281362329c682a1f7c038b932e4ccbb64`. Page rendering, ticker dossiers, stock integrity and inline JavaScript passed, but the dead-reference guard found a missing `account.html` target on 2,688 pages. Publication was skipped.

The shared panel now uses `{{ nav_prefix|default('') }}index.html?signin=1`, the existing landing-page sign-in route. The prefix preserves both root-page and nested stock-page resolution. The sole product change is that href; authentication implementation, API contracts, presentation, source IDs and sibling dashboard work are unchanged.

## Verification

- Added two regression cases that render the real shared Jinja template, at `stock.html` with an empty prefix and `stocks/NVDA.html` with `../`, then run the existing dead-reference checker.
- Both cases failed against the original template, specifically reporting missing `account.html` at their respective page depth.
- All **21 tests passed** in `tests/test_check_site_asset_refs.py` after the repair.
- Before log SHA256: `8c0339373f7acab228bdf3079058304e3173c0e54437781c53991576e96a3fb2`.
- After log SHA256: `f6e6ef5479853eb73e2d9624d9539f33b0293855dbb2a77c90da6c84261c8a10`.
- Reviewed panel SHA256: `0532a8f610f4c681ba05430bc27c92c2a848a271ae1199c633f284f2d58095e2`.
- Reviewed test SHA256: `78bed7e789a8cc58ed08ad25923a6e14873764206f03e0541994b45a0f13e4c7`.

The href-only change is outside the existing visual guard's material-path classifier. Prior committed visual captures retain their original source provenance; no screenshot or evidence date is restamped. Independent review receipts accompany this document.

## Release boundary

This is source/test qualification. Hosted CI, merge and a successful normal generated-page publication are separate facts and must be recorded on the PR as they occur. The unsuccessful run shipped no generated candidate. Reuse the normal coalescing render lane; do not cancel or duplicate a running shared job. Verify the actual `rendered_from` watermark and final NVDA dossier plus news JS/CSS assets before claiming stock-page deployment, then inspect the live route.

Heartbeat repair #9893 is independently merged at `87768d0af496c2668cca195750ebb7e8ad8b1254`; normal deployment and sustained live observation are in progress. Private Press #9888 is installed; a real private draft still requires a genuine eligible current-day original single-ticker slot. Licensed publisher activation was applied once and must not be replayed. Dashboard #9612 and Terminal sidebar #1081 retain their separate owners.
