# Basket Detail — keyboard sorting continuation

Status: built and local-browser verified; not production-proven. Same carrier: PR #7497.

## Outcome and authority
Chairman requested an ongoing grouped frontend/UX sweep via Web Chat, with VPS-only deployment. This continuation keeps the existing Basket Detail source writer and fixes unreachable sort controls; it does not widen ranking, position or data authority. Protected Skillpack: Mastermind@5f62e9f6119cc3e3bc542a793ba96731e063e3a1 (v1.0.1). Direct work is lower-overhead continuation on the existing source branch; no worker is spawned.

## Before / after
At source head 49c879f7ce5e47219759f4a0aa767cd0c96a8dc4 both clickable holdings headers had tabIndex -1, zero native buttons and zero aria-sort attributes. Users can now reach sorting by Tab, activate exactly once with Enter/Space/click, and retain focus through sorting and delayed optional-data refreshes. The native score disclosure keeps its previous state. Selected-language labels survive language toggles.

Potential continues to use the existing multi-key research ordering, NOT a pure numeric score sort; aria-sort is deliberately `other`. The 20-day return column uses ascending/descending semantics. Only the active header carries aria-sort. A bilingual tooltip and visually hidden caption explain this without adding another visible paragraph.

## Design
Dark: existing instrument surfaces/ink with a restrained text control and semantic focus ring. Light: existing research surface/hairline treatment with the same interaction and semantic ink; no palette or shared theme changes. Mobile allocates 80px to the Potential column so the label never breaks into two lines. Controls expose direction by shape rather than color alone. Existing mobile column visibility is unchanged.

## Data and failure contract
All 121 embedded DETAIL payloads and the existing sorting comparator are byte-identical to the previous head. Missing-value ordering, model weights, quote subscriptions, endpoint permissions and private-data authentication are unchanged. Local negative tests force optional requests to 401; delayed-refresh cases release the already-committed crossmarket JSON, not fabricated live data. The public verifier intercepts nothing. Native buttons/details and existing `_sort` remain the owners; no extra persistence or keyboard state machine.

## Verification
- 160 tests passed in the existing FTR, group-read, stock-personality, product-chrome, subdirectory navigation and Basket Detail suites.
- `verify_sorting.py`: 16 route/device/language/theme cases plus four asynchronous-response focus/order cases. Real Tab, Enter, Space and mobile touchscreen taps; no direct sort/render invocation. Source data and rank order preserved; numeric return ordering checked on desktop. No JS page errors or horizontal overflow. Explicit label line-height and control-width assertions prevent a falsely green but visually split label.
- Canonical 48-state rest/focus/hover capture: `mockups/evidence/uiux-basket-sort-20260920/`.
- Discriminating prior-source failures: `counterexample.txt`.
- Standards reference for native-button headers and aria-sort: WAI APG sortable-table example and grid-and-table-properties (w3.org, inspected 2026-09-20). No claim of manual NVDA/VoiceOver certification.

## Exact next action / do not redo
Conclude exact-head hosted checks, consume the incumbent shared theme repair #7523 through its owner, then qualify the immutable current-base integration. Only after actual gates clear, deliver through the existing VPS updater and run `verify_sorting.py --base-url https://www.mastermind-x.com --output-dir <production-evidence>` plus the prior resilience verifier. Do not force-merge, rewrite shared receipts by hand, rebase solely for ancestry, request Vercel deployment, create a replacement PR, reimplement sorting/ranking, or repeat completed source repairs. Source screenshots/tests do not prove deployment.

## Latest release checkpoint
See `../integration/README.md`: canonical current-base CSS binding, 160 tests and 20 browser cases verified. The original UI semantics remain frozen; exact-head hosted checks and VPS/public proof remain required.
