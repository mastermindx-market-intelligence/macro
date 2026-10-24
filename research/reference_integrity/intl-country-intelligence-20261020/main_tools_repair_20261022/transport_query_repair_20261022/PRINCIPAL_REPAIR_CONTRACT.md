# Principal architecture adjudication — workspace transport query

Independent reviewer: /root/intl_release_scope_adjudication. This is prospective architecture and verification scope, not completed implementation or runtime acceptance.

## Confirmed mechanism and source binding

At published base `14ed4f12f31b71c63bbabd969aebbf9c4305ccaa`, ordinary workspace mount and native popstate pass raw child `location.search` to the strict business parser. Its vocabulary is view/market/pins/horizon/basis/return_basis/group; transport-only mmx_shell/mmx_generation is therefore refused. The bridge already owns byte-preserving filtering of exactly those two decoded reserved keys. Its API is installed before page scripts by the blocking data-sync injection, but offers no query reader and emits mmx:shell-location only after qualifying LOCATION_ACCEPTED, not during INIT.

The first read-only planning pass used local bytes because ca4 was not yet published; root independently verified those bytes match the now-published base in INPUT_BINDING.json. The principal's compatibility adjudication then directly read the published base. Both templates/intl_workspace.js and site/intl_workspace.js have Git blob0ac7bb2009f1ab385fcf041e8031f4e9deecd199 and must remain paired.

## Adjudicated additive query interface

Add a synchronous no-argument readPageSearch() to the existing candidate-only bridge API. Return the current raw business search projected through the existing filterTransport(); return null for unavailable/refused capability. It is a current-page projection, not evidence of parent admission or LOCATION_ACCEPTED. Valid candidate pre-INIT calls must work; standalone/unauthorized frames retain existing boot refusal. Only exact decoded mmx_shell/mmx_generation are removed, with all nonreserved bytes preserved under the existing filter. No wildcard exemption, serialization, normalization, length truncation or parser relaxation.

A reader must have no messages, navigation/history/queues/timers, DOM/attributes, activation, scroll, focus or observer effects. Its own candidate instance must still be live and be the current public API. A cached method after actual cleanup must refuse even if called later; persisted pagehide/BFCache retains existing noncleanup behavior.

## Consumer ownership and compatibility

Centralize the external query read at initial mount and native popstate. Bind the bridge provider at mount. Compatible candidate API uses its raw projection. No bridge at mount keeps ordinary standalone raw validation. An installed but missing/older/refusing/throwing/invalid capability is not a valid empty query. If a bound provider disappears, is replaced or cleaned up, do not silently switch to standalone handling.

Mount capability failure reaches the existing snapshot-restoration/teardown catch and the entry script's readable fallback. On popstate, read before any inspector/state effects. On capability failure, set `controller.issues=[{code:'UI_UPDATE_FAILED',field:'url'}]`, repaintIssues(), and return. Preserve validated state, serializedQuery, inspector attachment/mode/open state, scenario draft/pending state, return stack, baseline and focus. Do not commit/paint/close inspector/replace history/focus a heading. The browser has already changed its own location; leave it intact. The existing issue renders “Workspace state unavailable” / “工作区状态不可用”.

A successfully obtained string rejected by the business parser follows existing invalid-business-query behavior and warning; do not reinterpret it as a capability error. Keep intl_workspace_state.js production unchanged. Do not attach the existing popstate path to every fragment ACK: that would reset inspector/scenario state. Preserve current ACK validation, deduplication, parent history, raw query comparison and country/Tools navigation.

## Required proof

Positive: transport-only pre-INIT mount (observed390ZHdark path) has correct default state/no warning with unchanged URL/history; valid nondefault business query plus transport restores actual view/market/horizon/basis/group. After INIT no remount/replay/warning flash.

Negative: equivalent standalone and shell invalid business queries preserve refusal/warning and original URL; unknown bad/mmx_feature/mmx_shell_extra/different case, malformed escapes, duplicate decoded business keys, unsupported values, missing equals and excessive business length remain rejected. Raw encoding/order/duplicates/empty segments survive the projection; encoded reserved spellings use existing decoded-key semantics.

Purity/compatibility: repeated pre/post-INIT reads produce no effects or queued work; missing/refusing/throwing/nonstring/replaced/cleaned API is truthfully unavailable with mount rollback or status-only live refusal. Preserve BFCache noncleanup. Preserve existing stale/mismatched/duplicate ACK tests.

Integration: actual controller plus real bridge before INIT, valid/invalid state, native popstate and parent fresh-document history. Fragment ACK must not reset inspector/scenario/return stack. Real parent Back/Forward must prove actual business UI state, not only URL or absence of warning. Recheck the saved Library input's visibility and focus after query repair before asserting any uniquely proven parent-exposure root cause.

Extend shared-shell bridge, workspace controller and state tests; preserve injection order/asset tests and complete Tools regressions. Root independently reviews worker source and runs ordinary-build/actual-parent proof. No parent protocol/focus/admission change is part of this repair.
