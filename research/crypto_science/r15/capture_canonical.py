"""Run the existing canonical capture owner with loopback-only network policy.
No DOM content/series substitution and no screenshots relabeled as live proof.
"""
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from scripts import capture_page_evidence as owner
from playwright.sync_api import Browser
HERE=Path(__file__).resolve().parent/'completion'
OUT=ROOT/'mockups/evidence/crypto-desk-r15-completion'
SITE=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/r15_actual')

def main():
    if (OUT/'manifest.json').exists():raise RuntimeError('Canonical receipt exists; inspect rather than overwrite')
    blocked=[];original=Browser.new_context
    def create(self,*args,**kwargs):
        context=original(self,*args,**kwargs)
        def guard(route):
            u=urlsplit(route.request.url)
            if u.scheme in ['http','https'] and u.hostname in ['127.0.0.1','localhost']:
                route.continue_()
            else:
                blocked.append({'scheme':u.scheme,'host':u.hostname,'path':u.path});route.abort()
        context.route('**/*',guard)
        return context
    argv=['--site-dir',str(SITE),'--routes','/crypto.html','--output-dir',str(OUT),'--manifest',str(OUT/'manifest.json'),
          '--smells',str(OUT/'smells.json'),'--viewports','desktop,mobile','--locales','en,zh','--themes','dark,light',
          '--max-pages','1','--settle-ms','1500','--force-state','brain-hover:hover(.desk-brain-entry)',
          '--force-state','brain-focus:focus(.desk-brain-entry)',
          '--force-state','chart-review:focus(.desk-chart-foot a)']
    with patch.object(Browser,'new_context',create):rc=owner.main(argv)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    receipt={'classification':'CANONICAL_OWNER_CONTROLLED_LOOPBACK_CAPTURE_NOT_DEPLOYMENT','owner_source':sha(ROOT/'scripts/capture_page_evidence.py'),
             'wrapper_source':sha(Path(__file__)),'html_sha256':sha(SITE/'crypto.html'),'blocked_external_requests':blocked,
             'exit_code':rc,'argv':argv,'limits':'Native hover/focus actions; scroll to coverage link exposes lazy chart. Rest captures may show below-fold lazy state. No real chat, live quote or provider endpoint is supplied.'}
    (HERE/'capture_run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if rc:raise SystemExit(rc)

if __name__=='__main__':main()
