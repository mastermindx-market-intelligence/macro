# Decision Desk R2 — actual BioCatalyst host integration

**2026-10-20 · BUILT_NOT_PROVEN · Draft/HOLD.** This is a review candidate on original Macro PR #9611, operation `biocatalyst-decision-desk-r1-20261018`. The source parent is `84bd28b6ae2badd444075e83e42b1390362cb068`. The containing commit and `mockups/evidence/biocatalyst-decision-desk-host-r2/source-hashes.json` identify the new source. No release, native admission, deployed entitlement, model qualification or trade authority is granted.

## User-visible change

The actual BioCatalyst page now opens with the existing Decision Desk: what needs review, the supplied company milestone, its principal unresolved question, and Setup/Scenarios/Research/Sources. The original trial tools remain under a secondary **Trial evidence** disclosure. Existing trial/filter URLs still open that workbench. No synthetic record is baked into the static page or used as a production fallback.

This closes the host insertion seam described in `IMPLEMENTATION.md` section 3. It does not change the existing WMN wire contracts or replace the native publisher. The investor-intelligence destination remains broader than this first milestone-review delivery: actual economic impact, same-subtheme behavior, technical context and conditional scenarios still depend on qualified owner outputs.

## Existing owners retained

`templates/biocatalyst_decision_desk_host.js` composes the reviewed component with the existing `MDXAuth`, `mdx-auth` events and Bio page `fetchJson`. It calls only the fixed WMN list/detail endpoints. MDXAuth user presence is a local availability hint; the unchanged server remains the paid-access authority. No session token is stored in URL/history, a new client, or a new cache.

Namespaced URL fields are `bci_view`, `bci_days`, `bci_case`, `bci_issuer` and `bci_task`. Other query fields and existing history state survive. Duplicate/malformed fields refuse without a source fetch. Case restoration is limited to the loaded owner page; an unknown case is explained rather than silently widened to a different universe. Back and direct navigation do not echo a new history entry.

Logout and account changes clear the case, counts, detail and legacy records synchronously. Obsolete in-flight completions cannot restore them even when abort is ignored. Language changes recreate presentation while preserving route meaning. Page hiding clears private state and a persisted page-show event revalidates. The test simulates that lifecycle; it does not establish actual browser back-forward-cache admission.

The builder emits all three Decision Desk assets and retains template/site parity. Only these data-free static asset paths are added to the public allowlist; no Bio API is made public. Existing mobile Brain behavior is preserved by hiding both loaded and lazy floating launchers at the same mobile breakpoint, leaving the in-flow action. Desktop retains the canonical floating launcher.

## Verification and boundaries

| Verification | Observed result |
|---|---|
| Existing JavaScript component + new host lifecycle tests | 89 + 20 checks passed through existing pytest wrappers; local Node 26.5.0, not a Node 20 claim |
| Combined page/component/hydration/D0a/D0b/shared-launcher suite | **108 passed, 1 inherited failure**, 9.61 seconds |
| Integrated actual-page browser harness | **14 behaviors, 16 theme/locale/width combinations, 8 actual CJK font checks passed**, zero page errors; Chromium 129.0.6668.29 |
| Canonical anonymous capture | **24/24** actual rest/hover/focus states; zero console errors, zero failed responses, no horizontal overflow in recorded desktop/mobile metrics |
| Design token ratchet | 0 new blocking findings; inherited estate findings remain separate |
| Runtime stylesheet ratchet | 234 JS files scanned, 44 injecting, 88 hits, all within existing allowances |
| Source claims | Passed; source-only scanner |
| Diff check | Passed |

These are overlapping test layers, not an additive unique-test count. The new Python wrappers execute the JavaScript checks. Hosted Node 20 and exact-head hosted CI retain their own verdicts. The previous current-head CI at `84bd28b6` passed all twelve code packs and `ci-gate`; that says nothing about this new candidate.

The sole remaining broad-suite failure is `tests/test_chat_launcher_stub.py::test_no_dynamic_child_asset_is_document_relative`, which flags `stock.html#` in shared `templates/theme.js`. Both shared files are unchanged from the source parent. No claim is made that the failure is harmless; it is not waived or repaired by modifying another owner's source. The original fixture-related failures were resolved by restoring the three frozen D0a JSON files byte-for-byte from HEAD.

Reproduce the focused suite with:

```sh
python3.12 -m pytest -q --tb=short --basetemp=.pytest_cache/host_r2_verify \
  tests/test_biocatalyst_decision_desk.py tests/test_biocatalyst_page.py \
  tests/test_biocatalyst_hydration.py tests/test_biocatalyst_d0a_design_contract.py \
  tests/test_biocatalyst_d0b_ui.py tests/test_chat_launcher_stub.py
```

Reproduce synthetic host behavior after building the paired assets with `python3.12 tests/verify_biocatalyst_decision_desk_host.py`. It requires the repository-declared rjsmin dependency and an installed Playwright/Chromium runtime. The dependency was supplied in the original ignored `.pytest_cache/host_qa_dependencies`, not installed globally. The retained result and two selected screenshots are under the canonical evidence folder's `synthetic-host/` subdirectory. Its authentication and WMN responses are explicitly fictional test seams, not an actual entitled account or native-data source.

The anonymous manifest is separate: `scripts/capture_page_evidence.py` version 1.3.0, unchanged SHA256 `8d753e2859d5261eb0d0bad3f626f8870eedf03e23a7f87b4b588bd792e88f16`. It retains explicit authenticated-access and data-state gaps. Its exact staged asset provenance is retained without distributing account credentials or live payloads.

## Interrupted-capture reconciliation

The prior Studio 502 had no PID or result receipt. On the recovered generation, the exact initial staging directory, inventory, log and manifest were all absent and no matching capture process was running. This established **NOT_APPLIED target effects**, not a claim that historical dispatch had never occurred. The same carrier and target were continued.

The first capture completed but exposed an omitted public `account.js` in QA staging. Including it exposed its actual lazy `nav_market.js` dependency. A bounded static traversal of the existing authored JS/CSS closure resolved the cause instead of hiding failed responses. The final same-tool capture completed with all 24 states and no failed responses. The two earlier manifest/log sets and 34 superseded PNGs are preserved in the original ignored QA cache, not passed off as current evidence. No source publication was included in any capture command; there is no unresolved capture effect now.

## Independent review and release

**Independent review of this host delta remains required.** The prior R1 component review is retained for its unchanged scope only. The Executive Session Bridge returned `backend_unavailable`; no new reviewer or worker was launched or represented as executing. Root inspection of screenshots is not independent source/visual approval.

The separate R10 chat retains #9662/#6712 and Codex retains native-adoption receiver `01a158fd-eaba-7342-8b59-081a483f2fc2`. Read-only census observed #9662 at `902465f702a30abb943b08e792d670827a68650b`, now on main, with current CI failures/running packs. Its new handoff resolves the Company case for its cut and identifies the remaining DataOS dependency through existing #9617. Existing production-host/canonical-staging denials and the refused native reviewer/census operations remain in force; this frontend does not bypass them. Coordination is recorded on #9662 comment `6291265578`.

The next combined acceptance needs: qualified current Company/DataOS inputs; compatible native pointer readers before writers; shared real admission/pointer/lock state; accepted frontend/native source composition; exact-head CI and independent review; an actual entitled source-change/correction user journey; and explicit release-hold removal. A model summary, clean static capture or green local tests cannot substitute for those gates.
