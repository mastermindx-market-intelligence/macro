---
key: GMI-CURATOR-ABC-GRAPH-MEMBERSHIP-USE-DELEGATED
question: >
  The three curator questions put to the Chairman on 2026-10-22, now delegated
  to the assigned GMI seat. (A) May the C01 Micron source-purpose ruling be
  revised to add graph_membership_use (internal graph use only, no display, no
  redistribution, same source hash)? (B) For EDGAR-derived relationship facts,
  are derived facts with a filing citation public while verbatim filing excerpts
  stay entitled-only? (C) Notice: the seat acts as curator and signs ratification
  receipts itself.
answer: >
  A YES: a revision ruling grants graph_membership_use for exactly the one
  ratified C01 proposal over the same source bytes, with display and
  redistribution false. B CONFIRM: a relationship fact derived from an EDGAR
  filing may be shown at the public display tier with its filing citation
  (form, accession, filing date, issuer); verbatim filing text beyond that
  citation stays entitled-only. C NOTED: the seat curates and signs ratification
  receipts, as it already did for actprop:287edbf7e04b8aba873b7493.
rationale: >
  The Chairman explicitly handed these questions to the seat on 2026-11-02 ("For
  Curator ABC and Graph membership use, you should make the decision for me").
  A is strictly narrower than the fact-only paid_product_display the Chairman
  ruled covered for the same bytes on 2026-10-11: internal graph membership adds
  no audience, quotation, magnitude, ranking, sizing or trade authority. B keeps
  the existing derived-fact/verbatim split that the relationship envelope
  already displays and asserts no vendor licence. C only describes a role the
  seat already holds under the 2026-10-21 commission.
alternatives:
  - option: Keep A/B/C as an EXACT_HUMAN_GATE and keep asking the Chairman
    why_not: The Chairman delegated exactly these questions; re-asking is the owner-wait the 2026-10-24 and 2026-11-02 rulings forbid.
  - option: A NO (no graph use until a licence document is inspected)
    why_not: The 2026-10-11 ruling already covers a wider use of the same bytes; refusing the narrower internal use protects nothing and leaves the activity fold empty.
  - option: Widen A to every C01 fact, edition or vendor
    why_not: Only one proposal is curated and ratified; any other fact still needs its own curation and ruling.
  - option: CHANGE B (publish verbatim excerpts, or hide derived facts)
    why_not: Publishing verbatim text adds redistribution risk for no product gain; hiding cited facts discards public-record evidence the envelope already shows.
evidence:
  - "Chairman 2026-11-02 delegation in seat 6f14c2da-02a9-467e-9f37-7c2ebaccfe09: For Curator ABC and Graph membership use, you should make the decision for me"
  - "research/theme_graph/issuer_disclosures_20261011/C01_GRAPH_MEMBERSHIP_USE_RULING.json sha256 1e90a8d558bb4117050dc18f4edcc0f0a536efd1809bb3d782f8c84ad58297da"
  - "revises research/theme_graph/issuer_disclosures_20261011/C01_CHAIRMAN_SOURCE_PURPOSE_RULING.json sha256 5b3fc66029456f38d40358496ba308596751ef7ffae0d3711adb1ab5caa84117 (source and permitted_use copied verbatim)"
  - "engine.theme_graph.activity_history_bridge.qualify_graph_membership_use -> GRANTED, refusals [] for the PROPOSED and RATIFIED rows of actprop:287edbf7e04b8aba873b7493"
  - "python3 scripts/bridge_activity_history.py --recorded-at 2026-11-02T23:50:00Z --dry-run -> APPEND GRAPH_MEMBERSHIP_USE_GRANTED actevt:35da49f7682bb2b5fd2c7779 actmem:dbdf774cb011d26f3c6d6936"
  - "research/theme_graph/activity_curation_receipts/actprop_287edbf7e04b8aba873b7493.json (RATIFIED, signed by seat 6f14c2da; receipt_sha256 d6796b51...)"
affects:
  - "WS:GMI-THEME-GRAPH"
  - "research/theme_graph/issuer_disclosures_20261011/C01_GRAPH_MEMBERSHIP_USE_RULING.json"
  - "data/theme_graph/probation/activity_history_events.jsonl (first real activity fold, written by the bridge after merge)"
  - "EDGAR-derived relationship display tier (relationship_edges/v1 consumers)"
confidence: high
reversibility: easy
decided_by: "GMI Meta-CEO seat 6f14c2da under the Chairman's 2026-11-02 delegation"
decided_at: 2026-11-02
review_by: 2026-12-02
---

The Chairman delegated the curator questions on 2026-11-02, in these words:
"For Curator ABC and Graph membership use, you should make the decision for me".
They stop being a human gate. This record is the decision.

**A: YES.** The revision ruling `C01_GRAPH_MEMBERSHIP_USE_RULING.json` grants
`graph_membership_use` for `co:us:MU` → `theme:hbm_packaging`
(`planned_product_integration`, NVIDIA H200, 24GB 8H HBM3E), for proposal
`actprop:287edbf7e04b8aba873b7493` only, over the same source bytes (sha256
`a7efabf9…`). `display` and `redistribution` are false. The original ruling's
`source` and `permitted_use` are copied unchanged. No licence document was
inspected and none is claimed. The existing validator (unchanged) returns
GRANTED, and the bridge dry-run appends exactly one event.

**B: CONFIRM.** This is a display-tier policy for facts taken from SEC EDGAR
filings. A derived fact (who supplies whom, what was disclosed) may be shown
publicly when it carries its filing citation. Quoted filing text beyond that
citation stays behind entitlement. This applies to no C01 source, because C01 is
a Micron IR release, not an EDGAR filing. It grants no rights to any vendor
feed, and SEC fair-access limits still bind every fetch.

**C: NOTED.** The seat curates and signs ratification receipts under its
commission. A receipt still needs its own evidence check; this note does not
let any other seat sign on the seat's behalf.

Not covered: other C01 facts or editions, other issuers, sources outside the
2026-10-23 commercial attestation, #868's hold, D2E sealing, or any ranking,
sizing or trade authority. An independent reviewer must accept this record
before it merges.
