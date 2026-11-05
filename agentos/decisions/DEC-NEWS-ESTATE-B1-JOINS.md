---
key: NEWS-ESTATE-B1-JOINS
question: >
  How do the news object families (qbus_news_store items/revisions/clusters, news_impact
  articles/clusters/provenance, Prophet news events, Chronicle/ontology facts, issuer identity)
  reference one another so that a consumer can follow one report through correction, clustering,
  derivation and publication without a second store, a new id namespace, or a cross-family hash
  comparison?
answer: >
  R1 The canonical cross-family evidence reference is the report key `source:source_item_id`
  (the qbus item_id namespace, identical to news_impact Article.story_id) plus the qbus
  `revision_id` whenever a specific revision is meant. Hash namespaces (`ev2_` cluster ids,
  Prophet `event_key`, `cev-`, `fact_`, `evt_cik`) are never compared across families.
  R2 Cluster ids are owner-local. A consumer that reconstructs clusters locally (news_impact
  cluster_articles) publishes the relation by listing member report keys plus a receipt
  (run_id, policy version, member set); identical ids never imply identical membership.
  R3 news_impact provenance.origin_document_id carries the report key; a revision reference is
  added as an optional field by the contract owner only when the first consumer needs it.
  R4 Per-family clocks stay as they are, each carried with its companion basis field;
  normalization happens at the consumer boundary; no cross-family clock comparison is
  published as a fact.
  R5 Issuer identity resolves ticker to CIK at read time through the existing ticker_cik_ledger
  and issuer ladder; derivatives carry both.
  R6 Derivatives reference (report key, revision_id) and re-check the current revision through
  the store before publication; a superseded revision is published only as superseded.
  R7 Only additive, optional fields on existing contracts; no renames, removals, new stores or
  new id namespaces. Legacy event-log supersede (gap G02) is deferred to the lane that first
  needs it.
rationale: >
  The B1 inventory (macro #10049) and the seat's gap census G01-G15 found that every family
  already carries the report key or can derive it from its member items, while cluster ids are
  minted by different policies per owner (ev2_ in qbus_news_cluster, local reconstruction in
  news_impact) and the Prophet event_key is a hash of a different tuple. Joining on the member
  identity that all owners share, and carrying revision_id only where a revision is meant,
  gives corrections a path through every consumer without inventing a registry. Ruling only to
  the depth the next real consumer (Mastermind get_news/get_intelligence boundary, D2) needs
  follows the Chairman's 2026-10-31 directive; deeper joins wait for the lane that needs them.
alternatives:
  - option: Mint one global news id registry mapping every family's ids
    why_not: >
      A second identity store is forbidden by masterplan section 11 and the Chairman directive;
      it would also have to be kept consistent with four owners' minting policies.
  - option: Treat identical cluster ids across families as the same cluster
    why_not: >
      ev2_ ids and news_impact local clusters are produced by different policies over different
      member sets; equality of ids is coincidence, not membership, and would infer independence
      the corpus law forbids.
  - option: Normalize all family clocks to one canonical field in the stores
    why_not: >
      Rewrites existing contracts and ledgers; the clocks measure different events (observed,
      published, built) and the companion basis fields already disambiguate them at read time.
evidence:
  - "macro #10049 head dabf5c9130d9 — B1_SCHEMA_INVENTORY.md (object families, id namespaces, absent revision join)"
  - "macro #10244 head e16dbdda392f — COMPLETION_MASTERPLAN_2026-10-31.md rows B1/D1 (resolve joins through existing owners; select a real consumer)"
  - "engine/qbus_news_store.py, engine/qbus_news_cluster.py, engine/news_impact/cluster.py at origin/main f2efb8baf983 — item_id/story_id = source:source_item_id; ev2_ cluster ids; local cluster reconstruction"
  - "Seat gap census G01-G15 (2026-10-31; G03 ev2_ vs event_key join via member identity, G11 no revision ref in news_impact contracts, G04/G13 clock collisions, G07/G08 issuer identity, G09 rights drops in derivatives)"
affects:
  - WS:NEWS-INTELLIGENCE-ESTATE-CONVERGENCE
  - WS:PROPHET-NEWS-IMPACT
  - Mastermind get_news/get_intelligence boundary (D2 consumer)
confidence: medium
reversibility: easy
decided_by: fable-meta-ceo
decided_at: 2026-10-31
---

## Operating law

A lane that adds a field to any news contract names the rule (R1-R7) it applies and adds the
field as optional. A consumer that needs a join this record does not cover extends this record
with a dated rule and the first consumer's name; it does not mint an id namespace. The qbus
store remains the only authority on which revision of a report is current; every publication
of a derivative re-reads it (R6).
