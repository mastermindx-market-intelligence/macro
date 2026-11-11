"""Cutoff-first public-data parsers; raw data never belongs in the source branch."""
from pathlib import Path
import csv, json, hashlib, re
import numpy as np
import pandas as pd
import xlrd

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'raw'
CUTOFF=pd.Timestamp('2019-12-31')
FIRST=pd.Timestamp('1926-07-01')
D_NAMES='Food Soda Beer Smoke Hshld Hlth MedEq Drugs Util'.split()
C_NAMES='Toys Fun Clths Chems Rubbr Txtls BldMt Cnstr Steel FabPr Mach ElcEq Autos Aero Ships BusSv Hardw Softw Chips LabEq Trans Rtail'.split()

def parse_french_text(text):
    """Select dates as strings before parsing ANY return values."""
    blocks=[]; columns=None; rows=[]; dates=[]; label=''
    def flush():
        nonlocal rows,dates
        if rows:
            df=pd.DataFrame(rows,index=pd.DatetimeIndex(dates),columns=columns)
            df=df.mask((df==-99.99)|(df==-999.0))/100.0
            assert df.index.is_unique and df.index.is_monotonic_increasing
            assert df.index.max()<=CUTOFF
            blocks.append((label,df)); rows=[];dates=[]
    for line in text.splitlines():
        fields=[x.strip() for x in line.split(',')]
        d=fields[0]
        if re.fullmatch(r'\d{8}',d):
            if d<'19260701' or d>'20191231': continue
            if columns is None: raise ValueError('No French header')
            values=[float(x) for x in fields[1:]]
            if len(values)!=len(columns):raise ValueError('French width mismatch')
            dates.append(pd.Timestamp(d)); rows.append(values)
        elif line.startswith(','):
            flush(); columns=fields[1:]
        elif not line.strip():flush()
        elif 'Returns -- Daily' in line:
            flush();label=line.strip()
    flush()
    if not blocks:raise ValueError('No in-sample daily data')
    return blocks

def french(name):
    return parse_french_text((RAW/(name+'.txt')).read_text())

def fred(name):
    rows=[]
    for row in csv.reader((RAW/(name+'.csv')).read_text().splitlines()):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',row[0]):continue
        if row[0]>'2019-12-31':continue
        rows.append((pd.Timestamp(row[0]),float(row[1]) if row[1] not in ['', '.'] else np.nan))
    out=pd.Series(dict(rows),name=name).sort_index()
    assert out.index.max()<=CUTOFF
    return out

def shiller():
    sheet=xlrd.open_workbook(RAW/'shiller.xls',on_demand=True).sheet_by_name('Data')
    rows=[]
    for i in range(8,sheet.nrows):
        date=sheet.cell_value(i,0)
        if not isinstance(date,(float,int)) or date<1800:continue
        year=int(date);month=int(round((date-year)*100))
        if not 1<=month<=12:continue
        stamp=pd.Timestamp(year,month,1)
        if stamp>CUTOFF:continue
        row=[sheet.cell_value(i,j) for j in [1,4,6]]
        rows.append([stamp]+[float(x) if isinstance(x,(int,float)) else np.nan for x in row])
    out=pd.DataFrame(rows,columns=['date','sp_composite','cpi','long_yield']).set_index('date')
    assert out.index.is_unique and out.index.max()<=CUTOFF
    return out

def known_monthly(series,index,lag_months):
    """Latest released row, preserving NaN in source observations."""
    dates=series.index+pd.DateOffset(months=lag_months)
    positions=np.searchsorted(dates.values,index.values,side='right')-1
    values=np.full(len(index),np.nan)
    valid=positions>=0
    values[valid]=series.to_numpy()[positions[valid]]
    return pd.Series(values,index=index,name=series.name)

def spx():
    path=RAW/'spx_yahoo.json'
    if not path.exists():return pd.Series(dtype=float,name='spx')
    result=json.loads(path.read_text())['chart']['result'][0]
    timestamps=result['timestamp'];quotes=result['indicators']['quote'][0]['close'];rows=[]
    for i,stamp in enumerate(timestamps):
        date=pd.Timestamp(stamp,unit='s',tz='UTC').tz_localize(None).normalize()
        if date<FIRST or date>CUTOFF:continue
        v=quotes[i]
        if v is not None:rows.append((date,float(v)))
    return pd.Series(dict(rows),name='spx').sort_index()

def load():
    factors=french('factors')[0][1]
    idx=factors.index
    ind=french('ind49')
    vw,ew=ind[0][1].reindex(idx),ind[1][1].reindex(idx)
    if not (vw.columns==ew.columns).all():raise ValueError('Industry column mismatch')
    assert factors.notna().all().all()
    observed=vw.notna().rolling(200,min_periods=200).sum().eq(200)
    targets={}
    missing_records=[]
    gross={}
    counts={}
    for group,names,min_count in [('C',C_NAMES,10),('D',D_NAMES,4)]:
        elig=observed[names]
        cnt=elig.sum(axis=1);counts[group]=cnt
        weights=elig.div(cnt.replace(0,np.nan),axis=0).where(cnt>=min_count)
        target=pd.DataFrame(0.,index=idx,columns=vw.columns)
        target[names]=weights
        target.loc[cnt<min_count]=np.nan
        targets[group]=target
        prev=target.shift(1)
        missing=(vw.isna() & prev.fillna(0).gt(0)).any(axis=1)
        for date in missing.index[missing]:
            members=list(vw.columns[(vw.loc[date].isna() & prev.loc[date].fillna(0).gt(0)).to_numpy()])
            missing_records.append({'source':'VW49','sleeve':group,'date':str(date.date()),'members':','.join(members)})
        gross[group]=(prev*vw).sum(axis=1,min_count=1).where(prev.notna().all(axis=1)&~missing)
    m=factors['Mkt-RF']+factors['RF']
    gross['M']=m
    gross=pd.DataFrame(gross)
    price=(1+gross).cumprod()
    industry_prices=(1+vw).cumprod()
    breadth={}
    for n in [50,200]:
        above=industry_prices[C_NAMES]>industry_prices[C_NAMES].rolling(n,min_periods=n).mean()
        breadth['C'+str(n)]=(above & observed[C_NAMES]).sum(axis=1).div(observed[C_NAMES].sum(axis=1)).where(counts['C']>=10)
    breadth=pd.DataFrame(breadth)
    monthly=shiller()
    spread=fred('BAA10YM');unrate=fred('UNRATE');bills=fred('TB3MS')
    credit=spread.gt(spread.shift(1).rolling(12,min_periods=12).mean()).astype(float).where(spread.shift(1).rolling(12,min_periods=12).count().eq(12)&spread.notna())
    u3=unrate.rolling(3,min_periods=3).mean()
    udiff=u3-u3.rolling(12,min_periods=12).min()
    unemployment=udiff.ge(.5).astype(float).where(udiff.notna())
    nom=monthly.long_yield
    nomavg=nom.shift(1).rolling(12,min_periods=12).mean()
    nomhigh=nom.gt(nomavg).astype(float).where(nom.notna()&nomavg.notna())
    real=nom-100*(monthly.cpi/monthly.cpi.shift(12)-1)
    realmed=real.shift(1).rolling(36,min_periods=36).median()
    realhigh=real.gt(realmed).astype(float).where(real.notna()&realmed.notna())
    curve=nom-bills.reindex(nom.index)
    conditions={'credit':(credit,2),'unemployment':(unemployment,3),'nominal_high':(nomhigh,2),'real_high':(realhigh,3),'curve_inverted':(curve.le(0).astype(float).where(curve.notna()),2),'spread':(spread,2),'unrate':(unrate,3),'nominal':(nom,2),'real':(real,3),'bill_yield':(bills,2)}
    macro=pd.DataFrame({k:known_monthly(s,idx,lag) for k,(s,lag) in conditions.items()})
    # E49 weights are lagged available industry membership, NOT stock weights.
    eqw=ew.notna().astype(float).div(ew.notna().sum(axis=1),axis=0).shift(1)
    eqmissing=(ew.isna() & eqw.fillna(0).gt(0)).any(axis=1)
    for date in eqmissing.index[eqmissing]:
        members=list(ew.columns[(ew.loc[date].isna() & eqw.loc[date].fillna(0).gt(0)).to_numpy()])
        missing_records.append({'source':'EW49','sleeve':'E49','date':str(date.date()),'members':','.join(members)})
    e49=(eqw*ew).sum(axis=1,min_count=1).where(~eqmissing)
    assets=vw.copy();assets['M']=m;assets['RF']=factors['RF']
    return {'index':idx,'factors':factors,'vw':vw,'ew':ew,'eligible':observed,'targets':targets,'gross':gross,'price':price,'breadth':breadth,'macro':macro,'assets':assets,'E49':e49,'counts':pd.DataFrame(counts),'shiller':monthly,'spx':spx(),'missing_records':missing_records}

def coverage(data):
    rows=[]
    for name in ['factors','momentum','size','ind12','ind17','ind49']:
        for label,df in french(name):
            rows.append({'source':name,'table':label,'first':str(df.index.min().date()),'last':str(df.index.max().date()),'rows':len(df),'columns':len(df.columns),'missing_cells':int(df.isna().sum().sum())})
    for name in ['BAA','BAA10YM','GS10','TB3MS','UNRATE']:
        s=fred(name);rows.append({'source':name,'first':str(s.index.min().date()),'last':str(s.index.max().date()),'rows':len(s),'missing_cells':int(s.isna().sum())})
    for name,s in [('Shiller',data['shiller'].long_yield),('S&P500_price',data['spx'])]:
        if len(s):rows.append({'source':name,'first':str(s.index.min().date()),'last':str(s.index.max().date()),'rows':len(s)})
    return pd.DataFrame(rows)

def manifest():
    from acquire import URLS
    urls=dict(URLS)
    for s in ['BAA','BAA10YM','GS10','TB3MS','UNRATE']:
        urls[s]=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}&cosd=1919-01-01&coed=2019-12-31'
    urls['shiller']='https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/1449043e-a1ed-4e2e-8e9c-7b9a2a064493/ie_data.xls?ver=1791297298731'
    urls['spx_yahoo']='https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=-1372723200&period2=1577836800&interval=1d'
    result=[]
    for name,url in urls.items():
        suffix='.zip' if name in ['factors','momentum','size','ind12','ind17','ind49','ind49monthly'] else ('.xls' if name=='shiller' else ('.json' if name=='spx_yahoo' else '.csv'))
        path=RAW/(name+suffix)
        if path.exists():
            b=path.read_bytes();result.append({'source':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    return result
