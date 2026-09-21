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


@pytest.mark.parametrize(("canonical_name", "alias_name"), [("data", "DATA"), ("site", "SITE")])
def test_cli_refuses_case_insensitive_alias_before_source_ingestion(
    tmp_path, monkeypatch, canonical_name, alias_name
):
    import os

    c=cli();root=tmp_path/'source';root.mkdir();(root/canonical_name).mkdir()
    req=tmp_path/'request.json';request(req,'0'*64)
    out=root/alias_name/'nested'/'turns.json'
    real_samefile=os.path.samefile
    def case_insensitive_samefile(left,right):
        if str(Path(left).absolute()).casefold()==str(Path(right).absolute()).casefold():
            return True
        return real_samefile(left,right)
    monkeypatch.setattr(os.path,'samefile',case_insensitive_samefile)
    def forbidden_loader(*args,**kw):
        raise AssertionError('protected alias must fail before source ingestion')
    monkeypatch.setattr(c,'load_panel',forbidden_loader)
    assert c.main(['--root',str(root),'--input',str(req),'--output',str(out)])==2
    assert not out.exists()
    assert not (root/canonical_name/'nested'/'turns.json').exists()


def test_cli_dangling_case_witness_still_refuses_alias_before_source_ingestion(
    tmp_path, monkeypatch
):
    import os

    c = cli()
    publisher = importlib.import_module(
        "scripts.build_macro_turnaround_research"
    )
    root = tmp_path / "source"
    root.mkdir()
    (root / "A_Dangling").symlink_to(root / "missing-target")
    (root / "CaseWitness").write_text("valid witness", encoding="utf-8")
    request_path = tmp_path / "request.json"
    request(request_path, "0" * 64)
    output = root / "SITE" / "nested" / "turns.json"
    resolved_root = root.resolve()
    real_samefile = os.path.samefile

    def mounted_case_insensitive_samefile(left, right):
        left_path = Path(left).absolute()
        right_path = Path(right).absolute()
        if "dangling" in left_path.name.casefold():
            raise FileNotFoundError("dangling case witness")
        if (
            left_path.parent == resolved_root
            and right_path.parent == resolved_root
            and {left_path.name, right_path.name}
            == {"CaseWitness", "caseWitness"}
        ):
            return True
        return real_samefile(left, right)

    monkeypatch.setattr(
        publisher.os.path, "samefile", mounted_case_insensitive_samefile
    )

    def forbidden_loader(*args, **kwargs):
        raise AssertionError("protected alias must fail before source ingestion")

    monkeypatch.setattr(c, "load_panel", forbidden_loader)
    assert c.main(
        ["--root", str(root), "--input", str(request_path), "--output", str(output)]
    ) == 2
    assert not output.exists()


def test_cli_refuses_replaced_case_witness_before_source_ingestion(
    tmp_path, monkeypatch
):
    import os

    c = cli()
    publisher = importlib.import_module(
        "scripts.build_macro_turnaround_research"
    )
    root = tmp_path / "source"
    root.mkdir()
    witness = root / "CaseWitness"
    witness.write_text("original witness", encoding="utf-8")
    replacement = tmp_path / "replacement"
    replacement.write_text("replacement witness", encoding="utf-8")
    request_path = tmp_path / "request.json"
    request(request_path, "0" * 64)
    output = root / "SITE" / "nested" / "turns.json"
    real_samefile = os.path.samefile
    replaced = False

    def replacing_samefile(left, right):
        nonlocal replaced
        left_path = Path(left).absolute()
        if not replaced and left_path == witness.absolute():
            witness.unlink()
            replacement.replace(witness)
            replaced = True
            return False
        return real_samefile(left, right)

    monkeypatch.setattr(publisher.os.path, "samefile", replacing_samefile)

    def forbidden_loader(*args, **kwargs):
        raise AssertionError("unstable case witness must fail before source ingestion")

    monkeypatch.setattr(c, "load_panel", forbidden_loader)
    assert c.main(
        ["--root", str(root), "--input", str(request_path), "--output", str(output)]
    ) == 2
    assert replaced
    assert not output.exists()


def test_cli_refuses_destination_alias_change_after_preflight(tmp_path,monkeypatch):
    c=cli();root=tmp_path/'source';protected=root/'data';protected.mkdir(parents=True)
    outside=tmp_path/'outside';outside.mkdir();alias=tmp_path/'alias';alias.symlink_to(outside,target_is_directory=True)
    req=tmp_path/'request.json';request(req,'0'*64);out=alias/'turns.json'
    def swap_then_load(*args,**kw):
        alias.unlink();alias.symlink_to(protected,target_is_directory=True);return object()
    monkeypatch.setattr(c,'load_panel',swap_then_load)
    monkeypatch.setattr(c,'replay',lambda *args,**kw:{'rows':[]})
    assert c.main(['--root',str(root),'--input',str(req),'--output',str(out)])==2
    assert not (protected/'turns.json').exists()
    assert not (outside/'turns.json').exists()


def test_cli_refuses_intermediate_ancestor_redirection_in_shared_publisher(
    tmp_path, monkeypatch
):
    c = cli()
    publisher = importlib.import_module("scripts.build_macro_turnaround_research")
    root = tmp_path / "source"
    gateway = root / "research"
    safe_storage = root / "research-safe"
    protected = root / "data"
    (gateway / "leaf").mkdir(parents=True)
    (protected / "leaf").mkdir(parents=True)
    req = tmp_path / "request.json"
    request(req, "0" * 64)
    out = gateway / "leaf" / "turns.json"
    original_assert = publisher._assert_research_output_path

    def point_to_safe_tree():
        if gateway.is_symlink():
            gateway.unlink()
            safe_storage.rename(gateway)

    def point_to_protected_tree():
        if not gateway.is_symlink():
            gateway.rename(safe_storage)
            gateway.symlink_to(protected, target_is_directory=True)

    def alternating_guard(path, *, root=None, **kwargs):
        point_to_safe_tree()
        original_assert(path, root=root, **kwargs)
        point_to_protected_tree()

    monkeypatch.setattr(c, "load_panel", lambda *args, **kwargs: object())
    monkeypatch.setattr(c, "replay", lambda *args, **kwargs: {"rows": []})
    monkeypatch.setattr(publisher, "_assert_research_output_path", alternating_guard)
    try:
        assert c.main(
            ["--root", str(root), "--input", str(req), "--output", str(out)]
        ) == 2
    finally:
        point_to_safe_tree()

    assert not (protected / "leaf" / "turns.json").exists()
    assert not out.exists()
    assert not list((protected / "leaf").glob(".*.tmp"))
    assert not list((gateway / "leaf").glob(".*.tmp"))


def test_cli_refuses_protected_root_change_after_preflight(tmp_path,monkeypatch):
    c=cli();root=tmp_path/'source';protected=root/'data';protected.mkdir(parents=True)
    outside=tmp_path/'outside';outside.mkdir();req=tmp_path/'request.json';request(req,'0'*64);out=outside/'turns.json'
    def swap_then_load(*args,**kw):
        protected.rmdir();protected.symlink_to(outside,target_is_directory=True);return object()
    monkeypatch.setattr(c,'load_panel',swap_then_load)
    monkeypatch.setattr(c,'replay',lambda *args,**kw:{'rows':[]})
    assert c.main(['--root',str(root),'--input',str(req),'--output',str(out)])==2
    assert not out.exists()


def test_no_parser_fallback_when_arrow_is_absent(tmp_path,monkeypatch,capsys):
    c=cli();m=api();root=tmp_path/'source';mp,p,h,df=source_tree(root);req=tmp_path/'request.json';request(req,h);out=tmp_path/'out.json'
    def missing(*args,**kw):raise ImportError('No Arrow installed')
    monkeypatch.setattr(m.pd,'read_parquet',missing)
    assert c.main(['--root',str(root),'--input',str(req),'--output',str(out)])==2
    assert not out.exists()
    assert 'Parquet parser dependency unavailable' in capsys.readouterr().err
