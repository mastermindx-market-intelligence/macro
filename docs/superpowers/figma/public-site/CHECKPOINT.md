# MastermindX Public-Site Figma Baseline — Execution Checkpoint

**Operation:** `public-site-figma-baseline-20260915-sol-001`  
**Owner:** Sol  
**Status:** `PARTIAL` — complete source-bound reference matrix and Figma execution assets; actual Figma file remains `NOT_BUILT`  
**Current Skillpack:** `mastermindx-market-intelligence/Mastermind@7642aea155d2817219135b24246b55c1d7611c66`  
**Frozen site source:** `mastermindx-market-intelligence/macro@15c01bd991f35d0bb2185ee1e608a05df0805803`  
**Design branch:** `sol/public-site-figma-baseline-spec-20260915`  
**Design-branch head before this checkpoint:** `ce52e8d50f621125f132d847b64c0677def59be3`

## Mission

Reconstruct the four flagship anonymous public pages as an editable, accepted **Current / 1:1** Figma baseline before any redesign. Preserve the accepted Current frames, duplicate them into **Revamp** only after explicit baseline acceptance, and change production code only after the revamp is accepted.

## Frozen scope

1. Homepage
2. Market Terminal
3. Mastermind AI
4. Market Dashboards

Canonical visual states are 1440 EN, 1440 ZH, 1024 EN, 390 EN and 390 ZH, plus representative observe, reason, resolve and hold motion states.

## Verified work completed

- Reconciled the existing detached reference tree against the frozen source. The five primary page/style blobs and all relevant dependency paths are byte-identical.
- Replaced the stale Playwright bundled-browser path with the repository's proven system-Chrome channel pattern.
- Built a deterministic capture harness that refuses source drift, stubs only the source-default founding-offer response, records console errors, and captures full documents at the exact requested viewport width.
- Captured and verified **20 / 20** static cells and **16 / 16** motion-state cells.
- Produced SHA-256 manifests, exact dimensions, a capture ledger, reference matrix, and static/motion contact sheets.
- Built and syntax-verified Figma import-target and finalization scripts for all 36 images.

Fresh verification outputs:

```text
CAPTURE_MATRIX_VERIFIED records=36 checked_static=8 motion=16 errors=0
COMPLETE_REFERENCE_MATRIX_VERIFIED static=20 motion=16 records=36
REFERENCE_PACK_VERIFIED static=20 motion=16
FIGMA_IMPORT_SCRIPTS_VERIFIED targets=36
```

## Durable artifact root

`/Volumes/Mastermind/agent-evidence/public-site-figma-baseline-20260915-sol-001`

Important children:

- `captures/reference-matrix.json`
- `captures/CAPTURE_LEDGER.md`
- `captures/static-contact-sheet.png`
- `captures/motion-contact-sheet.png`
- `capture_missing_matrix.py`
- `figma_upload_order.json`
- `figma_20_prepare_import_targets.js`
- `figma_21_finalize_import_targets.js`

## Figma write reconciliation

The Figma connector schema exposed write tools, but the first bounded `whoami` call returned a platform-level disabled-tool response. No create or edit call executed afterward. The previously attempted creates were reconciled as known no-effect. Therefore:

- no Figma file exists from this operation;
- no Figma node or asset was modified;
- there is no duplicate design carrier;
- the expected file name remains `MastermindX Public Site — Current 1:1 + Revamp`;
- the last known destination plan key is `team::1679263159873159004`, but it must be reverified before creation.

## Exact continuation sequence

1. Load the then-current protected Sol Skillpack and record its exact SHA.
2. Re-probe the actual Figma surface once with `whoami`; do not infer recovery from connector documentation.
3. If healthy, create exactly one design file named `MastermindX Public Site — Current 1:1 + Revamp` in the reverified plan and record its file key.
4. Execute the verified bootstrap, homepage-hero and product-hero scripts from the approved execution pack.
5. Execute `figma_20_prepare_import_targets.js`; collect the 36 target node IDs in `figma_upload_order.json` order.
6. Call Figma `upload_assets` with all 36 nodes using `FIT`; upload each exact local file to its corresponding signed URL.
7. Execute `figma_21_finalize_import_targets.js`; it must refuse to lock unless every target has an image fill.
8. Read metadata and screenshots from the actual file, then begin opacity-overlay review one page/state at a time.
9. Build the remaining editable full-page sections. Do not mistake imported captures or hero slices for the accepted editable baseline.
10. Keep `99 — Revamp` locked until the Current acceptance matrix passes.

## Non-goals still in force

No redesign, copy rewrite, section deletion, production code change, deployment, or broader anonymous-site expansion is authorized by this checkpoint.
