from pathlib import Path
import re,json,hashlib,os
R=Path.cwd();S=R/'site';E=R/'mockups/evidence/container-edge-removal'
repairs=[];digest=lambda b:hashlib.sha256(b).hexdigest()
# Restore an intentional Canada row divider that the China-specific exact hunk also matched.
neutral='.nb-cau-pop .cau-row + .cau-row { border-top:1px solid var(--line); padding-top:4px; margin-top:2px; }'
approved='.nb-cau-pop .cau-row + .cau-row { border-top:1px solid color-mix(in srgb,var(--warn) 20%,var(--line)); padding-top:4px; margin-top:2px; }'
for name in ['canada.html','canada_stocks.html']:
 p=S/name;s=p.read_text();before=s
 s=s.replace(neutral,approved)
 for ref in set(re.findall(r'assets/css/[0-9a-f]{8}\.css',s)):
  q=S/ref;t=q.read_text()
  if neutral not in t:continue
  new=t.replace(neutral,approved);h=digest(new.encode())[:8];dest=q.with_name(h+'.css')
  if dest.exists():assert dest.read_text()==new
  else:dest.write_text(new)
  s=s.replace(ref,str(dest.relative_to(S))).replace(h+'.css?v='+q.stem,h+'.css?v='+h)
 if s!=before:p.write_text(s);repairs.append(dict(path=str(p.relative_to(R)),reason='Canada accepted separator parity',before=digest(before.encode()),after=digest(s.encode())))
# Finite source-approved inline styles whose source list changed length.
risk=re.compile(r'(style=[\"\'])font-size:11\.5px;margin:8px 0 0;border-left:3px solid [^;\"\']+;padding-left:9px([\"\'])')
for p in S.rglob('*.html'):
 if p.name in ('macro_edge_fixture.html','stocks_edge_fixture.html'):continue
 s=p.read_text();new,n=risk.subn(lambda m:m[1]+'font-size:11.5px;margin:8px 0 0;border:1px solid var(--line);padding-left:9px'+m[2],s)
 if any(part in ('subsector','subsector_china','subsector_nasdaq','subsector_russell') for part in p.parts):
  new=re.sub(r'\s+style=[\"\']border-left-color:var\(--orange\)[\"\']','',new)
 if p.name=='us_stocks_lab.html':
  new=re.sub(r'\s+style=[\"\']border-left-color:var\(--(?:up|down|info,#4c8bf5)\)[\"\']','',new)
 if new!=s:p.write_text(new);repairs.append(dict(path=str(p.relative_to(R)),reason='approved inline container styles',before=digest(s.encode()),after=digest(new.encode())))
# Exact accepted standalone state semantics, already emitted by bounded owner renders.
finance=(S/'finance_intelligence.js').read_text()
assert 'labelFor(' in finance and 'setSectionFreshness' in finance and 'mirrorFreshness' in finance
china=(S/'china_intel.html').read_text()
assert 'Long context' in china and 'Short context' in china and '多头背景' in china and '空头背景' in china
# Fingerprinted @imports must not retain a renamed dependency. This is a proof of zero affected edges,
# otherwise fail closed for a separate bottom-up repair.
rename=json.loads((E/'consumer-projection-receipt.json').read_text())['renamed_assets']
bad=[]
for p in S.rglob('*.css'):
 # Old unreferenced hashes are historical; check current assets emitted or referenced by final pages later.
 if str(p.relative_to(S)) in rename:continue
 for ref in re.findall(r'@import\s+(?:url\(\s*)?[\"\']([^\"\']+)',p.read_text()):
  target=os.path.normpath(str(p.parent.relative_to(S)/ref.split('?')[0]))
  if target in rename:bad.append(dict(parent=str(p.relative_to(R)),ref=ref,replacement=rename[target]))
assert not bad,bad
(E/'consumer-residual-repairs.json').write_text(json.dumps(dict(repairs=repairs,renamed_import_dependencies=bad,finance_state_labels=True,china_context_labels=True),indent=2)+'\n')
print(json.dumps(dict(repaired_files=len(repairs),renamed_import_dependencies=len(bad))))
