"""P12.T42: pure retained-input native rendering; no writer/collector/browser."""
from pathlib import Path
import hashlib,html,json,re,socket,subprocess,sys
R=Path(sys.argv[1]);E=Path(__file__).parent;sys.path.insert(0,str(R));attempts=[]
def denied(*a,**k):attempts.append('blocked before transport');raise AssertionError('offline pure renderer')
socket.create_connection=socket.getaddrinfo=denied
from scripts.build_am_edition import render_html
raw=(R/'tests/fixtures/am_edition_title_snapshot_2e17ae66.json').read_bytes();payload=json.loads(raw);original=json.dumps(payload,sort_keys=True)
after=render_html(payload);(E/'after.html').write_text(after);before=(E/'before.html').read_text()
pattern=r'<title>(.*?)</title>';a=re.search(pattern,before,re.S);z=re.search(pattern,after,re.S);assert a and z
old=html.unescape(a.group(1));new=html.unescape(z.group(1));assert '<span' in old;assert '<' not in new and '>' not in new;assert new=='Morning Edition · 早间版 — '+payload['generated_at']
assert re.sub(pattern,'<title>REMOVED_FOR_COMPARISON</title>',before,count=1,flags=re.S)==re.sub(pattern,'<title>REMOVED_FOR_COMPARISON</title>',after,count=1,flags=re.S)
body=lambda s:re.search(r'<body\b.*</body>',s,re.S).group(0)
assert body(before)==body(after);assert original==json.dumps(payload,sort_keys=True);assert not attempts
base=json.loads((E/'source-baseline.json').read_text())['head']
# Existing emitted site artifact and every non-template tracked source stay untouched.
assert subprocess.check_output(['git','diff','--name-only',base,'--','templates','scripts','lib','engine','site','data'],cwd=R,text=True).splitlines()==['templates/am_edition.html.j2']
result={'baseline':base,'nativeRenderer':'scripts.build_am_edition.render_html','inputSha256':hashlib.sha256(raw).hexdigest(),'inputBytes':len(raw),'exactAsOf':payload['generated_at'],'beforeTitleRCDATA':old,'afterTitleRCDATA':new,'beforeHtmlSha256':hashlib.sha256(before.encode()).hexdigest(),'afterHtmlSha256':hashlib.sha256(after.encode()).hexdigest(),'bodyIdentical':True,'bodySha256':hashlib.sha256(body(after).encode()).hexdigest(),'fullHtmlOutsideTitleIdentical':True,'payloadUnchanged':True,'networkAttempts':attempts,'candidateTemplateSha256':hashlib.sha256((R/'templates/am_edition.html.j2').read_bytes()).hexdigest(),'generatedSiteArtifactBlobUnchanged':subprocess.check_output(['git','rev-parse','HEAD:site/am_edition.html'],cwd=R,text=True).strip(),'boundary':'local retained-input pure-render SOURCE proof only; generated site untouched, no browser/served/current-data claim'}
(E/'qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
