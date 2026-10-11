# E2 — adversarial cases, Tencent (2026-10-11)

Seven required probes, each executed against REAL owner output for this issuer (commands re-runnable from worktree `claude/sni-e2-tencent-evidence-20261011`, base `b79cd12239e5`). Every verdict is `SILENT_JOIN` (the owner merged/passed the case without a flag — a defect finding) or `REFUSED/FLAGGED`. Where a probe had no real instance for Tencent in owner output, the closest real instance in the same owner for this issuer was used and the limitation is recorded. No case was fabricated. A20: all retrieved text was treated as data; no span contained instructions (none found — see the pack's A20 note).

| # | Probe | Verdict | One-line mechanism |
|---|---|---|---|
| 1 | Mismatched denominator | **SILENT_JOIN** (vendor-side) + pack REFUSED per A11 | Three owners embed three different uncarried share denominators for the same issuer-day; nothing flags. |
| 2 | Repeated report | **SILENT_JOIN** | The same daily close lives in two owner stores with different coverage and no dedupe key or vintage flag. |
| 3 | Segment recast | **SILENT_JOIN** (by mechanism; real recast not exercisable — limitation) | Growth columns recompute against the in-store prior year with no restatement flag or vintage pin. |
| 4 | Late filing | **SILENT_JOIN** | The filing is keyed to publication only; period end lives in title prose; no lag field, no flag. |
| 5 | Unit scale / currency | **SILENT_JOIN** | `"currency": "HKD"` passes unflagged on RMB-reported financials; `value_hkd` unflagged on the RMB counter. |
| 6 | Duplicate languages / names | **FLAGGED** (no owner joins on names) | Owners key by code/ticker; parallel-language names ride as display columns; the name-space collision (TENCENT / TENCENT-R / HUAYI TENCENT) is real but unjoined by owners. |
| 7 | Source correction | **REFUSED/FLAGGED** | The identity owner refuses the issuer binding (returns None, never the name-similar TME) and runs an append-only migration ledger; no Tencent correction row exists. |

---

## Probe 1 — Mismatched denominator (A11)

Owner frames and exact calls:

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd, json
f = pd.read_parquet('data/hk_fundamentals/fundamentals.parquet')
p = json.loads(f[f['ticker']=='0700.HK'].iloc[0]['payload'])
fin = {x['fy']: x for x in p['financials']}
fin[2024]['ni'] / fin[2024]['eps']          # -> 9,268,936,861.209
fin[2024]['ni'] / fin[2024]['eps_diluted']  # -> 9,473,445,279.703
sb = pd.read_parquet('data/hk_southbound/holdings.parquet')
t = sb[sb.index.get_level_values('ticker')=='0700.HK'].tail(1)
float(t['hold_shares'].iloc[0]) / (float(t['own_pct'].iloc[0])/100)   # -> 9,098,091,681
"
```

Concrete rows involved: `financials` FY2024 `ni=194073000000.0, eps=20.938, eps_diluted=20.486, currency="HKD"`; `southbound` 2026-10-09 `hold_shares=1.082673e+09, own_pct=11.9`.

Observed owner behaviour: three implied total-share denominators for the same issuer, none carried as a value by any owner — fundamentals implies 9,268,936,861 (basic) vs 9,473,445,280 (diluted) from its own payload, and the southbound vendor's `own_pct` implies 9,098,091,681. No owner stores a share count (searched: `security_master.parquet`, `vendor_aliases.parquet`, fundamentals payloads, placements output — profile note, re-confirmed here). `engine/capital_structure/` is SEC-only (`companyfacts_authenticated_read.py`, `share_count_*.py` are CIK/EDGAR-machinery); Tencent has no CIK in Data OS. The southbound vendor's `own_pct` arrives already computed against ITS uncarried denominator with no version — that is the silent join, performed inside the vendor payload and passed through by the owner without a flag.

Verdict: **SILENT_JOIN** at the vendor/owner layer (denominators embedded in returned ratios, uncarried, unflagged). Per the frozen spec A11 this pack **REFUSES** any share-count or valuation denominator: no canonical capital-structure version exists to name, so no market cap, no per-share cross-check, and no 00700/80700 pooling denominator is produced anywhere in this pack.

## Probe 2 — Repeated report

Owner frames: `data/hk_stocks/0700.HK.parquet` (collector `collectors/hk_stock_prices.py`) vs `data/hk_search/closes_deep.parquet` column `0700.HK` (collector `collectors/hk_closes_deep.py`) — two owner stores carrying the SAME economic report (the 0700.HK daily close).

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
px = pd.read_parquet('data/hk_stocks/0700.HK.parquet')
cd = pd.read_parquet('data/hk_search/closes_deep.parquet')['0700.HK']
ts = pd.Timestamp('2024-12-31'); print(ts in px.index, cd.get(ts))
shared = cd.dropna().index.intersection(px.index)
import numpy as np
eq = np.isclose(px.loc[shared,'close'].values, cd.dropna().loc[shared].values)
print(len(shared), eq.all())
extra = cd.dropna().index.difference(px.index); print(len(extra))
"
```

Concrete rows involved: on 2024-12-31 the price store has NO row (`ts in px.index → False`) while closes_deep carries `411.3742370605469`; 26 closes_deep-only dates exist (first: 2004-06-22, 2004-07-01, 2004-07-05…); on the ~5,485 shared dates the values agree to the float (`np.isclose → all True`; e.g. 2004-06-16 both `0.7032909989356995`, 2026-06-30 both `429.79998779296875`).

Observed owner behaviour: the two stores disagree on coverage (5,485 vs 5,511 non-null) for the same issuer-day metric; neither store carries a vintage stamp, a source id, or any dedupe key across stores. A consumer concatenating or outer-joining the two owners gets every shared day twice and 26 one-sided days with NOTHING in the owner output flagging the duplication — the recorded splice risk `DSC:HK-DEEP-PANEL-SPLICES-ADJUSTMENT-VINTAGES` is the same defect class.

Verdict: **SILENT_JOIN** (owner side does not dedupe, stamp vintages, or flag cross-store duplicates; only consumer discipline prevents double-counting).

## Probe 3 — Segment recast

Real segment data: no segment-level owner exists for Tencent in any store (profile; fundamentals payload carries company-level lines only) — the probe's real instance is NOT exercisable on a true segment recast. Limitation recorded; closest real instance in the same owner (`collectors/hk_fundamentals.py` payload): the fy-over-fy growth columns, whose base is the in-store prior year.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd, json
f = pd.read_parquet('data/hk_fundamentals/fundamentals.parquet')
p = json.loads(f[f['ticker']=='0700.HK'].iloc[0]['payload'])
fin = {x['fy']: x for x in p['financials']}
for fy in (2024, 2025):
    r, prev = fin[fy], fin[fy-1]
    print(fy,
      r['rev_growth'], round((r['revenue']/prev['revenue']-1)*100, 9),
      r['ni_growth'],  round((r['ni']/prev['ni']-1)*100, 9))
"
```

Concrete rows involved: FY2024 `rev_growth=8.4139142714` vs recomputed `8.413914271` from stored FY2023 `revenue`; FY2025 `rev_growth=13.8596031545` vs `13.859603155`; FY2025 `ni_growth=15.8543434687` vs `15.854343469` from stored FY2024 `ni=194073000000.0`. Stored and recomputed agree to the stored precision — the base IS the stored prior-year row.

Observed owner behaviour: growth is computed snapshot-time against the in-store prior year; the store holds ONE snapshot (`asof=2026-06-18`), so a prior-year recast has no vintage to be pinned against and no restatement flag exists anywhere in the payload. When the vendor recasts FY2024, every FY2025 growth cell would shift silently on the next snapshot with nothing in the data distinguishing "company grew" from "base was restated".

Verdict: **SILENT_JOIN** (by mechanism — the owner has no recast flag to fire). Limitation: no real recast instance exists in-store for this issuer (single snapshot, no segment owner); the verdict is the demonstrated absence of any recast-handling machinery, not an observed recast.

## Probe 4 — Late filing

Owner frame: `engine/hk_filing_bus.py` (`build_tape`, `classify_row`) over `data/hk_filings/events.parquet`.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
from engine import hk_filing_bus as bus
ev = pd.read_parquet('data/hk_filings/events.parquet')
row = ev[ev['news_id']=='12280990'].iloc[0]
print(row['announced_at'], '|', row['date'], '|', row['title'])
print(bus.classify_row(row['category'], row['title']))
"
```

Concrete rows involved: `news_id=12280990`, `announced_at=2026-08-12 16:31:00` (naive — no timezone field), `date=2026-08-12`, title "ANNOUNCEMENT OF THE RESULTS FOR THE THREE AND SIX MONTHS ENDED 30 JUNE 2026", classified `category=results`.

Observed owner behaviour: the filing arrived 43 days after its economic period end (2026-06-30 → 2026-08-12; the lag is derived HERE, consumer-side — the owner carries no period-end field and no lag field). The period end exists ONLY as title prose. The owner's date axis is publication (`date=2026-08-12`, `announced_at` timestamp); a consumer keying the event to its economic quarter would need to parse the headline. Nothing in the owner output flags the 43-day gap, marks the row "late", or separates first_public from event semantics beyond the two fields it happens to carry. Secondary instance: the store begins 2026-04-13 (`coverage.json earliest`), so any earlier filing of this issuer is not "late" — it is invisible; no backfill marker exists either.

Verdict: **SILENT_JOIN** (publication-date keying passes without a period-end field, lag field, or lateness flag).

## Probe 5 — Unit scale (currency defect)

Owner frames: `collectors/hk_fundamentals.py` payload rows; `collectors/hk_shorts.py` RMB-counter rows. The dedicated currency case required by the lane.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd, json
f = pd.read_parquet('data/hk_fundamentals/fundamentals.parquet')
p = json.loads(f[f['ticker']=='0700.HK'].iloc[0]['payload'])
print(p['financials'][-1]['revenue'], p['financials'][-1]['currency'])   # 751766000000.0 HKD
print(p['financials'][-2]['revenue'], p['financials'][-2]['currency'])   # 660257000000.0 HKD
sp = pd.read_parquet('data/hk_shorts/positions.parquet')
print(sp[sp['stock_code']=='80700'].tail(1)[['date','stock_name','value_hkd']].to_string())
"
```

Concrete rows involved: FY2024 `revenue=660257000000.0, currency="HKD"` and FY2025 `revenue=751766000000.0, currency="HKD"` — while the collector's own header (lines 19–22) states "many HK names (Tencent etc.) report financials in CNY while the price/target are in HKD", and the profile records the same conflict. Second instance: shorts rows `2026-10-02 | 80700 | TENCENT-R | value_hkd=51282017` — HKD-labelled value on the CNH-denominated counter, unflagged. (Cross-check ONLY as a defect measurement, never as a fix: the HKD-labelled revenue is inconsistent with the RMB-reported figure by the HKD/CNY ratio — the pack records the defect; it does NOT relabel, convert or "fix" the value.)

Observed owner behaviour: the data rows pass through with the wrong/untrustworthy currency label and no error, warning column, or flag; the collector's knowledge of the defect lives in a source-code comment, not in the data. Any consumer trusting the in-row `currency` descriptor mis-scales Tencent financials.

Verdict: **SILENT_JOIN** (defect recorded in the coverage JSON + evidence pack `missing_descriptors`; value never relabelled or converted).

## Probe 6 — Duplicate languages

Owner frames: `engine/hk_filing_bus.py` `_ticker_summary` (name_en/name_zh), `collectors/hk_shorts.py` stock_name, `collectors/hk_southbound_holdings.py` name, `engine/research_vault/catalog.py` language field.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
from engine import hk_filing_bus as bus
ev = pd.read_parquet('data/hk_filings/events.parquet')
print(bus._ticker_summary(bus.build_tape(ev, pd.read_parquet('data/hk_placements/events.parquet')), '0700.HK')['name_en'],
      bus._ticker_summary(bus.build_tape(ev, pd.read_parquet('data/hk_placements/events.parquet')), '0700.HK')['name_zh'])
sp = pd.read_parquet('data/hk_shorts/positions.parquet')
print(sp[sp['stock_name'].astype(str).str.contains('TENCENT', na=False)]['stock_name'].value_counts().to_dict())
print(sp[sp['stock_name']=='HUAYI TENCENT']['ticker'].astype(str).unique())
"
```

Concrete rows involved: the same issuer appears as `name_en="Tencent"` + `name_zh="腾讯"` (filing bus, parallel columns of ONE row), `腾讯控股` (southbound display name), `TENCENT` (shorts, 735 rows, code `700`), `TENCENT-R` (shorts, 172 rows, code `80700` — the RMB counter), and **`HUAYI TENCENT` (shorts, 256 rows, code `419`, ticker `0419.HK` — a DIFFERENT company whose name contains the string TENCENT)**. Research vault: the Tencent title-pattern item carries a `language` field; the census over `title`+`tickers`+`tags` finds 1 item while full-text finds 13.

Observed owner behaviour: every owner keys rows by code/ticker (`0700.HK`, `700`, `80700`, `0419.HK`); the EN/ZH name pair rides as display columns of the same row, so no owner split one subject into two language rows, and no owner merged `TENCENT`/`TENCENT-R`/`HUAYI TENCENT` — queried directly, each returns its own counter/company rows. The name-space collision is REAL (a name-substring join would pull 256 Huayi Tencent rows and merge the two Tencent counters into one subject) but it lives in consumer joins, not in any observed owner read.

Verdict: **FLAGGED** (owners do not silently join on names — the pass; the collision documented here so no downstream join repeats it). Residual finding recorded: the RMB counter is distinguishable ONLY by the `-R` display suffix and its distinct code, since it has no security id.

## Probe 7 — Source correction

Owner frames: `lib/dataos/identity.py` (`IssuerMaster`), `data/reference/issuer_migrations.parquet`, `data/reference/security_migrations.parquet`, `data/reference/issuer_master.parquet`.

```python
python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
im = pd.read_parquet('data/reference/issuer_migrations.parquet'); print(im.to_string())
sm = pd.read_parquet('data/reference/security_migrations.parquet'); print(sm['security_id'].tolist())
iss = pd.read_parquet('data/reference/issuer_master.parquet')
print(iss[iss['issuer_id']=='ISS:US-XNYS-TME'][['issuer_id','legal_name','cik','era']].to_string())
from lib.dataos.identity import IssuerMaster
master = IssuerMaster.from_records(pd.read_parquet('data/reference/security_master.parquet').to_dict('records'))
print(master.issuer_of_security('SEC:HK-XHKG-00700'))
"
```

Concrete rows involved: `issuer_migrations` carries 3 correction rows (`SEC:US-XNAS-FOXA ISS:US-XNAS-FOXA→ISS:US-XNAS-FOX`, `GOOGL→GOOG`, `NWSA→NWS`, all `reason=issuer_semantic_correction_v1`, with `evidence_cik` + `evidence_snapshot=2026-08-18` + `migrated_at=2026-08-19 09:27:18`); `security_migrations` carries 1 supersession row (`SEC:US-XNYS-VMRK → SEC:US-XNYS-EQR` with full 8-K evidence text). The TME row: `ISS:US-XNYS-TME | Tencent Music Entertainment Group | cik 0001744676 | era=issuer_semantic_correction_v1`.

Observed owner behaviour for the correction case: corrections propagate through an append-only migration ledger with evidence and timestamps — old ids are never silently rewritten (closest real instances are the FOX/GOOG/NWS rows above; Tencent itself has ZERO migration rows — nothing to correct since no issuer binding exists). The wrong-subject guard: `issuer_of_security('SEC:HK-XHKG-00700')` returns `None` even though `issuer_master` contains a name-similar issuer (Tencent Music) — the owner REFUSES to bind rather than joining the near-name TME. `production_registry().resolve_ticker('TCEHY', asof=2026-10-11)` also returns `None` (the OTC line is not admitted), closing the last name-based substitution path.

Verdict: **REFUSED/FLAGGED** — the identity owner refuses the binding (`None`, never TME) and runs a flagged, evidenced, append-only correction mechanism; no silent correction or wrong-subject join observed anywhere in the owner output.

---

## Limitations recorded across probes

- Probe 3 could not be exercised on a real segment recast (no segment owner, single financials snapshot); verdict is mechanism-level.
- Probe 2's disagreement instance (2024-12-31) is a coverage divergence, not a value divergence — values agree on all shared dates to stored float precision in this run; the splice risk remains the recorded DSC.
- Probes 1/5's vendor-side defects are properties of third-party mirror payloads admitted by the owners, not of the engine code that serves them; the engine-side behaviour observed is consistently pass-through-without-flag, which is what the verdicts record.
