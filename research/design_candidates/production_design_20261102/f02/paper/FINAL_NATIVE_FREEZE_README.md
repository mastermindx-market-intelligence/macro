# Preparing the final native freeze

`prepare_final_native_freeze.py` is local-only packaging tooling. Its default is a read-only preflight. It never calls Paper, Browser, Git or the network; never changes construction inputs, source contracts, captures or bindings; and never approves a design.

## Read-only preflight

From the workspace root:

```bash
python3 f02/paper/prepare_final_native_freeze.py --dry-run
python3 f02/paper/prepare_final_native_freeze.py --dry-run --json
```

Exit `0` means the selected evidence is mechanically ready to package. Exit `2` means refusal. An incomplete current construction is expected to fail. Neither command creates a freeze directory.

The expected set is derived from the canonical construction keys, with current fixture/identity precedence, Company annual-growth v2 steps, repair companions and the observed metrics light clone: 6 + 8 + 6 + 4 + 2 + 1 + 4 + 1 = **32 boards**. Prepared repair IDs never become current IDs. Current board/step IDs and capture receipts come from the writer checkpoint and native board/role/predecessor bindings.

The checker refuses missing boards or planned steps; missing/changed final JPEG or JSX bytes; stale registry/checkpoint hashes; unconfirmed or uncertain operations; stale export roots/step IDs; capture receipts predating potentially affecting mutations; unresolved portable role bindings; and missing/stale predecessor companion identities. The four retained domain/source roles remain explicitly unqualified. New readme directory input must enumerate the final 32 observed boards.

The checker reads Paper's literal JSX tags and IDs without executing JSX. JPEG signature checks and hashes do not replace actual image inspection by the reviewers.

The four original production-before files retain their historical `.png` names although their observed payloads are JPEG. The packager preserves all seven before files byte-for-byte and checks the image signature independently of the suffix.

Their lengths and hashes must also match `paper/reviews/native-first-pass-artifacts.json`. That historical manifest is included for baseline identity; its old after-artifact receipts do not replace the new final manifest.

An unresolved transport operation blocks packaging even if a later read does not show its intended node. Absence is not terminal reconciliation. The current writer schema's accepted operation state is `APPLIED_RESPONSE_OBSERVED`; a later documented resolved-no-effect state requires an explicit receipt-bound checker update, not a status rename or silent exception.

## Final receipts

The checker automatically includes these files when present:

- `paper/native-final-retention.json`
- `paper/native-final-verification.json`

Alternative f02-relative paths can be supplied with `--retention-receipt` and `--verification-receipt`. Use `--require-final-receipts` to refuse their absence. If absent without that flag, the manifest records `NOT_SUPPLIED`; it does not invent successful live retention or final native verification.

The retention receipt uses `schema_version` (or `schema`), `status`, `observed_at`, `originals_expected: 67`, an `originals_present` list with `id/file/page` or `board_id/file_id/page_id`, `originals_missing: []`, `uncertain_operations: []`, `owned_mutation_scope_check`, and `shared_tokens` with expected/observed count 20 and original/observed hash `356191c3`. Include the actual file/page read receipts and observation limits. Retention must come from the writer's live reads.

The actual `f02.paper.native-retention-readback.v1` writer shape is also accepted: `recorded_at`, nested `counts`, `originals`, `tokens` with expected/observed content hashes, and `operation_scope_audit`. Every recorded original must be present at its expected location; the scope audit must cover the entire current operation history without original-target mutations. Either receipt form must follow the current operation timestamps. A readback containing an uncertain operation remains blocking.

The verification receipt uses `schema_version` (or `schema`), `status`, `observed_at`, exact `expected_board_keys` and `observed_board_keys`, `operations: {confirmed: <count or operation-ID list>, uncertain: []}`, `portable_role_bindings: {unresolved_count: 0}`, and `boards: [{key, screenshot: {path, sha256}, jsx: {path, sha256}, captured_at, capture_receipt}]`. A `per_board` object keyed by board key is also accepted. Include source/native arithmetic and identity checks and `remaining_gates`; those substantive claims remain reviewable evidence. Optional `checkpoint_sha256` is checked against the current writer file.

New current JSON repair receipts can be explicitly added with repeated `--repair-receipt paper/repairs/<file>.json`. The default includes the existing current fixture, identity/clock, Company v2, companion and native layout repair evidence. Company annual-growth v1 is not selected.

## Optional capture selection

By default the package contains only the **32 final full-board JPEG/JSX pairs** and the **seven original before images**. No interim screenshot glob is used.

| Flag | Selection and checks |
| --- | --- |
| `--include-final-sections` | Recorded complete/final captures bound to a current step; section JSX must match the same subtree in the final full export |
| `--include-closed-table-width` | Complete closed-table evidence on the width studies or 1280 dock study; all ten sector rows and table content must match the final export |
| `--section-capture <writer-capture-key>` | One explicitly selected eligible section/closed-table capture; repeatable; cannot promote an interim capture |

A structured `capture_scope: {kind: "final_section", complete: true}` or `{kind: "closed_table_width", complete: true}` is useful. Existing explicit `COMPLETE`/`FINAL` capture-state labels are also read, subject to the step/width checks. Partial and in-progress labels fail. Closed-table state labels must identify the closed table explicitly. No `rows3`, `rows6`, header-only or generic completed-source-receipt capture is treated as a final full screen. A final full capture must use the bare board key, bind its actual root, have all expected step IDs in its JSX, and follow affecting mutations.

## Create only after the sole writer is finished

After final captures, final live receipts and refreshed native bindings are present, root may run:

```bash
python3 f02/paper/prepare_final_native_freeze.py \
  --create \
  --require-final-receipts \
  --include-final-sections \
  --include-closed-table-width \
  --output paper/freezes/native-repair-<UTC-unique-name>
```

Output must be a new direct child of `f02/paper/freezes`. The script refuses an existing name, validates before creating anything, rechecks source hashes immediately before copying, verifies copied members and seals files/directories with read-only permissions. A failure after directory creation leaves a visibly incomplete directory for investigation; the tool never overwrites or silently cleans it. Read-only permissions are a local guard, not immutable Git identity.

The freeze preserves selected source paths relative to `f02`. It also contains `EXPECTED_BOARDS.json`, `CAPTURE_SELECTION.json`, the unchanged extracted `TASK_MANIFEST.json`, and these persistence lists:

- `FREEZE_SOURCE_FILES.txt`: selected original source paths relative to `f02`.
- `FREEZE_FILES_FOR_GIT.txt`: all freeze files, including the manifest, with workspace-relative `f02/paper/freezes/<name>/...` paths. Root can pass this to Git's `--pathspec-from-file` from the workspace's repository root, or use the exact list with the established persistence route. The script itself performs no Git operation.

The manifest records every member's byte length, SHA256, categories and a UTC timestamp. Its aggregate is SHA256 over sorted relative path + NUL + lowercase file SHA256 + LF. Only the enclosing `manifest.json` excludes itself. A file list can list itself because it contains paths, not its own hash.

Root supplies the immutable Git freeze commit **separately after committing**. Do not rewrite the frozen manifest to embed its containing commit. The optional `--source-commit <existing-40-character-SHA>` records prior source context only.

Verify the completed package read-only with:

```bash
python3 f02/paper/prepare_final_native_freeze.py \
  --verify-freeze f02/paper/freezes/native-repair-<UTC-unique-name>
```

Reviewers receive the frozen package, the separate immutable commit and only their own prior report. The repair-review packet requires every hash and actual image to be inspected and keeps peer reports quarantined. It does not supply a desired verdict or convert native design evidence into browser, F01, domain, formal RIG or production approval.
