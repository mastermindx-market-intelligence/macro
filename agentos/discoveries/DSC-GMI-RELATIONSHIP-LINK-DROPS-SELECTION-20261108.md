---
key: GMI-RELATIONSHIP-LINK-DROPS-SELECTION-20261108
claim: >
  At Macro 338a10852dcefa5d2bd07e5c6be0955c2b1e83fd, issuer relationship links target bare
  gmi-relationships.html while its detail renders model.edges[0], so the current
  presentation path does not bind the relationship selected on an issuer page.
falsifier: >
  Read the same pinned templates and gmi.js, or a later qualified repair, and prove that
  an issuer link carries its existing relationship_key into destination selection;
  exercise two different issuer/relationship pairs and an absent key without first-edge fallback.
so_what: >
  Extend the incumbent GMI builder/model/templates and gmi.js to resolve relationship_key
  within package_id/package_sha256 before adding transition motion or claiming exact
  evidence navigation; preserve source/package clocks and existing programme holds.
kind: landmine
verified_at: 2026-11-08
verified_by: >
  GitHub exact-pin reads at 338a10852dcefa5d2bd07e5c6be0955c2b1e83fd:
  templates/gmi_issuer.html.j2:200-205; templates/gmi_relationships.html.j2:119-125;
  templates/gmi.js; relationship payload blob 17f4a21c8016907358303b8308d5f36bff6237b2.
scope:
  - templates/gmi_issuer.html.j2
  - templates/gmi_relationships.html.j2
  - templates/gmi.js
  - scripts/gmi_explorer/model.py
confidence: verified
---

# Selected relationship identity is lost between issuer and detail

This is a source finding from the 8 November Paper audit. It does not assert a new live-browser incident or claim that a production repair has shipped.

The current records use relationship_key, not edge_id or id. The inspected package has 248 nonempty, package-unique keys, package_id pkg:4aba1d2a658bdff832c5 and package_sha256 455c0b95392e4523bee1aaa483f77fb35ff537bc93080f2c271c2cfc4b64a136. Cross-version key-generation stability was not examined. The package is proposed and its gate, prediction, rank, size and trade flags are false.

The model preserves records and the package envelope for presentation. Fix selection through those existing owners. Unknown or removed selection must show its own state, rather than another company's first record. The existing species strip likewise needs a real row-selection handler before it is described as an interactive explorer.

Paper GMI file 01M5H6EARN9YHQV17JC6ZG9BRY, foundations page p-4-0, S04B section 71U-0 and source panel 73G-0 now describe this contract. Full audit, proof and B1 acceptance cases are in [the audit package](../../research/design_candidates/paper_audit_20261108/README.md).

This discovery does not replace WS:GMI-THEME-GRAPH's acceptance ruler, source owners, natural proof, rights decisions, denied effects or unresolved original-carrier operations.

