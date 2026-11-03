# Company annual-change row repair v1

Prepared source inputs only. The two frozen independent reviews identify missing per-year change companions, small units and failed numeric alignment. This packet replaces nine existing row groups per theme while retaining every raw amount, the final change column, and the untouched 17×5 history.

## Writer instructions

1. Use `company-row-replacements.v1.json`. Re-read each target row’s actual identity, parent, widths and raw values. Style-only alignment differences are expected if the prior patch was applied.
2. Replace each owned row subtree in place, one visual group per call; bind returned new IDs. Do not append duplicate rows.
3. After replacement, the old Company body numeric-frame IDs are stale. Do not replay them. Header, Macro and Options alignment targets are independent.
4. New rows are 52px (previously 46px): allow the board to grow 54px in total and inspect its footer. Do not scale typography or chart marks.
5. Capture actual JSX and full boards after both themes; then update native evidence maps. Local arithmetic/HTML checks are not native review.

## Arithmetic

Each FY2022 amount says “Prior unavailable”. FY2023 onward uses adjacent displayed raw statement values. Standard metrics use relative percent; Operating margin uses pp; Dividend per share uses absolute USD/share, including explicit zero. FY2026 EPS remains unknown and its change says “Unavailable”. FY2025 EPS is 2.07 versus FY2024 1.20, giving +72.5%.

| Row | Dark target | Light target |
| --- | --- | --- |
| Revenue | 5CW-0 | 5M4-0 |
| Gross profit | 5DF-0 | 5LM-0 |
| Operating income | 5DY-0 | 5L4-0 |
| Operating margin | 5EH-0 | 5KM-0 |
| Pretax income | 5F0-0 | 5K4-0 |
| Net income | 5FJ-0 | 5JM-0 |
| Diluted EPS | 5G2-0 | 5J4-0 |
| Dividend per share | 5GL-0 | 5IM-0 |
| Free cash flow | 5H4-0 | 5I4-0 |

`company-source-overrides.v1.json` is for later versioned effective packet composition; it accepts the original row hash or the prior numeric-alignment source override hash. Frozen original packets, exports, reviews and fixture remain unchanged.
