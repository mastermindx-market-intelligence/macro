# Catalyst partner distribution previews (private, synthetic)

**DRAFT/HOLD. Not real issuer events, not real partner endorsements, and not a publication or authorization to distribute.** These 18 static output files are captured from the executable `--demo` command. The `example.invalid` source fixture and `preview.invalid` scan destinations are intentionally NOT live. All example partners/audiences and symbols EXA/EXB/EXC are explicitly synthetic, not qualified Session 05 targets.

| Editorial angle | Preview page | Related assets |
| --- | --- | --- |
| Earnings-first newsletter | [HTML](demo-earnings-letter/index.html) | [SVG card](demo-earnings-letter/intelligence-card.svg), [newsletter](demo-earnings-letter/newsletter.md), [social](demo-earnings-letter/social.txt), [embed](demo-earnings-letter/embed-concept.html), [manifest](demo-earnings-letter/manifest.json) |
| Semiconductor supplier community | [HTML](demo-chip-community/index.html) | [SVG card](demo-chip-community/intelligence-card.svg), [newsletter](demo-chip-community/newsletter.md), [social](demo-chip-community/social.txt), [embed](demo-chip-community/embed-concept.html), [manifest](demo-chip-community/manifest.json) |
| Portfolio exposure researchers | [HTML](demo-portfolio-risk/index.html) | [SVG card](demo-portfolio-risk/intelligence-card.svg), [newsletter](demo-portfolio-risk/newsletter.md), [social](demo-portfolio-risk/social.txt), [embed](demo-portfolio-risk/embed-concept.html), [manifest](demo-portfolio-risk/manifest.json) |

## Regenerate

From the Macro repository root, with Python and existing Jinja2 installed:

```sh
python3 scripts/build_catalyst_partner_pack.py --demo --out /tmp/catalyst-partner-demo
python3 -m unittest -v tests/test_catalyst_partner_pack.py
```

Three exact identities are stable for these fixture inputs: `cp_20835be661fe301d13`, `cp_e94908295003cd78eb`, and `cp_9bdc2e2f9f3e5ee27e`. Generated assets are deterministic. They do not constitute a verified public market packet or production/browser acceptance.

## Replacing the fixture with actual approved evidence

```sh
python3 scripts/build_catalyst_partner_pack.py \
  --packet /private/path/to/approved-public-event.json \
  --event-id <known-event-id> \
  --partner /private/path/to/approved-partner-descriptor.json \
  --tickers <ticker1,ticker2> \
  --out /private/path/to/operator-review
```

The source producer must affirm `verification.status=VERIFIED`, `verification.source_owner=engine.marketing.catalyst_packets`, public-safe disposition, source display/link rights receipts and affirmative `public_rehost` before SVG card reuse. Profile `status=candidate` produces a proposal with **no endorsement**; `status=approved` additionally requires an actual brand-permission receipt supplied by the owning human/commercial process. This code does not negotiate or verify contracts. The optional AI angle plan only reorders existing public claim IDs and cannot add claims, ticker relationships or inferred causality.

Session 00 must supply and independently verify a registered public scan `--scan-url` plus non-secret `--route-receipt`, then reconcile the exact route/UTM/packet API. The receipt is an integrator assertion, not live proof. Session 05 must supply fresh permissioned candidate profiles before any real-name asset is drafted; do not substitute this demo roster. A final operator review, real source-rights check, correction reconciliation, partner consent and hosted browser/attribution proof remain gates. No sender, publisher, X account or outreach action is invoked by this build.


## Session 05 candidate profiles (research inputs, **not** approvals)

The five JSON descriptors under [session05_candidate_profiles/](session05_candidate_profiles/) are transcribed from the actual [Session 05 Draft/HOLD prospect refresh PR #8681](https://github.com/mastermindx-market-intelligence/macro/pull/8681). They preserve its five suggested ticker triplets and publisher-specific research angles. Profile check time is conservatively normalized to the **beginning** of the Oct 8 US Eastern research date: it is **not** a claimed clock-time visit or current endorsement. `status=candidate`, `publication_permission=NOT_GRANTED`, no brand permission, no logos, no subscriber contact data. The `profile_url` is public publisher material and a validation lead, not an authorized promotional route. A source's mention is not an approved co-brand.

These profiles can be given to `--partner` (tickers default to `selected_tickers`) **only after** a fresh Session 01/00 public event packet supports every selected ticker with individual source-rights receipts. Without matching verified producer evidence the factory refuses output; it does not manufacture missing ticker scans. The optional research angle is advisory metadata, never a model license to invent event facts or future dates. No target-specific real-event pack exists yet, and no outreach is authorized.
