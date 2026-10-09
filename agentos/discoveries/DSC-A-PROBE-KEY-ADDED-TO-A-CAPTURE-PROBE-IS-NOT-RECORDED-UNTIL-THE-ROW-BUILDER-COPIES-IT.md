---
key: A-PROBE-KEY-ADDED-TO-A-CAPTURE-PROBE-IS-NOT-RECORDED-UNTIL-THE-ROW-BUILDER-COPIES-IT
claim: "In the receipt capture tools (mockups/evidence/*/capture.py) the browser probe's JS return object is NOT the dom.json row: an explicit Python row builder copies named keys, so a key added only to the JS return is silently absent from every recorded row."
falsifier: "Add a key to the probe's JS return object, run the capture, and find that key present in dom.json rows without any edit to the Python row builder."
so_what: "Every probe change is TWO edits (JS return + row builder copy) and a dry run must grep dom.json for the new key before the run is called evidence; a review that reads only the JS believes the measurement exists when the receipt never recorded it."
kind: runtime
verified_at: 2026-10-03
verified_by: "MO-PAID-006 R4c dry run 1: leadership_text_visible returned by the probe, None on 40/40 dom rows until capture.py's row builder copied it (dry run 2: 40/40 equal to leadership_text)"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "mockups/evidence/mo-paid-006-dossier-page/capture.py"
confidence: verified
---

The row builder is a deliberate allow-list (it keeps raw probe noise out of the committed receipt), so the trap is structural, not a bug to remove: a probe key is a measurement only once the builder copies it. The same tool pins its own sha256 into the manifest (`tool.module_sha256`), so the second edit also forces a full recapture — see `DSC:A-CAPTURE-TOOL-EDIT-REQUIRES-A-RECAPTURE-BECAUSE-THE-MANIFEST-PINS-THE-MODULE-SHA`.
