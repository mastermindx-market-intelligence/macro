# D03 T46 — truthful V2 shadow source coverage

Status: source implementation and isolated browser proof; Draft/HOLD. This is not a deployed page, released shared-shell reference, or live-market acceptance.

## Mission and ownership

The existing Phase 2A acceptance case T46 requires honest availability for error/missing inputs and a valid shadow result without changing live board files. Its 78-capability / 53-case task tree remains at macro `e521f04dcc5afb4fb06152584d35c8a01dbe21ff`. This slice does not replace D03, the existing US-2 grader, or the live Prophet opportunity writer.

- Protected procedure pin: Mastermind `75a6540519cf519edfef7633e74f57b68aef9329`, compatible skillpack 1.0.1.
- Admitted source base: macro `a1d489628a736fffdd5b95fb55afa8e12390261d`.
- Original branch: `claude/ssd-d03-v2-source-availability-20261104-c2-83f837d67b6f1244`.
- Cumulative continuation: https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6623889088
- Direct bounded maintenance rationale: LOWER_TOTAL_OVERHEAD. No new workstream, scheduler, ledger, publication mechanism, engine or ranker.

Historical #7508/#7664 only add entry-context/return metadata in disjoint functions. Their engines and tests remain untouched. Original #9495, its local dirty T004 work, the held R8 Paper operation and UX Fabric effect are not replayed or adopted.

## Behavior and invariants

Previously, missing/unreadable inputs returned `status: ok`, an empty board and a build-derived `as_of`. The existing grader ignores status and can reserve any truthy day before corrected inputs arrive.

The loader now records each consumed collection as readable, missing or invalid. Explicit empty lists remain valid; malformed collections cannot masquerade as confirmed zeroes. Only this reader's existing collection/row contract is checked. Values are not coerced, and valid rows are not rewritten.

| Input state | Coverage/UI | Shared observation / grader day |
| --- | --- | --- |
| Both candidate sources unavailable | Sources unavailable; counts shown as em dashes; qualification unknown | null; no day reserved |
| One source/collection readable | Partial coverage; available rows retained and labelled as a subset | null; no complete day reserved |
| Both complete, matching valid nonfuture source dates | Both inputs readable; empty or populated lanes retain their existing meaning | Exact supplied shared date |
| Complete but missing/invalid date | Readable inputs; source observation unavailable | null |
| Complete but dates differ | Readable inputs; mixed dates disclosed individually | null |
| Complete but any date is future | Readable inputs; future date explicitly unverified | null |

`generated_utc` remains the build clock, not source freshness. The page never calls an old observation “today” or “live now.” Complete undated legacy fixtures remain `status: ok`; no new qualification date gate is invented. The source-coverage envelope is additive, existing lane/count/concentration shapes remain, and `shadow: true` plus noindex/unlinked status remain.

Candidate union, WHAT gate, WHEN gate, setting-up logic, row construction, ordering and concentration functions are AST-identical to the admitted base. No threshold, tier, signal admission, ranking, trade authority, producer payload or live ledger is changed.

The template adds a neutral source-coverage panel and progressive source receipts in English/Chinese. It preserves the existing row functions, overlay and candidate destinations. Mobile grid/gutter fit, keyboard focus, >=44px source disclosure, reduced-motion ordering and nonbreaking dates are verified. This is scoped source-state accessibility, not a claim that all legacy card copy has been redesigned or fully localized.

## Native Paper provenance

Editable PROPHET file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, D03 page `p-D-0`, owned board `11GP-0` — “D03 T46 · Shadow source coverage · DRAFT.”

Three neutral component states were built and screenshot-inspected in the native app: unavailable, partial and readable/valid-empty. Existing shared tokens were reused; token hash `640746f9` stayed unchanged. The final date wrapping correction was visually checked before JSX extraction.

Final operation `d03-t46-native-component-finish-20261104-c2` returned `APPLIED_RESPONSE_OBSERVED`; no unresolved T46 native effect remains.

- [Actual native screenshot](paper-11GP-0.jpg), SHA-256 `1ba33a0285e1fbcfa8256cb006da23aa4f4aae57c75d7757705f522c4b9e8476`.
- [Post-QA JSX](paper-11GP-0.jsx), SHA-256 `511bd42079c7884c24620de320aded49946883d241d0222e04fd679115c70d47`.

The native component study is light EN; actual-template browser proof below covers the implementation's EN/ZH, light/dark and responsive states. Neither is an approved global reference.

## Tests and browser proof

The initial 63-case regression set against the exact-base loader/compute/template was **57 failed / 6 passed**. A further 13 malformed nested-row cases reproduced genuine exceptions/nonfinite acceptance before validation was extended. The final new suite contains **84 cases** including six real grader recovery paths.

Final focused aggregate: **283 passed / 1 skipped** in 20.13s. The skip is the existing `test_sa_w5_v2_grader_hook.py:601` check requiring absent sparse-checkout `cn_audit_scoreboard.json`; no new T46 case is skipped.

```bash
python3 -m pytest \
  tests/test_macro_header_compact.py tests/test_okx_retail.py \
  tests/test_w5b_edge_chips.py tests/test_stock_board_v2_availability.py \
  tests/test_stock_board_v2.py tests/test_sa_w5_v2_grader_hook.py \
  tests/test_reflexivity_overlay.py tests/test_board_contradictions.py -q -rs
```

The real grader recovery test covers unavailable, malformed, partial, unknown-date, mixed-date and future-date input followed by corrected valid data. It proves no incomplete snapshot, exactly one recovered AAA entry for the supplied date, idempotent replay and byte-preserved live-ledger sentinel. Build/write tests also preserve all live source/page sentinels and allow only the existing shadow outputs and existing write_page-owned shared-shell assets.

[Machine proof](browser/browser-proof.json) records **64 actual-builder Chromium 151.0.7922.34 cases**:

- Unavailable, partial, valid-empty and populated × 320/390/1440 × light/dark × EN/ZH = 48.
- Malformed, mixed-date, unknown-date and future-date × 390 × light/dark × EN/ZH = 16.
- Scenario-keyed coverage/clock meanings, exact visible warnings, per-source receipt dates, unavailable shared-date em dash, and separate build clock.
- No JS errors, no external network requests, no whole-page/component horizontal overflow.
- Neutral panel borders; new source-label/body copy >=12px/14px; measured source-copy contrast minimum **5.4267:1**.
- Real keyboard disclosure open/close and focus, 320px touch disclosure, candidate tab order/destinations, reduced-motion media and populated-card transition checks.
- Dates remain on one line. Nine actual source/assets are SHA-256-bound and verified unchanged during the run.

The initial browser pass caught the reduced-motion media rule losing to a later default transition. The rule was moved after the default and the entire matrix rerun. Visual QA also caught a 320px split source date; nonbreaking date treatment and explicit date assertions were added before the final run. All 83 actual screenshots (64 components, 16 expanded receipts, three full pages) are retained in [browser/](browser/). Representative final inspections:

- [320 dark EN full page](browser/page-populated-320-dark-en.png)
- [390 light EN partial page](browser/page-partial-390-light-en.png)
- [1440 dark ZH unavailable page](browser/page-unavailable-1440-dark-zh.png)
- [Future-date receipt](browser/details-future-dark.png)
- [Mixed-date receipt](browser/details-mixed-dark.png)
- [320 light ZH valid-empty component](browser/empty-320-light-zh.png)

Reproduce with an empty temporary directory and installed Playwright/Chromium:

```bash
d03_t46_proof=$(mktemp -d)
python3 research/design_candidates/production_design_20261102/evidence/d03-v2-t46-20261104/verify_browser.py \
  --repo "$PWD" --out "$d03_t46_proof"
```

The runner uses actual builder/template/write_page/assets, not replacement engine or HTML mocks. It patches only synthetic data roots and time, and serves the generated fixtures into network-isolated Chromium. It does not prove production authentication, runtime navigation to stock detail, server routing, deployed freshness or atomic JSON/HTML publication.

## CI and remaining acceptance

The new suite is registered in the existing code-gated `unrun-template-chips` job. Three adjacent hermetic pytest invocations are consolidated with it; every pre-existing suite/path/selector/dependency/gate remains. Computed job weight is **31 → 31**, with two fewer pytest processes. No packing ceiling or observed-weight override changes. Manifest validation remains 312 logical jobs / 12 packs.

Exact candidate contract-delta and hosted CI are separate checks; their final receipts belong on the existing cumulative continuation and this slice's Draft PR. Do not infer a gate pass from weight arithmetic.

**Release boundary:** no Ready, un-draft, label change, enqueue, merge, auto-merge or deploy. Existing protection and release holds remain binding. T38 mixed JSON/HTML publication is a separate retained obligation, not repaired here. F01/F02 joint-shell release, D23 mutation binding and original held effects are not cleared by this source slice.
