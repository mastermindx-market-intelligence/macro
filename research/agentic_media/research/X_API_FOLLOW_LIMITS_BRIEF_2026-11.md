# X API: follow access, cost and limits

Source correction for PR #10829, 2026-11-07. This is a planning brief. No account was accessed, credits purchased or platform action tested.

**Evidence labels:** VERIFIED = primary documentation retrieved for this correction; MODEL = arithmetic using stated assumptions; AUTHOR-REPORTED = earlier research retained without fresh validation; UNRESOLVED = evidence is insufficient. Documentation is not an account-entitlement receipt or programme authorization.

## 1. Access comes before the tariff

The [X changelog](https://docs.x.com/changelog), April 16 entry effective April 20, says follow, like and quote-post operations were removed from self-serve tiers. Its earlier reply change also restricts self-serve programmatic replies. **VERIFIED.** Generic pricing categories do not reverse an operation-specific restriction. Current self-serve follow entitlement must therefore be treated as unsupported unless the actual account has contrary authoritative entitlement.

The old proposal to buy a $5 credit pack and try one follow is **unapproved future work**, not a required action for merging these documents. A generic HTTP 403 can reflect different causes; it does not establish a universal Enterprise-only tariff, and cannot settle an earlier ambiguous write. Reconcile any original action before attempting another.

The [pricing page](https://docs.x.com/x-api/getting-started/pricing) describes prepaid usage without a subscription or minimum spend. It does not establish this account's minimum credit purchase. **Minimum pack and Enterprise quote remain UNRESOLVED.** The earlier $42,000–$50,000 Enterprise figures were third-party reports, not a vendor quote for this programme.

## 2. Unit prices and conditional model

Published categories from the [pricing page](https://docs.x.com/x-api/getting-started/pricing):

| Category | Published unit |
|---|---:|
| User interaction create | $0.015 |
| Interaction delete | $0.010 |
| Following/follower read | $0.010/resource |
| Qualifying owned read | $0.001/resource |
| Ordinary post creation | $0.015 |
| Post containing a URL | **$0.200 total** |

Mapping generic interaction categories to an available follow/unfollow entitlement is an inference, not an access grant. The owned-read condition depends on actual user/app ownership; do not apply it to every account under a shared app. URL pricing is a total, not an extra surcharge. No cash discount is created by an xAI credit-back offer.

### Like-for-like arithmetic

| Conditional workload | Calculation | Model cost/month |
|---|---|---:|
| 30,000 creates | 30,000 × $0.015 | $450 |
| 30,000 deletes | 30,000 × $0.010 | $300 |
| 90,000 discovery resources | 90,000 × $0.010 | $900 |
| Total at ordinary read rate | $450 + $300 + $900 | **$1,650** |
| Total if all reads genuinely qualify as owned | $450 + $300 + $90 | **$840** |

These calculations do not establish available endpoints, permission, tax, monthly quota, OAuth readiness or a payable quote. Non-cash credit-back is accounted for separately, not subtracted from the cash total.

Vendor [follow](https://docs.twitterapi.io/api-reference/endpoint/follow_user_v2) and [unfollow](https://docs.twitterapi.io/api-reference/endpoint/unfollow_user_v2) documentation lists sixty credits / $0.0006 each. At that stated unit, 60,000 writes model **$36**, replacing the old $120 figure based on $0.002. To compare the complete basket, add read charges, pagination/minimums, login, proxies and operating cost. If the original $0.00001/read assumption applied to all 90,000 resources, that line would be $0.90; it has not been qualified for this workload. The write-only total is not an equivalent all-in quote.

## 3. Request limits are not resource counts or permission

The [official rate-limit table](https://docs.x.com/x-api/fundamentals/rate-limits) lists:

| Endpoint class | Per user | Per app |
|---|---:|---:|
| Follow POST / unfollow DELETE | 50 requests/15 minutes | No value in these rows |
| Following / followers GET | 300 requests/15 minutes | 300 requests/15 minutes |

These are **request** limits, conditional on actual access. Multiplying 300 by ninety-six windows gives 28,800 requests/day, not users returned; pagination and resource charges remain separate. Bursts, shared app usage and other limits can bind even when a daily average is small. Official API tables are not a contract for a third-party session transport.

The [follow-limit help page](https://help.x.com/en/using-x/x-follow-limit) states 400 follows/day and an individually calculated ratio after 5,000 following. It does not supply the old brief's 1.1–2× ratio table. No numeric account-age ladder or guaranteed safe rate is established here. The masterplan's own zero-follower formula permits zero follows, so startup remains held.

## 4. Actual platform constraints

The current [automation rules](https://help.x.com/en/rules-and-policies/x-automation) require API-based automation rather than scripting the website, prohibit automated likes and follower-growth applications, and restrict bulk/aggressive/indiscriminate follow/unfollow behavior. Automated replies require the specified opt-in/opt-out conditions; AI reply bots require prior explicit written X approval. Related accounts must contribute distinct content rather than duplicate or substantially similar activity. **VERIFIED documentation constraints; no programme permission established.**

A vendor endpoint, small cadence, proxy, source label or lack of challenge does not satisfy those conditions. This blocks the proposed child-automation launch; it does not prevent a truthful planning document from being reviewed as source.

## 5. Account/app questions still unresolved

The earlier brief did not establish authoritative current limits for users per app, apps per developer account or this programme's webhook entitlement. Absence of a number in the pages read is not proof of unlimited capacity. Historical staff/forum statements about three subscriptions, app counts or legacy migrations must not be promoted into current account facts.

Before an admitted implementation relies on these features, obtain the actual account/plan entitlement, scope, quota, billing basis and canonical error contract. This is a future requirement, not permission to log in, create apps, buy credits or invoke endpoints now.

## 6. Effect handling

- **Applied:** retain the original platform receipt and do not repeat the logical action.
- **Definitely not applied:** retry only within existing authorization and on the original carrier.
- **Unknown:** stop the logical action and reconcile the original target before retry, route/account change or fallback.
- **Explicit denial:** stop that action. No alternate carrier, identity or account bypass.
- Rate-limit/authentication responses and cooldowns are not proof that an earlier write was unapplied.

These rules belong to the incumbent action owner. This brief does not create a replacement retry, credential or publication plane.

## Sources and provenance

Verified primary documentation for this correction is linked next to each factual claim above, retrieved 2026-11-07. Vendor login details are in [the rail comparison](X_AUTOMATION_RAILS_2026-11.md). Prices and permissions can change; the exact account has not been exercised.

The original legacy-plan chronology, developer-forum anecdotes and third-party Enterprise claims remain available in this file's history at parent head `4a003a146a07470bf612f067c09403376de822ff`. They are not current entitlement or independent proof. The [masterplan](../X_GUERRILLA_NETWORK_MASTERPLAN.md) retains the original business goals and unearned programme gates separately from this source correction.
