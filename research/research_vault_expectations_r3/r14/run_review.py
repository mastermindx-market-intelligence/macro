"""Reproduce the completed 24-case R14 full-reader review, never production.

Use --source-root pointing to a checkout of the containing research directory.
The default expects upstream snapshots already present beside r14/. No network,
package installation or original institutional data is needed. The additional
blocked review is deliberately excluded from this runner.
"""
from __future__ import annotations
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from patch_reader import amended
EXPECTED={'brain_pending.py':'376d1045e6187926bea2fd4c83385d140174b817','corpus_pending.py':'1bc0aacd46d8ec0ad25d3b53341040a3e6aa1af8','r2_store.py':'139fcbe8cf08945a2be1feaa0dca5428c818837b','view_ratelimit.py':'5e33b4d213ff3b9497134343712921e3d3ac6b77'}
CANDIDATE='c304ec40245d04e98ad00e8e9f28f50084ff491905fed183a43ff1cf18ff46e3'
def gitblob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def fixture(out):
    texts=['SYNTHETIC TEST ONLY - Industrial operations review','Orionquartz margin outlook for FY2027 is revised from 31% to 28%.']
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>']
    for page,text in enumerate(texts):
        stream=('BT /F1 12 Tf 40 720 Td ('+text+') Tj ET').encode()
        objects.extend([f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 7 0 R >> >> /Contents {4+page*2} 0 R >>'.encode(),b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream'])
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    b=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,obj in enumerate(objects,1):offsets.append(len(b));b.extend(str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    x=len(b);b.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for off in offsets[1:]:b.extend(f'{off:010d} 00000 n \n'.encode())
    b.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode())
    (out/'source.pdf').write_bytes(bytes(b));(out/'source.txt').write_text(texts[0]+'\n\f'+texts[1]+'\n\f')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args()
    sources={n:(a.source_root/'upstream'/n).read_bytes() for n in EXPECTED}
    for n,b in sources.items():
        if gitblob(b)!=EXPECTED[n]:raise ValueError('Unqualified source: '+n)
    if a.output_dir.exists():raise ValueError('Refuse overwrite of existing review output')
    out=a.output_dir.resolve();out.mkdir(parents=True)
    for d in ('upstream','r14','fixtures','results'):(out/d).mkdir()
    for n,b in sources.items():(out/'upstream'/n).write_bytes(b)
    for n in ('source_guard.py','test_full_reader.py','patch_reader.py'):shutil.copy2(Path(__file__).resolve().parent/n,out/'r14'/n)
    fixture(out/'fixtures');new=amended(sources['brain_pending.py'])
    if hashlib.sha256(new).hexdigest()!=CANDIDATE:raise ValueError('Unexpected amended source')
    (out/'upstream/brain_guarded.py').write_bytes(new)
    env=dict(os.environ,RV_R14_ROOT=str(out),RV_R14_BRAIN='brain_guarded.py',PYTHONDONTWRITEBYTECODE='1')
    r=subprocess.run([sys.executable,'-m','unittest','-v','test_full_reader'],cwd=out/'r14',env=env,capture_output=True,text=True,timeout=45)
    (out/'results/reader_tests.txt').write_text(r.stdout+r.stderr)
    passed=r.returncode==0 and 'Ran 24 tests' in r.stderr and r.stderr.rstrip().endswith('OK')
    result={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit':r.returncode,'completed_case_count':24,'passed':passed,'source_blobs':EXPECTED,'candidate_sha256':CANDIDATE,'auth_and_source_permission':'controlled fixtures','gateway_executed':False,'institutional_original_used':False,'blocked_adversarial_review_executed':False}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
