# ROR-1 — Asia source-to-machine-feed timing and entitlement boundary

**October 15, 2026; immutable source and workflow read-only analysis.** Current Macro main source pin `86db1b0487ec98c955b2ea9265779263c63d6454`. No new publisher/queue/service, scheduler, policy, or release edit.

## Existing primary pipeline ownership

1. Original Asia-close branch/main committed the native Oct13 China Risk-off/98 and Hong Kong Elevated/90 first-writer records at **2026-10-13T16:32:31Z** (`c49e4410492e8d2a0a16d00eca5edb3b45d66bc7`). Both Oct13 Market States in the same revision are Risk-off/34 and Risk-off/33, and both source-rendered country HTML pages have red first-glance heroes. This is Git source publication, not proof a customer saw the actual pages.
2. `.github/workflows/asia-close.yml` source blob `8cfb53eb3c3037c5858d6cc91fbe2c30c2c05a17`: schedule starts with early UTC slots around 06:00 and settles after 08:25 UTC HK data floor; it runs the CN/HK native radar/ledger builders, commits site/data and then calls `scripts.publish_r2 --dirs chinaohlc,hkohlc,subsectorohlc_china,chinastockdata,hkstockdata` (L1012+). **There is no `feeds` in that configured R2 publish list.**
3. `scripts/build_feeds.py` blob `f5d086666914849fe76549f30c3e50145b316851` explicitly documents that CN/HK Radar snapshots are otherwise render-inline and creates `site/feeds/intl_spillover.json` with a native `markets` map from `engine.risk_radar_intl.snapshot`. It is an R2-only machine feed, not checked into the inspected Git tree.
4. `.github/workflows/daily.yml` blob `9911a112287d4885f74d84e78db6e416c8c35297`: its EDT selected cron is **22:30 UTC = 18:30 EDT** (EST uses 23:30 UTC). Near the end of its engine job, **after** the primary commit step, `python -m scripts.build_feeds` assembles the machine feed, and the following `scripts.publish_r2 --dirs ...feeds...` uploads it (L4881–4900). This is a **different, U.S.-evening schedule** from the midday CN/HK Git source publication.

Therefore, for the configured scheduled path alone, the earliest selected **daily workflow trigger** after the Oct13 **16:32:31Z** Asia source commit is **22:30:00Z**: a minimum **5h57m29s source-commit-to-possible-job-trigger gap**, plus actual scheduler queue, build and upload time. This is NOT an observed R2 upload timestamp: a manual dispatch, an independent authorized publisher or a late/cancelled run could change actual serving. No claim that the deployed R2 feed was absent or that this schedule is the only publisher.

5. Both `build_feeds` and `publish_r2` in daily are nonfatal (`|| echo warning`); feed-generation failure can leave a file stale without failing that step. The adjacent strict `audit_r2 --anchors stockdata,ohlc,massive_stock_day` checks only those named anchors, **not native country warning source availability or `feeds/intl_spillover.json` source session**. Do not interpret a green generic data-plane check as feed freshness or subscriber delivery.

## Safety-critical entitlement limit — reuse existing classification

Accepted `config/r2_delivery_plane_classification.v1.json`, blob `fbae076b709c30c00101a7121554ee367c7c2d44`, already classifies `feeds/{risk_radar.json,intl_spillover.json,subsector_rotation.json}` as **PREMIUM_PRODUCT, required tier ESSENTIAL**, on the current `SHARED_PUBLIC_R2` lane. It also explicitly says `browser_direct=true`, and policy prohibits deriving public access from obscurity or client-side hiding. Scores, trajectories and operational risk context are NOT approved for anonymous homepage publication. Approved lower-tier copy must be a separately allowlisted, delayed context fact; `PUBLIC_FACT` feed keys are a different class. Other `feeds` keys are PRIVATE_OPERATIONAL or HOLD by default.

**Do not 'fix' the missing notification by publicly linking or copying the premium native `intl_spillover` object, or by adding `--dirs feeds` to the Asia-close publisher without the original R2 rights/tier owner**. That could upload additional private/paid family contents to a shared public prefix and does not cure malformed country JSON, missing native session calendar, alert fatigue or incomplete user delivery.

## Existing-owner bounded follow-on

- The original Asia close **source writer** should produce a qualified per-country original native Radar source/clock/health receipt through an accepted source-owned publication boundary once settled (not a duplicate engine or first-writer ledger). Its results are source facts, not trade sizing.
- The existing R2 rights/entitlement owner must decide whether a sanitized *public* attention projection can be shown outside login and how an **entitled** Essential-tier consumer receives full native warnings. Keep the explicit allowlist, no hidden premium bytes and no shared cross-user cache.
- The original Macro/Grey Deer attention and alert owners should connect those vetted source facts via the existing publisher/Chronicle/Reflex/QLedger, carrying source asof, issue/commit/publish/serve/render/notify clocks separately and deduplicating persistent country warning episodes.
- Add **owner-authorized source-specific stale-source acceptance** for the real `intl_spillover` feed (including holiday/expected market session, missing/stale, publication failure and manifest mismatch) instead of treating unrelated R2 OHLC anchors as the proof.
- Real acceptance requires the Oct13 historical source to appear in a mounted, entitled user view with actual browser/network timestamps and a notification/ack receipt. Git-history and source-code scheduling alone do not prove it.

**HOLD:** Grey Deer #8132 REQUEST_CHANGES and native country source mismatch, Macro #9428 CI/release holds, Terminal #894 empty-successful-JSON history, live entitlement and R2 publication restrictions remain. No runtime, network, source branch or production object changed by this audit.
