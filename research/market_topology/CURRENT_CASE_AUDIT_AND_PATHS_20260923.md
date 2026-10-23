# Current case: independent arithmetic and ordered-path diagnostics

RESEARCH ONLY. Continues `CURRENT_CASE_AND_MECHANISM_FINDINGS_20260923.md` (first commit `7287824ef4654a40ef40cccdc15bb53cd48f1945`) under the same operation and draft PR #7812. The following work is explicitly POST-RESULT DIAGNOSTIC; it was not a newly untouched forecasting experiment. No model was fitted, no production input changed and no broad-market estimate was obtained.

## 1. Arithmetic verification

A separately written audit used Python Decimal arithmetic at 40-digit precision, rather than the original NumPy calculations. It independently reconstructed 1/5/20-session returns, benchmark-relative wealth, positive/negative day counts, directional efficiency, price-only basis checks and the BROS event-window compounding identity. Maximum drawdown was recomputed by enumerating all earlier-peak/later-close pairs rather than reusing the original cumulative-maximum code.

Result: 51 numerical comparisons passed with an absolute tolerance of 1e-9; maximum observed difference was approximately 4.91e-14. The 105 dated adjusted-close observations had one common cutoff, 21 unique descending dates, and positive prices. Weekday ordering was checked; an official exchange-calendar replication was not performed. The original input and executed-script hashes matched their result record.

This verifies arithmetic against the SAME manually transcribed publisher observations. It does not provide independent market-data-source verification or establish adjustment quality, real-time availability or redistribution rights. The original source remains the five dated StockAnalysis history pages listed in the first report.

The audit first failed on a misnamed input key before writing its output. Its corrected v1r1 uses the actual saved input key; no observations or calculation targets changed. The original failed script remains in the local working directory. Do not describe this as a pristine first-run pass.

Audit script SHA256: `45be2d47e8739cf31d4436dfafbe4d50cace9d243d9b563f22ab374a7bd329fd`.
Audit result SHA256: `f73d7ef0008acb22bef22411f9a78f7644ff48b9aeb8732e5862708d24244228`.
Original case result SHA256: `2e4e8f3790589918f24cb745f526473851d8031dd54162c6741e1ca990a009e2`.

## 2. Four non-overlapping five-session blocks

All blocks derive from the same 20 increments ending September 22, 2026. They are five-session blocks, not four calendar weeks. Returns use the publisher-displayed adjusted closes; they compound rather than add.

| Instrument | Oldest 5 | Next 5 | Next 5 | Newest 5 | Full 20 |
|---|---:|---:|---:|---:|---:|
| BROS | -5.95% | -6.10% | -8.50% | -7.67% | -25.39% |
| KRUS | -7.98% | -2.85% | -20.02% | +5.27% | -24.73% |
| MCD | -3.30% | -2.24% | -1.18% | -0.96% | -7.49% |
| SMH | +1.80% | +3.07% | -5.51% | +12.05% | +11.09% |
| SPY | +0.47% | -0.14% | -1.12% | +2.37% | +1.55% |

BROS and MCD have negative returns in every selected block. KRUS has a positive final block after three negative blocks; that is a rebound description, not confirmed bottoming. SMH has strong net and recent performance but not an uninterrupted advance: its first 15 sessions together returned -0.86%, followed by +12.05% in the final five. Even the positive semiconductor proxy must not automatically receive a long-horizon 'persistent leader with runway' label from this one-month case.

The decomposition checked that the product of four gross block returns equals the full-window gross return within 1e-30 Decimal tolerance for all five instruments. It tests path interpretation, not forecasting effectiveness. All samples were deliberately selected from the Chairman's examples and proxies; none yields a restaurant-sector, semiconductor-constituent or market-wide population share.

Path script SHA256: `e9131d7dfdeb59a4c7c9ae11ea481baf0eba5768af727de8a25b8d4caec4aded`.
Path result SHA256: `a55a32c2bebbaee0544f63236ca9afd3c75ee7e261b47c603ec498ed5a9e2c0f`.

## 3. Research input custody

The transcribed input was written to the EXISTING Studio research artifact home as:

`/Volumes/Mastermind/research/market-topology-research-20260923-astra-001/phase4_current_case_inputs.json`.

The write succeeded and the entire 202-line content was read back, including all five 21-observation arrays, the two price-only basis arrays, dates, source URLs and limitations. This is an internal research-evidence copy, not a new canonical market-data store or public redistribution. No remote code or source-data refresh was executed. The original local input digest is `0b2a1a6b9e25a6f26fe696dff0406e99805a43d82a1c03f9a20769fdd9b7aa83`; the remote copy was verified by full content readback, not an independently executed remote hash command.

Aggregate findings and exact methods are durable in this branch. Other current-turn working artifacts remain under `/mnt/data/market_topology_phase4/` until individually published or archived; do not infer that a sandbox path is an organizational checkpoint. Executable population/context reference code and tests are committed separately under this research directory.

## 4. Holdout honesty

The named September 2026 prices and current operating releases have now been examined and used to refine research questions. They are NOT untouched holdout observations for this study. The earlier industry 2000-2025 results are also already viewed. The original stock trial's 2024-2025 design remains frozen and unexecuted, but any future claim that all of 2026 is pristine must disclose these selected-case exposures. A new prospective evaluation begins only after its model/data/selection rules are locked and predictions are actually recorded before outcomes through the existing evaluation owner.
