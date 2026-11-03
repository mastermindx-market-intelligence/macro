# Native clone equivalence assessment

**Local preparation only. No Paper calls or native changes.**

Input source: `mobile-state-boards.json@a52e7566fa7ff5ae8e55874fb2b28e0d5cfc1fbc415530532294d9c590c35d4d`.

Final clone-plan SHA256: `1885ae79561f03e6788da97f11a94a610b4e13ea816d0797962df9841f50da17`.

Both pairs have identical step keys, parent references and HTML tag/child topology. Every supplied element has an exact source-relative path; these paths are not Paper IDs.

| Pair | Text changes | Native style targets / properties | Layer renames | SVG presentation changes |
| --- | ---: | ---: | ---: | ---: |
| English dark 390 → Chinese light 390 | 57 | 124 / 215 | 14 | 16 across 2 subtrees |
| EPS 320 → zero dividend 320 | 15 | 0 / 0 | 0 | 0 |

The phone pair also changes the artboard background. The EPS pair needs the new artboard name plus text changes only. No declared width, height, padding, gap, font-size or line-height changes are present in either pair. Translation and font-family changes can still alter measured wrapping and height.

## Safe application boundary

Use the actual `duplicate_nodes` descendantIdMap and observed source JSX/tree. Match each descriptive path and expected old content to its observed source native ID, then use the map to select the destination. Do not invent IDs or assume the HTML parser and Paper serializer have identical array positions. Input CSS expressions can be resolved or normalized in actual computed styles; verify their meaning against the current token receipt.

If a source subtree has changed since these inputs—especially a native fit or repair—reconcile that exact difference before applying its clone delta. This assessment does not override later fixes. Clone position, current measured height and native editability require the parent’s actual same-carrier readback.

## EPS → dividend: exact text changes

| Step | Expected source text | Target text |
| --- | --- | --- |
| `title` | Diluted earnings per share | Dividend per share |
| `title` | 稀释每股收益 | 每股股息 |
| `value` | — | 0.00 |
| `value` | FY2026 value not supplied. Unknown is not zero. | Reported zero in this illustrative fixture. Zero is a value. |
| `period-2022` | 0.53 | 0.00 |
| `period-2023` | 0.73 | 0.00 |
| `period-2024` | 1.20 | 0.00 |
| `period-2025` | 2.07 | 0.00 |
| `period-2026` | — | 0.00 |
| `comparison` | Unavailable comparison | 0.00 USD/share |
| `comparison` | A missing current value cannot yield a change. | Percentage change is undefined because the prior value is zero. |
| `source-0` | f02.fixture.v2/company/EXM/diluted_eps/FY2022-FY2026 | f02.fixture.v2/company/EXM/dividend_per_share/FY2022-FY2026 |
| `source-1` | EXM / diluted_eps | EXM / dividend_per_share |
| `source-5` | USD per diluted share | USD per share; statement currency USD |
| `limitation` | The source fixture contains no FY2026 diluted EPS. Earlier reported values remain visible. Do not derive EPS from an unrelated share count. | The fixture reports 0.00 in each displayed period. Do not replace these observations with dashes or calculate 0/0 as a percentage change. |

Every text target also has an exact element path in `clone-diffs.json`. All five fiscal rows remain native; the history values, field key, current value, change and explanatory copy must migrate together.

## Phone pair: exceptions to inspect

- Translations and Inter→Noto Sans SC changes can change glyph width, wrapping and auto-height despite identical declared geometry. Inspect the title, scope receipt, scroll cue, two-line sector labels and build-note footer.
- The Chinese artifact/provenance-band text inherits Inter in the supplied target input. It requires actual CJK fallback rendering inspection; no extra font-style change is silently added to this exact diff.
- The fixed 596px table viewport, ten 56px rows, 44px source controls and all numeric values are identical. Confirm the source outline remains visible inside the clipped region.
- Two SVG subtrees (menu icon and history chart) have identical geometry but different theme presentation attributes. Native editability must be observed before selecting style updates versus a bounded vector-subtree replacement.
- A duplicate retains the source artboard name and current measured height. Rename to the supplied target name and inspect/set final content fit; do not assume the 1510px initial input height is measured proof.

The JSON includes all 57 exact text changes, 124 per-element style deltas, layer-name changes and the original/target SVG fragments. The two vector fragments are the compact menu icon and the history mark layer. Their geometry is identical; only fill/stroke expressions change. Resolve actual editable vector nodes before treating SVG attributes as native CSS properties. If the actual Paper representation does not expose those attributes, the exact target fragment supports a bounded replacement of the observed mapped SVG subtree—not the board, table or surrounding UI.

## Overlay pair: exceptions to inspect

- Only native text changes are required by the inputs; no CSS or SVG attribute delta exists. Source and destination use the same 320px overlay anatomy and 44px controls.
- The 38px value changes from an em dash to 0.00, moving the following unit within an intrinsic-width row. Inspect this row at its actual 280px body width.
- The title, long field identity, comparison explanation and limitation paragraph have different lengths; natural wrapping and total fit can change. Do not force a fixed height copied from the EPS instance.
- All five fiscal rows remain. Actual zeros and 0.00 USD/share absolute change must replace missing EPS; percentage growth stays explicitly undefined from a zero baseline.
- Update the board name and all changed exact field/source text. A clone with an EPS source identity and dividend values would be invalid.

## Reproduction

Run `python3 compare_clones.py`. The script reads the construction input, parses markup and styles, compares the full element topology and emits deterministic exact deltas. It does not connect to Paper, render fonts or prove browser behavior.
