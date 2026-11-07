# Q03 chronology guard: reject outcomes unavailable at fitting

Research continuation dated October 13, 2026. **Source repair built and deterministically tested; independent review and merge remain pending.** This is an isolated follow-up to merged Macro #9097, not a new study, publisher, model or program. The original research mission remains incomplete.

## Recovered source and scope

The October 3 research package #8321 is now merged at `97248942de057590d7fbaeae2d8e2c3b104acb19`. Its gamma/proxy repair has already landed; do not recreate it. October 11's prepared Fable completion packet is #8770. The existing product principal and Terminal #599 retain their separate implementation, source, release and natural-proof obligations.

The actual next research dependency inspected here is #9097's pure Q03 guard in `scripts/options_pilot_study_adapter.py`. Initial source cut: `d680a52d98a41264c8ee8d929726c9e0231a4e2a`. Publication base: `ce1da9761ae0cfcdd2cf2c7ae5a641b260bc1092`. The adapter blob was rechecked at publication preflight and remains `088f5a3f1086147ebc89a66cb86b35d612f69c16`; SHA256 `b52c55c7838d83e7c966da394eed4afa7381698bc628cbb50c84fb826529dd8d`.

The original brief requires point-in-time inputs, temporally separated evaluation and purging of overlapping labels. This patch enforces a necessary chronology condition in the existing guard; it does not establish those broader scientific requirements by itself.

## Reproduced counterexamples

All examples are synthetic. [Retained baseline results](baseline-counterexamples.json) were obtained by importing the hash-verified original adapter.

| Input | Original result | Required behavior |
|---|---|---|
| P1 decision 15:00 UTC; true 30-minute outcome ends 15:30; claimed maturity 15:05; fitting 15:10; validation 16:00 | Kept in training | Purge: the outcome has not ended at fitting |
| P1 same invalid maturity, but fitting moved to 15:45 | Early maturity still accepted | Purge the internally contradictory maturity receipt |
| Naive local decision/maturity/fitting times | Kept with no timezone interpretation | Typed refusal; do not invent the timezone |
| Aware decision/fitting with naive maturity | Raw `TypeError` | Typed `LABEL_CLOCK_INVALID` refusal |
| P3 calendar repeats the formation date 21 times | Twenty-session outcome collapses to the formation day and is kept | Refuse duplicate calendar |
| P3 calendar endpoint precedes formation | Reversed label interval is kept | Refuse non-increasing calendar |

The new regression suite also demonstrates that adding 30 wall-clock minutes across a daylight-saving fall-back can produce 90 elapsed minutes. P1 uses 30 elapsed minutes, not that local-time calculation. Reusing a one-shot calendar generator for multiple rows must not exhaust it after the first row.

## Minimal source repair

- P1 decision, maturity and fitting clocks must be timezone-aware and UTC-resolvable. P1 duration arithmetic and comparisons are performed as UTC instants; equivalent offset representations remain equivalent. Out-of-range endpoints produce typed refusals.
- A retained P1 training row now requires `actual_label_end <= fitting`, `actual_label_end <= label_mature_at <= fitting`, and `actual_label_end < validation_start`. Missing maturity remains purged; malformed clocks are refused. No input is silently timestamped or zero-filled.
- P3 calendars are frozen once per multi-row purge, must contain literal date values in strictly increasing unique order, and retain the original 20-supplied-session horizon. Invalid calendars are refused rather than sorted, deduplicated or repaired silently.
- P3 also refuses an outcome day after fitting or a claimed maturity day before its outcome day. **This remains only a day-level check.** Exact exchange close/fixing time, calendar venue/completeness and actual label/source receipt must still be qualified before an empirical use. This patch does not invent those missing clocks.
- Split proposals use the same calendar structural validation before converting dates to a membership set. Fit/validation ordering remains explicit. Input rows and supplied calendars are not mutated.

No registered feature, baseline, economic label, sign, horizon length, six-pilot Holm family, empirical binding or authority flag changes. The frozen study JSON and P3 reference remain byte-identical. `run_empirical()` still unconditionally raises `EMPIRICAL_GATES_UNSATISFIED`; G0–G6 remain held.

## Verification and limits

The test-first run against the original adapter executed 28 new tests and failed with **14 assertion failures and eight errors**. The errors expose missing typed refusals or a broken positive generator case, not missing implementation imports. After repair, all 28 passed.

The complete existing adapter test file was then run unchanged with the new file: **68 tests passed** (40 existing + 28 new). The first attempt lacked the published-board fixture in the isolated scratch snapshot and produced one `FileNotFoundError`. Supplying that exact existing fixture, blob `378a5d4ee359790c8b1b980a5515c3750eadc001`, resolved the environment-only failure; no existing test was edited.

The [portable deterministic checker](verify_chronology.py) passed **2,000 seeded P1 interval cases** across multiple UTC offsets using a separate Boolean interval oracle. It then restored five prohibited behaviors in disposable copies; each was detected by the regression suite: trusting maturity instead of actual endpoint, removing calendar validation, removing aware-clock normalization, doing elapsed-duration arithmetic in local wall time, and consuming the calendar generator separately for every row. AST parsing excludes syntax errors as mutation evidence. Some kills intentionally expose untyped runtime errors; the retained result names those separately.

[Validation receipt](validation-results.json): candidate SHA256 `9ceb0bdeb6352b0ea195375e164bb60e0dec86ec86ab1519bc9b60ddf9212832`; regression SHA256 `6630ef16ff93c01d3c4150b116f47fceddf7d4fc3726bf2eb1a5dfd6ce11a95a`. These are deterministic author checks, **not independent model review**. The entire Macro repository test suite was not run locally; hosted CI is a separate pending observation. No market-data fit, model performance, production/browser result or source certification is claimed.

### Reproduce

From repository root, run:

```sh
python3 -m unittest discover -s tests -p 'test_options_pilot*.py'
python3 research/options_intelligence/2026-10-13-q03-chronology/verify_chronology.py \
  --candidate scripts/options_pilot_study_adapter.py \
  --tests tests/test_options_pilot_chronology.py \
  --baseline /path/to/the/exact/original/options_pilot_study_adapter.py \
  --output /path/to/a/new/validation-results.json
```

The checker verifies the original baseline SHA before using it for a mutation and will not overwrite its output. Obtain the baseline from the immutable source cut above through an authorized source route. It does not fetch data, install packages or submit a study.

## Recoverable frontier and effect state

Original attended research operation: `options-intelligence-deep-research-20261003-astra-001`. Protected procedure pin: `Mastermind@9a8e9b50b6158eb38af78a5b867eedba1719b908`, skillpack1.0.1/bootstrap1. Host verified as M2 Studio. This patch was built in an isolated source snapshot, not by taking over an incumbent worktree. New carrier: branch `claude/options-q03-chronology-20261013-astra`, draft source PR; exact commit and remote readback belong to the PR receipt.

A new bounded Fabric review request, ID `options-research-q03-review-20261013-01`, was blocked by platform safety before start. Same-ID status readback returned `NOT_FOUND`, no root/parent/return or execution. It was **not retried, rephrased or dispatched through another carrier**. Independent review therefore remains outstanding. An earlier composite read/preflight request was also blocked before dispatch; its requested action was not replayed. These are scoped refusals, not evidence that all tools are unavailable. No modifying effect is unresolved. A later attempted copy of this scratch evidence to the external SSD was rejected as `Command not allowed`; the destination is absent, and the copy was not retried. No external-volume persistence is claimed. Repository publication is the separate source-persistence action.

**Do not redo:** merged gamma/proxy fixes, the 59-artifact October 3 package, original GEX arithmetic study, settled #8286 results, unchanged reference tests or any active Fable task. Preserve #8385 methods ratification and held #8555/#7328 independently; this patch neither resolves nor widens them.

**Next action:** inspect the draft's exact-head hosted checks and obtain the required independent source review through a legitimately authorized review interaction; do not bypass the refused dispatch. Only an accepted review and applicable checks can advance this source patch toward merge. Exact P3 close-time/consumer receipts, per-pilot historical population, data qualification, power, empirical seal and production proof remain separate unfinished obligations. No background Web execution or worker start is implied.
