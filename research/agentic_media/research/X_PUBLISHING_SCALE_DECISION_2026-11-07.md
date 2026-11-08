# X publishing scale: retained parent path and conditional alternatives

Research correction for PR #10829, 2026-11-07. All amounts are USD. This is a decision aid, not a subscription purchase, deployment, migration or child-account activation.

**Current disposition:** retain the existing parent Buffer publisher, item approval and receipts. The child programme's browser/vendor proposal is not authorized for execution. The earlier recommendation to move children to Postiz after fifty accounts and deploy a self-hosted hedge immediately was an **unselected alternative**, not a fleet decision.

## 1. Buffer pricing: verified coverage versus illustrative bands

The current [pricing page](https://buffer.com/pricing), retrieved for this correction, exposes Essentials at $5/month on annual billing ($60/year for one channel), per-channel billing and volume discounts beyond ten. The exact stepped multi-channel checkout and Team table were not established by the retrieved page. Do not describe the entire old table as freshly verified.

The author earlier reported monthly Essentials bands of $6 for channels 1–10, $4 for 11–25, $3 for 26–50 and $1 thereafter. Keep these as a **model pending current quote**, not as an actual invoice:

| Channels | Monthly total under the reported model | Conditional annual total if billed at ten monthly payments | Conditional monthly equivalent |
|---|---:|---:|---:|
| 10 | $60 | $600 | $50 |
| 13 | **$72** | $720 | $60 |
| 20 | $100 | $1,000 | $83.33 |
| 25 | $120 | $1,200 | $100 |
| 50 | $195 | $1,950 | **$162.50** |
| 80 | $225 | $2,250 | $187.50 |
| 100 | $245 | $2,450 | $204.17 |

The old fifty-channel annual equivalent of $181 was arithmetically inconsistent with that model. The old Team table also used Essentials bands while giving a different twenty-channel total; **Team prices remain UNRESOLVED**, rather than borrowing one table to manufacture another.

The source reports thirteen configuration rows, seven with handles and six planned. That is not thirteen verified live or paid channels. Actual connected inventory, plan, tax, billing cycle and invoice must be read before a purchase or cost commitment. This correction did not access a billing account.

Earlier API-key quotas, queue limits, trial terms and plan-migration claims were author research and were not freshly verified here. A model of 1,200 monthly publication requests does not establish current quota or account eligibility.

## 2. Capability claims and their limits

The earlier author research described Buffer partner-managed X connectivity, threads, ordinary publishing, UI quote support and no dedicated API field for some quote/reply workflows. Those are **reported feature observations**, not a new current-account test.

| Proposed dependency | Required evidence before use |
|---|---|
| Quote post from API | Current API schema and an authorized receipt for the selected plan; a pasted URL is not automatically a quote |
| Reply to a specific post | Actual supported operation and eligibility; a near-empty thread or URL workaround is not equivalent |
| Media/long posts | Current file, duration, length and account-tier limits |
| Communities or other retired/changed features | Current primary platform and provider support; stale fields do not establish functionality |
| Managed X connectivity | Actual connected account and provider terms; it does not authorize every automation pattern |
| Queue/API quota | Current selected-plan quota and usage |

Keep the original feature-source links for follow-up: [Buffer developers](https://buffer.com/made-for/developers), [X publishing](https://buffer.com/x), [metadata schema](https://developers.buffer.com/types/TwitterPostMetadataInput.html), [reply schema](https://developers.buffer.com/types/ReplyingConfiguration.html) and [X error library](https://support.buffer.com/articles/xtwitter-error-library-qzGT25L4VB.md). These were not all re-retrieved during this correction, so their earlier content is not promoted to current proof.

No automatic alternate publication follows a missing feature, outage or changed entitlement. Preserve the existing outbox item and original platform receipt; settle any unknown effect before a separately eligible successor action.

## 3. Direct API model

The [follow/access brief](X_API_FOLLOW_LIMITS_BRIEF_2026-11.md) records verified pricing categories and operation-specific restrictions. Ordinary posts use $0.015 in this model; URL-containing posts use $0.200 **total**. Quote/reply coverage is not universally available merely because a request schema includes a field.

At twenty accounts × two posts/day × thirty days, the model contains 1,200 posts:

| Assumed URL share | Formula | Model X post charge |
|---|---|---:|
| 0% | 1,200 × $0.015 | $18 |
| 50% | 600 × $0.015 + 600 × $0.200 | $129 |
| 100% | 1,200 × $0.200 | $240 |

These are arithmetic scenarios before reads, failed-call billing, media, tax, compute and labour. They are not an entitlement, approved workload or promise of free replies. At one hundred accounts × one post/day, the corresponding extremes are $45 text-only or $600 all-URL, again conditional on access.

An own-app path needs actual user authorizations, scope, secure token custody and revocation handling. Reuse existing auth/publication owners; an alternative scheduler does not justify a second token or retry lifecycle. Exact app/account limits remain unverified.

## 4. Alternative tools: retained research candidates

The original author compared the following products. Figures below are **earlier reported amounts**, not current verified quotes or chosen vendors. Their feature, access, quota, security and licence terms require qualification before any commitment.

| Candidate | Earlier reported price scenario | Unresolved dependency |
|---|---|---|
| Typefully | $200 at ten social sets; $400 at twenty | Actual selected-plan API, reply and quote support |
| Publer | $45 at ten accounts; $90 at twenty; Business API reported $180 | API-tier entitlement and current X feature support |
| Metricool | $145 at ten including X add-ons; $307 at twenty | Brand/account mapping and current add-on bill |
| Postiz cloud | $49 at thirty channels; $99 at one hundred | Actual X connection ownership, API quote support and quota |
| Mixpost cloud | $49 scenario; Agency $149 scenario | Cloud account limits, own-app requirements and API entitlement |
| Hypefury | Original research reported no supported X scheduling | Current primary product support, not assumed availability |

Original product sources: [Typefully](https://typefully.com/pricing), [Publer](https://publer.com/pricing), [Metricool](https://metricool.com/pricing), [Postiz](https://postiz.com/pricing), [Mixpost](https://mixpost.app/pricing) and [Hypefury](https://hypefury.com/pricing). The earlier local research path was not a durable source dependency; this repository history retains the original comparison.

A lower quoted software fee alone does not establish a cheaper complete programme or a compatible permission model. No child migration threshold is selected by this table.

## 5. Self-hosting is a future option, not an admitted hedge

The original candidates were [Postiz](https://github.com/gitroomhq/postiz-app) and [Mixpost](https://github.com/inovector/mixpost), with own-app X integration described in [Postiz provider docs](https://docs.postiz.com/providers/x) and [Mixpost provider docs](https://docs.mixpost.app/services/social/x/). Earlier stars, licence summaries, release dates, API-feature claims and the $299 Mixpost Pro figure were author research, not reverified current facts.

If a future deployment needs its own X access, software hosting does not eliminate the underlying platform usage bill. Under the illustrative $20/month server assumption and $240 all-URL usage scenario, infrastructure plus X usage would be $260 before labour/licensing. That is a conditional model, not a quote or authorization to deploy.

A standby is not automatically useful: it needs independent permission, maintained account custody and settled effect migration, and must reuse the canonical publication/receipt owner. Do not build a duplicate queue, scheduler, watcher or auth service. An outage cannot justify replaying a potentially published item through the standby.

## 6. Decision for this source revision

1. Keep the existing parent Buffer path and source-linked receipts.
2. Measure actual connected/billed inventory and URL share only through an admitted read when a commercial decision is needed.
3. Retain other tools as unselected candidates; verify current total cost, feature contracts and account permission before choosing one.
4. Resolve the masterplan's permission, budget, startup, staffing and evidence gaps before child activation.
5. Keep retries and publication settlement with the incumbent owner: applied actions are not repeated, unknown effects are reconciled on the original target, and explicit denial stops the action.

The original business goals remain useful content, attributable parent growth and controlled cost. Integrating this corrected proposal does not claim a live pilot, install a publisher, accept #10837 or complete the programme.
