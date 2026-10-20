from pathlib import Path
import re,sys,json
sys.path.insert(0,str(Path.cwd()))
from engine import valuation_assumptions as va, valuation_event_bridge as veb, valuation_scenario as vs
from tests.test_valuation_scenario import _rows
from tests.test_valuation_event_bridge import _render
root=Path.cwd()
evidence=root/'mockups/evidence/b-f07-3-event-bridge'
old=(evidence/'hosts/valuation-event-bridge-null.html').read_text()
wrapper=re.search(r'<style>\n\*\{box-sizing:border-box;\}(.*?)</style>',old,re.S).group(0)
controls=va.controls_blob(vs.compute(_rows(),ticker='AAPL'))
for state,cls in [('tender-offer','Tender Offers'),('restructuring','Restructuring'),('null',None)]:
 controls['latest_event_bridge']=veb.bridge(cls)
 html='''<!DOCTYPE html>
<html lang="en" data-theme="dark" data-lang="en" class="has-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="../../../../templates/">
<title>How a filing affects an assumption / 备案如何影响估值假设</title>
<style>\n'''+(root/'templates/theme.css').read_text()+'\n</style>\n'+wrapper+'''
</head>
<body>
<div class="page-wrap">
<p class="host-banner"><span class="l-en">Synthetic test data — not a real stock. No figure on this page belongs to any company.</span><span class="l-zh">合成测试数据，并非真实股票。本页数字不属于任何公司。</span></p>
'''+_render(controls)+'''
</div>
</body>
</html>
'''
 (evidence/f'hosts/valuation-event-bridge-{state}.html').write_text(html)
 print('regenerated',state)
