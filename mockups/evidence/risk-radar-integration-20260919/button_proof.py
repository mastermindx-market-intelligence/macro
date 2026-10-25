from pathlib import Path
import json,threading,functools
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
ROOT=Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/risk-radar-integration-20260919')
OUT=Path('/Volumes/Mastermind/agent-evidence/risk-radar-integration-20260919')
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True); page=browser.new_page(viewport={'width':1440,'height':900})
  page.goto('http://127.0.0.1:'+str(server.server_port)+'/macro.html',wait_until='domcontentloaded')
  page.wait_for_function("typeof window.mx5OpenDlg === 'function'")
  assert page.url.startswith('http://127.0.0.1:')
  # Isolated member-access fixture; no credentials, production access or auth claim.
  page.evaluate("window.MMXAccessPreview={isAnon:()=>false,openSignin:()=>{throw Error('Unexpected sign-in in local fixture')}}")
  button=page.locator('#regime-radar button[onclick*="dlg-risk"]:visible').first
  label=button.inner_text(); button.click()
  page.locator('#risk-envelope-band').wait_for(state='visible')
  summary=page.locator('#risk-envelope-band summary'); summary.focus(); page.keyboard.press('Enter')
  assert page.locator('#risk-envelope-band details').get_attribute('open') is not None
  page.keyboard.press('Escape'); page.locator('#risk-envelope-band').wait_for(state='hidden')
  result={'mode':'isolated_local_member_access_fixture','production_authentication_tested':False,'button':label,'existing_button_opens_radar':True,'evidence_keyboard_opens':True,'escape_closes':True}
  (OUT/'button-proof.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result)); browser.close()
finally: server.shutdown(); server.server_close()
