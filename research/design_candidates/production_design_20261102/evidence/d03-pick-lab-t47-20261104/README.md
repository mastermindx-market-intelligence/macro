# D03 T47 — Pick Lab local navigation

Status: source implementation + native component and actual-template browser proof; Draft/HOLD. This is not whole-D03, release or production acceptance.

## Identity and scope

- Mission: keep all seven existing Pick Lab tabs and each book/history path usable by keyboard and touch, with honest selected/focus state and safe missing-target behavior.
- Base: `52abe2e183833a216267942a99513e6c9cbe062f`.
- Protected Mastermind procedure pin: `75a6540519cf519edfef7633e74f57b68aef9329`.
- Operation: `d03-pick-lab-keyboard-navigation-20261104-c2`.
- Original admitted branch: `claude/ssd-d03-pick-lab-keyboard-navigation-20261104-c2-7ae8b28781766f3b`.
- Parent continuity: [D03 checkpoint](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6623889088).
- The accepted Phase 2A 78-capability / 53-case tree remains unchanged. This is the T47 local navigation slice, not a shared-shell/URL/storage state owner.
- Only the Pick Lab template, new deterministic tests, scoped CI registration and owned evidence change. Engines, renderer, publication builder, ranking, qualification, data, live ledgers and Long-Hold rules are untouched.

## Product behavior

Seven main tabs remain: Scoreboard, 1D Velocity, All Books, Beta, Long-Hold Grid, Record and Method. Main and nested book selectors have stable IDs, reciprocal tab/panel labels, selected state, one roving tab stop and matching hidden/display state. Left/Right wrap; Home/End reach the ends; native Enter/Space and Tab remain native. Modified shortcuts are not captured.

Both tablists share one page-local helper. A destination is resolved and validated before the origin is hidden. Missing, removed or mismatched controls leave the origin intact. Empty and singleton books are safe.

Scoreboard drill resolves the exact entry or Long-Hold book, retains its history, opens its existing all-fires disclosure, moves focus to its book heading and scrolls to the actual destination. It reads the current reduced-motion preference at activation, including preference changes after load. It never writes URL, history or storage.

New main tabs/chips/drill/disclosure targets are at least 44px. Chip names wrap. Keyboard focus is visible. Existing control tokens and colors are reused; mobile main-tab spacing fits two rows at 390px in both languages and at 320px Chinese. The longer 320px English labels retain three rows without clipping.

## RED and deterministic checks

- Actual unchanged-template browser proof in `browser/red/` reproduces four failures: absent selected state, no ArrowRight navigation, no destination focus after drill, and smooth scrolling despite reduced-motion preference.
- Corrected deterministic exact-base RED: 17 failures. An earlier incomplete synthetic fixture was corrected before being counted as product evidence.
- Final new suite: **21 passed** (3 markup checks + 18 executions of the rendered inline JavaScript in Node).
- Focused aggregate: **169 passed** (21 new + 148 retained).
- Final spacing refinement: new 21-case suite passed again; added-line design-system ratchet reports zero blocking findings.
- The Node harness is a deterministic DOM-state model, **not** browser evidence. Actual browser proof below separately exercises native input/focus/layout.

Reproduce the new deterministic suite:

```sh
python3 -m pytest tests/test_pick_lab_navigation.py -q
```

The local runtime was Python 3.12 with the CI job's six Python dependencies and Node **26.5.0**. Hosted CI explicitly selects Node **20**; local Node 20 execution is not claimed.

## Actual-template browser proof

`verify_browser.py` uses the real `build_vm`, `render_page` and `write_page`, with isolated synthetic inputs and actual local page assets. The public `site/live_config.js` is read from the admitted Git tree. External requests are blocked, and source hashes are checked again at the end.

Final proof: `browser/browser-proof.json`; Chromium **151.0.7922.34**; **56 cases**, **59 screenshots**, **0 page errors**, **0 failed responses**, **0 external requests**.

- Populated/empty × widths 320, 390, 768, 1024, 1440 × EN/ZH × light/dark = 40.
- Long-name/singleton × widths 320, 390 × EN/ZH × light/dark = 16.
- Actual shared-theme palette, visible language and loaded local font verified.
- Full main/nested keyboard cycles, native Enter/Space/Tab, touch activation, reciprocal selected/focus state, destination focus/history, settled scrolling, changed OS motion preference, missing targets, 44px geometry, no page overflow and no URL mutation verified.
- Main-tab text minimum measured contrast: **5.7343:1**.
- Proof binds 26 source/asset hashes and the runner SHA. Final template SHA-256: `8ff420e2cabec61f30fcb3e068a94d22d476e83354f18f1945c4c3b8e9da6904`.
- Actual screenshot self-QA included 320px dark Chinese, 390px light English, long names, desktop and the canonical page captures. It caught an avoidable third mobile row and a shared-theme transition overriding reduced-motion CSS; both were fixed before the final run.

```sh
python3 research/design_candidates/production_design_20261102/evidence/d03-pick-lab-t47-20261104/verify_browser.py --repo "$PWD" --out /tmp/d03-t47-browser-proof
```

Requires the repository's Python/render dependencies and an already installed Playwright Chromium. The runner writes only its specified output tree and serves isolated fixtures, not live market data.

## Native Paper and canonical visual receipt

Native PROPHET file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, page `p-D-0`, owned board **11KZ-0**, “D03 T47 · Pick Lab navigation · component DRAFT”, 960×760. This is a desktop-light-English / narrow-dark-Chinese **component study**, not a full phone or complete platform matrix.

Screenshot self-QA preceded JSX extraction. Finish operation `d03-t47-nav-component-finish-20261104-c2` returned **APPLIED_RESPONSE_OBSERVED**. `paper-receipt.json`, `paper-11KZ-0.jpg` and `paper-11KZ-0.jsx` retain the exact bindings/hashes. Shared token hash `640746f9` is unchanged. Other sessions' native boards were neither edited nor adopted.

Repository visual gate receipt: `mockups/refs/d03-pick-lab-navigation-20261104/EVIDENCE.yml`.

The unmodified canonical `scripts/capture_page_evidence.py` v1.4.0 captured **24/24** states: 1440/390 × EN/ZH × light/dark × rest / real tab focus / real tab hover. Console errors and failed responses are empty. The actual visual-evidence gate passed. Its captured HTML SHA-256 `f8c64fdfbc9c430b83db017c388e54e62dfb21d1aa8adc3f13a1d33607421629` matches the final browser fixture. Canonical tool module SHA-256: `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`.

The canonical manifest truthfully reports missing authenticated access/page states; custom behavior proof supplements it rather than silently replacing the repository evidence plane.

## CI and pending delivery checks

New code-gated exclusive job `pick-lab-navigation`: one 21-case suite, Node 20, Python 3.12, six existing Python dependencies, weight 4. All 29 derived concrete paths—including ancestor package initializers, actual template includes, and the Node harness—are retained. Only opaque unrelated fallback traversal is excluded. Existing Pick Lab jobs and packing ceilings are unchanged.

A one-job inference diagnostic after staging the new suite found all 29 concrete paths and no omissions. The earlier unstaged-suite check correctly found no tracked suite; that failure is not hidden or counted as a pass. Full nine-guard/manifest validation and committed-tree contract-delta results will be recorded in the PR and cumulative checkpoint.

## Retained boundaries

Draft/HOLD only. No Ready, un-draft, label, enqueue, merge, auto-merge or deploy. No final F01/F02 release assertion, D23 binding, identity/assessment persistence, production auth/data/freshness proof, or T38 publication adoption. Original #9495 dirty T004, held R8/Fabric effects and other active native boards remain untouched. No optional reviewer wait or duplicate worker was created.
