from pathlib import Path
from copy import deepcopy
import hashlib, json, re, sys, subprocess

ROOT = Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/theme-recommendation-reasons-20260921-sol')
OUT = Path('/tmp/mmx-7669-continuation-repair')
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))

from engine import basket_score
from jinja2 import Environment, FileSystemLoader
from lib.pages import write_page, externalize_css_text, externalize_js_text, dbase_prefix
from scripts.externalize_css import MIN_BYTES
from scripts.optimize_assets import make_optimizer

HEAD = '6942b2b62bad2dfc9d3b50eb7042e0a126b708c4'
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip() == HEAD
site = ROOT / 'site'
env = Environment(loader=FileSystemLoader(str(ROOT/'templates')), autoescape=True)
tmpl = env.get_template('basket_detail.html.j2')
optimize = make_optimizer(site)
roots = ('basket','basket_china','basket_hk','basket_canada','basket_intl')
pages = sorted(p for root in roots for p in (site/root).glob('*.html'))
assert len(pages) == 121, len(pages)

prepared, rows, created_assets = [], [], {}
for p in pages:
    old = p.read_bytes()
    text = old.decode()
    assert text.count('const DETAIL = ') == 1
    detail, _ = json.JSONDecoder().raw_decode(text.split('const DETAIL = ',1)[1])
    new = deepcopy(detail)
    assert detail['basket']['id'] == p.stem
    stamps = re.findall(r'<span>([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} UTC)</span>', text)
    assert len(stamps) == 1, (p, stamps)
    new['act_now'] = basket_score.act_now_stocks(new['members'], new['theme'])
    for key in ('status','buys','uncovered'):
        assert new['act_now'][key] == detail['act_now'][key], (p,key)
    assert {k:v for k,v in new.items() if k!='act_now'} == {k:v for k,v in detail.items() if k!='act_now'}
    before, after = deepcopy(detail['act_now']), deepcopy(new['act_now'])
    for record in (before, after):
        for key in ('entry_checks','entry_summary','note_en','note_zh'):
            record.pop(key, None)
        for item in record.get('early_turn_watch', []):
            item.pop('blocker_en', None); item.pop('blocker_zh', None)
    assert before == after, (p, 'non-explanation act_now mutation')

    region = new.get('region','us')
    en = 'Sector Intelligence' if region=='us' else 'China Sector Intelligence' if region=='china' else 'Theme Rotation Desk'
    zh = '行业智慧' if region=='us' else '中国行业智慧' if region=='china' else '主题轮动台'
    raw = json.dumps(new, separators=(',',':'), ensure_ascii=False, allow_nan=False).replace('</','<\\/')
    html = tmpl.render(detail_json=raw, basket_name=new['basket'].get('name',p.stem),
                       generated_utc=stamps[0], back_href=new['back'], back_label_en=en, back_label_zh=zh)

    def hashed_asset(body, index, media=None, kind='css'):
        data = body.encode()
        if len(data) < MIN_BYTES:
            return None
        digest = hashlib.sha256(data).hexdigest()[:8]
        dest = site/'assets'/kind/(digest+'.'+kind)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == data, (p, dest)
        else:
            dest.write_bytes(data)
            created_assets[dest.relative_to(ROOT).as_posix()] = hashlib.sha256(data).hexdigest()
        return dbase_prefix(p)+'assets/'+kind+'/'+digest+'.'+kind+'?v='+digest

    html = externalize_css_text(html, hashed_asset)
    html = externalize_js_text(html, lambda body,index: hashed_asset(body,index,kind='js'))
    html = optimize(html, p.parent)
    prepared.append((p, html))
    rows.append({
        'path': p.relative_to(ROOT).as_posix(),
        'before_sha256': hashlib.sha256(old).hexdigest(),
        'as_of': new['as_of'],
        'generation_stamp': stamps[0],
        'members': len(new['members']),
        'assessed': sum(isinstance(x.get('conviction'),dict) and x['conviction'].get('score') is not None for x in new['members']),
        'status_buys_coverage_unchanged': True,
        'non_explanation_data_unchanged': True,
    })

for (p, html), row in zip(prepared, rows):
    write_page(p, html)
    row['after_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()

receipt = {
    'source_head_before_repair': HEAD,
    'template_sha256': hashlib.sha256((ROOT/'templates/basket_detail.html.j2').read_bytes()).hexdigest(),
    'engine_sha256': hashlib.sha256((ROOT/'engine/basket_score.py').read_bytes()).hexdigest(),
    'pages': len(rows),
    'member_rows': sum(x['members'] for x in rows),
    'assessed_rows': sum(x['assessed'] for x in rows),
    'created_assets': created_assets,
    'rows': rows,
    'scope': 'Re-render existing embedded inputs only; no collection, rescoring, new prices, or date changes. Native theme rating preserved; initial-entry context and stock-entry checks remain separate.'
}
(OUT/'page-refresh-proof.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='rows'}, indent=2, ensure_ascii=False))
