# GMI M1 — combined research-to-curator readiness

**Operation:** `gmi-micro-curator-readiness-20261016-001` · **Owner:** `WS:GMI-THEME-GRAPH` · **Status:** source-only read-only derived view, **NO member, issuer, group, measurement or trading admission**.

## Product question

What exact evidence is still missing between GMI's 149 researched company/activity roles and a legally source-qualified, dated, curator-ratified canonical microtheme group? This report composes the two existing research documents and the incumbent Data OS CURRENT security/issuer readers. It deliberately creates no new identity database, source capture registry, curation queue, price basket or graph edges.

### Canonical inputs

- Merged GMI microtheme research: 68 microthemes, 12 subthemes, 132 hierarchy edges, 103 original unadmitted activity records and 100 source references from the preserved crosswalk/source pins.
- Merged research addendum: 46 additional unadmitted activity roles, 58 source pointers, 7 negative cases and 7 scope holds, all bound to original TSV input bytes and still lacking rights/authenticity qualification.
- Current Data OS `data/reference/{issuer_master,security_master}.parquet` passed as bounded bytes through the existing `scripts/explain_theme_overlap.py::_read_bounded_reference`. The same SHA-256 bytes feed the parser; the existing `IssuerMaster` is the owner of current issuer→security relationships.

Run from an authorized Macro checkout with the committed Data OS references:

```sh
python3 scripts/explain_theme_overlap.py \
  --microtheme-research research/theme_graph/microtheme_membership_candidates_2026-10-08.json \
  --microtheme-addendum research/theme_graph/micro_member_research_addendum_20261016/research_addendum.json \
  --issuer-reference data/reference/issuer_master.parquet \
  --security-reference data/reference/security_master.parquet \
  --curator-readiness --format json --out /tmp/gmi-micro-curator-readiness.json
```

**This is explicit opt-in only.** The original `--review`, `--microtheme-research`, `--microtheme-addendum` and `--issuer-reference` modes remain unchanged; the old forbidden mixed argument shape still refuses without `--curator-readiness`.

## Real source-local snapshot, October 16, 2026

| Research-to-curator observation | Count |
| --- | ---: |
| Original activity roles | 103 |
| Additional proposed roles | 46 |
| Total role records | **149** |
| Existing canonical micro definitions (no new IDs) | 68 |
| Separate research source references | 158 |
| Distinct source URLs across both entire registers | **157** |
| Distinct URLs linked directly to activity roles | 139 |
| Roles with at least one undated referenced publisher source | **91** |
| Roles without complete day-level publication claims | **99** |
| Current legal-name hint: single possible issuer | 85 |
| Current legal-name hint: no match | 48 |
| Current legal-name hint: unusable | 15 |
| Current legal-name hint: ambiguous | 1 |
| Qualified issuer/micro members, exact admitted groups, graph edges and measurement cohorts | **0** |

These numbers are **search/reference completeness diagnostics**, not economic population denominators. The 85 single-name matches are only lexical hints in CURRENT US/CN/HK Data OS snapshots; none independently proves a legal parent, listing history, product revenues or a public-rights entitlement. A company can supply multiple product activities across several micros but remains one economic issuer. The original 103-role Data OS screen is byte-for-byte identical to its already accepted consumer after extracting common helpers.

Publication dates are model-referenced only and **not authenticated** for a historical knowledge cutoff. Exactly 91 roles have one or more source links with no claimed publication date; this does *not* mean all source links for each role are undated. The remaining eight beyond those 91 have year-only references. Even records with a day-level publisher claim still need full source authentication and source-known clocks.

## Why no parent basket can be silently used as an exact micro cohort

The house inventory currently contains 49 broad baskets. A separate read-only mismatch check of 13 analyst-selected basket/micro proxies, using current security source-local hints only, shows why group names are insufficient:

- `semicap_equipment` versus `lithography_tools`: no shared current ticker hint within this 16-member house roster, while ASML appears in the original lithography evidence outside the basket. That is NOT proof of zero global lithography participants.
- `memory_storage` versus `hbm_packaging`: only MU overlaps the current basket and original issuer-name hints, while non-memory packaging references such as Amkor and ASE are outside. Never count those different roles as equivalent HBM die producers.
- `cybersecurity` spans network, endpoint, cloud and other capabilities. Matching Fortinet/CrowdStrike reference hints does not qualify all cybersecurity basket members for every child micro.
- `nuclear_power` and `obesity_glp1` contain adjacent operators/drug developers whose relationship does not make them nuclear-component manufacturers or peptide API suppliers.

These are read-only negative examples, not approvals/exclusions, because the original research lists are incomplete and the current house baskets lack a point-in-time admission receipt.

## Explicit required owner actions

Every candidate carries machine-readable **next source-owner actions**: verify exact publisher/product stage and permitted use rights; resolve legal entity, security and share-class lineage at knowledge/effective clocks through Data OS; qualify an actual exact source group, independence and historical provenance through its existing owner; and obtain GMI curation ratification under the controlled group→micro endpoint law. If any source is undated, establish its actual publication time before PIT use. If no unique issuer-name hint exists, require real Data OS resolution—not fuzzy ticker guessing.

Only after a valid exact group is admitted may GMI materialize a future dated `basket → micro_theme EXPRESSES` edge and prove the served F04/Terminal human/machine consumer. Existing C0 control intentionally prohibits auto-creating such edges from research or inherited parent baskets. DataOS/rights/curator authority stays with its original owner. **Zero** records here are candidates for Prophet Buy Now, ranking, returns, alerting, sizing or trading based on this worklist.

## Release boundaries

Success on local tests, hosted CI or a source merge means the *internal read-only composition capability* is available in source. It does not prove production installation, live provider source admission, default account selection or served browser outcomes. Keep the original source and addendum validation contracts; a future error or retraction must refuse or preserve correction history rather than silently emit a smaller selected cohort.
