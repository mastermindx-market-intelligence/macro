---
key: A-CAPTURE-TOOL-EDIT-REQUIRES-A-RECAPTURE-BECAUSE-THE-MANIFEST-PINS-THE-MODULE-SHA
claim: "A visual-evidence receipt whose manifest pins `tool.module_sha256` to its own capture.py cannot absorb a capture.py edit without a full recapture: any edit changes the pin, and a metadata-only restamp (`--finalize-only`) re-attributes old pixels to a tool that never produced them."
falsifier: "Edit capture.py, run only `--finalize-only`, and show the receipt still proves its cells were produced by the pinned module (it cannot: the pinned sha now names a module that captured nothing)."
so_what: "Batch capture-tool fixes into one round and recapture once; README-only truth corrections (wording, disclosed scope) are the only cheap repair class — they leave the pin and `source_commit` untouched, which is exactly why MO-PAID-006 R4d was README-only."
kind: runtime
verified_at: 2026-10-03
verified_by: "MO-PAID-006 R4 -> R4c rounds each required a full mini2 recapture after capture.py edits (manifest tool version 3 -> 4, module_sha256 d26164d4d380 == sha256 of the committed capture.py); R4d changed README only and kept the pin, source_commit 40fe0576 and the 28 receipt tests green"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "mockups/evidence/mo-paid-006-dossier-page/manifest.json"
  - "scripts/check_ui_visual_evidence.py"
confidence: verified
---

`--finalize-only` exists for metadata reshaping and must preserve the recorded `source_commit` (R4c made it refuse when the worktree template is not that commit's blob). It is never a substitute for a recapture after the tool itself changed.
