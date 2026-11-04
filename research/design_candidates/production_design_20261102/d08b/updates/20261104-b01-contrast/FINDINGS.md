# D08B live Paper export verification

Read-only advisory task `paper_export_verification`, performed in the resumed D08B session. File: Terminal `01M3NSZGE8JWN2EZCSF0DT05RM`. No Paper mutation, move, deletion, cleanup, worker dispatch or external watcher was performed.

## Result: B01 POSTCONDITION_MISMATCH

The actual B01 matrix child is **`1ONW-0`**, under board **`1NZL-0`**, on the D08B candidate page `p-12-0`. Its native JSX still has the earlier heatmap foregrounds: 52 labels use `#F7F8FA`, two use `#0F1115`; none use the final expected white/black pair. All 54 cell values, fills, alpha and positions agree with the frozen payload; all 54 foregrounds differ.

The lowest calculated **native** label contrast is **4.2446401523:1**, at `+128`, native fill `#65CCD291`, foreground `#F7F8FA`, over panel `#181B21`. This is below the package's 4.5:1 normal-text target. The native exporter quantizes fill alpha to an 8-bit channel (`145/255` here); this calculation uses that actual channel.

The new live full-board screenshot is **byte-identical** to the published/frozen `d08b-work/evidence/B01.jpg`: both are 167,098 bytes, SHA-256 **`7beedaab37baf59eca08ffd8c400d253e61af45614f3fda74faeb2554f715859`**. Therefore the earlier final claim that B01's native screenshot demonstrated the corrected 4.660:1 minimum is unsupported. Preserve that old evidence and append an explicit correction; do not overwrite its history or present the previous applied response as proof of intended-target success.

## Original-target and separate-frame reconciliation

The recorded contrast-operation target **`1O7B-0`** is currently a detached empty `Frame`: `parentId=null`, `childIds=[]`, `artboardId=null`. Its recorded width/height are 824×514 and world position 248,336. It is not B01's current live matrix child.

The separate frame **`1S2W-0`** has parent **`root_node_p-1-0`**, no enclosing artboard, dimensions **824×514**, local position 248,336 and child `1S2X-0`. Its exported matrix has **51 white `#FFFFFF` and three black `#000000` labels**. All 54 cell values, foregrounds, fills, quantized alpha and positions match the final expected B01 payload; no cell difference was found.

These observations are consistent with a stale detached target being used for the earlier replacement. They do **not** independently establish the creator/writer of `1S2W-0`, its custody, or authority to move/delete it. No cleanup was attempted. Root should reconcile the original operation record and perform any corrective write only against the freshly bound intended B01 child, with a new corrective operation identity and verified postcondition. Do not replay the old target.

## Other affected boards

| Board | Live target | Finding |
| --- | --- | --- |
| B02 | `1OD3-0` | Nine actual heatmap labels have the expected white/black foregrounds. Native minimum **4.6558051667:1**, with no label below 4.5:1. |
| B04 | `1OMF-0` | 20 uses of corrected `#2758E6`, matching the frozen composition; zero uses of old `#285FFF`. |
| B08 | `1PG1-0` | 11 uses of corrected `#2758E6`, matching the frozen composition; zero uses of old `#285FFF`. |
| B14 | `1QGP-0` | Four uses of corrected `#2758E6`, matching the frozen composition; zero uses of old `#285FFF`. |

The small difference between the final source-payload contrast calculation (~4.660) and the corrected native value (~4.656) comes from alpha quantization. Report the native value when making a native-rendering claim. The light-board checks verify the requested color postcondition; they are not a new full design, accessibility or runtime acceptance pass.

## Retained evidence

- `B01-matrix-1ONW-0.jsx`: raw JSX from the live B01 matrix.
- `B02-1OD3-0.jsx`, `B04-1OMF-0.jsx`, `B08-1PG1-0.jsx`, `B14-1QGP-0.jsx`: raw full-artboard JSX exports.
- `separate-frame-1S2W-0.jsx`: raw JSX from the separate active-page frame; no custody inference.
- `B01-live-before-repair.jpg`: actual live B01 screenshot, identical to the frozen screenshot.
- `export-observations.json`: native read states and original/separate node metadata.
- `native-contrast-findings.json`: actual fill/foreground/alpha contrast measurements.
- `matrix-payload-comparison.json`: all 54 cell comparisons for current B01 and the separate frame.
- `light-blue-comparison.json`: expected/actual color counts for the three light boards.

This is independent native read-only evidence for root reconciliation. It is not formal RIG, complete WCAG conformance, product implementation or production proof.
