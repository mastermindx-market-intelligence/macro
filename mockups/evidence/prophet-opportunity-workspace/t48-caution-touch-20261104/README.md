# Prophet T48 caution disclosure repair

Source repair: `f2fb5f52f3610daa46d56205971bb2811ff56016`, parent `43ac1d47cdc73b716301da3edbe9dc69da8bd120`. Subsequent `50cf9d22425587c04ce85c4c2774443abc500a16` changes only Market Memory HTML; all Prophet inputs and artifacts below are byte-identical.

## What changed and why

The real 320px Screener card had a 36px-high Cautions disclosure, below the D03 T48 44px touch-height criterion ([original measurement](https://github.com/mastermindx-market-intelligence/macro/pull/9495#issuecomment-6643931866)). The existing native `details > summary` now has a 44px minimum and token-based block padding. It retains native list-item layout and the disclosure marker, keyboard behavior, content-driven card height and progressive disclosure. There is no flex replacement, fixed card height or spacer.

The existing stylesheet contract was narrowed to permit that exact interactive-control minimum while retaining its bans on other minimum heights, fixed positioning and auto-margin spacers.

## Source-frozen publication

The previous `_prophet_workspace.css.j2` render matched `site/assets/css/1546f0cb.css` exactly. The canonical Jinja render and existing `lib.pages.externalize_css_text` emitter produced `site/assets/css/60dc406b.css`. Only the stylesheet and preload references in the committed `site/us_stocks.html` changed. The existing asset optimizer leaves the result unchanged. The historical CSS asset remains available.

No data producer or same-date origination ran. The protected payload, current board/gate, historical Plan index and append-only ledger match their original SHA256 digests. See [asset-receipt.json](asset-receipt.json).

## Verification

- Existing focused suites: **119 passed**, zero skipped or failed. See [focused-tests.txt](focused-tests.txt).
- Actual committed HTML in offline anonymous Chromium: **16/16** cells at 1440/768/390/320 × light/dark × EN/ZH.
- All three visible Cautions controls in every cell are at least **44 × 44 CSS px**; the minimum measured height is 44px.
- Native `display:list-item` and `disclosure-closed` marker retained. Enter opens; Space closes. Focus remains active and visibly outlined. Reduced-motion preference is applied.
- Zero page errors, failed local responses, document overflow or card overflow.
- The existing publication-pair verifier passes **12/12** checks. Membership remains 159 eligible = 3 public + 156 protected; Screener 3 public + 48 protected; Today 0 public of 12 Featured; **55/55 protected Plan targets resolve**; zero protected Plan controls in public HTML.
- Full material-UI diff gate against the PR's recorded base also passes in the complete validation checkout. This is a local gate result, not hosted CI.

[Browser observations](browser-16cell/observations.json) bind the page/CSS hashes and primary card captures. [Screenshot integrity](browser-16cell/screenshot-integrity.json) records every retained PNG digest and byte length. [Pair verification](pair-verify.json) binds the native artifacts. [Verification summary](verification-summary.json) confirms unchanged hashes at the later source head.

## Visual self-check

The actual desktop light viewport, mobile dark Chinese viewport, 320px light English expanded card and 390px dark Chinese expanded card were opened and inspected. Typography, hierarchy, focus ring, disclosure marker, wrapping, expanded caution content and card controls remain readable, unclipped and within the viewport. Twenty-four original screenshots are retained; none of the historical evidence was overwritten.

Representative captures:

- [Desktop light English](browser-16cell/screener-view-1440-light-en.png)
- [Mobile dark Chinese](browser-16cell/screener-view-390-dark-zh.png)
- [320px expanded English card](browser-16cell/screener-expanded-320-light-en.png)
- [390px expanded Chinese card](browser-16cell/screener-expanded-390-dark-zh.png)

## Scope and continuation

This is source and anonymous local browser proof. It does not establish deployed or signed-in Save/list/readback/reopen or Sources → Plan → same-candidate acceptance. The PR remains Draft/HOLD. The original Fabric run and held Paper operations were not replayed, accepted or modified.

See [CONTINUATION.md](CONTINUATION.md) for remaining owner-bound work and exact source-law pin.
