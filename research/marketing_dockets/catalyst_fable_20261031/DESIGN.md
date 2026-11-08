# Designing the experience: from evidence to a voluntary return

**Proposal, not a screen specification.** Fable may build a different experience. The durable requirements are that a reader receives useful research before giving identifying information, understands how strong the evidence is, and can withdraw from any subsequent relationship. The designs below give engineers, editors and independent reviewers something concrete to challenge.

## Three plausible entrances

| Concept | How the reader arrives | What it teaches | Main risk / when to reject it |
|---|---|---|---|
| Event first — recommended initial proof | A plain link opens one specific, current earnings event with a supported example. “Check my tickers” personalizes rather than gates it. | Can a reader recognize useful evidence, then choose to reveal which tickers matter? Efficient for newsletter context and narrow actual coverage. | Attractive demo with little personal relevance. Reject if people can repeat the headline but cannot explain a change, uncertainty or next question. |
| Dossier first | A company dossier offers “What changed in the last covered event?” before authentication. | Tests value among readers who already chose a ticker; may cost less than recruiting an editor. | Existing visitors are not proof of new external acquisition. Keep them in a different cohort. Don't fork the dossier or Market OS navigation. |
| Editor-native research insert | A publisher carries a short, sourced, permissioned comparison; one deep link opens the full evidence view. | Tests willingness to distribute an asset useful to the publication without a sales pitch. | Can mistake the publisher's reputation for product value. Use a tagged destination and an independent second placement; a link-only version is valid when media rehosting is not allowed. |

### A reader's first 90 seconds (design target, not a measured time)

**Arrival:** identify the issuer, event and scope before asking for a ticker. Offer one sentence that a careful reader can verify and a plain “See evidence” link. Give “Last checked” a real meaning; never silently substitute filing acceptance for stated publication time. A small coverage control says which symbols and period qualify. Provide a supported example, but never prefill a fabricated success.

**Result:** show a compact card per ticker. Lead with (1) what changed, (2) why this company is connected, (3) what remains unknown and (4) the next piece of public evidence that would change the interpretation. A direct company filing and an indirect supplier inference should not look equally certain. Numbers carry accounting basis, unit, period and source span or are omitted. Known figure without comparable prior ≠ improvement. No score color that implies a trade, naked change percentages or generic buy/sell labels.

**Example copy for an unpopulated template, not market facts:** “The issuer revised [reported measure] for [period]. The filing supports [fact]. It does not establish [rival explanation]. A later [specified disclosure] would help distinguish them.” Render nothing in brackets to users. For a supported company with incomplete data, name the missing comparison rather than producing a bullish narrative. For an unsupported peer, preserve any supported result and give that peer its own explanation.

**Return:** provide the canonical dossier link immediately. Stage A has no email fields or monitoring promise. In Stage B only, after a genuine signed eligible scan, invite the user to choose a narrow update: “Tell me when the evidence for these tickers changes.” Show who sends it, the trigger, what data are necessary, and how to leave. Do not make “not now” dismiss the research. Verification sent, verified consent, provider-accepted mail, observed inbox delivery and an actual return are separate states.

**A later change:** link directly to the revised evidence. Lead with the old vs new fact, underlying source and as-of dates, why it matters, and what is unchanged. Identify corrections or retractions explicitly. Do not resend the same generation to stimulate retention. Without send rights, do not deliver even seemingly harmless excerpts. An editor with an older asset gets a correction via its established, permitted owner, not a new outbound bot.

## Reading states, failure copy and side effects

| State | What users should understand | Allowed behavior | Never count as |
|---|---|---|---|
| Supported, current, entitled for public display | “Here is the change and what supports it.” | Dated source and dossier; optional update only after its own gate | A verified person or sale |
| Complete, empty window | “We checked this issuer and period and found no qualifying event.” | Explain coverage window and source. Only when owner attests completeness and no truncation. | A material event or supported first result |
| Outside coverage | “We don’t cover this symbol in this scan.” | Keep other results; allow edit, link to a valid dossier where possible | Quiet market or a negative signal |
| Source failed, stale, truncated, unknown identity | “We can’t verify a current result.” | Preserve known metadata where lawful; no invented facts or enrollment | Complete-empty or fresh information |
| Rights withheld or withdrawn | “This evidence isn’t available for this use.” | Strip claims, inaccessible citations and assets as appropriate | Support, or permission for other channels |
| Amended or retracted | “This replaces the earlier filing/read.” | Show current qualified generation and provenance; retire stale cards | Two investment opportunities or two leads |
| Interrupted verification / expired receipt | “No subscription was confirmed.” | Use owned, bounded recovery without revealing whether an address exists | A grant, permission to market, or conversion |
| Delivery uncertain after transport | “Delivery could not be confirmed.” | Reconcile original sender/key; hold batch as appropriate | Delivery, or permission to resend |
| Billing pending, duplicate or revoked | “Your access is being checked” or accurate access state | Re-read authoritative entitlement, isolate account identity | Client-side purchase or two paid customers |

Mobile design should preserve evidence before CTA at 320 CSS px; avoid horizontal scrolling for an individual fact. Put complex comparisons behind a labeled disclosure, retain keyboard focus through updates, and announce a meaningful loading/result message without hijacking focus. No-JS fallback must tell the same truth. Ensure state distinctions do not depend on color. Real localized text verification is distinct from a browser set to another locale. [W3C guidance on status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).

## Engineering design: improve the interfaces already in place

**Source → scan.** The existing issuer/event owners supply an issuer set, bounded event-window result, snapshot identity and trusted document grant. The producer binds exact URL and bytes to a verified observation. Distinguish SEC acceptance, first verified availability, latest check, official publication if attested, and scan generation time. A number qualifies only when the matched field, value, period/basis and evidence span belong to that precise document. Require the predecessor for an amendment; a later processing time is not a newer filing. Never use an event payload's self-asserted permission to admit itself.

**Scan → signup intent.** The Session00 router owns `/api/catalyst` for people and `/api/catalyst/scan` for machines, response sanitization, no-JS, CSP and signed scan authority. Site-full/private feeds and operator-supplied URLs cannot manufacture a public result. Stage A needs no scan token, user store, provider call, or outgoing mail. Stage B must bind the intent to the right event, generation, supported tickers and purpose. A form submission or an unverified address is not a grant.

**Verification → communication.** Scope is `catalyst_event_updates/v1`. Check rights and switches at entry AND after remote OTP before confirming; test the race, not just sequential happy paths. Confirm through the consent owner and preserve immutable first-touch. Test service-role access, row-level protections, TTL, revocation, alias handling and cleanup in approved staging. Avoid raw email/UUID/token in ordinary logs, URLs, source repo, partner exports or analytics. The proposed SQL is review-only; no migration is authorized here. At the actual dispatch boundary recheck entitlement for email, current material generation and suppression. Do not infer provider acceptance from enqueue or inbox delivery from an SMTP response.

**Commercial bridge.** Pass only allowed opaque attribution to D07 and existing Website/Terminal owners. Keep a user's previous marketing grant out of billing decisions. A signed and verified billing event, the correct account entitlement acknowledgement, retained canonical conversion and event settlement must reconcile. Return responses, retries or webhook duplication should not grant a second entitlement or create a second sale; cancellation/refund belongs to billing, not a Marketing label. [Stripe webhook behavior and duplicate handling](https://docs.stripe.com/webhooks); [testing guidance](https://docs.stripe.com/automated-testing).

## Acceptance matrix for a non-author reviewer

These are discriminating witnesses, not instructions to create 18 new suites. Reuse the existing eight enrolled Catalyst suites, original fixtures and native owners. Record exact revision, environment, input type (synthetic/retained source/live), expected refusal, observed effect and source link. Do not move personal data to prove the journey.

| ID | Witness | Result that disproves readiness |
|---|---|---|
| A01 | One real approved issuer result and one unsupported ticker in a mobile, anonymous session. | Login/email wall first; unsupported is silently dropped; result served from demo or stale cache. |
| A02 | Known issuer with complete-empty, unavailable service, or truncation, tested separately. | Empty list, failed fetch or maximum event count reported as “no news.” |
| A03 | Same filing accession, different exhibit, different rights; replace one digit in the retained exhibit. | Wrong exhibit accepted, altered number still rendered, or a document-only reference passes as numeric proof. |
| A04 | Official publication absent but first verified observation exists; delayed observation vs accepted filing. | Source rejected solely for unknown publication or it is relabeled with another clock. |
| A05 | Revoke the grant; deliver an amendment with/without correct predecessor; stale cross-ticker response arrives late. | Old claim survives as current, orphan is called correction, or an unrelated selection is overwritten. |
| A06 | Direct issuer vs indirect relation. Ask an evaluator to name the document and why the relation holds. | Name matching or inferred sector membership is presented as demonstrated causal impact. |
| A07 | Mobile, keyboard, no-JS, hostile markup and encoded private link; switch locale and reload. | Sideways scroll hides key facts, focus loss, leaked secrets, nonfunctional fallback, or mock UI mistaken for hosted. |
| B01 | Try unchecked consent, unsigned scan, expired receipt, wrong event, replayed nonce and unknown address. | Any grant, extra OTP effect, identity leak or verification counted as success. |
| B02 | Flip operator to OFF or revoke rights *during* OTP, between provider return and consent confirm. | Durable positive grant after the protected transition; unsubscribe fails while marketing is OFF. |
| B03 | Web permitted/email denied, then permission expires mid-batch. Race unsubscribe before send. | Email list disclosed before validation; a suppressed user receives the update; new side effect after denial. |
| B04 | Pre-send owner outage vs exception after sender invoked; repeat one event/generation across tickers. | Undispatched precheck reported as sent; uncertain send automatically replayed; incorrect duplicate behavior. |
| B05 | Authorized controlled inbox, signed native unsubscribe and subsequent eligible update. | Provider receipt counted as actual inbox, open pixel counted as return, or suppression doesn't survive re-entry. |
| C01 | Editor follows a real, tagged HTML link; source/asset has web-display but no rehost right. | CTA displays JSON, protected media leaks, fabricated endorsement or destination loses meaningful first value. |
| C02 | Revisit same person from two links; bot prefetch, internal staff, prior registered user, unjoined visitor. | Duplicate QAL, wrong first source, employee counted, or probabilistic PII join to fill missing data. |
| C03 | Retract a fact after a private pack exists; read old link and inspect downstream artifacts. | Superseded asset still offered as current, or revocation triggers automatic unauthorized outreach. |
| D01 | Authorized test-mode checkout and declined/expired flow, client-forged success, duplicate or out-of-order webhook. | Client grants paid access; settled before acknowledged conversion; duplicated or synthetic revenue. |
| D02 | Two accounts on one browser, failed preference write, loss of acknowledgement, refunds/cancellation. | Cross-account prefs/entitlement or old retry overwrites new state; refunded amount treated as retained revenue. |
| E01 | Compare first and independently repeated cohort with event opportunity, clock maturity, costs, attrition and missingness visible. | Reach substitutes for denominator; immature returns treated as failures; one publisher treated as replicated demand. |

**Minimum evidence for promoting a claim:** independently reviewed exact head, working rollback/flag custody and actual appropriate environment. For first value, capture deployed build, both positive/negative browser states and nonidentifying provenance. For second value, add confirmed intent, material update, lawful send/inbox/return plus unsubscribe negative. For paid, add authoritative provider/entitlement/ledger reconciliation. For repeatability, add a separate real cohort. A missing higher rung does not invalidate lower-rung proof.
