# Feedback belongs to its task

## User outcome

Current Save/Remove keeps its fresh confirmation alongside the current reader. Failed actions keep the original focused control and visible explanation. Historical review, evidence, native history traversal, Close/reopen, language rendering and explicit Retry retire the previous message and its reserved timeout space.

Successful frozen Remove carries its truthful result into Saved snapshots, including when that list cannot then be read. A later task change retires that result normally. A newer result keeps ownership if it appears during an older transition.

## Why this is necessary

The preceding layout phase deliberately retained a hidden nonempty status box after its five-second timeout, preventing timeout-induced scroll clamping in the current task. Neither body navigation nor Close emptied that status. An old success/error therefore appeared in a different task; after timeout its blank box could survive indefinitely.

The repair is a lifetime rule for the existing status, not another notification system.

## Existing owners

| Concern | Existing owner | Policy |
|---|---|---|
| Status and timeout | Existing #cri-toast and toastTimer | Keep one node, existing copy, polite status markup and five-second timer |
| Retirement | retireToast() beside toast() | Cancel, hide and empty only the specific message still owned |
| Task boundary | Existing apply() | Clean up after source/preflight guards and outgoing reading capture, before destination render/restore or closing/focusing |
| Current confirmed mutation | Existing direct render in save() | Preserve the fresh result and accepted reader/focus behavior |
| Frozen removal | Existing update() → apply() transition | One synchronous, destination/language-qualified result handoff |
| Newer choices | Existing route/history/body/focus guards, plus message identity for cleanup | An obsolete cleanup cannot clear a newer result; message identity is not a new navigation gate |

## Message identity and sequence

A short-lived witness contains the stable status element, the existing timer handle and its text. It is not written to storage or history. Matching all three prevents an older continuation from clearing a later message, even when the words happen to be identical.

Ordinary apply() captures its old message before storage preflight. Once the existing preflight checks pass and outgoing basis/reading is captured, retire that witnessed message before rendering or closing. If a newer message appeared in the meantime, cleanup is a no-op; navigation still follows its existing ownership rules.

Current confirmed Save/Remove retains its direct render path. Its fresh message survives that replacement without an extra preservation mechanism.

Frozen Remove passes the returned fresh witness through the existing synchronous update() call. The intended full destination URL and language are captured before the history write. At apply():

- Same owned witness and intended context: preserve the removal result.
- Same owned witness but a different destination/language: retire that supplied witness.
- Superseded witness: leave the newer result alone.

For an explicit handoff, retirement authority remains attached to the supplied witness. Capturing whichever newer message happens to exist when apply() begins would erase a result emitted inside the history-write callback. The native handoff falsifier covers this exact seam.

Do not emit confirmation after update()/apply(): their focus callbacks may already have chosen another task. The result is emitted before navigation and either preserved or retired through the guarded boundary. There is no late reissue.

## Timeout and layout

The existing timeout still hides a nonempty message without removing its occupied space inside its task. Explicit retirement cancels the timer, clears its handle, hides the status and empties its text. The existing CSS then removes its box. Cleanup precedes destination reading restoration, so old blank height is not incorporated into the new reader.

The status node, role, live-region attributes and all UI copy are unchanged. CSS, HTML template, focus clearance and reduced motion are unchanged. Browser checks do not establish a new assistive-technology announcement certification.

## Proof

The final native run passed **67 affected cases** in **69.78s** (pytest; **70.145s** subprocess, **70.46s** wrapper), on Chrome **157.0.8103.39**, with **67 contexts / 67 pages**, **zero page errors**, **zero external requests** and **zero WebSockets**. Assets: `89c2e5bd3fa3`. Source parent: `bbfdd6d9d039f4f08e17c6f1e917e535dd4b2ee4`.

| Run | Cases | Purpose |
|---|---|---|
| Initial parent baseline | 27 failed / 39 passed; 66 total | Demonstrated old feedback surviving task changes; included two defects in newly added harness code |
| Corrected parent baseline | 26 failed / 4 passed; 30 total | Corrected only the new harness and added the handoff-history control; product remained at the parent |
| Verified candidate | 67 passed | All 30 new cases plus 37 retained mutation, reading, focus, locale and navigation cases |

The initial baseline took 63.19s in pytest / 63.564s subprocess / 63.66s wrapper. The corrected baseline took 33.17s / 33.545s / 33.66s. All three recorded runs had no page errors, external requests or WebSockets. Counts are not additive: the final case set is the union of the initial and corrected baseline sets. The final browser module is byte-identical to the corrected-baseline module. The initial module is exactly recoverable by reversing its two documented new-test fixes and removing the added handoff control. No existing parent test function changed.

The new cases cover:

- English at 390px and Chinese at 320px; success and failure followed by review/evidence, Back, same-URL history traversal, Close/reopen, language changes and Retry.
- Real five-second timeout behavior: reserved space remains inside the originating task, disappears on task change, and a retired timer cannot hide a newer result.
- Frozen Remove → Saved, including unreadable storage, followed by explicit Retry; the confirmed result survives its intended handoff and no write is replayed.
- Newer outcomes inside storage preflight, history writes and focus callbacks; an old continuation cannot erase them or reissue a retired result.
- Exact stable status-node identity, empty/hidden/zero-height retirement, existing polite status markup, preserved collection behavior and controlled write counts.

**25 PNGs are retained:** all 23 final captures (10 new visual outcomes and 13 retained regression captures), plus two corrected-baseline comparison captures. The 10 new final captures and two baseline comparisons were visually inspected. The English baseline visibly carries “Saved on this device.” into Historical review; the corrected review removes it. The narrow Chinese baseline does not expose the complete stale error in the crop; its DOM/assertion receipt establishes the retained message. English/Chinese review, evidence and Retry outcomes remain readable.

The 21 recorded runtime/test inputs have **five changed and 16 unchanged** entries. Both served HTML files change only their two asset references. Template/served JavaScript match; CSS, HTML template, projection, source JSON, builder, server tests and shared assets remain exact. All six JavaScript transformations invert to the parent; removing the full new test addition restores the exact parent browser module.

The native publication readback (PID 7074, exit 0, 0.19s) identified 28 evidence/script files and 25 captures. The corrected-baseline completion was recovered through its original Studio Direct receipt pages; that recovery did not replay execution.

## Build and scope

Continue templates/crypto_intelligence_r4.js and the existing update(), apply(), save() and toast() owners. The source has six reversible transformations. Removing the appended tests recovers the complete parent module. The two harness corrections and extra pre-apply handoff control are recorded separately; they do not change existing parent test functions.

Read [current actions](CURRENT_ACTIONS.md), [current mutation reading](CURRENT_SAVE_READING.md), [drawer focus](DRAWER_FOCUS.md) and [storage safety](SNAPSHOT_SAFETY.md) together. The existing frozen Remove destination, explicit displayed intent, exact serialized storage confirmation, collection retention and no-replay rules remain.

[Native receipt](feedback-lifetime/PUBLICATION_RECEIPT.json) and [capture references](feedback-lifetime/CAPTURE_REFERENCES.json) identify exact inputs, cases, intermediate mistakes and limits.

Local historical/synthetic proof does not establish personal records, current-market freshness, hosted/public-route acceptance, H5/model authority, alerts, paired receipts, qualified results or release.
