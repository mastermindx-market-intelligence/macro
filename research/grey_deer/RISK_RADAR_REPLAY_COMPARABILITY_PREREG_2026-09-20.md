# Risk Radar replay comparability — fixed protocol

Authority: Chairman's continuing Risk Radar/research/model-improvement mandate.
Source: macro base 78ef3b7b9d50deb02ac06ec7e655b7e892bfd40c;
protected Mastermind Skillpack 23061ab70a7fb79636b7962d9b440a3de23fe016.
Direct execution: PRINCIPAL_JUDGMENT / CRITICAL_PATH_SHORTCUT; no worker transfer.

## Questions frozen before new replay outcomes are inspected
1. Does reducing the forecast-date index remove a real intervening SPY loss?
2. Can missing/nonfinite/nonpositive prices be silently scored as a negative outcome?
3. Can better F1 on different dates/outcomes be accepted as a calibration improvement?

Use the existing state_accuracy and compare_calib consumer, not another model.
The target is >=5% close-relative loss in the next H supplied SPY observations,
H fixed at 5/10/21. Missing forecast-date prices are not filled; unknown complete
windows are excluded on either sign. A supplied observation index is not proof
of an exchange-complete calendar. Preserve the live grader and calibration.
Comparisons require matching target, eligible dates and outcomes, valid F1,
and both event/non-event support in each existing full/recent comparison.

Real-input follow-up uses the unchanged current calibration, full available history
and the existing recent window starting 2020-01-01. No best-window selection.
The existing five-episode Atlas is context, not a new held-out trial. Report exact
source hashes, exclusions and confusion counts. Synthetic fault tests are correctness
proof only. Existing 33-date zero-event issued-probability findings are already known.
Historical reconstruction is NOT a publication-timed trial or current-model validation.
No weights, probabilities, live policies, ledgers, collectors or promotion thresholds
are changed. Existing UI releases and held sibling work must not be redone.
