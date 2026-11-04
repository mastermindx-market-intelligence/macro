# D03 Foresight: combined T35 / T36 / T37 fixture proof

## Result and limit

The isolated composition passes **104 actual-template tests** and **36 Chromium cases**. The browser cases exercise the three behaviors together: an unavailable entry window (T35), confirmation-only current signals (T36), and producer-declared pending outcomes beside graded and control results (T37).

This is evidence of a virtual template composition at the exact revisions below. It does not merge the PRs, integrate whole-PR builders, run live data, deploy a site, release the programme, or qualify all D03 acceptance cases. The source PRs and programme remain **Draft / HOLD**. Hosted CI and eventual served production-path acceptance remain separate.

| Input | Exact revision | Original carrier |
|---|---|---|
| T35 unavailable entry window | `8b9ed9a0b63b6771f6b0f637c2a1df1e3cba5d53` | [#10713](https://github.com/mastermindx-market-intelligence/macro/pull/10713) |
| T36 confirmation-only current signals | `d5350fcddeaa60c3a271e4029ace69560ef6a2b2` | [#10721](https://github.com/mastermindx-market-intelligence/macro/pull/10721) |
| T37 pending outcomes | `e488b0a00951747e2cab89ecc1d867f470746dc3` | [#10723](https://github.com/mastermindx-market-intelligence/macro/pull/10723) |

The template common-base blob is `91915538514ce1c6d3f0f754779ebcd02dd946dd`, read at base commit `51c35090a624de1e977920e98def2c64488751b3`. Two `git merge-file --stdout --diff3` operations composed T36 with T35, then that result with T37; both returned zero without conflict markers. The final template SHA-256 is `bb9610d3162db361b40fa2536470c6b8323d2b984dad9a450c0c034eba3f1d94`.

## What was verified

The six-file actual-template suite passed **104 tests in 17.08 seconds**. It uses T36's fingerprint tests, T37's flag-ledger tests, T35's dislocation-state tests, and the retained analyst-ZH, score-base, and trend-state tests. The existing tests/conftest.py was copied unchanged. The complete static Jinja include/import closure and tracked runtime assets were supplied from exact Git objects.

The final browser matrix covers **320 / 390 / 1440 px × light / dark × EN / ZH × confirmation-only hot / confirmation-only empty / FULL hot**. All 36 cases retain the existing T36 assertions and additionally open the historical record by keyboard to inspect the joint state:

- T35's unavailable entry state remains visible.
- Current early/supply signals are explicitly unconfirmed under confirmation-only health; FULL remains a control.
- The declared **229 pending 90-day outcomes** remain visible beside **122 graded** outcomes. The fixture retains **351 total** records and **51 directional** outcomes.
- Late / 偏晚 retains its forward-excess control-arm disclosure without a directional hit-rate.
- Historical Early stance, logged date, and recorded AAA / BBB membership are retained.
- Filing fiscal-year/member-floor withholding, provisional help, focus behavior, history disclosure, settings keyboard/Escape behavior, and reduced motion retain their assertions.

The final receipt reports zero page errors and zero horizontal page-overflow cases. Minimum contrast among measured target text is **5.329661:1**, and measured target text is at least **12 px**. These are scoped measurements of the selectors listed in the verifier, not a full-page accessibility certification. All network requests are intercepted; unrelated requests, including unavailable generated configuration, are recorded in the receipt. Synthetic fixtures are explicitly used; no displayed market values are asserted to be live.

## Visual inspection and remaining observation

The parent inspected final desktop EN history, 320 px dark ZH history, and the full 390 px light EN page. The pending/control disclosures wrap and remain legible, and the unavailable/unconfirmed states form a coherent page.

The existing floating assistant control partially overlaps the historical-members row in the **320 px dark ZH region capture**. The pending/control chips are unaffected, and the same historical members are readable in the 390 px full-page capture. This is preserved as a shared-overlay observation for existing T48/T49/shared-shell qualification, not claimed fixed by the three Foresight changes. Whole-page unobscured-control acceptance remains open.

- [Desktop history](browser/joint-record-limited-hot-1440-light-en.png)
- [320 px dark ZH history](browser/joint-record-limited-hot-320-dark-zh.png)
- [390 px light EN full page](browser/joint-open-limited-hot-390-light-en.png)
- [Complete browser receipt](browser/browser-proof.json)
- [Test output](test-result.txt)

## Reproduce from the original Git objects

Use existing macro repositories that contain the exact commits above. One repository can be supplied for all three arguments when it already has every object. The materializer only reads those repositories and refuses an existing output directory. It reconstructs both merges and verifies every input blob and SHA-256 before writing a fresh plain-file snapshot.

```sh
python3 reproduce_snapshot.py --t35-repo /path/to/t35-repo --t36-repo /path/to/t36-repo --t37-repo /path/to/t37-repo --out /tmp/d03-composed-fixture
```

From that new snapshot, with the existing Python / pytest / Jinja environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest tests/test_foresight_page_analyst_zh.py tests/test_foresight_page_fingerprint_depth.py tests/test_foresight_page_flag_ledger.py tests/test_foresight_page_score_base.py tests/test_foresight_page_trend_state.py tests/test_foresight_page_dislocation_state.py -q --tb=short -p no:cacheprovider
```

With an already installed Playwright Chromium environment, create a new empty output directory and run the included verifier from the evidence directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 verify_composition_browser.py --repo /tmp/d03-composed-fixture --out /tmp/d03-composed-browser
```

The materializer itself was run after packaging; its receipt verifies all 28 source inputs plus the composed template. Tests and browser checks above are the original final receipts, not claimed repeated by this reconstruction check.

## Diagnostics and provenance

Initial failures came from incomplete fixture materialization: a missing T35-added Jinja icon include, then omitted navigation CSS/fonts. An intermediate 36-case pass still stubbed two tracked assets (Inter-500 and nav_market.js); both exact source blobs were added and the final 36-case run passed. No product-source repair was made in this integration exercise. Prior raw test logs, browser reports, and the overflow diagnostic are retained in `diagnostics.tar.gz`; archive contents and uncompressed hashes are indexed in `diagnostics-index.json`.

[composition-proof.json](composition-proof.json) records the 28 source inputs, merge method, commands, final browser metrics, scoped visual inspection, and source hash checks. [manifest.json](manifest.json) binds every delivered artifact except itself. The final run uses `browser/`; earlier names inside archived receipts identify superseded attempts only.

Protected source-law pin: `8eb375fe081339be759888f74a7c93d855727190`. Existing [D03 continuation](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6625304967) and [qualified T37 census](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6626722360) remain the source-linked programme record. No #9495, held R8, held UX Fabric, F01/F02, or sibling workspace was mutated.
