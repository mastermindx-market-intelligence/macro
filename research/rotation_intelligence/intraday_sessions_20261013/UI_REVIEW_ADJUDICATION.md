# M2 Fabric UI review and final display remedies

Original child rotation9196-ui-review-r1 reviewed template 3b53a64fb1ef80b495f5c476c4eb2541c3588c6f on original root/parent rotation-intraday-session-research-20261013. Retained text-only result: 8165 bytes, SHA256 d420e49bf42f3ad7053c9dc6a227e23a3f70b43eb68e43a4fd8361d93dbc2606; verdict CHANGE_REQUIRED. No remote tool or repository effects claimed. Useful review delivery is not code approval.

## Rulings and repairs

- Future clock: retain rejection. Market/member endpoint skew and evaluation time are different quantities; a permitted asynchronous measurement does not authorize presenting future data as current. The proposed arbitrary 30-second future allowance was not adopted. A future source stamp now has explicit source/device-clock disagreement copy instead of missing-data copy, with a regression proving it still yields no accepted numbers.
- Focus and repeated announcements: changed data now preserves the focused summary if it survives, otherwise focuses the stable tabindex=-1 content region. Byte-equivalent render output is not replaced, so unchanged refreshes preserve the actual DOM node and avoid repeat announcements. Actual-browser tests drive automatic focus-triggered refresh followed by a denied result; both node retention and focus landing pass.
- Neutral heading: Intraday relative moves / corresponding neutral Chinese replaces wording that could imply only rising leaders. Absolute-magnitude ordering remains an explicitly descriptive display choice, not a new rank signal.
- Additive expiry: the timeout only rerenders its own panel, not the incumbent daily tape. Day numbers share the existing finite/sanity bound. Malformed observed rows say verification failed; unknown failure-state keys cannot expose Object.prototype. The existing NY-date formatter is constructed once. Show-all has aria-controls; in-flight refresh declares aria-busy.

No source clock was clamped, no freshness threshold loosened, and no new calendar, data source, signal, notification, recurring source poll or permission was added. Production source/entitlement proof remains separate.

## Evidence

Five new JavaScript regressions fail on the predecessor; all now pass. The combined eleven-module suite passes 637 tests. Four actual-Jinja-page Chromium captures, with locally intercepted synthetic producer-replay inputs, pass desktop/mobile, dark/light, EN/ZH, keyboard expansion, preservation of open state, exact focused-node preservation on unchanged automatic refresh, denial focus landing, stale clearing and show-all without refetch. Zero page-script errors and no horizontal overflow. Measured visible text contrast against the actual panel is at least 5.219:1 in dark and 7.032:1 in light for this matrix. Screenshot bytes and exact template hash are retained in ui_proof/browser_report.json.

The captured source still uses incumbent escaped display-name helpers and existing theme variables. The synthetic production-shaped payload is derived from the actual producer replay and confirms serialization precision, not a historical trade or current market observation.

Backend retention review r3 is separate, subject f873927f9ed410be1f11fc928dfaa4880e485b6b; these UI changes do not alter its backend blobs. A final bounded UI remedy review, final-head hosted CI and normal release remain owed. This source is BUILT_NOT_PROVEN; no deployed-user or financial-edge claim is made.
