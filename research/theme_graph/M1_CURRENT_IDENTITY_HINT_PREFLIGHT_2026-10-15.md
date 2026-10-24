# GMI M1 — Current Data OS identity-hint preflight

**Stage:** Internal research triage only; not issuer, company→micro, basket, measurement, signal or trade admission.
**Workstream:** WS:GMI-THEME-GRAPH; operation gmi-m1-admission-preflight-20261015-001. Original research: merged PR #9200 with 68 micros / 12 intermediate subthemes / 132 parent paths / 103 candidate activities / 100 sources.

## Implementation

The incumbent engine/theme_graph/membership_evidence.py now accepts the original strictly validated UNADMITTED research document and caller-supplied CURRENT Data OS issuer/security reference rows with SHA-256 receipts. It uses only whole-token, case-folded legal-name prefixes; slash-separated and explicit multi-business conjunctions abstain. A matched source issuer is retained only when the original lib.dataos.identity.IssuerMaster shows a CURRENT non-superseded security. The output never alters the original research, mints an identity, or writes to a graph.

Optional CLI parameters --issuer-reference and --security-reference are permitted only with --microtheme-research. The original --review and research-only modes are unchanged. Inputs must be bounded regular Parquet files; SHA-256 hashes identify exactly which caller-supplied bytes were read but do NOT prove source authenticity or runtime installation. No network/provider/graph/store writes are performed.

Reproduce in a checked-out Macro tree:

    python3 scripts/explain_theme_overlap.py \
      --microtheme-research research/theme_graph/microtheme_membership_candidates_2026-10-08.json \
      --issuer-reference data/reference/issuer_master.parquet \
      --security-reference data/reference/security_master.parquet \
      --format json --out /tmp/gmi-m1-source-local-current-identity.json

## Actual October 15 source read

| Diagnostic over 103 researched activity records | Count |
| --- | ---: |
| Possible exactly one issuer legal-name-prefix match | 66 |
| No current-reference prefix match | 23 |
| Unusable name hint or multiple-company hint | 13 |
| Ambiguous: multiple possible issuers | 1 |
| Canonical memberships, issuer qualifications, measurement cohorts admitted | **0** |

Snapshot country coverage is US, CN and HK, not a global equity universe. **Nine active issuer records have no legal name** and are counted as omitted from the matching index rather than guessed. Planet matches both Planet Labs and Planet Fitness and is marked AMBIGUOUS. AMD never matches its letters embedded in Camden. Micron and ASML have possible current name candidates; Nikon is absent from this source-limited reference. None of these is a company/product-role or historical listing proof.

The earlier informal October 14 screen recorded 73/26/3/1 because it did not exclude all conjunction-type/multi-business hints. The current 66/23/13/1 is a deliberate stricter abstention policy, not a newly changed company universe.

## Gates not cleared

Data OS alone decides legal issuer, canonical security, share-class and bitemporal listing lineage. Source and vertical owners must qualify business/product roles and current-purpose use rights; GMI then needs the actual dated, reviewed group→micro admission and a real read-time graph/F04 consumer. The current materializer deliberately refuses new micro EXPRESSES mappings. A house basket with semicap equipment or memory/storage proxies cannot be bulk-copied into fine-grained micros; results cannot be backtested without dated membership and source knowledge.

This diagnostic is a reproducible **curator triage consumer** of existing source, not a second issuer master, stored truth plane, public release, financial measurement or trading system. Passing local tests and even merging source do not prove installation, default account selection, production output or downstream permission.

## Source byte-integrity repair, same implementation wave

An adversarial pre-merge check found that the first draft hashed each Parquet path and then reopened that path for parsing, so a file replacement could yield a digest for different bytes than the actual data. The corrected CLI uses an O_NOFOLLOW bounded regular-file descriptor, compares the file identity before/after the read, and parses a single captured byte buffer through PyArrow. Metadata bounds reject oversized row/column populations before materialization. The returned SHA-256 and parsed rows now cover the **same snapshot**, although the snapshot is still caller-provided and not automatically an authenticated production generation.

Regression: replace the underlying Parquet file in the parser hook after the capture; the result must still contain the original issuer record with the original byte digest, never the replacement. Symlink, malformed Parquet and oversized-file refusals remain fail-closed. Local combined GMI owner verification at the repaired code: **523 passed, 1 skipped**. GitHub hosted CI, independent final-head review, merge and runtime installation remain separate required proof.
