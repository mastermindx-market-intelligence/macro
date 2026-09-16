# MastermindX Public-Site Figma Baseline — Execution Checkpoint

**Operation:** `public-site-figma-baseline-20260915-sol-001`  
**Owner:** Sol  
**Status:** `PARTIAL` — canonical Figma carrier and page architecture exist; editable page reconstruction and proof remain unfinished
**Current Skillpack:** `mastermindx-market-intelligence/Mastermind@bf843961c0e1b5bd45fa481f0138c71f2a87d4e2`
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

## Figma carrier reconciliation

A desktop-level read of Figma's own recent-file state and a direct open of the named file corrected the earlier no-file claim. The canonical carrier already exists:

- file name: `MastermindX Public Site — Current 1:1 + Revamp`;
- file key: `sDuVPajwNnGLkZlWyun9wq`;
- plan/user context: the authenticated Mastermind Professional workspace already used by this operation;
- duplicate status: **one file**. Two recent-history entries pointed to the same `/file/sDuVPajwNnGLkZlWyun9wq` path and were not duplicate files.

Direct window proof showed nine pages already present in this order:

```text
00 — Read Me & Acceptance
01 — Foundations
02 — Components
10 — Current · Homepage
11 — Current · Market Terminal
12 — Current · Mastermind AI
13 — Current · Market Dashboards
20 — Motion & Interaction
90 — Reference Captures
```

`99 — Revamp` is absent. The selected `00` canvas was blank and no visible top-level layers were present. Therefore the truthful carrier state is `PARTIAL`: file and page architecture exist, while native reconstruction, reference imports, overlays, acceptance content, motion proof and the locked Revamp gate remain unfinished.

The prior connector create attempts remain reconciled as known no-effect. They did not create a second file. The stale statement “no Figma file exists” is superseded by the direct carrier evidence above.

## Durable tooling added on 2026-09-16

The branch contains a source-bound, reusable capture and native-connector import path rather than only one-off evidence scripts:

- `capture_reference_matrix.py` verifies frozen source blobs before capture and defines the canonical 20 static + 16 motion jobs;
- `reference_matrix.py` refuses missing, duplicate, console-error, dimension-mismatched or noncanonical evidence;
- `build_import_plan.py` emits the ordered 36-target upload manifest plus idempotent Figma preparation/finalization scripts;
- three focused test modules cover capture ordering, matrix sealing and import-plan generation.

Fresh verification:

```text
SOURCE_VERIFIED local_head=e0e3fda2fa2a44d8d64c3f0a52b9d56c1de3653b frozen_source=15c01bd991f35d0bb2185ee1e608a05df0805803
11 passed
FIGMA_BASELINE_TOOLING_VERIFIED targets=36 js=2 source=verified
REAL_CAPTURE_RUN_RESEALED static=20 motion=16 hashes_match=36
```

The tooling prepares deterministic inputs for the native ChatGPT Figma connector. It does not itself prove execution in Figma or visual fidelity. No production-site path changed.

## Native ChatGPT Figma connector boundary

Chairman direction is explicit: all Figma canvas reads and writes must use the native ChatGPT Figma connector. Figma Desktop, Remote Desktop UI automation and local development plugins are not valid execution carriers for this program.

The current ChatGPT plugin state was checked directly:

- Figma is installed and enabled in ChatGPT;
- its app-specific permission is `Allow all actions`;
- a native `whoami` call returned the typed platform response `The Figma tool has been disabled` before any Figma read or write;
- therefore this conversation produced no Figma effect and must not retry through another carrier.

The rejected local-development-plugin implementation and runbook were removed from the worktree and evidence root. Do not recreate them.

## Exact continuation sequence

1. Use the native ChatGPT Figma connector only; do not use Figma Desktop, Mac UI automation or a local plugin.
2. Reuse file key `sDuVPajwNnGLkZlWyun9wq`; **do not create another Figma file**.
3. On a healthy connector surface, call `whoami`, then `get_metadata` on the existing file and reconcile authoritative page/node IDs.
4. Use `use_figma` to add and lock `99 — Revamp`, then populate `00 — Read Me & Acceptance` and the shared foundations/components.
5. Use `generate_figma_design` and/or `upload_assets` through the connector for the 20 source-bound static states and 16 motion references; never substitute a scaled desktop image for a mobile render.
6. Build the four Current pages as native editable Figma structure and link hidden 50% reference overlays one state at a time.
7. After each bounded wave, use connector metadata and screenshot reads to verify actual Figma state before advancing.
8. Keep all redesign, copy changes and production code work closed until the Current acceptance matrix passes and the Chairman explicitly accepts it.

## Current lane boundaries

- This conversation's native Figma runtime is `PLATFORM_FAILURE / known no-effect` after the typed disabled response.
- Repository and evidence preparation may use host tools, but no host tool may read or modify the Figma canvas.
- The existing Figma carrier remains `PARTIAL`; no native connector proof has yet shown its current node-level state.
- No design content, Figma asset, public-site source, deployment or production state was modified during this correction turn.

## Non-goals still in force

No redesign, copy rewrite, section deletion, production code change, deployment, or broader anonymous-site expansion is authorized by this checkpoint.
