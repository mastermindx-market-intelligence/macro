# E1 — Alibaba adversarial cases (2026-10-11)

Seven required probes, each executed against REAL owner output produced in this run
(as-of 2026-10-11, repo `b79cd12239e5`). Verdict vocabulary: **SILENT_JOIN** = the owner
merged/passed the case without a flag (a defect finding); **REFUSED/FLAGGED** = the owner
refused, or keeps the case explicit/distinguishable (pass). Where no real Alibaba instance of
the case exists on main, the probe was run on the closest real instance in the same owner for
this issuer and the limitation is recorded — nothing is fabricated. Retrieved document text is
treated as data (A20); no instruction-like span was acted on (see A20 note at the end).

| # | probe | verdict |
|---|---|---|
| P1 | mismatched denominator | **owner-side SILENT_JOIN (bvps/eps embed uncarried share denominators) + pack REFUSED per A11** |
| P2 | repeated report | **FLAGGED** in filings (distinct events preserved) / **SILENT_JOIN (structural)** in financials (single slot per period, no correction version) |
| P3 | segment recast | **SILENT_JOIN (structural)** — owner has no segment dimension to recast |
| P4 | late filing | **FLAGGED** (first-public announced_at preserved; no backdating) AND **SILENT_JOIN** (structural: no period-end/filing-lag field; period only in title prose) |
| P5 | unit scale / currency | **SILENT_JOIN** — the HKD-on-CNY currency defect passes unflagged |
| P6 | duplicate languages / dual counters | **SILENT_JOIN** on the ticker column (counter folded) / **FLAGGED** at the raw stock_code field |
| P7 | source correction | **FLAGGED** — corrections carried as explicit era/receipt rows; no silent rewrite |

## P1 — Mismatched denominator (A11)

- Owner calls/frames: `data/capital_structure/discovery.parquet` (688e781e91b0, 24,262 rows) and
  `data/capital_structure/event_versions.parquet` (52446066643d, 14,007 rows), filter
  cik/ticker `1577552|BABA` → **0 rows / 0 rows**; `data/reference/security_master.parquet`
  issuer_master row `n_securities = 1` (a listing count, not a share count);
  `data/hk_fundamentals/fundamentals.parquet` 9988.HK payload line `bvps 55.683165380648`
  (a per-share value whose denominator no owner states); `data/hk_southbound/holdings.parquet`
  `hold_shares 1,986,384,146` on 2026-10-08 AND 2026-10-09 (Southbound-portfolio shares only,
  not shares outstanding).
- Concrete case: the HK$80bn placing of NEW SHARES was proposed 2026-08-23, priced 2026-08-24
  and completed 2026-08-26 (hk_filings news_ids 12295308 / 12295380 / 12300619) — a real
  share-count change — and no owner carries a share-count series that would reflect it
  (placements store has 0 rows for this counter; capital_structure has 0 BABA rows).
- Observed behaviour: no owner provides a canonical capital-structure version or the corporate
  actions it binds for Alibaba; per-share owner values (bvps, eps) embed unstated denominators
  from different vintages.
- Verdict: **owner-side SILENT_JOIN (bvps/eps embed uncarried share denominators) + pack REFUSED
  per A11** — the owner-side SILENT_JOIN is the defect finding (per-share values carry unstated
  denominators from different vintages and no owner flags it); the pack side refuses: every
  share-count/valuation denominator for Alibaba is refused under A11; no denominator is derived,
  assumed or joined.

## P2 — Repeated report

- Owner call/frame: `engine.hk_filing_bus._load_filings()` (3,906 rows) +
  `classify_row`; duplicated-id scan `fil['news_id'].duplicated()`.
- Concrete rows: (a) the placing sequence 12295308 (2026-08-23 18:06) → 12295380 (2026-08-24
  06:04) → 12300619 (2026-08-26 19:23): three announcements about ONE action; the owner keeps
  three distinct rows with distinct news_ids and announced_at timestamps and the classifier
  labels each independently (`mandate`, dilution_flag True) — no merge, no dedupe: **FLAGGED**
  (events remain distinguishable). (b) The store DOES contain repeated ids: 18 rows / 9
  duplicated news_id values (e.g. 12187990 ×2, 2186.HK general_mandate 2026-06-03) — the owner
  preserves both rows without a duplicate flag; downstream consumers must dedupe on news_id
  themselves (limitation: none of the 9 is an Alibaba row; closest real instance in the same
  owner, recorded per packet rules). (c) financials frame: the 9988.HK payload has exactly ONE
  slot per fy (fy2020..fy2026, 7 lines) and no correction_version column — by contrast the SEC-side
  owner `data/capital_structure/event_versions.parquet` HAS a `correction_version` column, so
  the HK financials owner is structurally unable to hold two vintages of one annual report; a
  corrected refiling would overwrite or silently stack.
- Verdict: filings **REFUSED/FLAGGED** (distinct events preserved; no silent merge);
  financials **SILENT_JOIN (structural)** — single-version store, no real amended-annual
  instance exists for this issuer on main (limitation recorded).

## P3 — Segment recast (A09)

- Owner call/frame: `data/hk_fundamentals/fundamentals.parquet` 9988.HK payload
  (`json.loads(payload)`), all 7 annual lines inspected.
- Concrete rows: every fy line carries only consolidated keys (revenue, ni, gross_profit, eps,
  eps_diluted, bvps + ratios); there is NO segment dimension, NO restatement marker, NO
  prior-period comparative column, and no second Alibaba source on main to cross-check a recast
  against (FIF/capital_structure have 0 BABA rows — C13).
- Observed behaviour: the owner cannot EXPRESS a segment recast (nothing to merge it into), so
  a recast or redefinition between fy labels would replace values invisibly; the fy label
  convention itself is undeclared by the owner (profile: "fiscal year ends March; fy label
  convention undeclared"), so even period identity is unverifiable from owner fields.
- Verdict: **SILENT_JOIN (structural)** — a real recast would pass without a flag.
- Limitation: no real recast instance for this issuer exists in owner output on main; the probe
  was run on the real payload structure (the closest real instance). A09 consequence recorded in
  the pack: financials.hkd_9988 stays PARTIAL and no cross-period or cross-basis number is
  derived in this pack.

## P4 — Late filing

- Owner call/frame: `data/hk_filings/events.parquet` row news_id 12157537
  (`classify_row` via engine/hk_filing_bus.py).
- Concrete rows: FY2026 annual results (fiscal year ended March 2026, per profile convention
  note) announced `announced_at 2026-05-13 17:30:00`, `date 2026-05-13` — roughly six weeks
  after the fiscal period end; interim/other categories show the same pattern store-wide.
- Observed behaviour: the owner records first-public time (HKEX release timestamp) and keys the
  event by announcement date; it never folds a late announcement into the fiscal period it
  reports on, and it carries no expected-deadline field — lateness is therefore detectable
  downstream from owner fields alone, but is not flagged by the owner.
- Verdict: **FLAGGED (first-public announced_at preserved; no backdating) AND SILENT_JOIN
  (structural: no period-end/filing-lag field; period only in title prose)** — first-public is
  preserved and no period is silently attributed (FLAGGED), but the owner carries no
  period-end/filing-lag field: the fiscal period appears only in the announcement's title prose,
  so lateness is detectable downstream yet never owner-flagged (structural SILENT_JOIN). The
  pack does not infer a deadline — that would break the descriptor law.
- A07 cross-check: announced_at 2026-05-13 ≤ as-of 2026-10-11 for every row carried; no
  post-cutoff information was used in any then-known view.

## P5 — Unit scale / currency

- Owner call/frame: `data/hk_fundamentals/fundamentals.parquet` payload rows for 9988.HK and
  (control) 0700.HK; collector contract `collectors/hk_fundamentals.py:19-21` (3895bcd52d21).
- Concrete rows: all seven 9988.HK annual lines carry `currency: "HKD"` (fy2026: revenue
  1023670000000.0, ni 103592000000.0 labeled HKD) while the collector's own header states many
  HK names (Tencent etc.) report financials in CNY with price/target in HKD, and that PE/PB are
  deliberately NOT computed for that reason; the 0700.HK control row is ALSO labeled "HKD",
  confirming the label is store-wide vendor metadata, not an issuer fact.
- Observed behaviour: the data row passes the currency label through with no in-row flag; the
  contradiction is visible only by reading the collector header — a consumer keying on the
  recorded currency would silently mis-scale every financial value by the HKD/CNY relation.
- Verdict: **SILENT_JOIN** — defect finding. Carried in the pack: financials.hkd_9988 PARTIAL,
  correction/refusal state names the defect; values never relabelled, converted or "fixed".
- Secondary instance (explicit, for contrast): `data/hk_shorts/positions.parquet` rows for
  stock_code 89988 (RMB counter, stock_name "BABA-WR", e.g. 2026-10-02 value_hkd 11428560)
  carry HKD values on an RMB-counter subject — here the column NAME declares the unit
  explicitly, so this instance is **FLAGGED/explicit**, not silent.

## P6 — Duplicate languages / dual counters

- Owner call/frame: `data/hk_filings/events.parquet` (raw field) vs
  `engine.hk_filing_bus.build_tape()` output (normalized field), rows for this issuer.
- Concrete rows: all four 9988 events carry `stock_code "09988<br/>89988"` (HKD and RMB
  counters in one announcement — the dual-counter listing announces once, in both counter
  languages) but the normalized `ticker` column is `9988.HK` only; build_tape's 9988.HK
  selection returns the same rows under the HKD ticker alone.
- Observed behaviour: the raw store preserves BOTH counters (good), but the owner's own
  normalization folds the joint announcement onto the HKD counter key; a consumer keying on
  `ticker` silently attributes dual-counter events to the HKD counter and never sees the RMB
  counter, and cannot re-split without the raw stock_code string.
- Verdict: **SILENT_JOIN** on the ticker normalization (defect finding for RMB-counter
  attribution); the raw `stock_code` field itself is **FLAGGED** (both counters explicit).
  Contrast (owner does it right elsewhere): `data/hk_shorts/positions.parquet` keeps the
  counters distinct natively (BABA-W vs BABA-WR, stock_code 9988 vs 89988).

## P7 — Source correction

- Owner calls/frames: `data/reference/issuer_master.parquet` (era field),
  `data/reference/issuer_migrations.parquet` (ddef55b56231, 3 rows),
  `data/reference/security_migrations.parquet` (b2aae9179179, 1 row),
  `data/capital_structure/event_versions.parquet` (`correction_version` column),
  `data/reference/vendor_aliases.parquet` (`known_at` column).
- Concrete rows: the BABA issuer identity exists ONLY through a recorded correction era —
  issuer_master row `era = issuer_semantic_correction_v1`, `evidence_source sec_company_tickers`,
  `evidence_snapshot 2026-08-18` (registry `config/identity_seams.yml:71,316`); migration
  ledgers queried for Alibaba: issuer_migrations → 0 rows, security_migrations → 0 rows (no
  pending or superseded correction for SEC:HK-XHKG-09988, SEC:US-XNYS-BABA or 89988).
- Observed behaviour: corrections in the identity axis are carried as explicit, append-only
  receipt rows and named eras — never as silent rewrites; the HK counter's missing issuer link
  is carried as an explicit owner state (`issuer_state NO_ISSUER_EVIDENCE`), not as an absent
  column. Gaps recorded honestly: `vendor_aliases.known_at` exists as a column but is empty on
  all five Alibaba alias rows, and the financials owner has no correction mechanism at all
  (see P2).
- Verdict: **REFUSED/FLAGGED** — the correction path is explicit and auditable where it exists;
  no silent source correction observed in any consulted Alibaba row.

## A20 note (retrieved text = data)

Consulted owner outputs contain third-party prose (HKEXnews headline text, research-vault
summary_points, qledger falsifier text, forex desk headlines). All of it was treated as
untrusted data: no span was acted on as instruction, and no prose was copied into this pack
beyond short factual headline/subject strings needed as evidence (news_ids, titles as
recorded, names). No instruction-like span addressed to a processing agent was found in the
consulted rows.
