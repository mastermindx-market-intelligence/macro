# X action rails: contracts, costs and unresolved permission

Source correction for PR #10829, 2026-11-07. Scope remains the proposed parent/cohort programme; this brief admits no account, browser, credentials, spending or live action.

The original vendor-only recommendation and later browser-default proposal conflicted. The [masterplan](../X_GUERRILLA_NETWORK_MASTERPLAN.md) now records one proposed split, retains the existing parent Buffer owner, and explicitly blocks child activation pending permission, entitlement and programme gates. A capability comparison is not an execution grant.

## A. Vendor contract: what the primary documentation establishes

| Operation | Documented route | Unit price |
|---|---|---:|
| Follow | `POST /twitter/follow_user_v2` | 60 credits / $0.0006 |
| Unfollow | `POST /twitter/unfollow_user_v2` | 60 credits / $0.0006 |
| Login | `POST /twitter/user_login_v2` | 10,000 credits / $0.10 |

Sources: [follow](https://docs.twitterapi.io/api-reference/endpoint/follow_user_v2), [unfollow](https://docs.twitterapi.io/api-reference/endpoint/unfollow_user_v2), [login](https://docs.twitterapi.io/api-reference/endpoint/user_login_v2), retrieved 2026-11-07.

The login schema takes `totp_secret`, meaning the secret seed, not a generated six-digit code. The documented action shape uses an API key, acting-account cookies and supplied proxy information. Credentials remain in the approved secret/profile owner, outside tracked code and chat. Documentation does not prove actual account access, cookie lifetime, IP behavior or successful authentication.

The follow endpoint distinguishes an already-following/pending relationship from an X rejection. That does not justify a universal numeric-error-to-success mapping. An HTTP 200 and an action success are different observations.

### Billing and throughput uncertainties

The original brief contradicted itself: it said both that X-rejected calls were charged and that they were free. **Rejection/ambiguous-call billing is UNRESOLVED here.** Preserve the exact response and consult the applicable vendor contract/usage evidence only when separately authorized; never decide whether to retry from the assumed charge.

Earlier author research reported one request per five seconds before top-up and twenty requests/second after top-up. Those account-level limits were not reverified in this correction. At the former rate, twelve hours supports at most **8,640 requests**, not 10,000; overhead lowers usable capacity. Credit purchase is not authorized by this arithmetic.

Cookie lifetime, refresh frequency, rejected-call charge, quota, minimum page charge and exact read pricing for this workload remain unqualified. Do not transfer an old vendor rate or official X limit into a current account capability receipt.

### Cost model

At the documented write unit, one thousand writes model $0.60. The old $0.75/1,000 estimate depended on unverified read, login and allocation assumptions and omitted the monthly proxy floor. It is not an all-in price.

The original read model used $0.00001 per returned profile, with proposed bulk-ID savings and page/minimum-charge tiers. Those exact tiers were not freshly verified. Distinguish requests from resources returned, disclose pagination and minimums, and allocate login/proxy/compute/operator costs. The parent's $75 cap is not approved capacity for one hundred thousand follows or a new child programme.

The [follow brief](X_API_FOLLOW_LIMITS_BRIEF_2026-11.md) gives a conditional like-for-like official/vendor comparison and the actual access constraints.

## B. Browser proposal: evidence limits

The earlier text surveyed Patchright, Camoufox, Playwright/Puppeteer and small X-specific repositories. Their stars, maintenance dates, fingerprint claims, detection rankings and provider prices were **author-reported research**, not an independent comparison verified by this correction. No “undetectable” claim, fallback recommendation or anti-detection recipe is accepted as a programme requirement.

The relevant current issue is permission, not whether a browser can produce a desired source label. The verified platform restrictions are recorded once in the [follow brief](X_API_FOLLOW_LIMITS_BRIEF_2026-11.md). A browser route cannot be activated to evade an API restriction, authentication denial, challenge or unresolved earlier write.

### Isolation, persistence and capacity

Separate profiles and exclusive ownership can protect local state, but they do not create separate human operators or establish permitted use. Reuse the incumbent identity/secret, lease and effect owners. Do not create another browser-profile lifecycle, retry queue or credential store.

The old memory arithmetic was inconsistent: 300–500 MB per active instance implies roughly **two to three instances per GB before overhead**, not ten. The author later reported six light-page profiles using 5.71 GB and sixty processes on mini1. That dated observation supersedes the estimate but does not establish capacity under actual X pages, concurrent agents, recording or recovery. No browser or capacity test was repeated here.

Profile reuse does not settle a failed platform action. Backup restore, network rebinding and credential repair require custody and eligibility; they are not automatic responses to a timeout or denied login.

### Supplier research retained as unverified

The earlier brief compared mobile, static ISP and rotating residential offers from IPRoyal/Decodo and mentioned DigitalOcean/Hetzner compute. Those historical amounts are not current purchase quotes. The programme separately records Bart selection and reported existing IPs; new inventory, reserve packs and subscriptions remain open spend decisions. Supplier marketing cannot prove account permission, independent human identity or low suspension probability.

The original source URLs and project comparison remain in this file's Git history at `4a003a146a07470bf612f067c09403376de822ff`. No alternative repository is installed or executed by this correction.

## C. Rail comparison without invented acceptance

| Dimension | Official API | Vendor session adapter | Browser proposal |
|---|---|---|---|
| Access | Operation/account-specific; generic tariff is insufficient | Published vendor route is not X permission | Current platform restriction blocks the proposed scripted path |
| Cost | Conditional usage model; actual entitlement first | Writes priced; total workload/billing unqualified | Actual capacity, labour and infrastructure unqualified |
| Failure ownership | Existing action owner | Same owner | Same owner |
| Unknown effect | Reconcile original target | Reconcile original target | Reconcile original target |
| Explicit denial | Stop action | Stop action | Stop action |
| Current programme status | No new account entitlement proved | No child activation admitted | No child activation admitted |

No empirical ranking of ban risk or reliability is established. The earlier claims that one path was definitively cheapest/safest for the complete workload exceeded their evidence.

## D. Effect contract and integration

Every proposed adapter must use the parent's existing outbox construction, validation, item approval, claim-before-action, receipt settlement, dedupe, health and spend controls. An action record must retain its logical ID, carrier, account, request identity and observed result.

1. If applied, record the canonical receipt and do not repeat it.
2. If reliably not applied, a bounded retry may use existing authorization on the original carrier.
3. If unknown, stop and reconcile the original target before another route, account or retry.
4. If explicitly denied, stop that action; no alternate-carrier bypass.
5. Cooldown, re-login and profile restore are not evidence that a preceding write failed.

A vendor outage does not authorize a browser fallback; a browser outage does not authorize vendor continuation. Rate limits and permissions are separate from transport availability. The proposed `ActionRail` is an adapter seam, not a new publication or retry owner.

## E. Decisions still required

- Platform permission and actual account/operation entitlement.
- Approved total spend, usable existing inventory and any new purchase.
- Actual cookie/billing/read contracts and workload capacity.
- Complete disclosed identities and startup/staffing/sample issues in the masterplan.
- Independent qualification of any implementation candidate, including #10837.
- Real pilot and production evidence at the original gates.

These remain programme requirements. The four-document planning correction can be integrated as truthful source without pretending those requirements have been completed.
