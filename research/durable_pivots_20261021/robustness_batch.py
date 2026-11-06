#!/usr/bin/env python3
import argparse, concurrent.futures, itertools
from pathlib import Path
import robustness

def one(job):
    manifest,out,phase,basis=job
    robustness.run(manifest,out,phase,basis)
    return phase,basis

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    jobs=[(a.manifest,a.out,','.join(map(str,x)),'price') for x in itertools.product(range(2),range(3),range(2))]
    jobs.append((a.manifest,a.out,'0,0,0','total_return'))
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(one,j) for j in jobs]
        for f in concurrent.futures.as_completed(futures):print('DONE',f.result(),flush=True)
