# Shared shell — desktop navigation depth and integrated review

**DESIGN CANDIDATE. Not implemented, interaction-tested, approved for release or deployed.**

Operation: `market-os-shared-shell-design-20260924-sol-001`. Parent: `WS:MARKET-OS`. Sole carrier: Macro #7949 / `sol/market-os-shared-shell-design-20260924`. Chairman intent remains one coherent Macro/Terminal experience, with editable mockups and refinement before site-wide release. Sol retains design/integration responsibility; incumbent implementation, identity and data owners are unchanged.

## Current recommendation

Retain a compact primary sidebar, one-level disclosure, native workspace tabs and an All tools projection for deeper routes. Use a collapsed rail for focused Terminal work. This is the selected desktop direction for further refinement, not Chairman visual acceptance or implementation/release admission. Do not restart alternative sitemap exploration without a concrete invalidator or Chairman feedback.

The integrated review resolved three inconsistencies on the existing artboards: the directory's all-market scope no longer sits under a misleading United States label; personal alerts are labeled My alerts; and the Terminal example now carries the same Technology selection shown in the Sector map. No new artboard was created in this review.

Paper file: `01M2WGNCX9475G79JRKJTCM08P`, MASTERMIND PAGES. Review page: `p-D-0`.
https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-D-0

The directory study remains `UQV-0`, **08 · All tools · Desktop navigation depth · 1440**, 1440x900 at canvas7020,0. It shows nine selected example destinations, not the entire inventory or an assertion of entitlement or live serviceability. The original country-popup and mobile studies are still incomplete and are not replaced by these desktop corrections.

## Integrated decisions and exact limits

### One visible viewing scope per surface

The directory header now reads **SCOPE · All markets**. Its category row reads **9 example destinations**, rather than adding a second scope control. US overview and Sector retain their existing United States context. This supersedes only the original directory mockup's combination of United States in the topbar and All market scopes in the page.

All markets is a directory viewing scope, not a new country, not a change to followed/enabled markets, and not the existing FollowId global value. The design adds no taxonomy enum, preference write, persistent state store or universal all-market mode for tools that cannot support one. The eventual owning route must explicitly represent the directory scope; its parameter name and encoding are not invented here. Return to a country page must preserve that page's own explicit context.

Individual cards keep their real US, International or other-asset scope. A broad directory scope cannot widen access, relabel underlying data or imply every listed tool supports every country. Only the closed header was changed; no dropdown interaction was implemented, and the held popup UJ4-0 was not touched.

### My alerts and market alerts are different existing jobs

The personal navigation label now reads **My alerts** on the existing US Overview TUD-0, Sector UBT-0 and directory UQV-0 artboards. It is intended to reach the existing signed-in Terminal alert-management surface, not to be resolved by label similarity to Macro alerts.html.

Source evidence:
- Terminal `terminal/app/(shell)/alerts/page.tsx` at `febda456bf584a428aa4ed13ff596869116e0283`, blob `583191e487ebcb320c6ff1ec02b0aec88d17c686`: account-backed alert management and its existing SignupGate. The blob matches the preceding inspected Terminal snapshot.
- Macro `templates/nav_market.js:225-250` at `25fb8fa805d611727078f65626f2c3b0388070b3`, blob `4edee693e1e6d4391de3482b2a618057df686e56`: Alert Center is ranked market-moving alerts at alerts.html.

Do not merge the routes, stores, counts, access gates or notification semantics. The eventual navigation must bind the owning origin and route, not normalize both to an ambiguous alerts slug. A signed-out personal-alert visitor retains the existing sign-in gate; market-wide signals must not be substituted as a fake successful personal view. Conversely, a general market alert does not prove the user created a saved watch.

An intended replacement of the first directory example with Market alerts was safety-refused before dispatch. Same-carrier readback verified that UUX-0 still says Market dashboard, with its original description and SVG. That replacement was not retried, including through smaller requests. **Market alerts has not been added to the directory mockup.** The nine original examples below remain accurate. The distinction is partially visible through My alerts and fully specified here; the unrendered directory change remains on its exact original hold.

### One selected research context through Sector and Terminal

The existing Sector study selects Technology and names NVDA among its members. The focused Terminal study previously used Semiconductors / NVDA in its return context. Its top breadcrumb now reads **Technology / NVDA**. The research-context rail says **From Technology to NVIDIA**, explains that the security was opened from Technology on The map, and exposes **Back to Technology**.

This corrects the illustrated journey, not the live return implementation. NVDA, NASDAQ and USD remain unchanged; the synthetic chart and sample watchlist remain labeled. No watchlist membership, symbol selection or account data was written. The existing first-adoption contract still governs same-document retention versus direct/new-tab URL restoration: a return URL alone does not preserve unsaved in-memory filters. Production selection/scroll restoration must be proved through the current workspace and portal owners, not a new shell snapshot service.

## Interaction model retained

A disclosure changes visible child links, not the current route, market or selected security. In implementation it is a keyboard-operable button with exposed expanded state; child destinations are links with native modified-click behavior. Where a group also has a landing route, separate the navigation and disclosure targets. All tools is selected in the directory study while Markets is merely expanded.

Expansion belongs to the existing shell's presentation state, not a new navigation service. Collapsing must not remount the workspace or mutate personal data. Long localized labels and smaller desktop heights require deliberate navigation scrolling with reachable account controls; the1440x900 screenshots do not prove those cases. Collapsed-rail labels/tooltips must follow the same destination semantics, including My alerts; tooltip interactions are not implemented by a layer name.

All tools projects existing qualified route ownership, not another catalog. Consume the incumbent registry for qualified identity/eligibility and owning navigation definitions for labels and destinations. Reconcile differences instead of maintaining a second directory database, search index, entitlement list or compliance ledger. No new production URL or registry schema is assigned here.

The existing global search remains the intended search entry. A Tools result mode may project eligible route metadata through that owner; neither search nor category filtering is implemented by these static designs. Empty matches, unknown capability, denied access and missing data remain distinct. Raw registry records must not be promoted automatically into directory counts.

## Visible route examples retained

Bounded source: `templates/nav_market.js:205-268,390-478` at Macro `25fb8fa805d611727078f65626f2c3b0388070b3`; blob `4edee693e1e6d4391de3482b2a618057df686e56`. No adaptive JavaScript evaluation, broad menu extraction or refused Sector-test reads were repeated.

| Visible example | Existing destination | Preserved job |
|---|---|---|
| Market dashboard | macro.html | US market overview; this row was not replaced |
| Market structure | market_structure.html | Positioning, dispersion and weekly range |
| Intraday flow | intraday_flow.html | Native session board, original conditional visibility and delayed-data semantics |
| World dashboard | intl.html | Existing International dashboard, not relocated to markets.html |
| Country cycles | country_cycles.html | Country/region comparison |
| Global market cycles | markets.html | Separate market-cycle comparison |
| Commodities | commodities.html | Existing commodity desk |
| Forex | forex.html | Existing currency desk |
| Bonds | bonds.html | Existing rates/credit/duration desk |
| Confluence shortcut | sector_central.html#confluence | Retained native consumer, not another scanner |

Source presence is not access or deployment proof. Confluence's separate MM-07 serving dependency is not resolved by this shortcut. Missing China, Hong Kong, Canada, crypto or research example cards are not deletion decisions. The334-row source qualification, fragment/utility/operator exclusions and95/37 attribution limits remain unchanged and were not rerun.

## Visual verification

All edits stayed on the incumbent m2studio Paper client/process90003 after operation/file/page identity checks and targeted node reads. Current protected procedure was freshly pinned to Mastermind `a29161fa0a44cca9927afe042b5f7ea25aae1736`; INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT loaded at that same compatible1.0.1/bootstrap1 pin. Existing Inter and token hash5ae876bc were checked; no tokens changed.

| Evidence | Scope and review verdict | SHA-256 |
|---|---|---|
| 19-directory-scope-header.png | Scope, label and search lanes legible; closed header fits | cc85fe005df80c405c8b83ee850c9deccb1d0e7e4259b9c8b2b7a4fdb0313531 |
| 21-terminal-source-context.png | Full1440x900 Terminal study; same Technology context in breadcrumb and return rail; chart/sidebar/copy fit | 47d000b25b28105071fb8616e1f6961cdc87bc4e9e2ae07a41a19edd99b8ac4b |
| 22-directory-context-final.png | Full1440x900 directory; All markets, My alerts, nine unchanged example rows, shortcut and footer visible without observed clipping | bc8e101ce0cad0f9aff2eefa2b61c799ee28d0e0043687ea190f80d1c0970fca |
| 23-overview-my-alerts.png | Changed sidebar region only; label fits and Overview stays active | db1af7775aad9f225a53e62b19009b65bedbf6f00770619736a897535036e2b4 |
| 24-sector-my-alerts.png | Changed sidebar region only; label fits and Sectors & themes stays active | 4cbac894daa3d7e0cb6bd2c19e237ba464ba54335b4fa4943c46b573d19b9bb6 |

Each image above was visually inspected. Targeted node readback confirmed all seven changed label/return values. Sidebar-region evidence does not reaccept the full Overview: its existing footer-fit defect remains held. The Sector body and six native views were not modified. Spacing, typography, contrast, alignment and repetition were reviewed only in the changed composition/regions; browser interaction, accessibility, responsive and bilingual proof remain owed.

`finish_working_on_nodes` for TUD-0,U19-0,UBT-0,UQV-0 returned OK with token hash5ae876bc. All original reference pages and held popup/mobile artboards remain untouched. Files under `/tmp/market-os-shared-shell-design-20260924-sol-001` are convenience evidence; Paper and committed records carry continuity.

Historical evidence: original directory composition18-directory-complete-check.png digest ed9d0a81566114a4d1c3b64dd15f741a94316647b227aa028ba6ada7049a0933; original six-view Sector full screenshot13-sector-native-six-views-final.png digest60a84fae1e3a94c5b3bae7ab8a4b3c94f441b91ca02083815ff3a7a8694bcbfd. The former is superseded for directory header/personal-label appearance; the latter's unchanged body remains relevant, supplemented by the current sidebar capture.

## Remaining gate and next action

Desktop structure is ready for Chairman review as a coherent candidate; the whole integrated design is not accepted. Preserve current layouts rather than generate more unrelated desktop alternatives. Resolve specific feedback or a demonstrated defect; complete held country/mobile/alert-row/browser/hunk effects only after actual permitted recovery on their original targets. No successful independent edit releases those holds.

This review made no application, search, identity, auth, data, signal, personal-state, registry, source-writer, merge or production changes. There are no active children, watchers or background jobs. The new Market-alerts-row refusal is TOOL_DEGRADED / EFFECT_NONE after same-carrier readback, not EFFECT_UNKNOWN and not a global Paper outage.

Implementation remains an end-to-end responsibility under the original commission. Before code/release: integrated design decisions and missing states, exact current plan/custody, required checks, and the first-adoption contract's real overview-to-security-save-return proof. This document is neither a new implementation grant nor a claim that screenshots complete the migration.
