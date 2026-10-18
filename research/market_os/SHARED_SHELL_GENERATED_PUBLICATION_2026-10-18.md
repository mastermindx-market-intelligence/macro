# Shared Shell generated publication contract — 2026-10-18

Status: implementation and beta delivery in progress. This records the source-review boundary and required publication proof; it does not claim a deployed beta.

## Why the generated files use the existing renderer

Macro's trusted-base CI authority controller limits pull-request inventories to 3,000 changed files because the GitHub pull-files API cannot enumerate a larger complete inventory. PR7949's first full bridge refresh changed 13,215 paths and was rejected as current_pull_identity_rejected before authority-path evaluation. That was a real inventory refusal. No authority policy, limit, required check, or repository permission was changed.

The source implementation belongs in the reviewed pull request. The existing render workflow owns the mass generated documents: it runs the common HTML emitters and asset optimizer, checks the finalized references and required template pairs, stages site/ and the plain-copy template pairs, and commits those generated outputs. This is the established Macro delivery path. The VPS serves the resulting committed main tree through macro-update; a source merge by itself is not evidence that all documents are live.

## Exact reconciliation

The fully generated integration checkpoint remains in Git history at 8599a5ef5323c8dbd74e261261088cda067f46c1. The next integration joins current main at 8dc33f6df0a48df4492a16350fa849bbd0b49423. Its seven generated HTML conflicts were resolved from the exact incoming stage-3 blobs; four affected inline adapters were then reapplied from the already reviewed source edits. No unmerged entries remain.

Every changed HTML file was compared with that incoming main after only two normalizations: removing the single owned mmx-shared-shell capability block, and replacing hexadecimal asset v query stamps with one comparison token. 12,991 files were otherwise byte-equivalent. All 32 HTML files with any remaining behavior/content delta were retained. The required plain-copy about.html, chat.html, and index.html pairs were retained too. Exactly 12,988 generated-only files were restored to their exact incoming-main bytes and hash-checked after restoration. The resulting implementation diff contained 222 paths before adding this contract.

This retains the complete feature scope. It moves the repetitive capability/stamp emission to its existing generator owner; it does not remove routes, page adapters, the bridge asset, template changes, or tests. Both template and emitted copies of shared_shell_bridge.js remain in this PR, as do the required JS/CSS and plain HTML pairs.

## Generator and source verification

The retained source emits documentVersion 20261018.1 with bridge asset digest 9e98cc40 (full asset SHA-256 9e98cc403b65a433d2699885c793dcd8c95a656296d400074c977f5d7e5cb554).

An in-memory projection ran the actual common injector over all 13,039 retained HTML files: 13,028 full documents receive exactly one capability block, and 11 fragments remain unchanged. Reapplying the injector was idempotent for every file. This is generator evidence, not a claim that those bytes were written or published. The full local proof receipt SHA-256 is bdcfb643fa8ded00696aee2b130e79dbeb83a08d073c76c444d692b7827dd0e6.

After the artifact boundary change, the project's existing .venv-shared-shell interpreter passed the 128-pair template/site guard, site asset-reference guard, exact registry projection check, focused Python suite, and all 179 bridge/navigation/owner/handoff Node tests. The plain system Python was first refused because it lacked the required rjsmin emitter dependency; that refusal was retained and the existing project environment was used. No guard was weakened and no emitted file was overwritten to hide a dependency error.

The canonical registry projection remains 13,015 exact legacy paths, 14 native paths, 293 directory entries, and zero unregistered HTML coverage gaps. Its registry SHA-256 remains 30516d80cd64baf1f542e0d1cbf90ed254a1eab02cb55da3504766f5ae245535.

## Required delivery sequence

1. Land the source PR only after its current-head CI and review requirements pass through the normal landing owner.
2. Observe the ordinary template render triggered by the source changes. Use the existing workflow's completion and generated-main commit as publication evidence. Do not dispatch a duplicate render when the required run is already active, and do not cancel unrelated production work.
3. Verify the common injector against the resulting committed rendered tree and verify the actual VPS served tree. Require the exact bridge asset, one current document capability on every eligible document, unchanged fragments, correct relative asset paths, and no missing asset references. The earlier in-memory receipt cannot satisfy this step.
4. Verify public HTML and bridge delivery, including scoped Caddy embedding headers, normal framing protection, and beta's exact-origin handshake.
5. Expose beta only after the separately reviewed Terminal release owner, installed runtime identity, data namespace, DNS/TLS, and responsive/fresh-session browser acceptance are proved.

The beta service, DNS cutover, and public beta acceptance remain outstanding. The protected source procedure pin stays c355e6a4ce3c15ac1e46c14f642bb5984da810d2.
