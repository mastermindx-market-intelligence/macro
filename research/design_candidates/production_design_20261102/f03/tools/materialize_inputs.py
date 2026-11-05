#!/usr/bin/env python3
"""Read immutable input blobs using an existing checkout; no fetch or checkout writes."""
import argparse,hashlib,json,subprocess
from pathlib import Path
PACKAGE='6e1862867193ec6486a22001a0e4fb515da20448'
MACRO='b66ca0fcfe7d79f1c90dbfa395e2d43ac5824a6e'
PREFIX='research/design_candidates/production_design_20261102/'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    manifest=json.loads((Path(__file__).resolve().parents[1]/'data/provenance.json').read_text())['source_blob_map']
    for name,expected in manifest.items():
        if name=='current-registry.json':pin,path=MACRO,'data/product_experience/page_registry.json'
        elif name=='F03-handoff.md':pin,path=PACKAGE,PREFIX+'handoffs/F03-paper-organization.md'
        elif name in ['README.md','ORGANIZATION_RULES.md','SHARED_SHELL_CONTRACT.md','RE_AUDIT_CHECKLIST.md'] or name.startswith('templates/'):pin,path=PACKAGE,PREFIX+name
        else:pin,path=PACKAGE,PREFIX+'census/'+name
        data=subprocess.check_output(['git','-C',str(a.repo),'show',pin+':'+path]);actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert actual==expected,name+' input blob mismatch'
        dest=a.output/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    (a.output/'source-blob-map.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'verified_input_blobs':len(manifest),'output':str(a.output),'repository_modified':False}))
if __name__=='__main__':main()
