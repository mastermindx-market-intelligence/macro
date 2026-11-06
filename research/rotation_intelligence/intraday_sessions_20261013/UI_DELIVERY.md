# Sector Intelligence: visible interval comparisons

Original operation rotation-intraday-session-research-20261013, Macro PR #9196. The existing What's Moving view now contains an Intraday leadership panel. No new page, endpoint, data source, scoring engine, cycle model, alert, or history service.

## User capability

A user can compare a group's daily return, observed interval return, and SPY-relative return together. An unchanged daily price no longer hides an opposing interval move. Opening a row reveals exact UTC source times, duration, SPY return, matched/total constituent count and the permitted per-endpoint clock skew. Closing observations retain their explicit regular-session-close label. The observed price change is not presented as money flow, forecast, calibrated confidence or a buy signal.

The existing Basket Pulse fetch owns the data. It is now single-flight, supports the panel's Refresh button and existing page-focus/visibility events, and separates loading, denied, unavailable and invalid responses. The only new timeout invalidates expired displayed evidence; it performs no source polling. Row expansion and keyboard focus survive a repaint. English and Chinese, light and dark themes, and narrow viewports use the existing design tokens and language/name-map owner.

The view checks the producer-owned schema and measured fields. It does not originate a new detector or independently establish source rights. Same-session/calendar and source-signature qualification remains the producer's responsibility; the client checks explicit session-date identity and freshness before rendering. Unknown remains missing, not zero. Numbers and input labels are escaped/allowlisted.

## Verification

The eleven-module combined suite passed 622 tests: new shipped-JavaScript tests plus incumbent Sector Central measured-view/template tests and the eight backend suites. The existing pytest cleanup warning from another temporary runtime directory is retained, not repaired here. New test suite is invoked by the existing code-gated group-read-surface job; the current workflow already starts for tests/** and all repository paths, so no redundant workflow trigger was added.

The actual candidate Jinja template was rendered with synthetic producer-replay data before source placement, visually checked, then installed unchanged except for accessible numeric labels and the disclosure caret. The final source was captured again. Four Chromium cases cover 1440px dark/EN, 1440px light/EN, 390px dark/EN, and 390px light/ZH. All confirm zero page-script errors and no page/panel horizontal overflow, keyboard detail expansion, preservation of open state and focused summary, denied-response clearing, and stale-data clearing. This is the real existing page and routing code with isolated synthetic responses, not an invented standalone component or authenticated production evidence.

`ui_proof/browser_report.json` binds the exact template SHA256 and all screenshot bytes. `capture_intraday_view.py --out <new-dir>` reproduces the capture with the existing Playwright installation. All browser requests are intercepted locally; no live source, credential, customer data or remote publication is used. The two example groups and prices are synthetic controls, not current market findings.

## Boundary

Backend source review r2 runs through the installed M2 Fabric adapter against frozen backend commit 460af1ea68880543d880801b0838d970643e5a75. UI source needs its own bounded independent review before final acceptance. The earlier r1 result was consumed with its scope deviation and exact remedies documented, not silently marked PASS. Current source remains BUILT_NOT_PROVEN until normal release and an actual authorized product path are verified. Terminal React integration, fixed-horizon retained history, opening anchors, overnight coverage and notification-quality studies remain unfinished. The existing Terminal #881/#847 paths and private SSH denial are not bypassed.
