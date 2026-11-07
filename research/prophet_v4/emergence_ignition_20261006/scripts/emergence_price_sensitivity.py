#!/usr/bin/env python3
"""Supplemental final-vintage price confound diagnostic; never PIT-admitted evidence."""
import argparse,csv,hashlib,json,math
from pathlib import Path
import analyse_emergence as em
p=argparse.ArgumentParser();p.add_argument('--boards',type=Path,required=True);p.add_argument('--baselines',type=Path,required=True);p.add_argument('--controls',type=Path,required=True);p.add_argument('--price-controls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
price=list(csv.DictReader(a.price_controls.open()));pm={(r['as_of'],r['ticker']):r for r in price}
def number(x):
    try:
        v=float(x);return v if math.isfinite(v) else None
    except (TypeError,ValueError):return None
def supplement(key):
    r=pm.get(key)
    if r is None or r.get('price_control_status')!='OBSERVED' or r.get('price_control_last_date','9999')>key[0]:return {}
    rs=number(r.get('rs_spy_21'));dv=number(r.get('mean_dollar_volume_21'))
    return dict(prior_rs_spy_21=rs,log_mean_dollar_volume_21=math.log(dv) if dv and dv>0 else None)
def rows(path):
    out=[]
    for r in csv.DictReader(path.open()):
        for f in em.BASE_FEATURES:r[f]=number(r.get(f))
        r.update(supplement((r['as_of'],r['ticker'])))
        out.append(r)
    return out
es=rows(a.baselines);cs=rows(a.controls);extra=('prior_rs_spy_21','log_mean_dollar_volume_21')
ec=[r for r in es if all(r.get(f) is not None for f in extra)];cc=[r for r in cs if all(r.get(f) is not None for f in extra)]
bs=[b for b in json.loads(a.boards.read_text()) if b.get('rank_by')=='us_prophet_v3' and '2026-08-17'<=b['as_of']<='2026-10-05']
for b in bs:
    for lane in ('buy','watch','leaders','laggards'):
        for r in b.get(lane,[]):r['_research_asof']=b['as_of']
original=em.features
def enriched(r):return dict(**original(r),**supplement((r.get('_research_asof',''),r['ticker'])))
em.features=enriched
before,pairs_before=em.comparison(bs,ec,cc,12,'valid','date_sector_state_nn3',20261018)
em.BASE_FEATURES=em.BASE_FEATURES+extra
after,pairs_after=em.comparison(bs,ec,cc,12,'valid','date_sector_state_nn3',20261018)
disjoint,pairs_disjoint=em.comparison(bs,ec,cc,12,'valid','issuer_disjoint_nn3',20261018)
report=dict(status='RETROSPECTIVE_FINAL_PRICE_VINTAGE_SENSITIVITY_NOT_PIT_VALIDATION',exposed_total=len(es),exposed_price_join=len(ec),
    control_rows_total=len(cs),control_rows_price_join=len(cc),missing_exposed=[r['ticker'] for r in es if r not in ec],
    methods={'same_overlap_board_native_matching':before,'same_overlap_plus_RS21_and_liquidity':after,'issuer_disjoint_plus_RS21_and_liquidity':disjoint},
    input_sha256={str(x.name):hashlib.sha256(x.read_bytes()).hexdigest() for x in [a.boards,a.baselines,a.controls,a.price_controls]},
    caveats=['Source adjusted-price histories are final vintages at parent PR8495 head 770918cb266b5d884978e31d61670b4efd789eaf; not proven original adjustment vintages.',
      'RS21 and 21-session momentum differ by the same-date SPY constant; only RS21 enters distance to avoid double-counting.',
      'Incomplete joins excluded explicitly; none filled as zero.',
      'Matching uses fixed nearest-three same-date, sector and entry-status controls and baseline covariates only.',
      'No independent industry or market-cap PIT covariate is available. Dollar-volume liquidity is a proxy, not market cap.',
      'Capture outcome remains subject to disappearance/unknown-state censoring; effects are not calibrated conversion probabilities.'])
(a.out/'emergence_price_control_sensitivity.json').write_text(json.dumps(report,indent=2,sort_keys=True))
em.writecsv(a.out/'emergence_price_match_pairs.csv',[dict(variant='before',**p) for p in pairs_before]+[dict(variant='after',**p) for p in pairs_after]+[dict(variant='issuer_disjoint',**p) for p in pairs_disjoint])
em.writecsv(a.out/'emergence_price_controls_used.csv',[pm[(r['as_of'],r['ticker'])] for r in ec+cc])
print(json.dumps({'exposed_price_join':len(ec),'control_price_join':len(cc),'missing_exposed':report['missing_exposed'],
    'methods':{m:{k:v.get(k) for k in ['n_matched_exposed','observed_capture_exposed','observed_capture_controls','observed_capture_difference','date_cluster_bootstrap_capture_difference_95ci','true_conversion_difference_identification_bounds']} for m,v in report['methods'].items()}},indent=2))

