"""Bounded physical-Parquet diagnostic. Synthetic TemporaryDirectory only."""
from pathlib import Path
import hashlib,json,resource,subprocess,sys,tempfile,time
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from collectors import _crypto_observations as o
HERE=Path(__file__).resolve().parent

def stats(path):
    if not path.exists():return {'file_bytes':0,'rows':0,'declared_uncompressed_bytes':0}
    m=pq.read_metadata(path)
    return {'file_bytes':path.stat().st_size,'rows':m.num_rows,
            'declared_uncompressed_bytes':sum(m.row_group(i).column(j).total_uncompressed_size for i in range(m.num_row_groups) for j in range(m.num_columns))}

def run(n):
    payload={'code':'0','data':[[str(1767225600000+i*3600000),str(100000+i*17),str(200000+i*19)] for i in range(480)]}
    start=pd.Timestamp('2026-01-01T00:00:00Z')
    with tempfile.TemporaryDirectory(prefix='mmx-r12-parquet-') as td:
        root=Path(td);path=o.capture_path('okx_taker',root=root)
        rows=[o.build_capture('okx_taker',{'ccy':'BTC','instType':'CONTRACTS','period':'1H'},payload,start+pd.Timedelta(hours=i)) for i in range(n+1)]
        if n:o.fss.atomic_write(pd.DataFrame(rows[:-1],columns=o.COLUMNS),path)
        before=stats(path);t=time.perf_counter();out=o.persist_capture(rows[-1],root=root);append=time.perf_counter()-t
        assert out['status']=='stored',out
        after=stats(path);original=hashlib.sha256(path.read_bytes()).hexdigest()
        t=time.perf_counter();duplicate=o.persist_capture(rows[-1],root=root);dup=time.perf_counter()-t
        assert duplicate['status']=='already_present' and original==hashlib.sha256(path.read_bytes()).hexdigest()
        return {'existing':n,'payload_bytes_per_capture':len(rows[-1]['payload_json'].encode()),
                'logical_capture_bytes':sum(len(o.canonical(c).encode()) for c in rows),
                'before':before,'after':after,'append_seconds':append,'duplicate_seconds':dup,
                'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'input_shape':'synthetic480triplets/repeatedpayload;notobservedproductionresponse',
                'unit_note':'macOS ru_maxrss is bytes; highwater includes interpreter, imports and synthetic seed.'}

if __name__=='__main__':
    if len(sys.argv)>1:print(json.dumps(run(int(sys.argv[1]))));raise SystemExit
    out=HERE/'parquet_baseline.json'
    if out.exists():raise SystemExit('Saved measurement exists; do not overwrite')
    rows=[]
    for n in [0,100,1000]:
        v=json.loads(subprocess.check_output([sys.executable,__file__,str(n)],text=True));rows.append(v);print(n,v['append_seconds'],v['duplicate_seconds'],flush=True)
    result={'classification':'SYNTHETIC_PHYSICAL_PARQUET_MEASUREMENT_NOT_CAPACITY_APPROVAL','rows':rows,
      'runtime':{'python':sys.version,'pandas':pd.__version__,'pyarrow':pa.__version__},
      'candidate':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['collectors/_crypto_observations.py','collectors/_first_seen_store.py']},
      'limits':'One append/duplicate per size, warm seeded files, no throughput percentiles, live cadence, host isolation or multihost guarantee.'}
    out.write_text(json.dumps(result,indent=2)+'\n');print('PARQUET_PROBE_COMPLETE',flush=True)
