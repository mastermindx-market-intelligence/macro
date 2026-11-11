from pathlib import Path
import re,json,hashlib,subprocess
from jinja2 import Environment,StrictUndefined
from lib.pages import write_page
root=Path.cwd(); site=root/'site'
receipt=[]
def emit(css, pages, marker, label):
 digest=hashlib.sha256(css.encode()).hexdigest()[:8]
 out=site/'assets/css'/f'{digest}.css'
 if out.exists(): assert out.read_text()==css
 else: out.write_text(css)
 changed=[];old=set()
 for p in pages:
  text=p.read_text()
  refs=set(re.findall(r'assets/css/([0-9a-f]{8})\.css',text))
  match=[h for h in refs if (site/'assets/css'/f'{h}.css').exists() and marker in (site/'assets/css'/f'{h}.css').read_text()]
  assert len(match)==1,(p,match)
  previous=match[0];old.add(previous)
  new=text.replace(f'assets/css/{previous}.css',f'assets/css/{digest}.css')
  new=new.replace(f'{digest}.css?v={previous}',f'{digest}.css?v={digest}')
  if new!=text: write_page(p,new);changed.append(str(p.relative_to(root)))
 receipt.append(dict(label=label,asset=str(out.relative_to(root)),sha256=hashlib.sha256(css.encode()).hexdigest(),old=sorted(old),pages=changed))
css=re.search(r'<style>(.*?)</style>',Path('templates/basket_detail.html.j2').read_text(),re.S).group(1)
pages=[p for d in ('basket','basket_china','basket_hk','basket_canada','basket_intl') for p in (site/d).glob('*.html')]
emit(css,pages,'.ftr-anatomy-disclosure > summary','basket-detail')
from scripts.build_bonds import C
block=next(s for s in re.findall(r'<style\b[^>]*>(.*?)</style>',Path('templates/bonds.html.j2').read_text(),re.I|re.S) if '.dtp-chip--snapshot' in s)
css=Environment(autoescape=True,keep_trailing_newline=True,undefined=StrictUndefined).from_string(block).render(C=C)
emit(css,[site/'bonds.html'],'.dtp-chip--snapshot','bonds')
child=re.search(r'{% block base_css %}(.*?){% endblock %}',Path('templates/alt_data.html.j2').read_text(),re.S).group(1)
parent=re.search(r'<style\b[^>]*>(.*?)</style>',Path('templates/report_base.html.j2').read_text(),re.I|re.S).group(1)
css=re.sub(r'{% block base_css %}.*?{% endblock %}',lambda m:child,parent,flags=re.S)
assert '{%' not in css and '{{' not in css
emit(css,[site/'alt_data.html'],'shared Research-Reports chrome','alt-data-inherited')
Path('mockups/evidence/container-edge-removal/generated-css-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps([{k:v for k,v in row.items() if k!='pages'}|{'page_count':len(row['pages'])} for row in receipt],indent=2))
