"""Dossier controls follow configured selection scope, not payload inventory."""
from html.parser import HTMLParser
from tests.intl_gs_dossier_fixture import _specimen_panel
from tests.intl_gs_fixture_site import _env

CORE = ['JP','KR','TW','IN','AU','GB','EZ']

class Controls(HTMLParser):
    def __init__(self):
        super().__init__();self.actions=[];self.disabled=[];self.links=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'data-gs-select-market' in a:
            self.actions.append((tag,a))
        if a.get('aria-disabled')=='true':self.disabled.append((tag,a))
        if tag=='a':self.links.append(a)

def render(markets):
    panel=_specimen_panel()
    panel['payload']['default_market']='JP'
    html=_env().get_template('intl_workspace/dossier.html.j2').render(
        gs_panel=panel,intl_workspace={'config':{'markets':markets}})
    c=Controls();c.feed(html);return html,c

def test_only_configured_picker_and_peer_entries_are_actionable():
    html,c=render(CORE)
    assert c.actions
    assert all(tag=='a' and a['data-gs-select-market'] in CORE for tag,a in c.actions)
    assert any(a.get('data-gs-select-market')=='JP' for _,a in c.actions)
    assert any(a.get('data-gs-select-market')=='TW' for _,a in c.actions)
    assert not any(a.get('data-gs-select-market')=='CN' for _,a in c.actions)
    china=next(a for _,a in c.disabled if a.get('data-gs-market-row')=='CN')
    assert 'href' not in china and 'data-gs-select-market' not in china
    assert 'Selection unavailable in this workspace' in html and '当前工作区不支持选择' in html
    assert 'China' in html and '中国' in html

def test_no_configuration_never_promotes_the_broader_payload_to_selection():
    html,c=render([])
    assert not c.actions
    assert any(a.get('data-gs-market-row')=='JP' for _,a in c.disabled)
    assert 'Selection unavailable in this workspace' in html
