"""Challenge only disposable copies of the request-local research adapter."""
from __future__ import annotations
import json, pathlib, shutil, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
MUTATIONS=[
 ('allow_essential_body_scope',"if source_text and tier not in ('pro', 'unlimited'):","if False:"),
 ('ignore_exhausted_preflight',"if isinstance(preflight, dict) and preflight.get('remaining') == 0:","if False:"),
 ('recheck_quota_after_last_debit',"            current_gate = self._product_gate(user_id, source_text=True)","            late = self.owners['peek_view'](user_id, now)\n            if isinstance(late, dict) and late.get('remaining') == 0:\n                return {'decision': 'denied'}\n            current_gate = self._product_gate(user_id, source_text=True)"),
 ('double_debit',"            value = self.owners['charge_view'](user_id, now)","            self.owners['charge_view'](user_id, now)\n            value = self.owners['charge_view'](user_id, now)"),
 ('truthy_denial_tuple',"            return allowed\n","            return bool(value)\n"),
 ('invent_persistence_receipt',"'persistence': 'not_attested'","'persistence': 'confirmed'"),
 ('retry_unknown_accounting',"            value = self.owners['charge_view'](user_id, now)","            try:\n                value = self.owners['charge_view'](user_id, now)\n            except Exception:\n                value = self.owners['charge_view'](user_id, now)"),
 ('ignore_current_product_tier',"            current_gate = self._product_gate(user_id, source_text=True)","            current_gate = None"),
]
def main():
 out=[]
 for name,old,new in MUTATIONS:
  with tempfile.TemporaryDirectory(prefix='rv-r13-mutation-') as tmp:
   p=pathlib.Path(tmp)
   for folder in ('r13','upstream','prior'):
    shutil.copytree(ROOT/folder,p/folder,ignore=shutil.ignore_patterns('__pycache__','results','*.pyc'))
   source=p/'r13/owner_adapter.py';text=source.read_text()
   if text.count(old)!=1: raise ValueError('Nonunique mutation anchor '+name)
   source.write_text(text.replace(old,new,1))
   r=subprocess.run([sys.executable,'-m','unittest','-q','test_owner_adapter'],cwd=p/'r13',capture_output=True,text=True,timeout=20)
   import re
   matches=re.findall(r'FAILED \(([^)]+)\)',r.stderr)
   out.append({'name':name,'exit_code':r.returncode,'failure_summary':matches[-1] if matches else '',
               'rejected':r.returncode!=0 and bool(matches)})
 print(json.dumps({'kind':'direct_local_challenge_not_independent_review','cases':out},indent=2))
 return 0 if all(x['rejected'] for x in out) else 1
if __name__=='__main__':raise SystemExit(main())
