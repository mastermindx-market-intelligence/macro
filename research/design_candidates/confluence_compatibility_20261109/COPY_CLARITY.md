# Confluence access and snapshot copy

## Corrected descriptions

| Surface | Before | Current |
|---|---|---|
| Locked card, EN | Unlock this line-up's matching tickers with the free trial. | Matching names require an eligible plan. |
| Locked card, ZH | 开启免费试用即可查看此组合匹配的股票。 | 查看匹配名称需具备相应方案权限。 |
| Retained empty-match fallback, EN | No stock matches this one today — it fires rarely. | No stock matches this combination in this snapshot. |
| Retained empty-match fallback, ZH | 今日无股票匹配此组合——它触发较少。 | 此快照中暂无股票匹配此组合。 |

The visible locked explanation now agrees with the existing lower eligible-plan explanation and the protected-response owner. The existing trial CTA and its exact tagged application destination remain unchanged. Opening that link does not itself establish entitlement or hydrate names; the existing access and response checks continue to own that behavior.

An empty matching list cannot establish today's market state or historical rarity. The retained fallback now describes only its supplied snapshot. **Current eligibility excludes combinations with no active tickers**, so this is a defensive template correction, not evidence of a reachable current valid-source empty-card path. Its explicit render-only fixture clears the first card's active tickers/count after context construction; no such fixture is published as current data.

## Verification and conservation

Four text literals change in the template. The actual saved source renders two gated cards, so four text nodes change in that saved HTML. Reversing those exact substitutions restores both parent files byte-for-byte. All CSS, HTML structure, scripts, values, ranks, tooltips, hrefs and source clocks remain exact. Both rendered ledgers match the corresponding saved pages.

The builder, page-test file and protected JSON remain byte-exact; the protected JSON still matches its actual producer. The existing full-source receipt and tagged CTA are unchanged.

**92 existing page tests pass** on the copy source: 4.98 seconds pytest, 5.46 seconds process. No new test mirroring these literal strings was added.

Two native visual-inspection contexts show the changed actual saved-page explanations at EN 390px dark and ZH 320px light, with zero page errors, no document/card overflow and existing 44px CTAs. These are **two visual inspections, not a new functional browser-test suite**. Their actual text, destinations, geometry and original PNG hashes are in [COPY_CLARITY_VALIDATION.json](COPY_CLARITY_VALIDATION.json).

![English locked explanation](captures/copy-locked-390-en.png)

![Chinese locked explanation](captures/copy-locked-320-zh.png)

The Chinese 320px layout retains an existing flex-wrap issue that puts the icon on a separate row. Its text and action remain readable; the isolated icon is a concrete next layout follow-up, not part of this text-only repair.

## Builder and ownership

Use the existing entitlement controller, protected endpoint and source-selection rules. Add no new trial flag, access resolver, notification service, empty-state availability rule or data inference.

The R2 Paper anatomy already uses neutral locked/public-evidence descriptions; no customer-frame text change is required. The existing Build guide records the precise access/fallback semantics and current source pin.

This increment continues dependent Draft PR10893 from parent 27d50dc0. The preceding 20-case responsive and 16-case comparison browser receipts keep their own source heads. Current copy inspection does not restamp them as this head. Incumbent PR10705 admission and all wider programme/release holds remain unchanged.
