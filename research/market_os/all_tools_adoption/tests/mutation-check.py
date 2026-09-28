"""Adversarial controller probes, never a browser or production test."""
from pathlib import Path
import os, json, subprocess, tempfile, hashlib
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'src/all-tools.js').read_text()
cases={
 'redraw_revalidation_removed':('      validateDestinations();\n      if (focusedHref && live)', '      /* broken redraw check */\n      if (focusedHref && live)'),
 'auxclick_guard_removed':("    list.addEventListener('auxclick',guardDestination);",'/* broken auxiliary-click guard */'),
 'contextmenu_guard_removed':("    list.addEventListener('contextmenu',guardDestination);",'/* broken context-menu guard */'),
 'destination_focus_removed':('        (replacement || title).focus({preventScroll:true});','        /* broken focus restoration */'),
 'withdrawal_latch_removed':('      withdrawn[a.dataset.toolsHref] = true;','      /* broken presentation latch */'),
 'duplicate_mount':("if (doc.querySelector('[data-mmx-tools-mounted]')) return null;",'/* broken duplicate guard */'),
 'context_erased':('contextGroup=current?current.group:null;','contextGroup=null;'),
 'svg_handler_copied':("'fill-rule','clip-rule'", "'fill-rule','clip-rule','onclick'"),
 'changed_target_ignored':("(source.getAttribute('target')==='_blank'?'_blank':'')===(a.getAttribute('target')||'')",'true'),
 'server_disabled_ignored':("if (n.getAttribute('data-nav-disabled') === 'true') return false;",'/* ignores disabled source */'),
 'unsafe_origin_accepted':("if (url.origin !== source.origin && APPROVED.indexOf(url.origin) < 0) return null;",'/* accepts arbitrary origin */'),
 'ime_filters_early':('if(!composing){render();scroller.scrollTop=0;}','render();scroller.scrollTop=0;')
}
results=[]
with tempfile.TemporaryDirectory(prefix='mmx-r23-mutants-') as tmp:
 for name,(a,b) in cases.items():
  assert s.count(a)==1,(name,s.count(a))
  mutant=Path(tmp)/(name+'.js');mutant.write_text(s.replace(a,b))
  p=subprocess.run(['node','--test']+[str(ROOT/'tests'/n) for n in ('navigation.test.cjs','controller.test.cjs','refresh-boundaries.test.cjs')],env={**os.environ,'ALL_TOOLS_SOURCE':str(mutant)},text=True,capture_output=True,timeout=15)
  failures=[line for line in p.stdout.splitlines() if line.startswith('not ok ')]
  detected=p.returncode==1 and bool(failures) and 'SIGKILL' not in p.stdout
  results.append({'name':name,'detected':detected,'exit':p.returncode,'failures':failures,'sha256':hashlib.sha256(mutant.read_bytes()).hexdigest()})
report={'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'cases':results,'detected':sum(r['detected'] for r in results),'total':len(results)}
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence/mutations-r23.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert report['detected']==report['total']
