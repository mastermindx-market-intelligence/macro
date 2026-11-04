# D03 T36 — qualify confirmation-only Foresight reads

## Result and scope

When current health is `CONFIRMER-ONLY`, Foresight now says **Early status is unconfirmed** and qualifies current early-stage badges as **Supply unconfirmed**. The page preserves source stages, source counts, heat, filing years, member counts and below-floor withholding. Historical grading retains its recorded flag-time stance and membership.

This is a presentation repair in `templates/foresight.html.j2`, with regression cases in the existing `tests/test_foresight_page_fingerprint_depth.py`. It does not modify producer health, scores, source ordering, thresholds, sizing or trade authority. The existing FULL and missing-health presentation remains a control; missing-health producer repair is outside this slice.

**This record proves the source and controlled browser fixture path. It does not prove live-data production, deployment, final RIG/QA01 acceptance, or completion of the D03 programme.** Draft/HOLD remains in force.

## Why this change is needed

The health producer can report that leading supply inputs are unavailable while cached or partial current rows still carry early-stage values. Previously, those values could produce an unqualified current early thesis. The repair applies the existing health state consistently to the hero, convergence including its empty state, primary cards, watchlist and subsector labels. It keeps source observations inspectable and leaves the historical grading shelf unchanged.

The hero uses one short verdict and one explanation. Current uncertainty uses neutral cards and readable text. Touched card edge stripes were removed; canonical border/radius tokens, wrapping and text size were checked. Filing and text-based provisional qualifiers remain visible, including the convergence view.

## Authoritative proof for this source

| Evidence | Result |
| --- | --- |
| [acceptance-checks.json](acceptance-checks.json) | Existing five-file CI page-reader command: **37 passed**; design-system added-diff guard: **0 blocking findings**; visual-evidence guard and whitespace check: **pass**. |
| [browser-verified/browser-proof.json](browser-verified/browser-proof.json) | **36 cases passed** using Chromium 151.0.7922.34; final source hashes recorded. |
| [browser-verified.log](browser-verified.log) | Successful final browser run. |
| [verify_browser.py](verify_browser.py) | Reproducible browser fixture and assertions. |
| [manifest.json](manifest.json) | SHA-256 inventory of retained evidence and exact source inputs. |
| [red-test-result.txt](red-test-result.txt) | Original failing regression baseline: 12 failed / 9 passed before the repair. |

The 36 browser cases are 320/390/1440 px × light/dark × EN/ZH × three states: confirmation-only with convergence (including a conflicting raw physical-confirmed flag), confirmation-only without strong convergence, and FULL with convergence. Final measured text contrast is at least **5.3297:1** on the measured labels, all measured labels are at least **12 px**, and the run records **zero horizontal overflow and zero page errors**.

The real template, shared CSS and shared JavaScript are rendered with controlled synthetic source records. Requests are intercepted by the harness; unrelated JSON is stubbed. No live market data or deployed application is used. The browser journeys cover focusable provisional help and tooltip bounds, historical disclosure by keyboard, theme/language controls and Escape at 390/1440 px, reduced motion, and absence of decorative edge pseudo-elements on touched cards. These measurements are scoped to the assertions in the verifier; they are not a blanket accessibility certification.

Representative final screenshots:

- [390 px / light / EN full page](browser-verified/page-limited-hot-390-light-en.png)
- [320 px / dark / ZH](browser-verified/limited-hot-320-dark-zh.png)
- [1440 px / light / EN](browser-verified/limited-hot-1440-light-en.png)

## Test and CI ownership

The existing `healthcare-fda-supply` job in `.github/ci/legacy-jobs.yml` already owns the changed test file and runs this command:

```sh
python3 -m pytest \
  tests/test_foresight_page_analyst_zh.py \
  tests/test_foresight_page_fingerprint_depth.py \
  tests/test_foresight_page_flag_ledger.py \
  tests/test_foresight_page_score_base.py \
  tests/test_foresight_page_trend_state.py -q --tb=short
```

Sixteen T36 regression cases were added within that existing file. No CI job, pack or runtime allocation is added. Local results do not stand in for the Draft PR's required hosted checks.

## Provenance

- Protected source-law pin: [Mastermind 8eb375fe081339be759888f74a7c93d855727190](https://github.com/mastermindx-market-intelligence/Mastermind/tree/8eb375fe081339be759888f74a7c93d855727190).
- Original implementation base: `51c35090a624de1e977920e98def2c64488751b3`.
- Original branch/carrier: `claude/ssd-d03-foresight-confirmer-t36-20261104-c2-4cdf52c0894d99c2`.
- [D03 Phase 2A task tree at e521f04dcc5afb4fb06152584d35c8a01dbe21ff](https://github.com/mastermindx-market-intelligence/macro/blob/e521f04dcc5afb4fb06152584d35c8a01dbe21ff/research/design_candidates/production_design_20261102/D03_US_PROPHET_PHASE_2A.md): T36; the 78 capabilities and 53 acceptance cases remain unchanged.
- [Cumulative D03 C2 checkpoint and takeover](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6625304967).
- The 12-file template/static-dependency/builder/health/test/CI closure was checked via GitHub blob identity against main `52abe2e183833a216267942a99513e6c9cbe062f`; all match the original base. A shared-clone fetch encountered concurrent movement of `origin/main`; it was not retried or force-repaired. Immutable source comparison supplies the evidence.

## Recovered Paper study and development attempts

[confirmation-only.paper.jpg](confirmation-only.paper.jpg) and [confirmation-only.paper.jsx](confirmation-only.paper.jsx) are the recovered native Paper study for component `11HT-0`, in PROPHET file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, owned page `p-D-0`. The screenshot and JSX were inspected in this continuation. No new live-Paper edit or final native acceptance is claimed.

Other browser directories, logs, contrast diagnostics and test-result text files are preserved development provenance. They are superseded by **browser-verified** and **acceptance-checks.json** for this final source. Earlier iterations exposed a low-contrast lifecycle label, redundant caveat copy, touched style-token violations and a harness assumption about the existing settings gear. The final source corrects the visual issues; the final harness follows the real focus-to-open settings behavior. Failed or older attempts must not be counted as additional successful coverage. The readable red-test and failed settings-attempt logs have trailing whitespace normalized for the repository guard; manifest.json records their before/after hashes and unchanged token content.

## Integration boundary

T35 gate-state work, T43 Winner Health and T46 V2 availability remain separately owned slices. This repair must be composed with applicable sibling source changes before release. F01/F02 candidate.4 is provisional; final joint v1 and RIG/QA01 acceptance remain outstanding. F04 typed availability/reason/time remains an upstream data dependency.

No Ready action, un-draft, label, enqueue, auto-merge, merge or deployment is authorized here. The existing original-effect holds remain unchanged. See [CONTINUATION.md](CONTINUATION.md) and the cumulative checkpoint for the next permitted action.
