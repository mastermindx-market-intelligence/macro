# Intraday Flow — candidate verification

## Candidate and scope

Latest integrated implementation: `d0201df47d889fb50cef04b5aa2fcda251b1a034`.
Canonical screenshot candidate: `aeff31db0803d75e41881fd566e13f6222d4ca05`.
Initial base: `f754bdee6b803b18191841863c35527c0a74571e`.

The template, rendered page and paired stylesheet implement the redesigned scan.
The shared navigation, producers, canonical freshness thresholds, six-class
deterministic model and seven-leg calculation remain under their existing owners.
The separate timing/precursor work in macro #6867 is not replayed here.

The first shared-shell integration incorporates main `f6fb23200bb2fee8368aecda7f23725ccf4a6add`.
The conflict was limited to generated cache tags and was resolved by page-only
rendering. The template and paired CSS retain the reviewed repairs; the generated
page also receives main's canonical Expectation Surface navigation item. This
feature does not customize shared navigation. Verification was repeated with the
integrated shared assets.

A later main update `bca436e58f7069ff8b52d31074f30726cfecf0e4` was reconciled at the latest
candidate above. It changes this page only by the shared theme cache tag; the
upstream new GMI variables are unused. The template, paired page CSS and embedded
base remain unchanged. All regression/browser and relevant guard checks were
repeated. MAIN_INTEGRATION.md documents the exact carry-forward scope; the canonical
matrix is preserved at its actual capture commit rather than falsely repinned.

## Results

| Check | Observed result |
|---|---|
| Intraday pytest suite | 280 passed; final integrated run 21.46 seconds |
| Isolated browser harness | 515 passed, zero failures |
| Matrix | 1440×900 and 390×844 × light/dark × EN/ZH |
| Canonical screenshots | 24/24 captured: eight resting + eight hover + eight focus |
| Capture errors | Zero console errors and zero failed responses |
| Horizontal overflow | None at either canonical viewport |
| Desktop density | First scan row 298.98px below nav; seven complete rows visible |
| Phone clearance | Rightmost metric at x311, clear of the existing launcher; 44px evidence targets |
| JavaScript syntax | Node syntax check passed on rendered inline scripts |
| Paired assets | Template/site CSS byte-identical |
| Visual receipt guard | Passed against the material source diff and staged canonical evidence |
| Design-system ratchet | Zero newly blocking findings |
| Runtime stylesheet budget | 146 JS files scanned; 44 injecting; 88 existing hits within frozen allowances |
| Model preservation | 15 core regions byte-identical to the initial base |

Commands used:

```sh
python3 -m pytest tests/test_intraday_flow*.py -q --disable-warnings --tb=short
python3 research/intraday_flow_design_upgrade/verify_browser.py
python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/intraday-flow-design.diff
python3 scripts/check_runtime_style_injection.py
```

The visual receipt points to the canonical capture driver's manifest. The receipt
guard passed against the material source diff after all canonical image files were
staged; the subsequent evidence commit preserves that exact matrix.

## User paths exercised

Search and reset; all theme-menu controls and Escape; name/numeric/group sorting;
a native phone sort control; keyboard evidence expansion; selected-name evidence;
seven explicit localized check states; Activity help open/Escape without sorting;
counted expansion and Tab continuity into the first newly revealed name; collapse;
language changes; async refresh with focus retained in the row, sidebar, stock link,
opened evidence region and count control. Short and empty menus remain unclipped. Open evidence has no document-wide
horizontal overflow in all eight viewport/theme/language cells. Four supplemental
actual-click evidence captures are linked from the visual README.

The harness uses an isolated anonymous browser against the owned loopback preview.
Normal cells use the real committed base snapshot and the available local/public
feed responses; they are not fabricated market observations. Six transport scenarios and an
additional populated phone check use clearly identified synthetic TEST FIXTURES.
No fixture values were written to site data, published as observations or used to
claim a current trading signal.

## Test migration

Assertions coupled to the retired duplicate spotlight, decorative breathing
animation and obsolete hero counters were replaced with the deliberate single-scan
contract, executed render coalescing, truthful source clocks and correct ordering.
Existing classifier, coverage, null-safety, call-only options premium, OPEX and
builder tests still run. The old w11-r4 evidence fixture remains unchanged.

## Visual critique and repairs

Principal advisory critique identified refresh focus loss, offscreen expansion
focus, unlabeled three-state evidence, inaccessible Activity help, possible menu
clipping, floating-assistant overlap with phone metrics, and an orphaned phone
feed-help icon. All were addressed and covered by the browser paths above.
Native advice is not independent human/Opus visual acceptance.

## Independent review repairs

The paid independent review at predecessor `cdc17bf634219135c000b0d97c84d1dd102014c6`
returned changes required and a partial visual disposition. The bounded repairs
are recorded in INDEPENDENT_REVIEW.md. Actual browser checks now cover both rising
lanes against the shared locale token; phone stock-overview navigation and refresh
focus; unchanged live-region silence; localized feed help and dealer strength;
visible native-sort focus; and untagged-name filtering.

Expanded evidence separates unavailable inputs from false rule results with a
presentation-only mask. Missing, zero, positive and supported volume-fallback
fixtures verify all four affected checks in both languages while the original K
and seven-rule denominator remain intact. A separate neutral no-read count
reconciles to the complete population. Quote clocks marked synthetic are excluded;
nightly package dates and unavailable dealer-chain clocks are named explicitly.

The independent follow-up at `99b6151530160f1fb432277e48274040f2581660`
returned CODE=PASS from xAI / Grok 4.7. See REPAIR_REVIEW.md for the complete result,
methods and limitations. Its Node/Chrome probes, protected-function comparisons,
image hashes and 57 contract tests independently verify the bounded repairs. The
full 280/515 suites were not relaunched by the reviewer; its six additional test
attempts lacked supporting files in its partial scratch tree. Qualified human/Opus
visual judgment remains an open, separate gate.

## Performance limitation

The initial-load trace on implementation commit
`43c31bf5888bdeb71c56873e8064d5d43254ce51` recorded layout-shift sums of approximately
0.69/0.68 on desktop and 0.28/0.25 on phone (light/dark). A baseline HTML comparison
using the same shared assets recorded approximately 0.73 on desktop and 0.23 on phone.
The dominant entries contain the existing shared search/control re-layout and the
resulting main-content movement. These are isolated lab observations, not field
Core Web Vitals or a performance pass.

The final integrated matrix also records this limitation: resting desktop light/EN
CLS is approximately 0.881; other desktop cells are 0.681–0.706, and phone cells
are 0.252–0.307. The final-r3 manifest is the exact measurement record. These values
are not covered by the interaction pass or by the review's CODE=PASS.

An in-memory experiment relocating the existing theme script did not materially
resolve the desktop movement; it was not adopted. Shared navigation source,
styling and script order remain unchanged. This limitation needs the existing
shared-component owner's assessment before unqualified performance acceptance.

## Outstanding gates

1. Paper: the intended file is now inspectable and its write binding is ready, but the current catalog is unqualified for writes. The latest read reports
   paper-desktop 0.5.18; the observed schema digest is unchanged and
   `accepted_for_write=false`. See PAPER_QUALIFICATION_HANDOFF.md.
2. Qualified human/Opus visual judgment. Independent exact-head repair code review passed.
3. Concluded binding CI checks and permitted integration/release.
4. Served production proof on desktop and phone, followed by commissioning acceptance.

No Paper mutation, merge into main, production deployment or final acceptance is claimed.
See CLOSEOUT.md for the release frontier and the PR for the final containing head's CI.
