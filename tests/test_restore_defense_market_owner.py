from datetime import datetime, timezone
from hashlib import md5, sha256
from io import BytesIO
import json
from pathlib import Path
import pytest
from scripts.restore_defense_market_owner import restore_defense_market_owner, MAX_BYTES, TICKERS


class Client:
    def __init__(self):
        self.manifest = json.dumps({'dir':'massive_stock_day','count':5,
            'files':[t+'.parquet' for t in (*TICKERS,'SPY')],
            'store':{'latest_date':'2026-10-09','updated_at':'2026-10-10T00:00:00Z','coverage':{},'anchor':{}}}).encode()
        self.bodies = {'massive_stock_day/_manifest.json':self.manifest,
            **{'massive_stock_day/'+t+'.parquet': ('PAR1-'+t).encode() for t in TICKERS}}
        self.calls=[]; self.moved=False; self.bad_size=False; self.bad_body=False; self.list_moved=False; self.list_calls={}
    def get_object(self, **kwargs):
        key=kwargs['Key']; self.calls.append(kwargs)
        body=self.bodies[key]; etag=md5(body).hexdigest()
        if key.endswith('_manifest.json') and len([v for v in self.calls if v['Key']==key])>1 and self.moved:
            body+=b' '; etag=md5(body).hexdigest()
        if kwargs.get('IfMatch') and kwargs['IfMatch'] != '"'+etag+'"':
            raise ValueError('provider_precondition_failed')
        return {'Body':BytesIO(body + (b'x' if self.bad_body and key.endswith('LMT.parquet') else b'')),
            'ETag':'"'+etag+'"','ContentLength':len(body)+(1 if self.bad_size else 0),
            'LastModified':datetime(2026,10,10,tzinfo=timezone.utc)}
    def listing(self, client, bucket, key):
        self.list_calls[key]=self.list_calls.get(key,0)+1
        body=self.bodies[key]; etag=md5(body).hexdigest()
        if self.list_moved and self.list_calls[key]>1:etag='changed'
        return {key:(etag,len(body))}


def run(root, client):
    return restore_defense_market_owner(root,client=client,bucket='canonical-owner',list_objects=client.listing)


def test_exact_four_existing_files_and_publisher_receipt_preserve_collector_anchor(tmp_path):
    c=Client();store=tmp_path/'data/massive_stock_day';store.mkdir(parents=True);(store/'_manifest.json').write_bytes(b'collector anchor')
    result=run(tmp_path,c)
    assert (store/'_manifest.json').read_bytes()==b'collector anchor'
    assert (store/'.defense_read/manifest.json').read_bytes()==c.manifest
    receipt=json.loads((store/'.defense_read/read_receipt.json').read_bytes())
    assert receipt==result and receipt['state']=='STABLE_CANONICAL_SNAPSHOT_READ'
    assert set(result['objects'])==set(TICKERS) and result['manifest_before']['observed_at']!=result['manifest_after']['observed_at']
    for ticker in TICKERS:
        body=(store/(ticker+'.parquet')).read_bytes();assert sha256(body).hexdigest()==result['objects'][ticker]['sha256']
    assert all('IfMatch' in v for v in c.calls[1:])
    assert result['source_written'] is False and result['vendor_acquisition'] is False


@pytest.mark.parametrize('fault',['moved','bad_size','bad_body','list_moved'])
def test_changed_or_unqualified_remote_has_no_local_effect(tmp_path,fault):
    c=Client();setattr(c,fault,True)
    old=tmp_path/'data/massive_stock_day/LMT.parquet';old.parent.mkdir(parents=True);old.write_bytes(b'old valid bytes')
    with pytest.raises(ValueError):run(tmp_path,c)
    assert old.read_bytes()==b'old valid bytes' and not (old.parent/'.defense_read').exists()


@pytest.mark.parametrize('change',['missing','duplicate','count_bool','count_partial','wrong_store'])
def test_manifest_complete_membership_is_required_before_local_writes(tmp_path,change):
    c=Client();m=json.loads(c.manifest)
    if change=='missing':m['files'].remove('LMT.parquet');m['count']-=1
    if change=='duplicate':m['files'][0]=m['files'][1]
    if change=='count_bool':m['count']=True
    if change=='count_partial':m['count']=4
    if change=='wrong_store':m['dir']='other'
    c.bodies['massive_stock_day/_manifest.json']=json.dumps(m).encode()
    with pytest.raises(ValueError):run(tmp_path,c)
    assert not (tmp_path/'data').exists()


def test_bounded_object_read_refuses_oversize_before_effect(tmp_path):
    c=Client();c.bodies['massive_stock_day/LMT.parquet']=b'a'*(MAX_BYTES+1)
    with pytest.raises(ValueError,match='size'):run(tmp_path,c)
    assert not (tmp_path/'data').exists()


@pytest.mark.parametrize('location',['data','store','receipt_dir','parquet','dangling_parquet','manifest','receipt'])
def test_existing_local_redirects_refuse_entire_market_hydration_before_writes(tmp_path,location):
    c=Client();root=tmp_path/'root';root.mkdir();outside=tmp_path/'outside';outside.mkdir()
    store=root/'data/massive_stock_day'
    targets={'data':root/'data','store':store,'receipt_dir':store/'.defense_read','parquet':store/'LMT.parquet','dangling_parquet':store/'LMT.parquet','manifest':store/'.defense_read/manifest.json','receipt':store/'.defense_read/read_receipt.json'}
    link=targets[location];link.parent.mkdir(parents=True,exist_ok=True)
    dest=outside/'redirected'
    if location in ('data','store','receipt_dir'):dest.mkdir()
    elif location!='dangling_parquet':dest.write_bytes(b'protected bytes')
    link.symlink_to(dest)
    with pytest.raises(ValueError,match='symlink'):run(root,c)
    assert link.is_symlink() and not (outside/'RTX.parquet').exists()
    if location not in ('data','store','receipt_dir','dangling_parquet'):assert dest.read_bytes()==b'protected bytes'


@pytest.mark.parametrize('location',['parquet','receipt'])
def test_existing_directory_target_refuses_before_any_parquet_write(tmp_path,location):
    c=Client();root=tmp_path/'root';target=root/('data/massive_stock_day/RTX.parquet' if location=='parquet' else 'data/massive_stock_day/.defense_read/read_receipt.json');target.mkdir(parents=True)
    with pytest.raises(ValueError,match='not_file'):run(root,c)
    assert not (root/'data/massive_stock_day/LMT.parquet').exists()
