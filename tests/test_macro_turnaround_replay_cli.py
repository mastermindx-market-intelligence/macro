from pathlib import Path
import importlib
import json
import sys

import pytest

# Reuse the sibling fixture regardless of pytest package/import mode.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_macro_turnaround_replay import api, source_tree  # noqa: E402

def cli():
    try:return importlib.import_module('scripts.replay_macro_turnaround')
    except ModuleNotFoundError:pytest.fail('The replay machine-consumer CLI is not implemented')

def request(path,h):
    path.write_text(json.dumps({'schema':'macro.turnaround_replay_request.v1',
      'manifest_sha256':h,'bindings':[{'key':'ppi','series_id':'PPIFIS','family':'inflation'}],
      'cutoffs':['2022-02-10'],'domain':'inflation','config':{}}))

def test_cli_executes_real_adapter_engine_and_immutable_publisher(tmp_path,monkeypatch):
    c=cli();m=api();root=tmp_path/'source';mp,p,h,df=source_tree(root)
    req=tmp_path/'request.json';request(req,h);out=tmp_path/'replay.json';calls=[]
    loader=m.load_panel
    def with_test_decoder(*args,**kw):calls.append(True);return loader(*args,decoder=lambda b:df,**kw)
    monkeypatch.setattr(c,'load_panel',with_test_decoder)
    args=['--root',str(root),'--input',str(req),'--output',str(out)]
    assert c.main(args)==0
    first=out.read_bytes();inode=out.stat().st_ino
    assert c.main(args)==0 and out.stat().st_ino==inode and out.read_bytes()==first
    report=json.loads(first)
    assert len(calls)==2 and report['rows'][0]['selected']['ppi']['value']==df.iloc[-1]['value']
    assert report['source_receipt']['production_parser_executed'] is False
    assert report['authority']['trade_authority'] is False
    assert p.read_bytes()==b'synthetic parquet bytes; decoder is explicitly injected'

@pytest.mark.parametrize('raw',['[]','null','{"schema":"x","schema":"y"}','{}'])
def test_cli_invalid_request_fails_cleanly_without_output(tmp_path,raw,capsys):
    c=cli();req=tmp_path/'bad.json';req.write_text(raw);out=tmp_path/'out.json'
    assert c.main(['--root',str(tmp_path),'--input',str(req),'--output',str(out)])==2
    assert not out.exists()
    captured=capsys.readouterr();assert 'ERROR' in captured.err and 'Traceback' not in captured.err

@pytest.mark.parametrize('target',['input','manifest','parquet','generated_site'])
def test_cli_cannot_write_into_source_or_generated_product(tmp_path,target,monkeypatch):
    c=cli();root=tmp_path/'source';mp,p,h,df=source_tree(root);req=tmp_path/'request.json';request(req,h)
    out={'input':req,'manifest':mp,'parquet':p,'generated_site':root/'site/turns.json'}[target]
    before=out.read_bytes() if out.exists() else None
    def forbidden_loader(*args,**kw):raise AssertionError('forbidden output must fail BEFORE source ingestion')
    monkeypatch.setattr(c,'load_panel',forbidden_loader)
    assert c.main(['--root',str(root),'--input',str(req),'--output',str(out)])==2
    assert (out.read_bytes() if out.exists() else None)==before


@pytest.mark.parametrize('directory',['data','site'])
def test_cli_refuses_symlinked_root_data_destination_before_ingestion(tmp_path,monkeypatch,directory):
    c=cli();root=tmp_path/'source';root.mkdir();canonical=tmp_path/f'canonical-{directory}';canonical.mkdir()
    (root/directory).symlink_to(canonical,target_is_directory=True)
    req=tmp_path/'request.json';request(req,'0'*64);out=canonical/'turns.json'
    def forbidden_loader(*args,**kw):raise AssertionError('symlinked canonical path must fail before source ingestion')
    monkeypatch.setattr(c,'load_panel',forbidden_loader)
    assert c.main(['--root',str(root),'--input',str(req),'--output',str(out)])==2
    assert not out.exists()


def test_no_parser_fallback_when_arrow_is_absent(tmp_path,monkeypatch,capsys):
    c=cli();m=api();root=tmp_path/'source';mp,p,h,df=source_tree(root);req=tmp_path/'request.json';request(req,h);out=tmp_path/'out.json'
    def missing(*args,**kw):raise ImportError('No Arrow installed')
    monkeypatch.setattr(m.pd,'read_parquet',missing)
    assert c.main(['--root',str(root),'--input',str(req),'--output',str(out)])==2
    assert not out.exists()
    assert 'Parquet parser dependency unavailable' in capsys.readouterr().err
