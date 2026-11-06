# Reusable decision card and assurance notes

This is a reporting template, not a new datastore or second authority. Fill it from approved aggregates in the existing owner; leave unknowns blank with a reason. One card per planned test or mature cohort. Do not enter contact information, customer IDs, credentials, raw email, actual addresses or links bearing user-specific tokens here.

## Before observing results

| Field | Answer to record |
|---|---|
| Decision | What would we do differently after this test? Continue, revise, stop or reject measurement. |
| Persona, offer, alternative | Who is the reader, what question do they bring, what is the smallest thing they should learn? What would they do instead? |
| Eligible event, time and scope | Selection rule fixed prospectively, exact owner source and document, permitted surfaces, known issuer/window coverage. Mark retrospective examples clearly. |
| Placement, evidence and rights | Candidate vs approved vs booked vs actually published. Exact artifact/generation, human destination and source-scoped grants; no brand reuse by inference. |
| Cohort | Original eligible arrival dates, first-touch rule, repeat/existing users, bot/internal/test exclusions, observation windows, actual denominators and handling of missing identity. |
| Variants | Registered comparison, unit of assignment, randomization if real, known overlap and confounders. Mark observational when no randomization. |
| Cost, controls and stop | Approved budget envelope/owner; no assumed free placement. Flag owners, permitted environment and rollback. Harm and privacy stop rules dominate growth targets. |
| Decision threshold | Freeze the directional thresholds and the minimum mature sample from PILOT.md, or explain why Fable chooses different ones before seeing results. |

## After observations mature

| Stage | Count | Denominator / data quality | Interpretation |
|---|---|---|---|
| Publisher-reported unique outbound clicks | — | Provided / unavailable, measurement period | Not visitors, not QAL |
| Eligible tagged landing sessions | — | Arrivals less predeclared exclusions | Report unattributed separately |
| Visible personalized supported result | — | Eligible sessions; support-hit rate separately | Supported before signup, not just API success |
| Explicit submissions / verified scoped people | — / — | Eligible to opt in / actual submissions | No asserted consent by default |
| New deduplicated QAL | — | Eligible tagged sessions with full 7-day window | Primary report: counts, rate, uncertainty, missing join |
| Material update opportunities / deliverable recipients | — / — | Verified and in scope; account for no eligible change | No-event is not churn |
| Sent / provider accepted / controlled inbox observed / human return | — / — / — / — | State observation method and missingness; do not imply inbox telemetry for all | No pixel/forwarded click as personal return |
| Trial / actual new payer / refunded or cancelled / D30 retained | — / — / — / — | Production/test split and mature cohort | Only real net commercial events count |
| Actual channel and attributable operator cost | — | Currency, coverage and horizon | Report cash and fully loaded CAC only with paying denominator |
| Decision and next falsifier | — | Source links, major confounds and contrary evidence | Do not combine two publisher samples into a randomized lift |

## Independent Fabric critique and adjudication

One bounded planning-only Fabric child returned 6,688 bytes under planning root `mx-catalyst-fable-plan-20261031`, run `mx-catalyst-fable-plan-20261031-assurance01`, digest `7d26d0ba12eaea44d516acbce2105bcb7df5ac89bc0369e26490efad4039010e`. The terminal return explicitly reviewed the proposed acceptance protocol only; it did not independently read GitHub source, run tests, inspect live records or review this final document. This is not formal PR approval. No Fable execution is implied. The following decisions incorporate its six challenges:

1. **Installed evidence, not local database fixtures.** Let the authorized owner verify the actual grant and consent environment for the designated test, and return a redacted minimum receipt. No raw consent table export to this repo.
2. **Negative delivery decisions.** For an unverified or revoked identity and a real eligible event, prove that the gate was consulted and dispatch suppressed; an empty inbox by itself is ambiguous. Confirm suppression survives restarts and correction-triggered delivery. Do not register real users for such tests.
3. **Inspect what actually left.** In controlled authorized mail, inspect the rendered text, HTML, links and attachments against applicable grants, not just the template. Retain a redacted digest and owner-side receipt under approved retention; do not publish private MIME or claim a general license from one send.
4. **Forwarded links and privacy.** A forwarded link must not credit the original recipient as a returning user; distinguish a legitimate opaque unsubscribe capability from a tracking parameter. Link previews, security scanners and opens are not human return. Exclude unauthorized third-party pixels.
5. **Idempotency and environment.** Exercise duplicate/artificial failures only on controlled, known-safe operations in a permitted environment. Fake/test checkout cannot enter the paid cohort; entitlement delivery is separate from payment. Never blindly replay an unknown real operation.
6. **Preselection and small samples.** Freeze selection, unsupported ticker behavior and time windows before inspection. Use a reviewer other than the builder to judge actual usefulness. Present denominators and maturity; one guided success establishes possibility, not repeatability or causal lift.

## What Fable should return at each decision

Which user capability changed; evidence with exact code/build/environment/receipt; failed cases and unresolved owner dependency; why this changes the next product decision; what will not be repeated. Before claiming closure, an independent non-author should be able to reconstruct one positive, one denial, one interrupted or corrected path, and the denominator used. If the tested proposition fails, preserve the data and change the proposition rather than quietly changing the denominator.
