# Running follow/unfollow at volume on X — rails comparison (as of 2026-11-07)

Scope: 5–20 parent accounts + 30–100 child accounts, reads ≈ 10× writes, budget low hundreds USD/month, TOS risk accepted, want minimum ban exposure per dollar. All prices verified on the date shown; anything not verifiable is marked **UNKNOWN**.

---

## Part A — twitterapi.io **does** do follow/unfollow writes, with per-account login cookies

Verified live from their own docs (retrieved 2026-11-07).

**Endpoints and price**

| Action | Method + path | Price |
|---|---|---|
| Follow | `POST /twitter/follow_user_v2` | 60 credits = **$0.0006/call** |
| Unfollow | `POST /twitter/unfollow_user_v2` | 60 credits = $0.0006/call |
| Log in (get cookies) | `POST /twitter/user_login_v2` | 10,000 credits = **$0.10/login** |

- https://docs.twitterapi.io/api-reference/endpoint/follow_user_v2 — "You must set the login_cookies… Price: 60 credits ($0.0006 per call). Returns success if you already follow the user (or a follow request is pending). If X rejects the follow, status is `error` with X's reason." (retrieved 2026-11-07)
- https://docs.twitterapi.io/api-reference/endpoint/unfollow_user_v2 — same contract (retrieved 2026-11-07)
- https://docs.twitterapi.io/pricing — "Write actions as an X account (post, like, retweet, follow, DM, upload, profile …) — 60 per call — $0.60 per 1k calls"; "100,000 credits = $1.00" (retrieved 2026-11-07)
- https://docs.twitterapi.io/api-reference/post-action-v2.md — write pricing dropped "from 200–300" credits in October 2026, and "Unfollow and profile … updates now work for accounts logged in with `user_login_v2`" (the Oct-2026 changelog is on that page; retrieved 2026-11-07)

**Auth model**: `X-API-Key` header (your own key) + a JSON body per call containing `login_cookies` for the acting account, the target `user_id`, and a `proxy` string. Cookies returned by `user_login_v2` work only on `_v2` endpoints (post-action-v2.md, retrieved 2026-11-07). Cookies are obtained once per account from `user_login_v2` — you supply username, email, password and the **TOTP secret (base32 seed, not the 6-digit code)**: https://docs.twitterapi.io/api-reference/endpoint/user_login_v2 (retrieved 2026-11-07). 2FA "strongly recommended — accounts without 2FA may yield a login_cookie that gets flagged and can't post"; proxy is for the login call.
Cookie lifetime / refresh interval: **UNKNOWN** — not documented; only observable behaviour shifts matter (X can force re-login at any time). You must also pay for the residential proxy, passed per call.

**Rate limits** (https://docs.twitterapi.io/rate-limits, retrieved 2026-11-07): per-API-key, per-second — 1 req / 5 s on an account that never topped up; **20 rps** after top-up (Starter/Builder/Pro), 50 rps Scale, 500 rps Business, up to 1,000 on request; `429` beyond. Practical guidance is to spread load rather than burst, and "use one key per account" because limits are per key. 20 rps is not the binding constraint — X's own ~400 follows/day/account is.

**Read endpoints for target discovery**

| Endpoint | Price |
|---|---|
| `GET /twitter/user/followers` | 1 credit/follower at 200/page (max) = $0.01/1k; 2 credits (100–199/page); 3 credits (<100/page); min charge 60 credits/call |
| `GET /twitter/user/followings` | same tiering = $0.01/1k at 200/page |
| `GET /twitter/user/followers_ids` | 0.45 credit/ID at 4,000+ per page = $0.0045/1k |
| `POST /twitter/user_login_v2` | $0.10/login |

- https://docs.twitterapi.io/api-reference/endpoint/get_user_followers and `…/get_user_followings` (retrieved 2026-11-07). Note `GET /2/users/:id/followers`-style lookups on the official API are Enterprise-only, so this is the *_cheap_* discovery path, not a workaround for a minor gap.

Cost consequence of your 10:1 read:write ratio: 1,000 writes ($0.60) + ~10,000 candidate profiles read ($0.10, or $0.045 via id-only) + amortised logins ($0.10/account, one-off per session) ≈ **$0.75 per 1,000 follows**, i.e. your existing $75/month ceiling covers roughly 100,000 follows or a 10:1 mixed workload at ~10,000 writes/month with room to spare.

Billing detail that matters for retries: the call is charged on HTTP 200 **even when X rejects the action** (`status: "error"`); only HTTP 400 param errors are free (post-action-v2.md, retrieved 2026-11-07).

---

## Part B — self-hosted browser automation

### B1. Stealth browsers: what each one actually patches

**Patchright** (Chromium only; 5.1k★; last push 2026-09-12, active; https://github.com/Kaliiiiiiiiii-Vinyzu/patchright, retrieved 2026-11-07). Patches, per its README: avoids `Runtime.enable` by evaluating JS in isolated execution contexts (its biggest patch — the classic CDP leak); disables the Console API entirely (so `console` doesn't work); strips `--enable-automation`, `--disable-component-update`, `--disable-extensions`, `--disable-popup-blocking` and adds `--disable-blink-features=AutomationControlled`; patches "general leaks"; can reach elements inside closed shadow roots. Claim: "With the right setup, Patchright currently is considered undetectable", listing passes against Cloudflare, Kasada, Akamai, F5/Shape, DataDome, Fingerprint.com, CreepJS, Sannysoft, Incolumitas, IPHey, Browserscan, Pixelscan — self-reported, not independently audited. It now ships its own patched Chromium ("Clearcote … maintained in-house, not a stock build"). Practical constraints: use `launch_persistent_context` with `headless=False` and `no_viewport=True`, and add `--webrtc-ip-handling-policy=disable_non_proxied_udp` or WebRTC leaks the VPS IP (README + issue #47).

**Camoufox** (Firefox/Juggler; 13.1k★; last push 2026-11-04, active; https://github.com/daijro/camoufox). Injects fingerprint data at the C++ implementation level instead of JS, sandboxes Playwright's page agent so the page can't see injected JS, spoofs WebGL/fonts/WebRTC/timezone via BrowserForge's real-world distribution, and patches headless mode to look windowed (https://camoufox.com/stealth/, retrieved 2026-11-07). Its own honesty is the important part: *"There has been a year gap in maintenance due to a personal situation. Camoufox has gone down in performance due to the base Firefox version and newly discovered fingerprint inconsistencies"* — still "under active development", and anti-bot vendors cycle against it: *"Anti-bot providers test Camoufox over and over again to find even 1 unique inconsistency."* Mouse motion "may still be detected with sophisticated enough analysis".

**Vanilla Playwright/Puppeteer + stealth plugin**: leaks `navigator.webdriver`, `Runtime.enable`-style CDP tells and automation flags; adequate against weak walls, not against Cloudflare/DataDome-class checks. Both projects above exist precisely because of that.

For X specifically the calculus differs from a scraped blog: X's wall is login + `x-client-transaction-id` signing + behavioural scoring, not Cloudflare, so **a logged-in persistent profile matters more than the stealth layer**. Patchright is the better fit (Chromium, closer to the real Chrome X expects, and it is what current X bot repos use); Camoufox is the fallback if fingerprint walls bite later.

### B2. Isolation, persistence, concurrency

- One `user_data_dir` per account, always via `launch_persistent_context` — never a shared profile; Patchright's own proxy example keys the sticky-proxy username per profile (`_s_profile1`) and pins `timezone_id`/`locale` to the proxy's city. **Timezone must match the proxy city or the profile is inconsistent on first byte.**
- Lock each profile directory (one process per profile) — rajatmshukla/twitter-bot does exactly this with `browser_guard.py` before any engine runs (https://github.com/rajatmshukla/twitter-bot, README, retrieved 2026-11-07).
- Memory: a rendering Chromium is ~300–500 MB per concurrent instance, ~50–150 MB idle at boot, i.e. ~10 concurrent per GB of RAM (https://blog.crawlex.net/blog/headless-browser-tax/, published 2026-03-16). With 100 accounts you do **not** run 100 browsers at once — you cycle 4–8 concurrent workers per box.
- Session persistence is real but not permanent: cookies survive in the profile, yet X forces re-login and re-verification unpredictably. AgentX's README states X "flags/expires `auth_token` cookies aggressively when traffic doesn't look human" (https://github.com/DezXBT/AgentX, retrieved 2026-11-07).

### B3. Proxies, including prices for 30–100 profiles

| Type | Price (retrieved 2026-11-07) | Fit for 30–100 profiles |
|---|---|---|
| Mobile (dedicated) | IPRoyal $10.11/IP/24 h, $123.50/IP/60 d (≈$61.75/30 d) — https://iproyal.com/mobile-proxies/ | ~3–5 accounts per IP → 20–30 ports = $1,235–1,850/mo. Only for high-value parents |
| Static ISP / residential | IPRoyal $2.70/IP/30 d, $1.80/24 h — https://iproyal.com/static-residential-proxies/ | 1 IP per account, unlimited traffic: 100 IPs = **$270/mo** |
| Rotating residential (metered) | Decodo $3.75/GB at 3 GB down to $2.75/GB at 100 GB; $4/GB pay-as-you-go — https://decodo.com/proxies/residential-proxies/pricing | Cheapest at low write volume, but a shared IP per action; needs sticky sessions per profile |

Practical shape: static ISP per account is the sane default for a 30–100 account fleet that must *keep* sessions; rotating residential only makes sense for read-heavy scraping. Mobile is a premium for accounts that keep dying.

### B4. Login / 2FA / email-verification friction (the real tax)

- X login from a fresh datacentre IP typically triggers a challenge loop: email code, then phone or "verify it's you" interstitial, sometimes requiring the *original* signup email to still receive mail. Automating it needs a mailbox per account (IMAP or a provider API) and an IMAP/OTP step in the login flow; nothing in the OSS projects below solves provisioning for you.
- 2FA must be enabled to hand a TOTP seed to any API (twitterapi.io requires the seed, not a code). Enabling 2FA on 100 accounts through the web UI is itself a manual pass.
- Post-login, X re-challenges on IP/timezone drift — hence sticky proxies and matching timezone per profile.
- Logins from the same box without per-profile proxies collapse all accounts onto one IP and correlate them; expect "suspicious login" emails and forced 2FA re-enrol.

### B5. Open-source projects that already do X follow/unfollow on browser automation

Stars and last-push from the GitHub API, retrieved 2026-11-07.

| Project | ★ | Last push | What it does | Maintained? |
|---|---|---|---|---|
| https://github.com/rajatmshukla/twitter-bot | 1 | 2026-09-12 | Closest match: Playwright against a persistent logged-in Chromium profile, with `follow_accounts.py`, `unfollow_maintenance.py`, `list_following.py`, a profile lock (`browser_guard.py`), reply/mention engines. Single-account, documented selector fragility | Yes, but single-author and tiny |
| https://github.com/nirholas/XActions | 645 | 2026-11-05 | Toolkit: browser scripts, extension, CLI, MCP server, 152 MCP tools; cookie/no-API-keys approach | Yes, very active; breadth over depth |
| https://github.com/timgrossmann/TwitPy | 108 | 2020-09-03 | Classic Selenium follow/unfollow, follows by keyword/location | **No** — dead, Selenium-era |
| https://github.com/yousefissa/Twitter-Follow-and-Unfollow-Bot | 123 | 2019-09-05 | Selenium follow/unfollow | **No** |
| https://github.com/ricardojoserf/twitter-followers-bot | 77 | 2023-06-23 | Selenium follow by location/hashtag | No since 2023 |
| https://github.com/DezXBT/AgentX | 46 | 2026-11-06 | Not a browser: Go, cookie+GraphQL client, multi-account, follow/mute/block writes, signs `x-client-transaction-id`, optional uTLS JA3 | Yes, active. **No unfollow command** (README lists follow only) |
| https://github.com/luismalamoc/x_playwright_unfollow | 1 | 2026-07-20 | Playwright unfollow-all | Barely |

Blunt read: **there is no well-maintained, popular project that owns X follow/unfollow on browser automation.** You are assembling: a stealth browser + a per-profile runner + your own selector layer. The one genuinely current reference implementation (rajatmshukla) has 1 star.

---

## Part C — cost per 1,000 follows, and risk

| Rail | Cost per 1,000 follows | Basis |
|---|---|---|
| X official API (pay-per-use) | **Not available on self-serve** — $0.015/1k × 1,000 = $15/1k *if* it existed | Follows, likes and quote-posts "will be removed for all self-serve tiers" effective 2026-04-20 (https://devcommunity.x.com/t/x-api-pricing-update-owned-reads-now-0-001-other-changes-effective-april-20-2026/263025). The current rate card still lists "User Interaction: Create $0.015 per request" (https://docs.x.com/x-api/getting-started/pricing, retrieved 2026-11-07). Follower/following *reads* are Enterprise-only. Enterprise follow-write price: **UNKNOWN** (quote-only) |
| twitterapi.io | **≈$0.75/1k** | $0.60 writes + ~$0.10 of 10:1 discovery reads + amortised $0.10 logins; rate card at https://docs.twitterapi.io/pricing |
| Browser automation | **≈$1.90–3.10/1k** | Proxy 0.3–0.7 MB per action at $2.75–4/GB = $1.38–2.00/1k, plus compute $0.5–1.1/1k (a $48/mo 4 vCPU/8 GB DigitalOcean droplet, $0.07143/h, https://www.digitalocean.com/pricing/droplets, retired at ~45k writes/mo; Hetzner's same class is cheaper, roughly €16–20/mo, JS-rendered page read 2026-11-07 — approximate). Static-ISP variant: 100 IPs × $2.70 = $270/mo; at 30 follows/account/day (3,000/day, 90k/mo) = **$3.00/1k** |

Risk notes:

- **Official API** — ban exposure lowest: it is X's own rail and automation is sanctioned. But it now cannot do the core job on self-serve: no follow writes, no follower/following reads without Enterprise. Breakage low, debugging good (typed errors), but per-account cost is OAuth-token management for 100 accounts and the pay-per-use cap is 3M post reads/month. Not a candidate for this workload at your budget unless Enterprise pricing surprises you.
- **twitterapi.io** — ban exposure identical in kind to any web-session rail, because it drives X with real account cookies; the proxy you pass per call is your IP reputation. Its protections are on your side: real X rejection reasons surfaced, `429` documented, no charge when X rejects. Breakage risk is concentrated in one vendor and invisible to you (cookie TTL, X-side changes to the web GraphQL surface). Debugging is the best of the three — per-call error `code` and `x_status`. Cost is also the lowest by 2.5–4×. Main single-vendor risk: if it dies you have no local fallback; keep the browser runner for the parents.
- **Browser automation** — ban exposure highest with worst-case opaqueness: full fingerprint, TLS, cookie and behavioural surface is yours, and X re-challenges logins. Breakage is constant (selectors, DOM, transaction-id signing); you own the maintenance. Debugging is screenshots and log archaeology. Cheapest at high volume *only* if you already amortise a VPS; at 100 accounts the static-ISP bill alone equals or exceeds the API path.

**X's hard ceilings, regardless of rail**: 400 new follows per account per day, and a ~5,000 following cap with a follower-ratio gate beyond it (https://help.x.com/en/rules-and-policies/x-limits; the 400/day figure is stated in https://devcommunity.x.com/t/updates-to-daily-follow-limits/124446 — "Requests / 24-hour window: 400 new follows per user"). X's automation rules still say "No bulk, aggressive, or automated following" for third-party tools: https://help.x.com/en/rules-and-policies/automation-rules (Cloudflare-gated to curl; text captured 2026-11-07).

---

## Recommendation for this fleet

1. **Now**: twitterapi.io for all child-account follow/unfollow and for discovery. $0.75/1k is an order of magnitude under any browser fleet, and your $75 cap already covers ~100k follows/month. Use `/followers_ids` at bulk page size for discovery, then `batch_info_by_ids` (1 credit/user, $0.01/1k) only for shortlisted candidates.
2. Keep **Patchright on one small VPS** as the fallback/verification rail for the 5–20 parents — its profile isolation and login flow are the parts that break, so exercise them monthly rather than discovering it during an outage.
3. Proxies: static ISP, one per parent, if you end up running browser sessions long-term; rotating residential metered otherwise.
4. Watch cookie lifetime on twitterapi.io empirically from day one (log re-login frequency per account) since it is undocumented — that number, not the rate card, is what sets your real cost.

## Unknowns to close

- twitterapi.io login-cookie TTL and refresh cost under sustained use (undocumented).
- Whether X still honours follow writes for any self-serve API tier as of Nov 2026, and Enterprise per-follow pricing.
- Independent (non-vendor) detection testing of Patchright/Camoufox against X's current login flow in 2026.
- Hetzner exact instance prices (page is client-rendered; the €16–20/mo figure is read off the live table, not quoted by Hetzner).
