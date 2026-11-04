# F02 recovery contract — isolate the unresolved target

**Advisory finding: the Chinese390 operation remains unresolved; a file-wide pause is broader than the protected contract.** Root may resume separately authorized, provably disjoint F02 board repairs on the **same Mastermind Paper direct app**, as the sole F02 writer, while preserving the original operation and conservatively holding the entire `7IS-0` board subtree. This finding is source adjudication, not a terminal operation receipt, native edit, or formal design approval.

## Exact preserved operation

| Field | Value |
| --- | --- |
| Operation | `f02-c2-macro-light-zh-390-chart-footer-20261103-01` |
| File | `01M312VSDSZFVT45674GDVJVZN` |
| Board / body | `7IS-0` / `7J4-0` |
| Carrier | Mastermind Paper direct |
| Action | `write_html`, `mode: insert-children` |
| Dispatch interval in the retained record | `2026-11-03T06:32:57.235Z`–`06:33:17.706Z` |
| Observed result | `UNAVAILABLE` / `Connection timed out.` |
| Current terminal status | **UNRESOLVED** |

The actual retained payload inserts one 358px-wide footer containing coverage text and an exact-values action into `7J4-0`; its styles are inline. It contains no shared-token update, file/page operation, cross-board move, or remote asset. Its possible late effect can change that body's children and the containing board's layout. This is the basis for holding the entire containing board, rather than assuming that only the missing child name is at risk. The [dispatch checkpoint](../writer-continuation-progress.json) and [original reconciliation receipt](zh390-chart-footer-reconciliation.json) remain unchanged.

The parent reports a new same-carrier children read in this resumed turn: eight children ending at `7NX-0`, with the footer absent. That is corroborating document-state evidence supplied by the parent; this reviewer made no Paper call. **Absence, elapsed time, a new successful read, catalog qualification, or mutex acquisition does not establish terminal non-dispatch.**

## Same-pin source findings

All current sources were fetched from protected Mastermind commit **`910803421beca53ca25145392725ab2d84c7a8e9`**. Source inspection does not attest that those exact runtime bytes are installed.

| Source | Current Git blob | Finding |
| --- | --- | --- |
| [Paper workflow](https://github.com/mastermindx-market-intelligence/Mastermind/blob/910803421beca53ca25145392725ab2d84c7a8e9/skills/paper-design-workflow/SKILL.md) | `1c8c8c713e3648a0f503477494b3d0c334e63665` | “Select the Paper carrier,” item 5, binds the unknown effect to its logical operation/target and explicitly permits disjoint targets in the same file/page. “Inspect, design and verify” requires current target identity, fresh guards and actual screenshots. |
| [Connection contract](https://github.com/mastermindx-market-intelligence/Mastermind/blob/910803421beca53ca25145392725ab2d84c7a8e9/skills/paper-design-workflow/references/connection.md) | `4498df7752f3827f9208481a2980d77a7199eb10` | “Mutation and fallback fence” is operation/target scoped. Its carrier-decision matrix evaluates the selected logical mutation, not every unrelated edit in the file. |
| [RECONCILE_STATE](https://github.com/mastermindx-market-intelligence/Mastermind/blob/910803421beca53ca25145392725ab2d84c7a8e9/docs/sol_skills/RECONCILE_STATE.md) | `e72bb4e6609eb61a042cee8c30367869672e7ca9` | Step 4 requires canonical original-operation reconciliation; client timeout/cancellation does not prove the underlying mutation stopped. |
| [ACTIVE_EXECUTION](https://github.com/mastermindx-market-intelligence/Mastermind/blob/910803421beca53ca25145392725ab2d84c7a8e9/docs/sol_skills/ACTIVE_EXECUTION.md) | `84dbaf920fed2b498b11a56b9ef5d305da718531` | “Gate the action” and Step 4 permit independent work while dependent uncertain actions remain frozen. Step 6 requires actual capability evidence, not inferred blanket outage. |
| [SESSION_RELIABILITY](https://github.com/mastermindx-market-intelligence/Mastermind/blob/910803421beca53ca25145392725ab2d84c7a8e9/docs/sol_skills/SESSION_RELIABILITY.md) | `095f2165c3a6a57561e1e17ce14fcbcd0ef64eb9` | `ROTATION_SUSPECTED` freezes dependent work; stopping all modifications is reserved for an unsafe surface or universal dependency on the unknown effect. |
| [mcp_server.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/910803421beca53ca25145392725ab2d84c7a8e9/integrations/paper_desktop/mcp_server.py) | `7498e92a7f84f06d1d10a23ab69de52b4671195a` | `build_server`, `run`, and the five published actions separate exact-file serviceability from foreground focus and declare board/node coordination. There is no per-operation status action. |
| [bridge.py](https://github.com/mastermindx-market-intelligence/Mastermind/blob/910803421beca53ca25145392725ab2d84c7a8e9/integrations/paper_desktop/bridge.py) | `5f23c971bf8501ad1621e76eed64fee60a87dbfa` | `READ_TOOLS`, `PaperClient.rpc/call`, and `execute` expose no operation-status getter, persistent deduplication ledger, or cancellation receipt. The wrapper operation ID is validated and echoed; it is not forwarded as a vendor idempotency key. |

### What changed, and what did not

Compared with the prior reviewed source pin `b4a5a8925c6c1412dac67ba296cf65ee81c4d4c8`, the Paper workflow, connection contract, reconciliation law and MCP server blobs above are **byte-identical**. Target-scoped isolation is therefore **not a newly granted permission from this plugin update**. The [earlier F02 source investigation](zh390-timeout-source-reconciliation.md) already concluded that only the affected operation/target and dependent actions must pause. The over-broad interpretation in later F02 continuation language needs correction without rewriting historical receipts.

The bridge changes from blob `49483bc6764d72357f7133d108ad154bf7634f37` to `5f23c971bf8501ad1621e76eed64fee60a87dbfa`: a line comparison found 48 additions and 30 deletions. It extracts `qualify_call_arguments` and repeats live contract/input qualification **after** the guard RPC and **before** requested-tool dispatch. It adds no request-lifecycle lookup, retry guarantee, cancellation command, or new terminal reconciliation route. Consequently the update cannot clear the historical footer's uncertainty.

`execute(status)` still returns current connection/document information. `PaperClient.call` still sends only the vendor tool name and arguments. A lost modifying response remains `EFFECT_UNKNOWN` with `retry_allowed: false`; a successful post-read establishes document identity and the response category, not final design acceptance. No new status method or argument may be invented.

## Strongest contrary reading of the user's instructions

The user's “one canvas writer/carrier” and “one modifying operation/carrier until reconciled” could be read as a stricter blanket ban on any subsequent canvas mutation while any historical operation is uncertain. If the user explicitly imposed that global ban, source guidance could not weaken it.

The complete instruction set instead also says to block only affected lanes, preserve original effects, and keep progressing on independent work. The compatible interpretation is **one writer for this assignment, sequential bounded edits, and one original carrier for each logical mutation**. Root stays the sole F02 writer on the same direct app; it does not replace, replay, transfer, cancel, or relabel the held footer. Independent updates to existing F02 artboards are new work already in scope, not an alternate way to obtain that footer. The parent retains the decision and must prove the next target's independence from live ancestry/content before dispatch.

## Concrete next action and held boundary

1. Preserve the original dispatch, stable ID, payload, carrier and `UNRESOLVED` state. Do not retry it, mint an equivalent replacement ID, invoke `prepare` as a recovery substitute, or change host/runtime/account/carrier.
2. Record root's sole-writer continuation and the held set: **board `7IS-0`, its entire subtree, operations that move/replace it or its ancestors, and shared changes that would affect that board**. This is a conservative target partition in the existing checkpoint, not a new lease or lifecycle registry.
3. Start with an existing disjoint board repair, for example the already prepared Macro dark board `4PO-0` corrections. Read its actual target/ancestry and current content, verify the packet's source precedence, then obtain a fresh exact-file snapshot and apply one bounded change through the same direct app. A fresh read of the file is necessary but does not itself prove node-level independence.
4. Inspect the real changed board screenshot and relevant node/JSX readback, record that operation's actual outcome separately, then continue the next independent repair. Treat any new uncertain effect independently and extend the held target set; do not silently treat the original record as resolved.
5. New boards can follow once their source packets and intended placement are verified independent. Avoid cloning the held board, constructing a duplicate footer elsewhere as a substitute, or using automatic placement assumptions that depend on its unfinished height.
6. Continue to hold Chinese390 completion, any final complete-set freeze, and acceptance claims that require it. The currently exposed direct surface has no original-operation status query; a terminal receipt or documented canonical original-request reconciliation remains the exact missing evidence for that target. Root owns the next recovery decision; no response from an archived writer is a prerequisite for the independent steps above.

## Scope and verification of this advisory

This was a bounded current-source and saved-record investigation. Seven current files and the prior bridge source were read; the bridge delta was compared, and the original footer payload was inspected. No Paper calls, remote host commands, tool retries, runtime changes, GitHub writes, browser calls, external messages, or formal RIG actions were performed. No native repair or acceptance is claimed. The only written artifact is this advisory; root owns persistence and integration into the existing F02 frontier.
