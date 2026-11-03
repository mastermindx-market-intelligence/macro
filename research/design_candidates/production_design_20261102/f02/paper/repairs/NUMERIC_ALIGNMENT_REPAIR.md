# Numeric column alignment — native repair preparation

**Status: PREPARED_NOT_APPLIED.** Local binding passes for all 290 numeric header/body cell frames. No Paper or browser calls were made. Current native state must be read again after reconnection; this report does not establish a rendered fix.

## Exact scope

The rule is in `f02/SYSTEM_CONTRACT.md`, section 3: “Numeric columns align to the end; preserve precision and unit labels”. These six owned boards are on page `p-6-0` of file `01M312VSDSZFVT45674GDVJVZN`.

| Board | Actual artboard ID | Header frames | Body frames | Total |
|---|---|---:|---:|---:|
| Macro dark | `4PO-0` | 3 | 30 | 33 |
| Macro light | `4YD-0` | 3 | 30 | 33 |
| Company dark | `56L-0` | 6 | 54 | 60 |
| Company light | `5HV-0` | 6 | 54 | 60 |
| Options dark | `5VE-0` | 4 | 48 | 52 |
| Options light | `67V-0` | 4 | 48 | 52 |
| **Total** | | **26** | **264** | **290** |

- **Macro:** Above 50D, Change · pp, Covered / eligible.
- **Company:** five FY 2022–2026 period columns and FY26 / FY25 change. Missing values and reported zero remain in their corresponding numeric columns.
- **Options:** Strike · USD, Premium · USD, Contracts, DTE. Time, expiry, type, estimated side, categorical moneyness, flags and source remain unchanged.

## Observed cause and bounded repair

Actual exports contain fixed-width cell frames with a single `max-content` native text child. Existing `textAlign: right` does not position that intrinsic-width child at the end of its parent frame. Options numeric headers were also authored with left alignment.

The proposed frame style follows the already repaired metrics anatomy:

```json
{
  "display": "flex",
  "flexDirection": "column",
  "alignItems": "end",
  "justifyContent": "center",
  "textAlign": "right"
}
```

The column cross axis provides horizontal end alignment; the main axis preserves centered placement. Existing frame widths, 10px inline padding, row heights, precision, unit text, values, source identities/actions, chart nodes and other fields are untouched. No native Text node is targeted. Numeric header/body cells alone receive the style patch.

## Binding and evidence

`numeric-alignment-native-patch.json` contains six `update_styles` payload batches and 290 detailed bindings. Every binding records the actual row, frame and text IDs; consumer/row/column identity; expected width; full current frame/text styles; absent layout properties; desired style; and role evidence.

Dark-board roles are verified against observed `write_html` `createdNodes` receipts. Light-board IDs are verified both against actual exported target JSX and the observed clone `descendantIdMap`, linked back to the dark Frame/Text roles. Parent and step-root IDs are checked against `native-progress.json`. No target is inferred from ID order or textual similarity alone. **Ambiguous targets: zero.**

`numeric-alignment-source-input-override.json` contains 68 separate, hash-bound HTML step overrides for any later authorized reconstruction. It leaves the original applied input packet and per-board files intact. Each override preserves the original text/columns/widths and supplies only the numeric cell layout/alignment change. These overrides are not proof of native import behavior.

## Application and remaining proof

Root owns the qualified direct-call envelope and guard. After reconnection, re-read each owned board and match IDs, row/column identity and expected current styles before using a batch. A changed or absent node is a stop for that target; rebind it from observed evidence. Do not overwrite any intervening native repair.

After applying, obtain JSX and screenshots to inspect numeric header/body end alignment, unchanged widths, density, data, source access, and the Company unknown/zero cells. A call acknowledgment alone is not rendered verification. Sorting, source services and interactive behavior are outside this static repair evidence.

## Integrity

- Native patch SHA256: `1a597788640380f0bf439c768c33b4a62381c565d80413e1ee89affe6b1836f3`
- Source override SHA256: `4586e3dcbda11ab2fab3751b4b70e65a6dfcea0c32a2a696a0e01cf41e9e2cb7`
- Unchanged applied consumer packet SHA256: `163c42de68b7e5f630ef5e4f36b16cec639cb969096cc8e4ac29f351de4c7d92`
- `numeric-alignment-verification.json`: `PASS_LOCAL_BINDING_ONLY`, six boards, 290 frame targets, 68 source steps, zero ambiguities.

The generator `build_numeric_alignment_native_patch.py` reads only the existing inputs, actual exports and native-progress evidence. It writes this directory's preparation artifacts and fails closed when a bound structure/style differs. Re-running it after source evidence changes produces a new evidence binding; preserve any consumed revision before doing so.
