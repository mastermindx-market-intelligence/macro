"""Current incumbent publisher composition, temporary files and fake object IO.
No credentials, network, production publisher or retained materialization writes.
"""
from pathlib import Path
import shutil
import pytest
from tests.test_intl_policy_feed_preview import prepared
from tests.test_publish_r2 import _FakeS3
from scripts import publish_r2
from lib import config

@pytest.mark.parametrize('fault',[None,'failed_dependency','altered_dependency','changed_pointer'])
def test_exact_generation_dependencies_precede_pointer_or_leave_it_untouched(tmp_path,monkeypatch,fault):
    (tmp_path/'input').mkdir()
    _,_,descriptor,source,_,_,_=prepared(tmp_path/'input',monkeypatch)
    base=tmp_path/'site/feeds';base.mkdir(parents=True)
    for path in source.iterdir():
        if path.is_file():shutil.copyfile(path,base/path.name)
    current=base/'intl_generation_current.json'
    artifact=descriptor['artifact_name']
    original_pointer=current.read_bytes()
    if fault=='altered_dependency':(base/artifact).write_bytes(b'{}')
    class Store(_FakeS3):
        def upload_file(self,Filename,Bucket,Key,**kw):
            result=super().upload_file(Filename,Bucket,Key,**kw)
            if fault=='changed_pointer' and Key=='feeds/'+artifact:
                current.write_bytes(b'{}')
            return result
    store=Store(fail_keys={'feeds/'+artifact} if fault=='failed_dependency' else set())
    monkeypatch.setattr(publish_r2,'_client',lambda *_:store)
    monkeypatch.setattr(publish_r2,'_transfer_config',lambda:None)
    monkeypatch.setattr(publish_r2.time,'sleep',lambda *_:None)
    monkeypatch.setattr(config,'ROOT',tmp_path)
    monkeypatch.setattr(config,'load',lambda:{'storage':{'site_dir':'site','data_dir':'data'}})
    monkeypatch.setenv('R2_BUCKET','test-only-never-remote')
    result=publish_r2.publish(['feeds'],workers=1)
    pointer='feeds/intl_generation_current.json'
    if fault is None:
        assert result==0
        assert store.objects[pointer]==original_pointer
        assert store.uploaded[-1]==pointer
        assert 'feeds/'+artifact in store.uploaded[:-1]
        assert any('/intl_generation_descriptor_' in key for key in store.uploaded[:-1])
    else:
        assert result==1
        assert pointer not in store.objects and pointer not in store.uploaded
        assert store.manifest_puts==[]
