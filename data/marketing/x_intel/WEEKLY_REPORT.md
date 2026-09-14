# X competitive intelligence — weekly report

Generated 2026-09-13T23:47:40Z by `engine/marketing/x_intel.py` (schema `marketing.x_intel_report/v1`).
2909 original posts from 17 accounts inside a 90-day window (2909 in the corpus all-time).

Every number here is arithmetic over observed counters — no model scored anything (LLM-never-scores law). A post with no view count is EXCLUDED from rate denominators (`n_no_views`), never folded in as a zero. A row under the n-floor of 12 is marked *(seeding)* and makes no ranking claim.

## By shape (our vocabulary)

| shape | n | no-views | med views | med likes | med interaction/view | med repost/view |
|---|---|---|---|---|---|---|
| `one_liner` | 1684 | 1 | 55,063 | 188 | 0.00357 | 0.00028 |
| `stack` | 705 | 0 | 131,233 | 435 | 0.00521 | 0.00042 |
| `two_part` | 329 | 0 | 65,332 | 248 | 0.00578 | 0.00040 |
| `caption` | 137 | 0 | 40,096 | 240 | 0.00731 | 0.00046 |
| `list` | 54 | 0 | 163,986 | 748 | 0.00564 | 0.00042 |

## By register

| register | n | no-views | med views | med likes | med interaction/view | med repost/view |
|---|---|---|---|---|---|---|
| wire | 1455 | 1 | 97,814 | 190 | 0.00256 | 0.00022 |
| aggregator | 894 | 0 | 115,017 | 866 | 0.00815 | 0.00079 |
| trader | 315 | 0 | 47,616 | 177 | 0.00483 | 0.00021 |
| commentary | 173 | 0 | 13,367 | 46.5 | 0.00487 | 0.00051 |
| macro_color | 72 | 0 | 24,753 | 78 | 0.00382 | 0.00049 |

## By account

| account | n | med views | med likes | med interaction/view | med repost/view |
|---|---|---|---|---|---|
| @FirstSquawk | 539 | 17,061 | 13 | 0.00104 | 0.00017 |
| @unusual_whales | 511 | 128,138 | 595 | 0.00563 | 0.00030 |
| @DeItaone | 405 | 132,719 | 320 | 0.00297 | 0.00021 |
| @Barchart | 384 | 65,913 | 613 | 0.01002 | 0.00105 |
| @KobeissiLetter | 358 | 282,444 | 2,317 | 0.00834 | 0.00080 |
| @wallstengine | 78 | 29,052 | 108 | 0.00429 | 0.00034 |
| @Mr_Derivatives | 76 | 43,105 | 231 | 0.00636 | 0.00022 |
| @StockMKTNewz | 74 | 35,559 | 116 | 0.00382 | 0.00021 |
| @bespokeinvest | 71 | 8,345 | 11.5 | 0.00200 | 0.00024 |
| @PeterLBrandt | 67 | 53,584 | 267 | 0.00554 | 0.00026 |
| @alphatrends | 60 | 24,350 | 122 | 0.00554 | 0.00025 |
| @traderstewie | 60 | 38,068 | 96 | 0.00296 | 0.00012 |
| @LizAnnSonders | 59 | 23,607 | 67 | 0.00378 | 0.00055 |
| @RyanDetrick | 58 | 15,281 | 98.5 | 0.00781 | 0.00042 |
| @markminervini | 52 | 107,828 | 534 | 0.00441 | 0.00017 |
| @charliebilello | 44 | 36,852 | 294 | 0.00898 | 0.00102 |
| @jam_croissant | 13 | 43,664 | 249 | 0.00408 | 0.00032 |

## Shape distribution vs our quotas

| shape | corpus share |
|---|---|
| `caption` | 4.7% |
| `list` | 1.9% |
| `one_liner` | 57.9% |
| `stack` | 24.2% |
| `two_part` | 11.3% |

- `one_liner` — ours (min) 25.0% vs corpus 57.9%. corpus share of single-content-line posts vs our floor
- `two_part` — ours (max) 30.0% vs corpus 11.3%. corpus share of two-content-line posts vs our ceiling

## Precision + signature rates

| metric | rate |
|---|---|
| decimal strict rate | 7.3% |
| decimal any rate | 17.7% |
| bare int rate | 63.1% |
| has number rate | 66.8% |
| cashtag rate | 18.3% |
| starts cashtag rate | 2.7% |
| all caps lead rate | 51.0% |
| emoji rate | 15.8% |
| url rate | 34.8% |
| blank spacer rate | 35.1% |
| quote rate | 7.9% |

> strict decimal is the docket's \d+\.\d\d (4.75); any-decimal also catches the far more common single-decimal percent (4.7%). The gap between them IS the finding — see the docket's key finding #2.

## Week-over-week

Prior snapshot 2026-08-23 (2029 posts).

| metric | was | now | delta |
|---|---|---|---|
| all caps lead rate | 50.7% | 51.0% | +0.0034 |
| bare int rate | 63.4% | 63.1% | -0.0032 |
| blank spacer rate | 35.3% | 35.1% | -0.0016 |
| cashtag rate | 19.2% | 18.3% | -0.0093 |
| decimal any rate | 17.7% | 17.7% | +0.0001 |
| decimal strict rate | 7.2% | 7.3% | +0.0008 |
| emoji rate | 16.4% | 15.8% | -0.0051 |
| has number rate | 67.1% | 66.8% | -0.0032 |
| quote rate | 8.3% | 7.9% | -0.0037 |
| starts cashtag rate | 2.9% | 2.7% | -0.0023 |
| url rate | 35.3% | 34.8% | -0.0059 |

| shape | was | now | delta |
|---|---|---|---|
| `caption` | 5.0% | 4.7% | -0.0032 |
| `list` | 1.9% | 1.9% | -0.0006 |
| `one_liner` | 57.2% | 57.9% | +0.0067 |
| `stack` | 24.7% | 24.2% | -0.0045 |
| `two_part` | 11.1% | 11.3% | +0.0017 |

