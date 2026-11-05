"""Synthetic native lineage through actual Macro reader/client; no live proof."""
import pytest
import json

from tests.test_entry_radar_quote_lineage_read import published_lineage, prepared, generation, native, inputs
from tests.test_ontology_radar_research_browser import start, listing, settled, browser


@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('lang',['en','zh'])
@pytest.mark.parametrize('width',[390,1440])
def test_bound_lineage_is_disclosed_in_existing_evidence_details(browser,published_lineage,theme,lang,width):
    context,page,seen,errors,episode=start(browser,published_lineage)
    try:
        page.set_viewport_size({'width':width,'height':1000})
        page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l}",[theme,lang])
        listing(page);page.locator('[data-episode]').click();settled(page,'ready')
        text=page.locator('[data-radar-result]').inner_text()
        assert '1,234' in text
        assert ('Provider identity is not authenticated here' in text) if lang=='en' else ('此处未认证提供方身份' in text)
        assert 'SEC:US-XNAS-MU' not in text
        page.locator('[data-radar-result] details > summary').click()
        text=page.locator('[data-radar-result]').inner_text()
        assert 'SEC:US-XNAS-MU' in text and 'polygon · MU' in text
        assert '2026-10-07T13:59:10+00:00' in text and '2026-10-07T13:59:30+00:00' in text
        assert ('spool content was not re-read' in text) if lang=='en' else ('未重新读取缓冲内容' in text)
        assert 'identity_read_receipt' not in text and 'live_flow/' not in text
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert all(r['headers']['authorization']=='Bearer fixture-token' for r in seen)
        page.locator('[data-radar-clear]').click();settled(page,'idle')
        assert 'SEC:US-XNAS-MU' not in page.locator('[data-radar-result]').inner_text()
        assert len(seen)==2 and not errors
    finally:context.close()


@pytest.mark.parametrize('mutation',['context','episode','provider','clock','live','rights','authority','nested_body','array_hash','array_vendor'])
def test_closed_browser_projection_refuses_bad_lineage(browser,published_lineage,mutation):
    def change(v):
        if v['state']!='published_context':return
        l=v['case']['quote_lineage']
        if mutation=='context':l['research_context_ref']['context_sha256']='0'*64
        elif mutation=='episode':l['episode_binding']['canonical_sha256']='0'*64
        elif mutation=='provider':l['quote']['provider_identity_attestation']='authenticated'
        elif mutation=='clock':l['quote']['recorded_at']='2026-10-07T14:05:00Z'
        elif mutation=='live':l['live_projection_eligible']=True
        elif mutation=='rights':l['rights_state']='display_ok'
        elif mutation=='authority':l['authority']['can_rank']=True
        elif mutation=='nested_body':l['origin']['private_body']='DO_NOT_EXPORT'
        elif mutation=='array_hash':l['identity']['snapshot_sha256']=[l['identity']['snapshot_sha256']]
        else:l['quote']['vendor']=['polygon']
    context,page,_,errors,_=start(browser,published_lineage,mutate=change)
    try:
        listing(page);page.locator('[data-episode]').click();settled(page,'unavailable')
        assert 'SEC:US-XNAS-MU' not in page.locator('[data-radar-result]').inner_text()
        assert 'DO_NOT_EXPORT' not in page.locator('[data-radar-result]').inner_text() and not errors
    finally:context.close()


def test_lineage_cannot_render_after_final_session_account_switch(browser,published_lineage):
    context,page,_,errors,_=start(browser,published_lineage)
    try:
        listing(page)
        page.evaluate("""() => {
          let calls=0;
          sdk.auth.getSession=()=>{
            const result={data:{session:{user:{id:owner},access_token:token}}};
            if(++calls===3)return new Promise(resolve=>{
              resolve(result);queueMicrotask(()=>queueMicrotask(()=>{
                window.owner='owner-b';callbacks.forEach(f=>f('SIGNED_IN',{user:{id:owner}}));
                window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:owner}}}));
              }));
            });return Promise.resolve(result);
          };
        }""")
        page.locator('[data-episode]').click();page.wait_for_function("window.owner==='owner-b'");settled(page,'idle')
        assert 'SEC:US-XNAS-MU' not in page.locator('[data-radar-result]').inner_text()
        assert '1,234' not in page.locator('[data-radar-result]').inner_text() and not errors
    finally:context.close()


def test_legacy_context_retains_unestablished_quote_disclosure(browser,published_lineage):
    live,path,source,episode=published_lineage
    source['episodes'][0].pop('quote_candidate_provenance');path.write_text(json.dumps(source))
    context,page,_,errors,_=start(browser,published_lineage)
    try:
        listing(page);page.locator('[data-episode]').click();settled(page,'ready')
        text=page.locator('[data-radar-result]').inner_text()
        assert 'does not establish which security' in text
        page.locator('[data-radar-result] details > summary').click()
        assert 'SEC:US-XNAS-MU' not in page.locator('[data-radar-result]').inner_text() and not errors
    finally:context.close()
