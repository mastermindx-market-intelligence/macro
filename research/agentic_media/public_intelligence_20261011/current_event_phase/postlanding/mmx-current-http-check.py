import json,pathlib,datetime,urllib.request,re,hashlib,urllib.parse
expected=json.loads(pathlib.Path(__file__).with_name('mmx-current-expected-pages.json').read_text());observations=[]
for path,e in expected.items():
 url=e['canonical']
 req=urllib.request.Request(url,headers={'User-Agent':'Mastermind-delivery-acceptance/1.0'})
 with urllib.request.urlopen(req,timeout=30) as r:b=r.read();status=r.status;final=r.url;headers=dict(r.headers)
 s=b.decode('utf-8');title=re.search(r'<title>(.*?)</title>',s,re.S);canonical=re.search(r'<link rel="canonical" href="(.*?)"',s)
 cards=[]
 for href,inner in re.findall(r'<a class="public-nav-card" href="([^"]+)">(.*?)</a>',s,re.S):
  if '>Glossary<' in inner or '>Morning Edition<' in inner:cards.append({'href':href,'resolved':urllib.parse.urljoin(url,href),'glossary':'>Glossary<' in inner,'morning_edition':'>Morning Edition<' in inner,'zh_present':'词汇表' in inner or '早间版' in inner})
 obs={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':url,'status':status,'finalUrl':final,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'matchesExpectedBytes':hashlib.sha256(b).hexdigest()==e['sha256'],'title':title.group(1) if title else None,'canonical':canonical.group(1) if canonical else None,'navCards':cards,'headerEvidence':{k:v for k,v in headers.items() if k.lower() in ['cache-control','content-type','eo-cache-status','last-modified','server']}}
 obs['accepted']=obs['matchesExpectedBytes'] and status==200 and obs['title']==e['title'] and obs['canonical']==url and len(cards)==2 and all(c['zh_present'] for c in cards) and {c['resolved'] for c in cards}=={'https://www.mastermind-x.com/glossary.html','https://www.mastermind-x.com/am_edition.html'}
 observations.append(obs)
pathlib.Path(__file__).with_name('mmx-current-http-observations.json').write_text(json.dumps(observations,indent=2)+'\n')
print(json.dumps(observations,indent=2))
