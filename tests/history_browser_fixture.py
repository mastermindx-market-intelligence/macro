import json
from tests.test_intl_history_mount import fixture
from tests.test_intl_workspace_history_render import render
w,_=fixture()
toolbar='''<button data-im-action="set_view" data-im-view="history">History</button><button data-im-action="set_view" data-im-view="overview">Overview</button><select data-im-action="set_horizon"><option>1m</option><option>3m</option></select><select data-im-action="set_basis"><option value="usd_unhedged">USD</option><option value="local">Local</option></select><button data-im-action="pin" data-im-market="JP">Pin</button>'''
overview=''.join(f'<section data-im-panel data-view="overview" data-horizon="{h}" data-basis="{b}" data-return-basis="price" data-source="" data-im-generation="{w["config"]["source_reference"]}">Overview</section>' for h in w['config']['horizons'] for b in w['config']['bases'])
html=f'<section data-im-workspace data-im-mode="macro" data-im-binding-version="2"><h1 data-im-heading>Workspace</h1><p data-im-issues></p><p data-im-unavailable hidden></p>{toolbar}{overview}{render()}</section>'
print(json.dumps(dict(html=html,config=w['config'])))
