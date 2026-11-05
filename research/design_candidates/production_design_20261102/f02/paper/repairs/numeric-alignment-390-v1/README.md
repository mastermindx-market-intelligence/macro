# Macro 390 numeric frame alignment — prepared source repair

**Prepared only; no native application or fresh live validation.** The retained actual JSX shows numeric Frames without explicit flex-column/end layout. Rate and change Frames already carry right text alignment; coverage Frames do not. This packet places the existing Text child at the numeric Frame's end while preserving its text, width, padding, typography and semantics. It does not claim a new screenshot finding or a rendered correction.

## Exact native scope

| Board | Native board | Retained export | Numeric Frames |
| --- | --- | --- | ---: |
| Macro EN / dark / 390 | `7CM-0` | `../../exports/macro-dark-en-390.jsx` | 33 |
| Macro 中文 / light / 390 | `7IS-0` | `../../exports/macro-light-zh-390--comparison.jsx` | 33 |

The **66 Frames** comprise six headers and 60 body cells: rate, delta in pp and coverage only. Each Frame and its unchanged Text child is bound to the retained JSX and an `APPLIED_RESPONSE_OBSERVED` creation receipt. The source patches cover **22 steps**. All **64 nonnumeric row/header cells**, including source controls, names and definition labels, are preserved. Metric-summary labels, charts, footer, source identities and clocks are outside this repair.

Retained export SHA-256 values:

- EN / dark: `a2ca7e6a897c4b6eac3a4c29bb3049f31db6e2757ebe42d0fece91dcccc8d4bd`.
- 中文 / light comparison: `6da71ea6a681b4a6f0b49fa3f233f019d832c91e9db817f211ed0862fdaecf09`.

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| [native-patch.v1.json](native-patch.v1.json) | `7dd1c727557f5a6150bfc2b7034b2d579fa03284d1a45a3d31bae69e9ab633d7` |
| [source-overrides.v1.json](source-overrides.v1.json) | `dc1c1c7a3b7bc148642a74908c0791ace9b8482b228ab96718481de96872ff67` |
| [pending-width-source-overrides.v1.json](pending-width-source-overrides.v1.json) | `abf8f62551f6c08f48cca930fda67a81f9760e047cac7fba4efc059932cff824` |
| [validation.json](validation.json) | `e1fd3966157ccc952e5e96fc82ff065a8aaa9ebaf4f135109021d0036e85c596` |

The native patch contains exact `update_styles` payloads and full before-style/text guards. The two source packets splice only the selected numeric cells' style-attribute bytes; all other source bytes remain unchanged. Compose against the listed exact before-HTML hashes after `fixture-coherence-v1/effective-spaced`. Do not replace or replay the already-applied construction steps to obtain this style repair. No original inputs or exports were edited.

## Pending width findings

The same authored numeric-cell pattern exists in **macro-docked-1280**, **width-768-overlay**, **width-1024-overlay** and **width-1600-docked**. The separate pending-width source packet supplies **44 guarded step overrides / 132 numeric cells**. These boards were absent from the retained writer progress; no actual native IDs are invented.

Apply corresponding source overrides before building the 1280 and 1600 pair. The historical `supplemental-wide-clone.json` contains hashes for the prior source; its input/hash bindings must be refreshed against the composed aligned source before use. This repair does not claim a newly qualified clone plan.

The pending `macro-zh-evidence-return-390 / returned-selected-row` also has three affected numeric lanes: `66.7%`, `+1.13`, `177 / 177`. It is explicitly flagged in the validation and pending-width packet, without changing that separate board's input in this bounded repair.

## Verification and execution limits

Source validation found **zero mismatches**: all 66 Frame/Text pairs and their widths match the original source; all actual roles are supported by retained creation receipts; only the intended style fields differ in the source overlays. Existing values, signs, precision, source controls, row identities/order, dimensions, padding, colors, fonts and Text nodes are preserved.

The original Chinese chart-footer operation `f02-c2-macro-light-zh-390-chart-footer-20261103-01`, target `7J4-0`, remains unresolved. This packet neither resolves it nor grants dispatch authority. Preserve the applicable target pause and consult [the source reconciliation finding](../zh390-timeout-source-reconciliation.md). The sole writer must resolve the applicable effect gate, fresh-read the exact retained bindings, use the accepted original direct carrier and verify the rendered result before claiming completion. An already-satisfied style change must be recorded as satisfied, not blindly replayed.

This is authoring preparation. No Paper or Browser calls, native mutations, interactive proof, independent product/taste review or formal RIG approval are claimed.
