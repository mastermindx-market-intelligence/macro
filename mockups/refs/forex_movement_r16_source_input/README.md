# Forex movement evidence — exact-source review inputs

**SYNTHETIC INPUTS ONLY. NOT LIVE DATA, BROWSER EVIDENCE OR A DEPLOYED DASHBOARD.**

This package reconstructs the complete existing Forex route from commit `ac79e07634ec3903167969d2922d411d3969817d`. No product code or Paper design is replaced. Each case uses `forex.html.j2`, the actual validated movement projection, the existing page writer and CSS extractor. The underlying market fixtures and state-writing substitutes are the existing `tests/test_forex_context_bus.py` helpers, not collected market data.

## Four inspectable cases

| Case directory | Expected interface behavior |
|---|---|
| `cases/matched/site/forex.html` | The synthetic five-observation return is −0.19% while relative momentum is +1.51 z. Matching dates/windows permit a descriptive joint reading, not a reversal forecast. |
| `cases/different_dates/site/forex.html` | The return ends on2026-09-22, momentum on2026-09-25. The combined reading is withheld; valid individual numbers and the earlier date remain. |
| `cases/unavailable/site/forex.html` | The movement inspector shows unavailable, with no zero/prior reading substituted and no currency evidence rows. Other fixture panels remain independently present. |
| `cases/raw_fallback/site/forex.html` | The real existing producer runs on deterministic synthetic prices without a dollar driver. Its output is labelled unadjusted fallback, not falsely dollar-adjusted. This case's calculation index is2024-11-29. |

Every case contains the unchanged existing page shell and pair section, both languages, the native details/summary disclosure and explicit unknown source freshness. No newly added component JavaScript, input, diagnosis setter or forecast is introduced. `cases/<name>/kinematics.json` is the exact projection supplied to that case's template, not a production snapshot.

The original builder inserts the current wall-clock time into the page footer. An initial exact-hash check correctly caught that nondeterminism. These review fixtures therefore set only that context field to the explicit bilingual marker **SYNTHETIC REVIEW INPUT / 合成审阅输入**, rather than inventing an actual build timestamp. The marker and all expected page hashes are recorded in SPEC.json; the production builder/template are unchanged.

The cases are **separate page roots**. Do not combine their assets, claim their synthetic dates are source release/observation timestamps, or present their fixture headline as a current market view. Source bytes and expected full-page hashes are frozen in `SPEC.json`; generated manifests identify each output and asset independently.

## Rebuild and verify without navigating

Use an existing trusted checkout with the recorded Git objects and the repository's existing Python render/test dependencies (including pytest, Jinja2, pandas/NumPy, PyYAML and BeautifulSoup). No installation, Git fetch or source update is performed by these utilities.

From the repository root, choose an output directory that does not exist:

```sh
python3 mockups/refs/forex_movement_r16_source_input/prepare.py \
  --repo . --output /path/to/new-forex-review-input
python3 /path/to/new-forex-review-input/verify_input.py
```

The result contains all four cases, `SOURCE.json`, the frozen `SPEC.json`, these instructions, the scripts and `candidate.zip`. To verify the published archive in place, run:

```sh
python3 mockups/refs/forex_movement_r16_source_input/verify_input.py
```

An extracted copy can be rebuilt with its own `prepare.py --repo /existing/trusted/checkout --output /another/new/directory`. Retain candidate.zip beside the extracted files for the archive verifier: the ZIP intentionally does not contain itself. A repeated build must preserve every fixed HTML hash and should produce the same archive in the same Python/compression environment; verify actual bytes rather than assuming cross-environment ZIP identity.

The script checks the pinned source dependencies, all loaded Jinja templates and imported local repository Python modules. Shared non-font assets come from immutable Git objects. Missing local objects fail instead of initiating a network fetch (`GIT_NO_LAZY_FETCH=1`, no terminal authentication). Existing output is refused rather than overwritten. The synthetic builder's optional state/network writers are replaced by its existing test seams; the real full HTML render happens afterward. Temporary fixture data are not copied into production paths.

## What static closure does not establish

Direct HTML resources and CSS URL references are inventoried. The directly referenced favicon/apple-touch icons are included. A small explicitly recorded set of existing shared scripts is also included for eventual admitted runtime review. Fonts are never read or copied: their local Git blob identity, size and source path are recorded separately, so an accepting operator can verify existing trusted assets under their own permissions. Fallback typography does not prove Paper parity.

The inherited runtime can still use Supabase/session/analytics/data services and linked pages; those network and entitlement conditions are NOT_PROVEN. Local resource accounting is not a browser network trace or an offline-runtime guarantee. No server, page navigation, screenshot, accessibility scan, EVIDENCE.yml or deployment is produced by preparation.

The prior administrator browser restriction is unchanged. Do not change browsers/profiles/hosts/schemes to bypass it, and do not treat this retrievable input as permission to invoke external services. Genuine browser admission, accepting operator, trusted font supply and allowed fixture/network behavior remain separate prerequisites.

## Acceptance still owed

After those prerequisites are satisfied, the existing visual-evidence workflow must verify all four case states at the intended desktop/tablet/mobile sizes, EN/ZH and dark/light; native disclosure keyboard operation, focus visibility, text/number/date wrapping, enlarged text, reduced motion, contrast and unknown-data treatment. Check that no label turns a calculation date into a source date, a z-score into price direction, or a raw fallback into an adjustment. Use the accepted owning EVIDENCE schema and real captures. Static parsing/tests and hosted source CI cannot substitute for that proof.

This package supports the existing PR #8243 review. It is not a new calculation, publisher, design system, source-clock service or parallel evidence authority. The original Bonds/Forex mission remains incomplete.
