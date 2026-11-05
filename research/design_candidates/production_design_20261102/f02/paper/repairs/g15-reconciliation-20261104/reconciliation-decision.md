# G15 exact document-effect reconciliation — current receiver decision

**Finding: ABSENT_ON_RECONCILIATION.** This is a descriptive finding from the supplied original-carrier reads, not a returned Paper state or a historical terminal receipt. The original G15 transport outcome remains `TRANSPORT_ERROR_EFFECT_UNRESOLVED` / `UNAVAILABLE`, with `retry_allowed: false`.

## Actual comparison

The successful original operations at zero-based runtime indices **411–433** account for **190 native board nodes**. The fresh complete tree contains **190 nodes**. Missing IDs: **0**; unexplained IDs: **0**; parent-link differences: **0**; name/type differences: **0**; child-order differences: **0**.

The eight direct children of `7J4-0` match in identity and order: `7J6-0`, `7JE-0`, `7JL-0`, `7JQ-0`, `7JT-0`, `7NQ-0`, `7NT-0`, `7NX-0`.

All created-node lists match the original HTML anatomy after explicitly accounting for Paper's receipt-backed Frame/Text expansion of padded leaf divs. Component types, explicit layer names and text names/prefixes are checked before deriving parent links. The live tree supplies independent parent links from its indentation. The requested tree depth is 10; the deepest returned node is depth 5. Every returned line is parsed; no unparsed/truncation line is accepted.

The JSX supplies 174 native IDs, with no unknown/duplicate IDs and no missing non-SVG IDs. SVG nodes are fully accounted for by the tree; JSX may inline SVG without their native IDs. All five G15 structure/content sentinels are absent from the target JSX and tree. Thus no additional or partial appended footer structure is present under the exact target at this observation.

The fresh full-board JSX **and JPEG are byte-identical** to the original complete in-progress capture recorded at **2026-11-03T06:40:32.467Z**, through operation count 435. Both original local file bytes and the canonical `native-current-verification.json` hashes were compared. That canonical record's Git blob is `9dd9ef60ec64cd65804ea4d6e857aa140ab8f91d` at design head `6db372b13e208ace22b6d3472a9dbcc9b61ff888`. This establishes unchanged current content/rendered bytes between those observations, not a historical request receipt.

## Exact payload hash correction

The dispatched HTML is **806 UTF-8 bytes**, no trailing newline, SHA-256 **`6e77280834e8641f52fb6c4f83e3d55540f68747f84af3f44d44e69f74ef491f`**. The runtime and all three original journal argument objects agree. `g15-dispatched-payload.html` preserves these exact bytes. The earlier local `g15-original-html.html` export is 808 bytes because it adds exactly two LF bytes; its file hash **`23c9679543d87db628c6fda14dbca84f0baedd46ac4fc078aa9e23bcd87e0a19`** must not be described as the raw dispatched-payload hash. That earlier export remains unchanged.

## Source interpretation and preserved uncertainty

At protected Mastermind `700eef54bca4a2dc4e30d94a6b30dcfa733ad57c`, `PAPER_DESIGN_INTEGRATION.md` lines 670–675 directs inspection of the original document and same-carrier reconciliation; the Paper workflow lines 128–129 requires exact-effect reconciliation. `SESSION_RELIABILITY.md` lines 102–113 permits canonical readback to establish absence and permits a fresh generation of the same carrier. `RECONCILE_STATE.md` lines 120–148 continues to prohibit ambiguous status being treated as `not_found`, inference of cancellation from timeout, and disguised replay. The bridge explicitly assigns effect reconciliation to the caller without a new retry ledger.

These provisions permit the current document-effect finding without inventing a historical receipt or mandatory backend-drain certificate. They do not prove that G15 was never dispatched, never temporarily applied, or returned success. The parent's retired-dispatcher, later completed operations, current carrier and writer observations remain separately attributable evidence; this file does not manufacture process/request proof.

## Review and next action

The current assigned F02 receiver reviewed and accepted this current-effect finding at 2026-11-04T20:32:18Z. All structural comparisons and the actual before screenshot were inspected. Canonical publication and readback through the existing F02 evidence owner precede any dependent edit. The fresh reads were obtained in this attended session; the upstream read payloads expose no exact timestamp. No timestamp is invented. A new exact-target snapshot is required immediately before the next edit. Retain the original journal unchanged. Re-read the exact target/schema/guard immediately before actual corrected missing work. A new key is for genuinely changed work after reconciliation, not a means to clear the original hold. Verify the resulting complete post-read and actual board screenshot.

Retain the hold if there is concrete pending/replayable original-request evidence, an unexplained tree change, an unqualified carrier/file/schema binding, an overlapping writer, or an incomplete recovered payload. This preparation performed no Paper mutation and changed no original runtime or journal.

## Evidence

- Detailed comparison: `structural-comparison.json` — SHA-256 `329c9a9bb1d5b8fcc67a9265709657c79e179717c083349a428a3fb18294ddf2`.
- Retained original operations: `historical-operations-411-434.json` — SHA-256 `776975d755f14a68ac9185044f13dd38a71e0c09404ee576590bdcb6c7659b22`; extracted from runtime SHA-256 `86428a868e5861d2205279557580156c7572173c16585a29f89a24208010e296`.
- Historical/fresh full-capture equality: `historical-capture-byte-comparison.json` — SHA-256 `0416cd09d219c51ef722b14d48a664d9bf9279914c3458c057e1461dd2a32898`.
- Machine-readable decision: `reconciliation-decision.json` — SHA-256 `3269e9f3b315075317321afaf615ccfe27b820c9efa60789b618fd16b43afaae`.
- `board-before.jsx` — 41342 bytes; SHA-256 `adf6f90dea30d3773916cb06ecae4ff8f2794855364cea7813bea14c97343a6c`.
- `board-before-read.json` — 42974 bytes; SHA-256 `846bba94619ba887318339cef4f8ebb3c5d8101a8c4aa1ff651e5f577c68b6d4`.
- `tree-before-read.json` — 12150 bytes; SHA-256 `4110496f76c054ecf163bdffc93305c9185e6747551465bf5d43f9c17a988f22`.
- `screenshot-before-metadata.json` — 434 bytes; SHA-256 `c9f21d4606c0c8d1af990cf2a5a9bdf89d2a3b31e2c53b9c5083f75def1453f6`.
- `board-before.jpg` — 69446 bytes; SHA-256 `563f312cf109a91e992fcd317905ebd8b48d93fd8808c184d4375857e15427e9`.
