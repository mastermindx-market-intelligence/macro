# Auction context: publication and entitlement path audit

**Verdict:** the selected Macro HTTP path already has the correct canonical registration/paywall boundary. The source-only vertical still needs a delivery bridge: its current producer artifact is Git-ignored and R2-published, while the two selected consumers require a file in Macro's local/Git-served tree. A narrow single-file Git delivery exception plus a move of the existing daily build step resolves that gap without a new owner, controller, authentication policy, hydration job, or deployment.

## Scope and pins

Read-only source inspection used Macro `8a35d8b62494a84b2448182aaa561edea83fe54f`, Terminal `54f97dda68a76a55ba0813afc9433ef54aaf401c`, and Mastermind `c7e47c859eb2925c5626931fd511800773ba09ac`. Exact Git blob identities, canonical URLs, full-file hashes where copied, and hashes of preserved source excerpts are in [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). The candidate Terminal route, upstream constant and Mastermind reader were also read from the shared scratch candidates; their exact observed hashes are in [CANDIDATE_READ_RECEIPT.json](CANDIDATE_READ_RECEIPT.json). No candidate commit identity is implied.

One anonymous bounded GET inspected the known Macro path; it sent no Cookie or Authorization, followed no redirects, and read at most 512 bytes. No sessions, credentials, accounts, production filesystem, deployment, background process, publisher, commit or PR were changed. The proposed ignore-rule behavior was checked in an isolated temporary local Git directory using only `check-ignore` and `git add --dry-run`; no index staging or commit was performed.

## 1. The existing HTTP gate covers `/feeds/event_calendar.json`

The candidate route selects `EVENT_CALENDAR_URL = new URL("/feeds/event_calendar.json", NW_BASE).href`, so the default upstream is `https://www.mastermind-x.com/feeds/event_calendar.json`. A request cannot supply a different URL or path. The endpoint is outside `/neuralwebdata`, but that directory distinction does **not** change Macro's access classification.

Macro's [Caddyfile](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/app/deploy/Caddyfile) declares a default-deny non-HTML asset matcher. The reviewed public path exclusions contain neither `/feeds/event_calendar.json` nor the incumbent `/neuralwebdata/market_plane.json` or `/neuralwebdata/selection_cohort/us.json`. The matched route performs these operations in order:

1. Send the original request to `/api/regwall/check`, with the original URI and asset-kind marker. Continue only on a 2xx gate response.
2. Send it to `/api/paywall/check`, again using the original URI. Continue only on 2xx.
3. Set private/no-store, Cookie-varying headers and serve the file from `/opt/macro/site.served`.

The protected error path contains no file server. A failure cannot fall through to a public static copy. The exact routing block is at Caddyfile source lines 289–379. The asset handler's URI classification and ordered gate behavior are source facts; they do not certify which Caddy revision is deployed.

The [policy file](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/config/site_access.yml) and [paywall classifier](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/app/paywall.py) produce identical results for all three paths:

| Path | Public/free/deny match | Classification | Paid requirement when staged on | Enforced before global paid switch? |
|---|---|---|---|---|
| `/feeds/event_calendar.json` | None | Premium | `site_full` | No |
| `/neuralwebdata/market_plane.json` | None | Premium | `site_full` | No |
| `/neuralwebdata/selection_cohort/us.json` | None | Premium | `site_full` | No |

The classification calculation is recorded in [CLASSIFICATION_RECEIPT.json](CLASSIFICATION_RECEIPT.json). Unknown paths are premium by default. The global paid wall is controlled by the existing `PAYWALL_ENABLED` policy switch; these paths are not `enforced_early`. The separate registration wall defaults on and has its existing operator switch. This audit neither reads their secret-bearing environment file nor changes their values. It would be incorrect to claim that paid-only runtime enforcement was proven merely because the path classifies premium.

Registration is more than a cookie-name check upstream. [app/regwall.py](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/app/regwall.py) uses the existing configured Supabase session-cookie parser, then `_mm_verify_uid_cached`. The [inspected functions in app/main.py](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/app/main.py) extract a token from the expected session envelope and verify it against Supabase Auth, retaining the existing cache semantics. When paid enforcement applies, paywall performs its own identity and entitlement check. Auth or policy errors deny.

### Observed live response

At **2026-10-08 23:18:35.681818 UTC**, the anonymous GET returned:

- HTTP **401** with JSON `authentication_required`;
- `X-Regwall: deny`;
- `Cache-Control: no-store` and `Vary: Cookie`.

The original response receipt and body hash are in [ANONYMOUS_PATH_RECEIPT.json](ANONYMOUS_PATH_RECEIPT.json). This confirms a registration refusal on the real path at that instant. It does **not** prove file existence behind the gate, a successful entitled read, the paid switch's runtime value, or deployment of these exact source pins.

## 2. Terminal's guarantee and the canonical helper alternatives

The candidate `/api/nw` checks for an allowed `sb-…-auth-token` cookie name before any upstream request. **With no matching cookie it returns 401 even if the upstream would otherwise be public.** The auction feed is excluded from the development fixture bypass. The route forwards only matching whole/chunked session cookies, uses manual redirects and no-store requests, maps upstream denials to the existing locked states, validates the extracted nested auction context, and returns private/no-store data.

Cookie-name filtering alone does not verify a user. If a future configuration pointed this route at a public host, a syntactically matching but invalid cookie could pass the local presence check and a public upstream could return 200. No such bypass was attempted. The inspected canonical Macro origin supplies the missing identity/entitlement authority, so **no new independently chosen Terminal tier gate is required for the selected path**. Keep the guarded origin and do not introduce a direct public-R2 fallback.

Terminal's [proxy.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/54f97dda68a76a55ba0813afc9433ef54aaf401c/terminal/proxy.ts) excludes `/api/*`; page/session middleware is not a security backstop for this handler. The canonical helpers, if a future independently guarded API needs them, are:

- [`billingAuth()`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/54f97dda68a76a55ba0813afc9433ef54aaf401c/terminal/app/api/billing/gateway.ts), which uses the existing server Supabase client and checks `getUser()` alongside `getSession()`;
- [`lib/entitlement.ts`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/54f97dda68a76a55ba0813afc9433ef54aaf401c/terminal/lib/entitlement.ts), which resolves Macro `/api/me` rather than trusting `profiles.is_pro`.

Those helpers should be reused only with an already adopted product gate. `hasLiveOptions`, `isPaidTier`, `isProTier`, and the operator capability have different scopes; none is automatically an auction-feed entitlement. The current guarded-origin relay preserves Macro's staged access policy more faithfully than inventing such a predicate in Terminal.

## 3. The present artifact delivery gap is established by source

The producer writes `site/feeds/event_calendar.json` in [scripts/build_feeds.py](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/scripts/build_feeds.py). At the audited Macro ref:

- `.gitignore` excludes the entire `site/feeds/` directory, and `git ls-tree` reports zero tracked files beneath it.
- [`daily.yml`](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/.github/workflows/daily.yml) assembles feeds **after** its engine-output commit, then includes `feeds` in the R2 publish invocation.
- [`publish_r2.py`](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/scripts/publish_r2.py) includes `feeds` in its directory set and calls the plane R2-only. Closing-bell also builds and publishes that directory.
- [`app/deploy/update.sh`](https://github.com/mastermindx-market-intelligence/macro/blob/8a35d8b62494a84b2448182aaa561edea83fe54f/app/deploy/update.sh) rsyncs the local Git-updated `site/` tree into `site.served/`, using per-file replacement and a nonempty-file floor. No calendar build or feeds hydration appears in that updater.

Mastermind's [macro refresh source](https://github.com/mastermindx-market-intelligence/Mastermind/blob/c7e47c859eb2925c5626931fd511800773ba09ac/data_layer/macro_refresh.py) includes `site` in its sparse checkout, but its R2 synchronization list contains **stockdata only**. Consequently, sparse checkout cannot materialize an ignored/nontracked feed and that R2 leg does not fill the gap. The existing [`feeds-plane` contract](https://github.com/mastermindx-market-intelligence/Mastermind/blob/c7e47c859eb2925c5626931fd511800773ba09ac/config/contracts.yml) declares the directory as a Macro-owned, display-only input; declaration alone is not transport.

The current Git object for `vendor/macro` is a **symlink**, target `macro_src`; it is not a submodule Gitlink despite the older `.gitmodules` commentary. In both the owned Mastermind workspace and the primary Mac checkout, that symlink is currently dangling and the calendar file is absent. The refresh module documents a different production arrangement, `vendor/macro -> /opt/macro`, with external management available. The VPS filesystem was not inspected, so that documented arrangement is not presented as a new live readback. [TRANSPORT_SOURCE_RECEIPT.json](TRANSPORT_SOURCE_RECEIPT.json) contains the exact observations.

## 4. Recommended bounded source-only bridge

**Publish the one existing calendar artifact through Git as well as its existing R2 delivery.** This retains the same producer, JSON object, source clocks, contract owner, file path and guarded Caddy route. It avoids editing the deployment updater or adding a hydration mechanism.

### Exact changes for root implementation

1. In `.gitignore`, replace the blanket directory exclusion with `site/feeds/*`, followed by `!site/feeds/event_calendar.json`. Update the nearby R2-only comment to describe the single guarded Git-delivery exception. Every other feed stays ignored. The full current ignore file was tested with this proposed rule: exactly the calendar becomes eligible for `git add site/`, while other JSON and nested payloads remain ignored. See [BRIDGE_RULE_REVIEW.json](BRIDGE_RULE_REVIEW.json).
2. In `.github/workflows/daily.yml`, move the **existing** “assemble machine-consumable feeds” step from after “commit engine outputs” to immediately before it. Keep one invocation, its existing `if: always()` and its nonfatal source-failure posture. Do not add a second invocation, new scheduler, or wholesale workflow rewrite. This fixes the call-order defect without changing collector authority.
3. Add the generated `site/feeds/event_calendar.json` to the held source PR from the qualified first-vertical capture/build evidence. Preserve its observed source clocks and provenance; do not rewrite them to the commit or deployment time. This is the same complete wrapper already consumed by both candidates, not a second auction-scoring object.
4. Keep `scripts/build_feeds.py` as the sole producer. The existing `daily_engine_commit_outputs.sh` already stages `data/ site/ reports/`; it needs no staging-code change once the ignore exception exists. Closing-bell already assembles feeds before its `git add site/`, so it needs no order change. The existing R2 publication can continue to copy the same produced file.

### Resulting call order and identity

The existing daily producer finishes its input work, builds the calendar once, stages and commits that file, then publishes the same local file through the existing R2 step. Macro's normal Git update receives the committed `site/feeds/event_calendar.json`; the existing rsync copies those bytes to `site.served/feeds/event_calendar.json`. Caddy serves them after its existing gates. Mastermind's normal sparse checkout includes the tracked file under `vendor/macro/site/feeds/event_calendar.json`; under the documented external `/opt/macro` wiring it sees the same source artifact directly.

No bridge operation reserializes the object or changes `source_observed_at`, the query cutoff, publication clocks, amounts or receipt hashes. On a given committed artifact, source and served/local copies must hash identically. Different hosts can still be on different Git revisions or failed refreshes; their existing health checks and the new reader's own source-age/null behavior must expose that state. This bridge is not permission to call a stale or absent artifact fresh.

A complete capture schedule and durable raw-observation custody remain separate readiness requirements. The bridge does not start them. If the producer has no qualified observations, its emitted context must report that absence. Source-only implementation can close the delivery-code gap without asserting a running prospective collector or a deployed feature.

### Overlap and authority caveats

The five recovered held Macro heads were compared from their individual merge bases against the proposed bridge paths. None modifies `.gitignore`, `scripts/build_feeds.py`, or `.github/workflows/daily.yml`. **Held #7273 does modify `app/deploy/update.sh`**, which the recommended bridge avoids. Exact heads and the bounded comparison result are in [BRIDGE_COLLISION_RECEIPT.json](BRIDGE_COLLISION_RECEIPT.json).

This is not all-open-PR or live-lease clearance. Root must still check the latest protected ref, each file's preimage, other current PR writers and operation ownership before applying the small change. The daily workflow is a busy shared file; use a targeted move and a path-specific review. No held PR is taken over, merged or deployed by this recommendation.

## 5. Required source verification after root's patch

A sufficient bounded acceptance record should show:

- The ignore exception admits exactly `site/feeds/event_calendar.json`; sibling and nested feeds remain excluded.
- The daily workflow has exactly one feed-build step, ordered before the existing engine commit and before R2 publication; closing-bell remains build-before-stage.
- One actual qualified build emits the complete expected wrapper, with source clocks unchanged by publication; source/committed/served-simulation/Mastermind-input copies have the same digest.
- Terminal's no-cookie, upstream-denial, redirect, malformed-body and private-cache tests remain green. The anonymous live 401 is evidence of the current boundary, not a replacement for an entitled test at a later authorized release gate.
- Missing source receipts and absent local transport still render honest unavailable states, without altering risk, sizing, exit authority, stored decision planes or null-study conclusions.

The audit performed no implementation or release. Its actionable conclusion is that the existing auth path is suitable and a clean, narrow publication remedy is available within the existing Macro owner.
