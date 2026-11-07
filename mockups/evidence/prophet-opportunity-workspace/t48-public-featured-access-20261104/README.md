# D03 T48 — public Featured access-empty UI

Scope: only the `_today_visible=[]` and `_today_total>0` branch of the real
`templates/dashboard.html.j2` US Prophet page. Other empty, loading, error,
real zero-source and entitled Featured card states are preserved. The CSS is
scoped to `#us-today .mx-today-access-*`; it does not redefine shared
`.mx-empty` or the Prophet data/entitlement admission.

## Honest product semantics

When the published source has a nonzero Featured roster but the current public
access exposes zero Featured cards, say *access-limited preview*, not *no setups
exist*. Keep the header's actual observed/total counts, link to the real
`window.USProphetSource.set('candidates')` owner, and make the in-card 44px
action keyboard-focusable. Do not render/ship private setup details here. For
`_today_total=0`, preserve the separate true empty explanation.

## Native and code evidence

- Native editable Paper candidate file `01M3NT5Y3G5HTJHVR0K5W2MDJM`,
  page `p-D-0`, board `12PR-0`, 320 Light EN, plus full eight-state normal
  320/390 × light/dark × EN/ZH matrix on Macro PR #10617.
- The attached four PNGs are **local Playwright component-fixture**
  screenshots, rendered from the actual Jinja branch and shared theme CSS
  tokens. They are not deployed-route screenshots.
- `tests/test_prophet_public_featured_access_card.py`: 8/8 combinations
  passed (320/390 × light/dark × EN/ZH); actual template branch markup,
  44px action, visible-language and accessible-name selection, static
  visible text/button contrast >=4.5:1, no horizontal scroll, focus and
  Screener action, no page errors.
- Independently, before this code change, the original published
  `site/us_stocks.html` was exercised through local Playwright at 320 and
  390 dark EN: public 0/12 truthful copy, no overflow/page error, and the
  header Open Screener changed source to `candidates`.
- Browser fixture is a bounded visual/behavioral proof, not signed-in account,
  release URL, real source freshness, backend entitlement, or production proof.

## Publication boundary (observed)

The isolated `MACRO_DUMP_VM=1 python -m scripts.build_site` diagnostic
ran for 486 seconds but was stopped before successful publication. GDELT
returned 429 on attempts 0/1/2; the full news vector reported its newest
event at 2026-10-26 (9 days old, freshness ERROR), and the builder moved
on to unrelated profile fetches. Do not treat any generated files from that
incomplete run as accepted publication; **none are staged here**.
The accepted scope is the actual Jinja source, component-browser proof,
and focused tests (139 passed, 22 skipped, 0 failed).

## Holds

Keep Macro #9495 and #10617 Draft/HOLD. Source publication, exact-head
fences/CI, main integration (25 known conflict paths), true account/reopen
journeys and cross-width/full-route real-browser acceptance remain separate.
No merge, enqueue, Ready/un-draft, label, deploy or purchase.
