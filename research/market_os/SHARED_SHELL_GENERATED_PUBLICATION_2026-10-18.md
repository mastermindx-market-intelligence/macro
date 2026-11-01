# Shared Shell generated publication contract — 2026-10-18

Status: implementation and beta delivery in progress. This records the source-review boundary and required publication proof; it does not claim a deployed beta.

## Why the generated files use the existing renderer

Macro's trusted-base CI authority controller limits pull-request inventories to 3,000 changed files because the GitHub pull-files API cannot enumerate a larger complete inventory. PR7949's first full bridge refresh changed 13,215 paths and was rejected as current_pull_identity_rejected before authority-path evaluation. That was a real inventory refusal. No authority policy, limit, required check, or repository permission was changed.

The source implementation belongs in the reviewed pull request. The existing render workflow owns the mass generated documents: it runs the common HTML emitters and asset optimizer, checks the finalized references and required template pairs, stages site/ and the plain-copy template pairs, and commits those generated outputs. This is the established Macro delivery path. The VPS serves the resulting committed main tree through macro-update; a source merge by itself is not evidence that all documents are live.

## Exact reconciliation

The fully generated integration checkpoint remains in Git history at 8599a5ef5323c8dbd74e261261088cda067f46c1. The next integration joins current main at 8dc33f6df0a48df4492a16350fa849bbd0b49423. Its seven generated HTML conflicts were resolved from the exact incoming stage-3 blobs; four affected inline adapters were then reapplied from the already reviewed source edits. No unmerged entries remain.

Every changed HTML file was compared with that incoming main after only two normalizations: removing the single owned mmx-shared-shell capability block, and replacing hexadecimal asset v query stamps with one comparison token. 12,991 files were otherwise byte-equivalent. All 32 HTML files with any remaining behavior/content delta were retained. The required plain-copy about.html, chat.html, and index.html pairs were retained too. Exactly 12,988 generated-only files were restored to their exact incoming-main bytes and hash-checked after restoration. The resulting implementation diff contained 222 paths before adding this contract.

This retains the complete feature scope. It moves the repetitive capability/stamp emission to its existing generator owner; it does not remove routes, page adapters, the bridge asset, template changes, or tests. Both template and emitted copies of shared_shell_bridge.js remain in this PR, as do the required JS/CSS and plain HTML pairs.

## 14:48 generator and source verification

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

## 2026-10-18 17:08 UTC — static stylesheet and publication integration

The current source keeps protocol mmx.shared-shell.v1 and bridge/document versions 20261018.1. The bridge now uses a separate dormant stylesheet. Both files are published by the existing copy_asset owner, and each carries its own content digest:

| Asset | Content stamp | SHA-256 |
| --- | --- | --- |
| shared_shell_bridge.js | 048314d5 | 048314d5a56e2eb639262829b2b54a5419fd92532c392b85668d3c717c0b653d |
| shared_shell.css | 6a3f8fe8 | 6a3f8fe83206789d7b4f8fe69842f7976d4e1d45d0be3582ab7b82cc3295cdbf |

The common owner puts the stylesheet before the blocking bridge inside the existing capability block. Chrome suppression starts only after the existing trusted INIT and context checks. A guarded computed-style marker must be present before activation and before every READY; a missing, gated, blocked or unreadable stylesheet cannot produce a successful readiness claim. The parent contains the existing initialization_failed error in its retry/open-original boundary. Independent review found no substantive regression in the exact 11-file repair, patch SHA-256 897a5289cf744b011d31a8fc9c9fdf5e1c9741ead3be8799e3f8d9506b2954d5.

The sole access addition is the exact /shared_shell.css asset in site_access.yml and the four existing Caddy access/cache matchers. The original runtime-style allowlist stays byte-identical. The actual runtime-style detector now reports no injected-style hits in either bridge copy. The publication check verifies both source/emitted assets. The render and engine-render lanes check finalized output before publication, and cannot push stale generated changes after a failed optional healing commit.

The retained refresh updated 37 site documents, including the previously stale glossary and markets output, and mirrored the three about/chat/index plain-copy templates. It used the common injector, preserved all bytes outside its owned block, and retained each file's final-newline state. A separately recorded Markets correction added exactly the two newlines emitted by the current navigation include; the unchanged comparator proved this was the only remaining non-lane output difference. No market-data rebuild or comparator relaxation was used.

Actual M2 verification passed: 184 bridge/navigation/owner/handoff Node cases; 89 injection/public-policy/export/Caddy Python cases; all 83 glossary/markets/research builder cases; the canonical template/site and asset-reference guards; the runtime-style guard; and the source claim scanner. The complete contract census against the exact joined base 7b318164a1a757bacbe9d0ad104ec76fc820ca07 reports zero introduced and zero inherited findings, with all three scheduling probes below their existing ceilings.

A new in-memory projection proved idempotent current JS/CSS emission over 13,028 documents and 11 unchanged fragments, without writing the full site tree. Its receipt SHA-256 is 141af9795a1b8c76f0295de15be2f56e1b991bb7299ff90e88045368e8a4eb75. The later two-newline Markets output correction has its separate fresh-builder proof. Neither receipt substitutes for a generated-main commit and inspection of the actually served tree.

The route projection still contains 13,015 legacy paths, 14 native paths, 293 directory entries and zero coverage gaps. Fourteen existing registry rows received evidence-backed archetype classification repairs; no route or access scope changed. The current registry SHA-256 is 5307ea5a7964fde609a8f20f1af30b6bf483b7631f7232e5db74f9ef1d710023, already carried by the published Terminal candidate 1d6024c8ae39bafee328017fa96769d17b3be378.

Fresh P0b renderer/browser receipts and a real local hydrated-shell browser run remain the next evidence steps at this checkpoint. The full generated publication, source landing, isolated beta installation, DNS/TLS and public browser acceptance remain pending. The source procedure pin remains c355e6a4ce3c15ac1e46c14f642bb5984da810d2.


## 2026-10-19 — About Main navigation repair and full publisher proof

The actual R6 browser run reached the current About document and its genuine content READY, but exposed a duplicate body-level marketing navbar beneath the persistent Terminal header. Both the dormant stylesheet and browser observer had omitted that component. About's separate breadcrumb, article header and main content remain retained.

The canonical and emitted stylesheet now add only the scoped `html[data-mmx-shared-shell="1"] body > nav.nav[aria-label="Main"]` selector. The CSS stamp is `8c102aa3` (full SHA-256 `8c102aa390969828d0d82c9b2f58d88cf9078c227259c1eae5fcd4ac10cc6c86`). The bridge remains `048314d5` and its activation, source/origin/generation checks and readiness sentinel are unchanged. The new R7 observer includes that actual component while still requiring a nonempty chrome set and every observed node hidden with zero geometry. R6 remains a failed run; the separate R7 source review is not a runtime pass.

The added regression first failed on the original CSS in both actual M2 Python and Node runs. With the source fix, all 34 injection/publication Python cases and all 70 bridge Node cases passed; no Node cases were skipped. The canonical project environment passed all 129 template/site pairs. An earlier system-interpreter check lacked the required rjsmin emitter and was refused; its output is preserved, and neither theme file changed.

The real, unchanged `scripts/inject_shared_shell.py` publisher ran over all 13,039 retained HTML files. It produced 13,028 full documents and retained 11 fragments. A subsequent full-site check required zero changes. The before/after byte audit covered those files plus three paired templates: all 13,042 retained every byte outside the single owned shell block. The publisher restamped 40 existing blocks and added one block to each of 12,991 previously uninstrumented documents. The complete original About bytes were preserved outside its CSS URL stamp, and both plain-copy About outputs matched the independently predicted owner output.

The established generated-publication boundary still applies. After retaining the actual full-run proof, the 12,991 generated-only outputs were restored to their exact clean source-head bytes; all 40 existing document restamps, both CSS copies and the two regression tests remain in the source change. This does not claim that the partially materialized source worktree is a fully published site. The ordinary renderer must later publish all generated documents to an accepted main commit, followed by verification of the actually served tree.

Evidence is retained in `research/market_os/evidence/shared-shell-public-nav-20261019/MANIFEST.json`, including the meaningful failures, green results, actual full-site audit, generated-output reconciliation and independent R7 source review. The compressed audit files contain the original exact JSON bytes. Beta installation and public acceptance remain separate outstanding work.
