# GMI CN identity: why the bound THS-theme members are NOT_IN_MASTER (census and gap, 2026-11-02)

Status: **gap statement. No producer change, zero rows closed.** This note records
the census, the mechanism, the inventory of dated naming sources, and the two
reachable resolutions. Both resolutions are outside the commissioning seat's
write and rights bounds, so the seat has to decide.

Artifacts:
- `research/theme_graph/gmi_cn_identity_20261102/census_cn_identity.py` is a
  read-only census. It runs every member through the resolver's own
  `_resolve_node_row` in both modes.
- `research/theme_graph/gmi_cn_identity_20261102/census_2026-11-02.json` holds
  one row per theme, member node and cause.

## 0. Answer

- **The "237" is 237 bound THS themes, not 237 company nodes.** It comes from
  PR #10627 at head `dedd4b68`: "membership receipts AVAILABLE 237; every member
  resolves NOT_IN_MASTER". Those themes have **919 distinct CN company-node
  members** and **3,532 theme-member pairs**. Zero themes have any member that
  resolves.
- In HISTORICAL mode at asof `2026-11-02`, every member is `NOT_IN_MASTER`:

  | cause | member nodes | theme-member pairs |
  |---|---:|---:|
  | Master row exists, but there is no dated alias row from any eligible vendor (`no_dated_eligible_alias`) | **917** | 3,526 |
  | No master row at all (`no_master_row`) | **2** | 6 |
  | Dated eligible row exists but does not cover the asof | 0 | 0 |
  | Cross-market mismatch | 0 | 0 |
  | Other | 0 | 0 |

  All 917 resolve in CURRENT mode (`vendor_alias` via the undated
  `theme_graph_native` space). The two `no_master_row` nodes are
  `co:cn:300229.SZ` and `co:cn:600059.SS`.
- **There is no lawful dated naming source within the commissioned provider
  bounds.** Those bounds are the 2026-10-23 Chairman attestation: the Yahoo/yfinance
  route, Massive/Polygon, Tiingo and ThetaData. The one genuinely dated,
  contemporaneous primary source in the repo is CNInfo, and CNInfo is outside
  that list (section 3).
- The canonical coverage proof reads **`cn NOT_IN_MASTER/canonical` = 2 before and
  2 after**. That proof measures the persisted CURRENT-mode sidecar, so it
  **cannot observe the 917 class at all**. Even a successful dated-alias fix would
  not move it. The instrument for this gap is the census script above, or the
  #10627 adapter's own receipts.

## 1. Mechanism

These findings were checked against `origin/main` `3b9cacba`.

- **Rule 5** (`engine/theme_graph/identity_resolution.py:462`) is the exact match
  on `inception_code`. It is asof-invariant in both modes. The CN
  `inception_code` is the bare 6-digit code (D2B2 spec section 3.1), while the
  node symbol carries a suffix (`000967.SZ`, `600xxx.SS`). The two never compare
  equal.
- **Rule 6** (`:483`), in HISTORICAL mode, accepts only DATED rows, and only from
  vendors outside `{store, yahoo_fetch}` (`:364`, `_historical_alias_resolve`
  `:367`) and outside `polygon`.
- **The CN alias rows are all one kind.** Every CN row in
  `data/reference/vendor_aliases.parquet` is `theme_graph_native`: XSHE 499 and
  XSHG 520, all with `valid_from` and `valid_to` null. They are minted at
  `scripts/build_security_master.py:1773`, and the producer documents them as a
  current-catalog space (`:327-335`).
- **Rule 7** (`:532`) therefore returns "no dated alias evidence at asof;
  current-catalog rows exist but are not historical-naming evidence".
- **The US comparison is decisive.** Of the 1,211 US nodes RESOLVED in
  HISTORICAL mode, **1,209 resolve via `master_inception_exact`** (rule 5) and
  only 2 via a dated `vendor_alias`. US historical identity therefore does not
  rest on dated naming evidence either. It rests on the asof-invariant canonical
  code, with dated `RENAME_EVENTS` rows covering renames.
- **The CN refusal is a spelling asymmetry at rule 5,** combined with D2B2
  frozen boundary 7 ("Current-identity semantics only unless a separately
  receipted historical source supports a dated boundary"). It is not an evidence
  defect specific to these 917 issuers.
- The 147 HK nodes are in the same structural class: HISTORICAL `NOT_IN_MASTER`,
  CURRENT `RESOLVED`. They are not THS members, so they are outside this census
  population.

## 2. Census command

```
PYTHONPATH=. python3 research/theme_graph/gmi_cn_identity_20261102/census_cn_identity.py \
    2026-11-02 research/theme_graph/gmi_cn_identity_20261102/census_2026-11-02.json
```

- It needs `data/` (`python3 scripts/worktree_sparse.py add data` in a sparse
  tree).
- The theme binding mirrors #10627's `_expressed_basket` rule, which is not on
  main. Exactly one live `basket:baskets_china_ths:*` node must EXPRESS the
  `ltheme:ths:*` node, and a basket expressing two concepts binds neither.
  Members come from `engine.basket_membership_pit.members_asof`; all 237 are
  `pit=True`, basis `pit_snapshot`.
- Theme membership is used **only to enumerate** the population. It is never
  identity evidence (gate #2).

Census over all company nodes, from the same resolver:

| mode | state |
|---|---|
| HISTORICAL | cn NIM 1021, hk NIM 147, ca NIM 167, us RESOLVED 1211 / NIM 27 / DEFERRED 2 / ENTITY_TYPE_CONFLICT 1, intl UNSUPPORTED 233 |
| CURRENT | cn RESOLVED 1019 / NIM 2, hk RESOLVED 147 |

## 3. Inventory of candidate dated naming sources for CN

| source / vendor space | emitted for CN today | fetch | dating carried | verdict |
|---|---|---|---|---|
| `yahoo` (historical-naming space) | no | `collectors/china_stock_prices.py`, `collectors/china_stock_raw.py` (yfinance; per-ticker `data/china_stocks*/<code>.S[SZ].parquet`) | Bar dates only (`000967.SZ` from 2000-03-30). These are history restated under today's symbol, which is the trap documented at `lib/dataos/identity.py:808-822`. Contemporaneous Yahoo receipts exist only for the 9 sector-ETF cohort (`lib/store.py:40`, `collectors/base.py:598-716`). | **No genuine dated evidence.** Building on it would fabricate dates. |
| `membership` | no | universe seeds | Current keys only; no dated CN seed record | none |
| `ledger` | no | `quality.ticker_key_migrations` | US rename events only | none |
| `theme_graph_native` | **yes**, 1019 rows | GMI node spelling (`mint_cn_hk_rows`, `:1677`) | Undated. Current-catalog by the producer's own definition. | Not historical evidence, by law |
| Tencent tail repair (`collectors/china_stock_tencent.py`) | no | recent-tail bars | Bars only | Not attested; no naming dates |
| THS baskets / `ths_concepts` / `finviz_themes` | n/a | | | **Forbidden** (gate #2) |
| **CNInfo** `data/china_filings/filings.parquet` | read by this producer for admission (`load_cninfo_evidence`, `:1572`) | `collectors/china_filings.py`: forward-only 3-7 day pulls, `_collected_at` | `publish_ts` 2026-05-07 to 2026-11-02; 121,726 rows; 5,582 codes; **0 codes bound to more than 1 `org_id`**. Contemporaneous, so the dates are genuine. | Lawful per the house registry: "Y", public regulatory disclosure (`research/china_alpha_intelligence/RIGHTS_REGISTRY.md:41`, `docs/QUAL_DATA_COMPLIANCE.md` section 1.4). D2B2 boundary 5 also names CNInfo as a primary source. **Not on the 2026-10-23 attestation list, which this commission bounds by**, so it was not used. |

## 4. Residual gaps and reachable resolutions

**G1: 917 nodes / 3,526 pairs. CN HISTORICAL identity.** Both resolutions need a
seat decision and lie outside this commission's write scope.

- **R1. Resolver change (structural; closes every asof; symmetric with US).**
  - **Change:** give rule 5 a venue-qualified form for CN/HK. Map the node symbol
    `<code>.SZ|.SS|.HK` to the bare `inception_code` plus a venue, and match
    `master_by_code[code]` only when the master `listing_key` venue
    (XSHE/XSHG/XHKG) equals the suffix venue. Keep the existing
    `_cross_market_mismatch_reason` refusal.
  - **Owner:** `engine/theme_graph/identity_resolution.py` (D2A, F2 two-clock
    reviewer), plus a D2B2 boundary-7 amendment.
  - **Assumption it makes:** that the code maps to the same security across
    time. US rule 5 already makes the same assumption, and US guards it with
    `RENAME_EVENTS`. A-share codes persist through renames, and the CNInfo window
    shows no code reused across `org_id`s. That window is only 6 months, though,
    so an identity-scoped CN reuse fence would be the companion obligation.
- **R2. Producer change: dated rows from CNInfo.**
  - **Space:** create a new historical-clock vendor space, for example
    `cninfo_disclosure`. Register it in
    `config/dataset_registry.yml::reference.vendor_aliases` (`:431`) and pin it
    in `tests/test_dataos_security_master.py`.
  - **Symbol:** `vendor_symbol` is the node spelling derived from
    `(sec_code, cn_board)`. CNInfo itself never writes the suffix, so the space
    must declare that its spelling is venue-normalized.
  - **Dates:**
    - `valid_from` is the earliest `publish_ts` per code: a genuine first
      observation, truncated on the left by the collection start.
    - `valid_to` is open. That is the same right-open convention as the new-side
      rows of the existing `RENAME_EVENTS`.
  - **Evidence:** the input digest of `filings.parquet`.
  - **Effect:** closes the 917 for asof dates on or after each code's first
    observation (all on or before 2026-10-29). Any asof before 2026-05-07 is
    still refused, which is correct.
  - **Two decisions it needs:**
    1. a seat ruling that the house rights registration covers this use outside
       the 10-23 list;
    2. a D2B2 boundary-7 acceptance that CNInfo is the "separately receipted
       historical source".
  - **Do not:** put these dated rows into `theme_graph_native`. That would mix
    two clocks in one space.

**G2: 2 nodes / 6 pairs. No master row.**
- **Nodes:** `co:cn:300229.SZ` and `co:cn:600059.SS`.
- **Evidence:** the committed CNInfo store has zero rows for either code, by code
  and by issuer name. `data/reference/_receipt.json` `china_hk_admission` records
  both as `no_committed_primary_source_evidence`.
- **Cause:** not diagnosed here. Both are expected to file periodic reports, so
  six months with zero rows points to a collection-coverage gap in
  `collectors/china_filings.py`. One candidate is the per-exchange time budget
  `_EXCHANGE_BUDGET_S` (`:157`).
- **Resolution:** this belongs to the china_filings collector lane. Once a filing
  is observed, the next `build_security_master.py` run admits both nodes in
  CURRENT mode with no code change. HISTORICAL mode then still falls under G1.

## 5. What this note does not do

- It makes no edit to the producer, resolver, coverage proof, crosswalk or any
  #7870 / #10627 / #10636 / #10638 path.
- It closes no row with undated, current-catalog, theme-membership or fabricated
  evidence.
- It makes no new network fetch.
