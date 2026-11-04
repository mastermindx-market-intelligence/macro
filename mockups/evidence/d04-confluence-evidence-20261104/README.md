# D04 Confluence — bounded implementation evidence

This is a draft source implementation on Macro base `c53915f6d67078d5c0aeaf73bf85ddea1a23de03`. It addresses evidence truth, dense historical comparison and atomic protected-name hydration on `/confluence_screener.html`. It is not final D04 composition, a Paper reference approval, a deployment, or production entitlement proof.

The domain plan and complete ten-route retention/UX/data contract remain in [D04's existing draft #7727](https://github.com/mastermindx-market-intelligence/macro/pull/7727). Chairman instruction on 2026-11-04: **Resume design and implementation.** No merge, Ready/un-draft, enqueue, held relabel or production deployment is authorized.

## Dark treatment

Neutral dark surfaces establish depth through panel luminance and even borders. Recent and older period rates use the same 28px monospaced weight, with visible months and fires adjacent. Source counts, source-generation time and explicit availability carry meaning. Semantic color annotates the comparison; there is no accent edge.

## Light treatment

Cool canvas, white panels, fine neutral borders and the existing card-shadow token replace dark material depth. The cards explicitly remove the inherited glass treatment in light mode. Type hierarchy, density, period semantics, actions and responsive layout remain equivalent. This is a separate material treatment within the incumbent semantic token system.

## Responsive and interaction decisions

Desktop places the evidence pair beside the recipe; phone places the pair below the title. Every D/W leg remains visible. Long company names wrap independently from unbroken ticker symbols. Native `details/summary` gives touch and keyboard users a persistent methodology disclosure; rate values are readable text, not unreliable touch tooltip triggers. Existing shared navigation and Brain chrome are unchanged.

The private reader validates the complete expected row set before replacing any wall. It distinguishes denied, expired, unavailable, generation mismatch and malformed responses. Retry focus belongs to the current request and transfers only while the retry control still owns focus. Sign-out, account changes, visibility/page transitions and the existing session's expiry deadline clear paid rows. The existing protected endpoint remains the entitlement authority.

## Evidence and limits

- [EVIDENCE.yml](EVIDENCE.yml) is the existing three-key `mastermind.page_evidence_receipt.v1` receipt.
- [manifest.json](manifest.json) is emitted by the existing `scripts/capture_page_evidence.py` owner. Its matrix includes anonymous desktop/mobile × EN/ZH × dark/light, plus actual focus and hover interactions.
- [smells.json](smells.json) is a measured census, not a visual approval.
- The nearest Git HEAD in the canonical capture records the base checkout; it is not a claim that the uncommitted candidate was deployed. The page's Git blob and the implementation report's SHA-256 bind the actual served bytes.
- The separate finite handler harness passed 39 cases; the page/miner suite passed 132 tests. Controlled auth and private HTTP responses exercise reader behavior without claiming live server entitlement or subscription-revocation acceptance. Full logs and 23 labeled fixture screenshots are retained through the D04 domain carrier.
- Samples measure 5.73:1 contrast in dark and 7.03:1 in light in the dense fixture. No page overflow was observed at 320, 390, 820, 1024 and 1440 CSS pixels. This does not claim a full assistive-technology or actual 400% zoom audit.
- Existing floating Brain chrome can overlap the right edge on a phone. Existing shared Lens behavior for legacy metadata was not rewritten; the new methodology disclosure provides the numerical definitions on touch. These are retained owner constraints, not hidden screenshot exclusions.
- Session expiry bounds display; plan revocation without an auth event is learned through the existing owner or the next protected read. There is no new token, plan, polling or persistence owner.

F01/F02 final joint foundations and P00 Paper runtime acceptance remain separate gates. No D04 Paper mutation was dispatched. All 25 inherited reference conditions retain their recorded status; these local checks do not close the whole programme's reference review.

## Reproduce the bounded verification

```sh
python3 -m scripts.build_confluence_screener
python3 -m pytest tests/test_confluence_screener_page.py tests/test_tech_confluence.py -q
python3 scripts/verify_confluence_screener_browser.py --out /tmp/d04-confluence-browser
```

The anonymous canonical capture command uses `--site-dir site --routes /confluence_screener.html --viewports desktop,mobile --locales en,zh --themes dark,light --settle-ms 1400`, with `method_focus:focus(.lc-method summary)` and `trial_hover:hover(.lc.gated a.btn)` force states. These names invoke real browser focus/hover in the existing capture owner; they do not simulate paid access.
