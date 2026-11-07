# X API — cost & limits for programmatic follow/unfollow (checked 7 Nov 2026)

Evidence grades: **[OFFICIAL]** = X docs/help/changelog · **[STAFF]** = X staff post on devcommunity · **[3P]** = third-party blog/forum, unverified · **[UNKNOWN]** = not documented anywhere found.

## Headline

- X killed subscriptions. API access is now prepaid **credits / pay-per-use (PPU)**, Enterprise is the only sales-led tier. **[OFFICIAL]**
- The follow-write endpoints are the one thing where docs and reality disagree: a 16 Apr 2026 changelog entry says follow writes were **"removed from all self-serve tiers"**, but the live PPU rate card still prices them. Treat "can PPU follow at all?" as **unresolved** and settle it with a $5 credit test before committing. **[OFFICIAL + conflict]**
- If PPU follows work: ~**$1,650/mo** at 30k follows + 30k unfollows + discovery reads. If they don't, the floor is **Enterprise ≈ $50k/mo** per a community report. **[3P for the $50k]**
- Hard binding constraint is not the API, it's the **400 follows/day per account** product cap — 30k/mo needs ≥3 accounts, realistically 10–20.

## 1. Packages (Nov 2026)

| Plan | Status | Price | Notes |
|---|---|---|---|
| Free | Legacy, closed | $0 | `POST .../following` **removed from Free on 22 Aug 2025**. Legacy free users got a $10 credit on retirement. **[OFFICIAL]** |
| Basic | Retired for new signups | **$200/mo** | Basic closed 1 Jun 2026; subscribers migrated to PPU with $200 credit. **[OFFICIAL]** |
| Pro | Retired for new signups | **$5,000/mo** | Pro migration announced for after 1 Sep 2026. **[OFFICIAL]** |
| Pay-per-use (credits) | **Default self-serve** | Prepaid credits, **$5 min purchase**, no subscription | Capped **3M Post reads/month**; xAI credit-back 10% @$200 / 15% @$500 / 20% @$1,000 spend. **[OFFICIAL]** |
| Enterprise | Sales-led | **≈$50,000** floor **[3P, in a staff thread]**; one blog says ~$42k/mo **[3P]** | 5,000+ webhook subs, higher caps. |

- Pricing page: https://docs.x.com/x-api/getting-started/pricing — states "No contracts, subscriptions, or minimum spend", credit packs, min $5. **[OFFICIAL]**
- Free-tier follow removal: https://docs.x.com/changelog (22 Aug 2025) · https://devcommunity.x.com/t/update-to-x-api-free-tier-removal-of-like-and-follow-endpoints/247646
- Basic retirement: https://devcommunity.x.com/t/important-update-legacy-x-api-basic-plans-are-moving-to-pay-per-use-ppu/266305
- $50k Enterprise floor: https://devcommunity.x.com/t/how-can-i-get-more-subscribe-webhooks/263691/3

## 2. Per-call cost

| Action | PPU unit price |
|---|---|
| **User Interaction: Create** (follow) | **$0.015 / request** |
| **Interaction: Delete** (unfollow) | **$0.010 / request** |
| Mute: Delete (separate row) | $0.005 |
| Followers/Following **read** — other people's accounts | **$0.010 per resource** (per user returned) |
| Followers/Following read — **own** account, app owned by that user | **$0.001 per resource** |
| Webhook `follow.follow` / `follow.unfollow` | $0.010 each |
| Post: Create | $0.015 ($0.20 if it contains a URL) |

- Source: https://docs.x.com/x-api/getting-started/pricing (write table + "Owned Reads" table), read 7 Nov 2026. **[OFFICIAL]**
- **Caveat:** no row is literally named "Follow" — mapping follow→"User Interaction: Create" and unfollow→"Interaction: Delete" is an inference from the row names (DM Create and Mute Delete are priced separately, so these two rows have no other candidate). **[INFERRED]**
- "Owned Reads" $0.001 applies only where `{id}` = the authenticated user **and that user owns the app**. With one app and 50 accounts, only the owner account gets cheap reads — the other 49 pay $0.010. Whether enforcement is per-token or per-app is **[UNKNOWN]**.

### 30k writes/month, modelled

| Line | Units | Cost |
|---|---|---|
| Follows | 30,000 × $0.015 | $450 |
| Unfollows | 30,000 × $0.010 | $300 |
| Discovery reads (3 users scanned per follow) | 90,000 × $0.010 | $900 |
| **Total** | | **$1,650/mo** (~$1,320 net after 20% xAI credit-back, which is xAI credits not cash) |
| Same, but all reads at $0.001 owned rate | $750 + $90 | **$840** |
| twitterapi.io equivalent (60k calls × $0.002) | | **$120/mo** + proxies |

Reads dominate. Scanning followers is 2/3 of the bill at $0.010/user; a 1,000-follower target costs $10 to enumerate.

## 3. Accounts per app, token and write caps

- **Distinct users per app: no published ceiling. [UNKNOWN]** Neither https://docs.x.com/fundamentals/developer-apps nor the OAuth 2.0 pages state a number. Rate limits are enforced **per user token** (below), so one app serving 50–120 accounts is the intended shape.
- **Apps per developer account: no number published. [UNKNOWN]** Developer Terms require one app per use case: "You may not register multiple applications for a single use case" — https://docs.x.com/developer-terms/policy **[OFFICIAL]**
- **Account Activity API / webhooks on PPU: hard cap 3 unique user subscriptions + 1 webhook.** X staff: "Pay Per Use is fixed at 3 unique user subscriptions and 1 webhook — no per-account billing option." https://devcommunity.x.com/t/how-can-i-get-more-subscribe-webhooks/263691/2 **[STAFF]** So event-driven non-followback detection only covers 3 accounts unless Enterprise.
- **Monthly/daily write cap per app: none published for PPU. [UNKNOWN]** The only published volume cap is 3M **Post reads**/month (doesn't touch follows). Writes are limited by rate limits + product caps, not by a plan quota.

## 4. Documented rate limits

From https://docs.x.com/x-api/fundamentals/rate-limits (read 7 Nov 2026), "Manage follows" table: **[OFFICIAL]**

| Endpoint | Per user | Per app |
|---|---|---|
| `POST /2/users/:id/following` | **50 / 15 min** | none listed |
| `DELETE /2/users/:source_user_id/following/:target_user_id` | **50 / 15 min** | none listed |
| `GET /2/users/:id/following` | 300 / 15 min | 300 / 15 min |
| `GET /2/users/:id/followers` | 300 / 15 min | 300 / 15 min |

50/15min = 4,800/day of headroom per account — 12× the product cap, so rate limits never bind on follows. 300/15min reads = 28,800 users/day/account, enough for discovery. Note the read limit is **per app** too: 300/15min shared across all 50 accounts is the real ceiling on fan-out scanning.

## 5. Product-level limits (these, not the API, decide capacity)

https://help.x.com/en/using-x/x-follow-limit — page stamped **March 2019, unchanged in Nov 2026**: **[OFFICIAL]**

- **400 follows/day** per account. "This is a technical account limit and is not tied to your time zone." X explicitly says the 400 is enforced across clients **including the API** — API calls count against it.
- **5,000 following cap** per account; above that you must add followers to follow more.
- **Ratio rules:** at 5,000 following you need ~1.1× followers to exceed it; at 8,000–10,000 following roughly 1.1–2× depending on volume. Hard ceiling even with followers.
- **New accounts:** *nothing numeric is documented.* No age-based table exists on help.x.com — new accounts are just told to stay under 400/day and expect "follow limits" messaging. **[UNKNOWN]**
- **Premium/verified:** the 2019 page still does **not** mention Premium raising follow limits. No official source says it does. **[UNKNOWN]**
- **Unfollow:** no separate daily unfollow cap is documented. Only the general anti-churn rule. **[UNKNOWN]**
- X Rules, https://help.x.com/en/rules-and-policies/x-limits: follow churn and "indiscriminate following, particularly by automated means" are violations. The Rules page still says "scripting the x website… may result in the permanent suspension of your account" — the exact argument for the official API rail. **[OFFICIAL]**
- Automation rules: https://help.x.com/en/rules-and-policies/x-automation

## What changed vs the old 400/day

Nothing on the product side — 400/day, 5,000 total and the ratio table are the same 2019 numbers, still live. What changed is the **API side**:

- Aug 2025: follows pulled from Free tier.
- Feb 2026: PPU launched; subscriptions put on a retirement path.
- 16 Apr 2026: "Following, Likes, and Quote-Posts via the API have been removed from all self-serve tiers." https://docs.x.com/changelog **[OFFICIAL]**

## The open conflict — resolve before building

| Evidence | Says |
|---|---|
| Changelog, 16 Apr 2026 | follow writes removed from all self-serve tiers **[OFFICIAL]** |
| Live PPU rate card, 7 Nov 2026 | still lists User Interaction: Create $0.015 / Interaction: Delete $0.010 **[OFFICIAL]** |
| X staff endpoint list for PPU, 19 Mar 2026 (pre-removal) | includes POST follow and DELETE unfollow **[STAFF]** |
| Community app on PPU, 13 Sep 2026 | still lists follow/unfollow as its live endpoints **[3P]** |
| opentweet.io, Aug 2026 | "Enterprise-only now, at roughly $42,000 a month" **[3P, low reliability]** |

Most likely reading: the rate-card rows are Enterprise metering carried over, and PPU lost follow writes on 20 Apr 2026 — which would make the official API a $50k/mo rail, not a $1,650/mo one. **Verify with a $5 credit pack: one POST follow on a PPU app.** If it returns 403/`client-not-enrolled`, it's Enterprise.

## Sources, dated

- https://docs.x.com/x-api/getting-started/pricing — live, read 7 Nov 2026
- https://docs.x.com/x-api/fundamentals/rate-limits — live, read 7 Nov 2026
- https://docs.x.com/changelog — entries 22 Aug 2025, 6 Feb 2026, 16 Apr 2026, 5 Nov 2026
- https://devcommunity.x.com/t/x-api-pricing-update-owned-reads-now-0-001-other-changes-effective-april-20-2026/263025 — 16 Apr 2026
- https://devcommunity.x.com/t/inquiry-regarding-apis-available-under-the-pay-per-use-plan/260208 — 19 Mar 2026, staff
- https://devcommunity.x.com/t/how-can-i-get-more-subscribe-webhooks/263691 — 24–25 Apr 2026, staff
- https://help.x.com/en/using-x/x-follow-limit — stamped Mar 2019
- https://help.x.com/en/rules-and-policies/x-limits · /x-automation — live
- https://docs.x.com/developer-terms/policy — live
- https://opentweet.io/how-to/fix-x-api-like-follow-endpoint-removed — Aug 2026 [3P]
- https://docs.twitterapi.io/api-reference/endpoint/unfollow_user_v2 — $0.002/call, needs login_cookie + proxy (it is session automation, so X's product caps apply and the account carries the ban risk)
