# Industrials Wave 5 - Verification, source corrections and limits

23 September 2026. Operation: `gmi-industrials-sector-research-20260923-sol-001`. Macro Draft/HOLD PR #7789. Principal research and proposed requirements only; final Fable handoff withheld.

## Executed checks

`python verify_wave5_research.py` completed before publication and again after immutable readback with **95 PASS, 0 FAIL**, exit 0. The suite contains 54 arithmetic/scenario checks, twelve invalid-input checks, twelve incompatible comparison fixtures, five positive/publication-availability controls and twelve document/index checks. No failed assertion or tolerance change occurred. A self-review renamed the comparison fixture's revision field to method_revision so it describes comparison-basis compatibility, not a blanket prohibition on comparing different source documents. The complete suite passed again.

The arithmetic includes fixed-price/incentive/fixed-fee cost risk, service-pricing productivity capture, same-profit cash timing, known-loss double counting, cumulative revenue intervals, guidance midpoint and financing reconciliations. Selected checks use independently expressed exact rational arithmetic. Actual issuer contract parameters, future cost distributions and market expectations were not calibrated. The fixture is not a production admission service; the 36 W5-T cases remain unexecuted application requirements.

## Exact-byte verification

At immutable commit `cd429619ded7874fe3f3ccc87807ce73a73e985f`, the four model/code/index blobs below matched the executed local UTF-8 files. The evidence register was read back at its first immutable commit `00b20827273abf73377f47929e8e63c053094fb4` and its local copy also matches the exact remote blob. An extra explanatory period label in the original local copy was removed to match published bytes; no numerical source input or scope conclusion changed. This is copy verification, not independent factual verification.

| Artifact | Bytes | Exact Git blob |
|---|---:|---|
| `INDUSTRIALS_WAVE5_EVIDENCE_2026-09-23.md` | 21139 | `2d2380fab0ebdca76f54140bccdc5f14be7ae2cc` |
| `INDUSTRIALS_WAVE5_ECONOMIC_MODEL_2026-09-23.md` | 34693 | `53ff6924f56a90c0fc2fa55534a90e92b4d7195f` |
| `calculate_wave5.py` | 8777 | `83236b8bed5d89bed349a84ada1c1685f1fb565d` |
| `verify_wave5_research.py` | 8241 | `d20e42d98c346fc9f6937aa253039e4dd3b255e0` |
| `WAVE5_SOURCE_INDEX.json` | 7469 | `777318ba9acc60b795719b01937ca01b0fd4cf62` |

## Explicit source-reading corrections

Section 1 of the economic model and the corrected source index supersede only three statements/metadata from the first register: GD's unestablished exact fiscal endpoint; the initially unqualified Fincantieri horizon conflict, whose narrative distinguishes an additional contract; and FAR effective-date labels that were incorrectly placed under publication. Original publication dates for the relevant FAR pages remain unknown. These are research-author corrections, not a claim that publishers changed their documents. The original register remains recoverable. Rheinmetall's separate percentage-versus-values discrepancy remains held, not corrected by guessing.

## Coverage and unproved matters

The economic model contains 4,997 whitespace-delimited words, 24 proposed research slices, twelve falsifiable hypotheses and 36 proposed application requirements. The bibliography has 27 entries: eighteen issuer records across thirteen corporate groups, one GAO overview and eight government contract/reference records. Coverage is not a complete sector census, admitted company graph or set of live basket constituents.

No independent factual-review receipt, current valuation/consensus panel, calibrated probability, empirical backtest, forecast advantage, application test, CI acceptance, deployment or browser proof is claimed. All legal references require actual incorporated contract/version/jurisdiction review; illustrative cost reimbursement assumes authorization, allowability and limits. Period-end funding estimates omit intra-period peaks, tax and financing. The loss example is a cash identity, not implementation of an accounting standard. No weapon design or operational analysis was performed.

Generated calculation/check/hash JSONs are portable reproducible outputs, not new canonical data stores. No raw publisher corpus, paid source data or current private GMI payload was committed. Source retention, rights, exact business/ownership mapping, specialist breadth and point-in-time expectations remain open research and admission obligations.
