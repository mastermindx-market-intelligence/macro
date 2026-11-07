# X publishing at 5–20 (then 30–100) accounts: Buffer vs direct X API vs schedulers
Research date: 2026-11-07. All prices USD, monthly unless stated. Quotes are verbatim from the cited URL on 2026-11-07.

## Bottom line
- Buffer discounts steeply with volume (from $6 to $1 per channel) but the curve is still linear-per-channel, not bundled: **$100/mo for 20 channels**, **$245/mo for 100**.
- Buffer is an **official X API partner** and supplies the X access itself; no developer app, no OAuth app, no per-account tokens. That is the structural answer at 5–20 accounts.
- Real Buffer gaps for this workflow: **no scheduled reply to a specific post**; **X Communities is dead platform-wide (30 May 2026)**; API has no quote-post or community field, so quote posts are UI-only.
- Direct X API is technically the cheapest *text-only* rail ($0.015/post) but becomes the most expensive with links (**$0.20/post** = $240/mo at 20 accounts × 2/day) and adds one OAuth authorization per child account plus a scheduler you maintain.
- Self-hosting Postiz/Mixpost does **not** remove X's bill: both require *your* X developer app on X's **pay-as-you-go** tier, so you pay X directly per post. Self-host at 20 = ~$260/mo all-links vs Buffer's $100. The vendors' own clouds (both $49) undercut Buffer but shed quote-in-API (Postiz) or roadmap depth (Mixpost).
- Recommendation: **Buffer Essentials for the parent accounts now; revisit self-host only as a standby/hedge or when link-free child volume exceeds ~50 accounts** — and only after measuring link share.

## 1. Buffer pricing (current)
Source: https://buffer.com/pricing (2026-11-07), markdown twin https://buffer.com/pricing.md (2026-11-07).

Tiers: **Free**, **Essentials**, **Team**. Billing is per connected channel: $6/channel for the first 10, then $4 (11–25), $3 (26–50), $1 (51+).

| Channels | Essentials | Team |
|---|---|---|
| 1–10 | $6/channel | $6/channel |
| 11–25 | $4/channel | $4/channel |
| 26–50 | $3/channel | $3/channel |
| 51+ | $1/channel | $1/channel |
| Example 10 | $60/mo ($50/mo billed yearly) | $60/mo ($50/mo billed yearly) |
| **Example 20** | **$100/mo ($83.33/mo billed yearly, $1,000/yr)** | **$160/mo ($133.33/mo billed yearly, $1,600/yr)** |
| Example 25 | $120/mo ($100/mo billed yearly) | $120/mo ($100/mo billed yearly) |
| Example 50 | $195/mo ($181/mo billed yearly) | $195/mo ($181/mo billed yearly) |

The 20-channel figures are **read off Buffer's own live stepper** (set Channels = 20, Yearly): Essentials `20 channels · $1,000 billed yearly`, Team `20 channels · $1,600 billed yearly`, and at 100: Essentials `100 channels · $2,450 billed yearly` ($204.17/mo yearly, **$245/mo monthly**) — confirming the 51+ tier is a flat $1/channel with no bundle. https://buffer.com/pricing (2026-11-07).

- **Cost at 10 channels: $60/mo** ($50/mo yearly). **Cost at 20 channels: $100/mo**, **$83.33/mo on yearly billing**. Monthly and yearly are exact ×10 relationships (2 months free), so yearly is the same product 16.7% cheaper.
- Free plan: **3 channels**, **10 scheduled posts per channel** in queue, 1,000 API requests/channel/mo up to 3,000. https://buffer.com/pricing.md (2026-11-07)
- API key quota: Free 1 API key, 1,000 requests/channel/mo (max 3,000); Essentials 3 keys, 3,000 requests/channel/mo (max 30,000); Team same 30,000 ceiling. https://buffer.com/pricing (2026-11-07)
- Fair-use cap: **5,000 scheduled posts per channel** (rolling). https://buffer.com/pricing.md (2026-11-07)
- No per-seat cost on Essentials beyond included users; Team adds approvals. All plans include the API: "The API is available on every Buffer plan, including the free plan." https://buffer.com/made-for/developers (2026-11-07)
- 14-day trial of paid plans. https://buffer.com/x (2026-11-07)
- Legacy Pro/Premium/Business plans still exist and migrate to this pricing on request. https://support.buffer.com/articles/using-xtwitter-with-buffer-nA84XnWtuU.md (2026-11-07)

At your 20-account target, API calls ≈ 20 channels × 2 posts/day × 30 = **1,200 creates/mo**, 4% of the 30,000 Essentials ceiling — quota is not a constraint.

## 2. X-specific restrictions in Buffer
- **Daily posting cap:** "150 posts per 24 hours for verified X/Twitter accounts. • 100 posts per 24 hours for unverified X/Twitter accounts." https://support.buffer.com/articles/using-xtwitter-with-buffer-nA84XnWtuU.md (2026-11-07). Your daily cadence is nowhere near this.
- **Media:** 4 images, 1 GIF, or 1 video per post; video ≤140s and ≤512MB, images ≤5MB. Video over 140s is native-only. Same URL.
- **Character limit:** 280 for X Free; 25,000 for X Basic/Premium/Premium+ on Buffer Free/Essentials/Team. Same URL.
- **Threads:** yes, composer "Start Thread"; thread posts publish in order each replying to the previous. https://buffer.com/x and https://developers.buffer.com/types/TwitterPostMetadataInput.html (2026-11-07)
- **Quote posts:** yes, in the UI — "you can schedule text-only, threads, single image posts, multi image (up to 4 images), GIF, video, reposts, quote, and link preview posts." https://buffer.com/x (2026-11-07). **Not in the API**: `TwitterPostMetadataInput` exposes only `isAiGenerated`, `retweet`, `thread` — no quote-tweet ID field. https://developers.buffer.com/types/TwitterPostMetadataInput.html (2026-11-07). A pasted status URL may produce a link preview, not a true quote — UNKNOWN without a live test.
- **Reply to a specific existing post:** **no dedicated flow.** Reply is absent from the post-type list above; the only reply modelling in the docs is `ReplyingConfiguration` ("Reply configuration for an engagement type… whether a reply can quote a specific message"), which belongs to Buffer's own engagement/Community replies, not arbitrary external posts. https://developers.buffer.com/types/ReplyingConfiguration.html (2026-11-07). Workaround: create a 2-post thread whose first item is a near-empty root, or post the URL as text.
- **X Communities:** **gone** — announced 2026-04-23, final shutdown **2026-05-30** after moderators objected, replaced by XChat group chats and Custom Timelines. https://techcrunch.com/2026/04/23/x-is-shutting-down-communities-because-of-low-usage-and-lots-of-spam/ and https://blog.tchop.io/en/x-communities-shutdown-rented-platforms/ (2026-11-07). Publer still advertises Communities and `community` fields survive in Postiz/Buffer-era schemas — treat as vestigial in all six tools.
- **Follows:** Buffer has no follow/unfollow automation; the X feature list covers publishing, analytics, engagement only. Keep follows on the other rail, as planned.
- **Per-channel, not per-account-group:** every X handle is one paid "channel"; there is no sub-account construct.

## 3. Does Buffer hold its own X API access?
Yes. Buffer is an **official X API partner** and the API is the same one that powers Buffer:
"Buffer is an official API partner with Instagram, LinkedIn, Threads, Facebook, Bluesky, YouTube, TikTok, and **X**, so the integrations are deeper and more reliable than scraping or workarounds." https://buffer.com/made-for/developers (2026-11-07)

- **Customers need no X developer app, no OAuth app, no tokens.** Connecting is account-level OAuth inside Buffer. For your own scripts: "generate an API key from your Buffer dashboard" — auth is fully managed. Same URL.
- **If X access changes:** Buffer has historically absorbed X API shocks rather than passing them to users: "these changes will not impact Buffer users… Your Buffer account and Twitter channel connections will continue working as usual. We have a longstanding, enterprise relationship with Twitter built over the last 12 years." https://buffer.com/resources/twitter-api-changes/ (2026-11-07; written for the 2023 repricing).
- Failure mode is **Buffer-wide, not account-wide**: a partner-app suspension or X policy change breaks all channels at once and you have no fallback credentials in hand. Buffer has published nothing binding (no SLA/uptime or API-continuity commitment found → UNKNOWN). Commercial exposure is month-to-month, so leave-on costs nothing but a migration is not instant.
- Buffer's own outage/error surface is documented per error code: https://support.buffer.com/articles/xtwitter-error-library-qzGT25L4VB.md (2026-11-07).

## 4. Alternatives
### Direct X API (own developer app)
- **Price:** pay-per-usage, no subscriptions. **Post: Create $0.015/request; Post: Create (with URL) $0.200/request; Post: Create (summoned) $0.010**; reads $0.005/resource; 3M post-reads/cycle cap; $20 free credits with first card. https://docs.x.com/x-api/getting-started/pricing.md (2026-11-07)
- Cost at 20 accounts: 2 posts/day → 1,200 posts = **$18/mo text-only, $240/mo all-link** (reads extra). At 1 post/day → $9 / $120.
- **Rate limits:** POST /2/tweets 100/15min per user, 10,000/24h per app. https://docs.x.com/x-api/fundamentals/rate-limits.md (2026-11-07)
- **Feature coverage:** full — `reply.in_reply_to_tweet_id` (true replies, free), `quote_tweet_id` (quote posts), media upload, polls, `community_id` (now vestigial), long posts. https://docs.x.com/x-api/posts/create-post.md (2026-11-07)
- **Burden:** one developer app, OAuth 2.0 PKCE or OAuth 1.0a, **one user authorization and stored refresh token per child account**, callback URL handling, token revocation/reauth UI, 429 backoff, media upload. Your Python publisher already exists, so the delta is auth + token store + media, not scheduling.
- **App cap:** commonly cited **10 apps per developer account**; not stated in docs.x.com → UNKNOWN officially, and not binding at 20–100 accounts if you run **one app with many user authorizations** (one app is sufficient).
- X may change unit prices unilaterally; no volume commitment at this tier.

### Managed schedulers
| Tool | 10 X channels | 20 X channels | X feature coverage | Programmatic API | Own X access? |
|---|---|---|---|---|---|
| **Typefully** | $200/mo (Business, 10 social sets) | $400/mo (20 sets); 50-set ceiling | strong: threads, reply-to-any-post, quote | REST API v2 on all plans | yes |
| **Hypefury** | no native X scheduling left | impossible (X not a supported platform) | none for X | none | n/a |
| **Publer** | $45/mo (Professional, 10 accounts) | $90/mo (20); API needs Business $180 | good: quote, threads, 25k chars | Business/Enterprise only | yes |
| **Metricool** | $45 + $100 X add-ons = $145 | $107 (25 brands) + $200 = $307 | good | Advanced/Custom only | yes, resold as $10/X add-on |
| **Postiz cloud** | $39/mo | $49/mo (30 channels) → $99 at 100 | quote in UI, no quote field in API; `community` + `who_can_reply_post` fields | public API on all plans | yes (vendor app on cloud) |
| **Mixpost cloud** | $49/mo | $49/mo (Agency $149 = 180 channels) | threads/quote; own-app OAuth | API in Pro/Enterprise | cloud: vendor; self-host: own app |
Sources: https://typefully.com/pricing, https://publer.com/pricing, https://metricool.com/pricing, https://hypefury.com/pricing, https://postiz.com/pricing, https://mixpost.app/pricing (all 2026-11-07). Per-tool plan detail is in `/Users/chriswong/x-scheduler-pricing-2026-11-07.md`.

Postiz cloud is the cheapest option that also covers quote posts (UI); Typefully has the best X craft (true reply-to-any-post) but costs 4× Buffer at 20 channels.

### Postiz (self-hosted)
- Self-hostable, official Docker/compose install; repo **https://github.com/gitroomhq/postiz-app** — **41,049 stars, 7,826 forks, AGPL-3.0, last push 2026-11-06T03:04:30Z, not archived** = very active. GitHub REST, 2026-11-07.
- **X requires your own app:** set `X_API_KEY` / `X_API_SECRET` (+ callback `${FRONTEND_URL}/social/x`), then authorize each account. https://docs.postiz.com/providers/x (2026-11-07)
- X settings schema: `who_can_reply_post`, `community`, `made_with_ai`, `paid_partnership` — **no quote-tweet ID**. https://docs.postiz.com/public-api/providers/x (2026-11-07)
- Public API on every plan/self-host: good fit for your Python publisher.
- Licence cost $0, but **X bills you per post** and you own the server, upgrades, and token store.

### Mixpost (self-hosted)
- Self-hostable (Laravel); repo **https://github.com/inovector/mixpost** — **3,913 stars, 591 forks, MIT, last push 2026-03-16T10:06:38Z, not archived** = maintained but visibly slower than Postiz (last release cadence UNKNOWN). GitHub REST, 2026-11-07. Docs: https://docs.mixpost.app/services/social/x/ (2026-11-07)
- **X requires your own app:** "If you want to schedule posts on X, you'll need to create and configure an app for this platform", **OAuth 1.0a keys**, tier must be set to **Pay as you go**. Same URL.
- Explicitly documents that X charges per post and that link posts cost "many times more"; exposes spend caps. Same URL.
- Public API only in Pro (self-host Pro is a one-time paid licence, $299) → confirm before relying on it. Cloud is ~$49/mo (180 channels on Agency at $149) and includes API.
- Licence $0–$299, plus X usage bill, plus ops.

## Cost comparison at 20 accounts, 2 posts/day (1,200 posts/mo)
| Option | Software | X usage | Server | Total/mo |
|---|---|---|---|---|
| Buffer Essentials | $100 | $0 | $0 | **$100** |
| Postiz cloud | $49 | $0 | $0 | **$49** |
| Mixpost cloud | $49 | $0 | $0 | **$49** |
| Direct X API, text-only | $0 | $18 | ~$20 | **~$38 + labour** |
| Direct X API, all links | $0 | $240 | ~$20 | **~$260 + labour** |
| Postiz self-host, all links | $0 | $240 | ~$20 | **~$260 + labour** |
| Mixpost self-host Pro, all links | $0 (one-time $299) | $240 | ~$20 | **~$260 + upfront** |
Only if your link share is low does self-host/direct beat Buffer. At 100 children × 1 post/day: Buffer **$245**, Postiz cloud **$99**, X API **$45 text / $600 links**.

## Recommendation
1. **Now (5–20 parents): stay on Buffer, Essentials, 20 channels, $100/mo ($83 yearly).** $51 over Postiz cloud but buys native quote posts, official partner access, and zero X app burden; API quota (30,000) dwarfs your 1,200 creates and the 100–150/day cap is 50–75× your cadence. Accept: no scheduled reply-to-post (script around it), no Communities (dead).
2. **Do not self-host for cost at 20 accounts.** Self-hosting hands you X's $0.20 link tariff plus an OAuth app per deployment; if you want cheap managed, Postiz cloud ($49) or Mixpost cloud ($49) beat Buffer on price but cost you quote-in-API (Postiz) and a vendor with a thinner X roadmap (Mixpost).
3. **Children (30–100):** Buffer stays sane to ~50 ($195); past that the flat-rate clouds win outright — **Postiz cloud $99** vs Buffer $245 at 100, both without an X bill. Switch the children there once count exceeds ~50, accepting Postiz's missing API quote field.
4. **Hedge:** stand up one Postiz self-host instance with your own X app now (cheap, weekend job). It is the migration target *and* the fallback if Buffer's X access is ever revoked.
5. Keep follows on the separate rail; neither Buffer nor the alternatives automate them.
6. Instrument link share before the 100-channel decision; it is the single variable that flips the economics.
