"""Public input acquisition. Raw inputs are scratch only and MUST NOT be committed.
No outcome calculation occurs here; later parsers reject rows after 2019-12-31.
"""
from pathlib import Path
import urllib.request, zipfile, io, hashlib, json, concurrent.futures, re
ROOT=Path(__file__).resolve().parent
RAW=ROOT/'raw'
URLS={
 'factors':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip',
 'momentum':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_daily_CSV.zip',
 'size':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Portfolios_Formed_on_ME_Daily_CSV.zip',
 'ind12':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/12_Industry_Portfolios_daily_CSV.zip',
 'ind17':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/17_Industry_Portfolios_daily_CSV.zip',
 'ind49':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_daily_CSV.zip',
 'ind49monthly':'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_CSV.zip',
 'shiller':'https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/1449043e-a1ed-4e2e-8e9c-7b9a2a064493/ie_data.xls?ver=1791297298731',
 'spx_yahoo':'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=-1372723200&period2=1577836800&interval=1d',
}
for series in ['BAA','BAA10YM','GS10','TB3MS','UNRATE']:
 URLS[series]=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=1919-01-01&coed=2019-12-31'
def get(item):
 name,url=item
 try:
  data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Academic historical research contact via GitHub issue 11014'}),timeout=45).read()
  suffix='.zip' if url.endswith('.zip') else ('.xls' if name=='shiller' else ('.json' if name=='spx_yahoo' else '.csv'))
  (RAW/(name+suffix)).write_bytes(data)
  meta={'name':name,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
  if suffix=='.zip':
   z=zipfile.ZipFile(io.BytesIO(data)); txt=z.read(z.namelist()[0]).decode('utf-8-sig')
   (RAW/(name+'.txt')).write_text(txt)
   meta['sections']=[line.strip() for line in txt.splitlines() if line.strip() and not re.match(r'^[\s,]*\d',line)][:40]
  return meta
 except Exception as e:return {'name':name,'url':url,'error':str(e)}
if __name__=='__main__':
 RAW.mkdir(exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
  result=list(ex.map(get,URLS.items()))
 (ROOT/'acquisition.json').write_text(json.dumps(result,indent=2))
 for row in result:print(json.dumps(row))
