"""Tests for the Market Memory history command line interface.

All four archive callables are monkeypatched, so no real provider data, no
real archive module and no real file system outside ``tmp_path`` are touched.
Run inside the commissioned checkout with
``pytest tests/test_market_memory_history_cli.py``.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import scripts.market_memory_history as cli

SHA256 = "a" * 64
SHORT_SHA256 = "a" * 63
REQUEST = {"symbol": "SPY", "start": "2026-01-02", "end": "2026-10-01"}
PACKET = {
    "manifest": {"symbol": "SPY", "days": 1},
    "states": [{"date": "2026-01-02", "close": 1.0}],
    "outcomes": [{"date": "2026-01-05", "close": 1.1}],
}


class Recorder:
    """Callable stub that records every invocation and returns a canned result."""

    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result

    @property
    def last(self):
        assert self.calls, "expected the stub to have been called"
        return self.calls[-1]


@pytest.fixture()
def stubs(monkeypatch):
    """Install recording stubs for the four imported archive callables."""
    box = types.SimpleNamespace(
        assemble_history=Recorder(result=PACKET),
        write_archive=Recorder(result={"status": "written", "days": 1}),
        read_day=Recorder(result={"date": "2026-01-02", "state": {"close": 1.0}}),
        read_manifest=Recorder(result={"manifest_sha256": SHA256, "days": 1}),
    )
    for name in ("assemble_history", "write_archive", "read_day", "read_manifest"):
        monkeypatch.setattr(cli, name, getattr(box, name))
    return box


def run_cli(argv, capsys):
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def expect_usage_error(argv, capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(argv)
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    return captured.out, captured.err


def write_text(path, text):
    path.write_text(text, encoding="utf-8")
    return path


class TestBuild:
    def test_success_forwards_request_and_prints_receipt(self, tmp_path, stubs, capsys):
        request_path = write_text(tmp_path / "request.json", json.dumps(REQUEST))
        output_path = tmp_path / "archive-out"

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(output_path)], capsys
        )

        assert (code, err) == (0, "")
        assert stubs.assemble_history.calls == [((REQUEST,), {})]
        assert stubs.write_archive.last == ((PACKET, output_path), {})
        assert out.count("\n") == 1
        assert json.loads(out) == {"status": "written", "days": 1}

    def test_input_request_document_is_not_overwritten(self, tmp_path, stubs, capsys):
        request_path = write_text(tmp_path / "request.json", json.dumps(REQUEST))
        before = request_path.read_bytes()

        code, out, _ = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 0
        assert request_path.read_bytes() == before

    @pytest.mark.parametrize("text", ["{oops", "", "null", "[1, 2]", "42", '"text"'])
    def test_invalid_or_non_object_json_never_calls_assembler(
        self, tmp_path, stubs, capsys, text
    ):
        request_path = write_text(tmp_path / "request.json", text)

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 1
        assert stubs.assemble_history.calls == []
        assert stubs.write_archive.calls == []
        assert out == ""
        assert json.loads(err)["error"]

    def test_malformed_utf8_is_refused(self, tmp_path, stubs, capsys):
        request_path = tmp_path / "request.json"
        request_path.write_bytes(b'{"symbol": "\xff\xfe"}')

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 1
        assert stubs.assemble_history.calls == []
        assert out == ""
        assert json.loads(err)["error"]

    def test_input_over_128kib_is_refused(self, tmp_path, stubs, capsys):
        oversized = b'{"padding":"' + b"a" * cli.MAX_INPUT_BYTES + b'"}'
        assert len(oversized) > cli.MAX_INPUT_BYTES
        request_path = tmp_path / "big.json"
        request_path.write_bytes(oversized)

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 1
        assert stubs.assemble_history.calls == []
        assert out == ""
        assert str(cli.MAX_INPUT_BYTES) in json.loads(err)["error"]

    def test_input_exactly_128kib_is_accepted(self, tmp_path, stubs, capsys):
        head, tail = '{"padding":"', '"}'
        text = head + "a" * (cli.MAX_INPUT_BYTES - len(head) - len(tail)) + tail
        assert len(text.encode("utf-8")) == cli.MAX_INPUT_BYTES
        request_path = write_text(tmp_path / "edge.json", text)

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert (code, err) == (0, "")
        assert len(stubs.assemble_history.calls) == 1
        assert json.loads(out) == {"status": "written", "days": 1}

    def test_symlink_input_is_refused(self, tmp_path, stubs, capsys):
        real_path = write_text(tmp_path / "real.json", json.dumps(REQUEST))
        link_path = tmp_path / "link.json"
        link_path.symlink_to(real_path)

        code, out, err = run_cli(
            ["build", "--input", str(link_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 1
        assert stubs.assemble_history.calls == []
        assert out == ""
        assert "symlink" in json.loads(err)["error"]

    def test_missing_input_file_reports_error(self, tmp_path, stubs, capsys):
        code, out, err = run_cli(
            ["build", "--input", str(tmp_path / "absent.json"), "--output", str(tmp_path / "o")],
            capsys,
        )

        assert code == 1
        assert stubs.assemble_history.calls == []
        assert out == ""
        assert json.loads(err)["error"]

    def test_existing_output_directory_refusal_is_preserved(self, tmp_path, stubs, capsys):
        request_path = write_text(tmp_path / "request.json", json.dumps(REQUEST))
        existing = tmp_path / "already-there"
        existing.mkdir()
        stubs.write_archive.result = FileExistsError(f"target exists: {existing}")

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(existing)], capsys
        )

        assert code == 1
        assert len(stubs.assemble_history.calls) == 1
        assert out == ""
        assert "exists" in json.loads(err)["error"]

    def test_non_object_packet_is_refused_before_write(self, tmp_path, stubs, capsys):
        request_path = write_text(tmp_path / "request.json", json.dumps(REQUEST))
        stubs.assemble_history.result = ["not", "a", "dict"]

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 1
        assert stubs.write_archive.calls == []
        assert out == ""
        assert json.loads(err)["error"]

    def test_non_finite_receipt_is_refused(self, tmp_path, stubs, capsys):
        request_path = write_text(tmp_path / "request.json", json.dumps(REQUEST))
        stubs.write_archive.result = {"status": "written", "bytes": float("nan")}

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 1
        assert out == ""
        assert json.loads(err)["error"]

    def test_assembler_value_error_is_reported_not_raised(self, tmp_path, stubs, capsys):
        request_path = write_text(tmp_path / "request.json", json.dumps(REQUEST))
        stubs.assemble_history.result = ValueError("request failed schema validation")

        code, out, err = run_cli(
            ["build", "--input", str(request_path), "--output", str(tmp_path / "out")], capsys
        )

        assert code == 1
        assert out == ""
        assert "schema" in json.loads(err)["error"]


class TestDay:
    def test_forwarding_with_reveal_outcomes_defaulting_to_false(self, tmp_path, stubs, capsys):
        archive = tmp_path / "archive"

        code, out, err = run_cli(
            [
                "day", "--archive", str(archive), "--manifest-sha256", SHA256,
                "--date", "2026-01-02",
            ],
            capsys,
        )

        assert (code, err) == (0, "")
        assert stubs.read_day.last == (
            (archive, "2026-01-02"),
            {"expected_manifest_sha256": SHA256, "reveal_outcomes": False},
        )
        assert out.count("\n") == 1
        assert json.loads(out) == {"date": "2026-01-02", "state": {"close": 1.0}}

    def test_forwarding_with_reveal_outcomes_true(self, tmp_path, stubs, capsys):
        archive = tmp_path / "archive"

        code, out, err = run_cli(
            [
                "day", "--archive", str(archive), "--manifest-sha256", SHA256,
                "--date", "2026-01-02", "--reveal-outcomes",
            ],
            capsys,
        )

        assert (code, err) == (0, "")
        assert stubs.read_day.last == (
            (archive, "2026-01-02"),
            {"expected_manifest_sha256": SHA256, "reveal_outcomes": True},
        )
        assert json.loads(out) == {"date": "2026-01-02", "state": {"close": 1.0}}

    @pytest.mark.parametrize("missing", ["--manifest-sha256", "--date", "--archive"])
    def test_required_options_are_enforced(self, tmp_path, stubs, capsys, missing):
        argv = ["day", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256,
                "--date", "2026-01-02"]
        index = argv.index(missing)
        del argv[index:index + 2]

        out, err = expect_usage_error(argv, capsys)

        assert stubs.read_day.calls == []
        assert not out

    @pytest.mark.parametrize("digest", [SHORT_SHA256, "a" * 65, "z" * 64, "", "0x" + "a" * 62])
    def test_digest_must_be_exactly_64_hex_characters(self, tmp_path, stubs, capsys, digest):
        out, err = expect_usage_error(
            ["day", "--archive", str(tmp_path / "a"), "--manifest-sha256", digest,
             "--date", "2026-01-02"],
            capsys,
        )

        assert stubs.read_day.calls == []

    @pytest.mark.parametrize(
        "value", ["2026-13-01", "2026-02-30", "20261014", "26-01-02", "2026-1-2", "not-a-date"]
    )
    def test_date_must_be_real_yyyy_mm_dd(self, tmp_path, stubs, capsys, value):
        out, err = expect_usage_error(
            ["day", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256,
             "--date", value],
            capsys,
        )

        assert stubs.read_day.calls == []

    @pytest.mark.parametrize(
        "failure", [ValueError("manifest sha256 mismatch"), OSError("archive root missing")]
    )
    def test_operational_failure_reports_error_json(self, tmp_path, stubs, capsys, failure):
        stubs.read_day.result = failure

        code, out, err = run_cli(
            ["day", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256,
             "--date", "2026-01-02"],
            capsys,
        )

        assert code == 1
        assert out == ""
        assert json.loads(err)["error"]

    def test_non_finite_record_is_refused(self, tmp_path, stubs, capsys):
        stubs.read_day.result = {"date": "2026-01-02", "close": float("inf")}

        code, out, err = run_cli(
            ["day", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256,
             "--date", "2026-01-02"],
            capsys,
        )

        assert code == 1
        assert out == ""
        assert json.loads(err)["error"]


class TestInspect:
    def test_forwards_archive_and_digest_and_prints_manifest(self, tmp_path, stubs, capsys):
        archive = tmp_path / "archive"

        code, out, err = run_cli(
            ["inspect", "--archive", str(archive), "--manifest-sha256", SHA256], capsys
        )

        assert (code, err) == (0, "")
        assert stubs.read_manifest.calls == [((archive,), {"expected_manifest_sha256": SHA256})]
        assert out.count("\n") == 1
        assert json.loads(out) == {"manifest_sha256": SHA256, "days": 1}

    def test_manifest_sha256_is_mandatory(self, tmp_path, stubs, capsys):
        out, err = expect_usage_error(["inspect", "--archive", str(tmp_path / "a")], capsys)

        assert stubs.read_manifest.calls == []

    def test_operational_failure_reports_error_json(self, tmp_path, stubs, capsys):
        stubs.read_manifest.result = ValueError("manifest digest mismatch")

        code, out, err = run_cli(
            ["inspect", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256], capsys
        )

        assert code == 1
        assert out == ""
        assert json.loads(err) == {"error": "manifest digest mismatch"}

    def test_non_finite_manifest_is_refused(self, tmp_path, stubs, capsys):
        stubs.read_manifest.result = {"days": float("nan")}

        code, out, err = run_cli(
            ["inspect", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256], capsys
        )

        assert code == 1
        assert out == ""
        assert json.loads(err)["error"]


class TestCliContract:
    def test_missing_command_is_a_usage_error(self, stubs, capsys):
        out, err = expect_usage_error([], capsys)

        assert stubs.assemble_history.calls == []
        assert stubs.read_manifest.calls == []

    def test_unknown_command_is_a_usage_error(self, stubs, capsys):
        out, err = expect_usage_error(["frobnicate"], capsys)

        assert stubs.read_manifest.calls == []

    def test_keyboard_interrupt_is_never_swallowed(self, tmp_path, stubs, capsys):
        stubs.read_manifest.result = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            cli.main(["inspect", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256])

    def test_unavailable_archive_module_reports_clean_error(self, monkeypatch, tmp_path, capsys):
        for name in ("assemble_history", "write_archive", "read_day", "read_manifest"):
            monkeypatch.setattr(cli, name, None)

        code, out, err = run_cli(
            ["inspect", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256], capsys
        )

        assert code == 1
        assert out == ""
        assert "unavailable" in json.loads(err)["error"]

    def test_success_output_is_single_line_finite_json(self, tmp_path, stubs, capsys):
        code, out, err = run_cli(
            ["inspect", "--archive", str(tmp_path / "a"), "--manifest-sha256", SHA256], capsys
        )

        assert code == 0
        assert err == ""
        assert out.endswith("\n")
        json.loads(out)


class TestDossierAndExport:
    def test_dossier_forwards_exact_source_bindings(self,monkeypatch,capsys):
        stub=Recorder(result={'schema':'market_memory.daily_dossier.v1'})
        monkeypatch.setattr(cli,'build_daily_dossier',stub,raising=False)
        code,out,err=run_cli(['dossier','--archive','/archive','--manifest-sha256',SHA256,'--date','2020-02-13','--macro','/macro.json','--macro-sha256',SHA256],capsys)
        assert code==0 and not err
        assert stub.last==((Path('/archive'),'2020-02-13'),{'expected_manifest_sha256':SHA256,'macro_path':Path('/macro.json'),'expected_macro_sha256':SHA256,'reveal_outcomes':False})
    def test_export_is_default_outcome_free(self,monkeypatch,capsys):
        stub=Recorder(result={'html_sha256':SHA256})
        monkeypatch.setattr(cli,'export_browser',stub,raising=False)
        code,out,err=run_cli(['export','--archive','/archive','--manifest-sha256',SHA256,'--output','/new.html'],capsys)
        assert code==0 and not err
        assert stub.last==((Path('/archive'),Path('/new.html')),{'expected_manifest_sha256':SHA256,'macro_path':None,'expected_macro_sha256':None,'include_outcomes':False})
    def test_export_requires_explicit_outcome_inclusion(self,monkeypatch,capsys):
        stub=Recorder(result={'html_sha256':SHA256})
        monkeypatch.setattr(cli,'export_browser',stub,raising=False)
        code,out,err=run_cli(['export','--archive','/archive','--manifest-sha256',SHA256,'--output','/new.html','--include-outcomes'],capsys)
        assert code==0 and stub.last[1]['include_outcomes'] is True
    @pytest.mark.parametrize('command',['export','dossier'])
    def test_partial_macro_binding_never_calls_consumer(self,command,monkeypatch,capsys):
        def fail(*a,**k):pytest.fail('partial macro binding dispatched')
        monkeypatch.setattr(cli,'export_browser',fail,raising=False)
        monkeypatch.setattr(cli,'build_daily_dossier',fail,raising=False)
        args=[command,'--archive','/archive','--manifest-sha256',SHA256,'--macro','/macro.json']
        args+=['--date','2020-02-13'] if command=='dossier' else ['--output','/new.html']
        code,out,err=run_cli(args,capsys)
        assert code==1 and 'together' in json.loads(err)['error'] and not out


def test_cli_import_failure_has_reachable_compact_error(monkeypatch, capsys):
    import builtins
    import importlib.util
    original = builtins.__import__
    unavailable = {'engine.neuralweb.market_memory_history_archive',
                   'engine.neuralweb.market_memory_history_dossier',
                   'engine.neuralweb.market_memory_history_view'}
    def guarded(name, *args, **kwargs):
        if name in unavailable:
            raise ImportError('simulated missing source dependency')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    spec = importlib.util.spec_from_file_location('history_cli_missing_dependency', Path(cli.__file__))
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    for command in ('inspect', 'dossier', 'export'):
        args = [command, '--archive', 'not-opened', '--manifest-sha256', SHA256]
        if command == 'dossier': args += ['--date', '2020-01-05']
        if command == 'export': args += ['--output', 'not-written.html']
        assert candidate.main(args) == 1
        captured = capsys.readouterr()
        assert captured.out == '' and 'Traceback' not in captured.err
        assert 'unavailable' in json.loads(captured.err)['error']


def test_cli_normalizes_accepted_hex_case():
    assert cli._sha256_argument('ABCDEF01' * 8) == 'abcdef01' * 8



def test_cli_dossier_and_export_forward_explicit_filing_bindings(monkeypatch,tmp_path,capsys):
    dossier=Recorder(result={'filings':{'events':[]}});export=Recorder(result={'filing_events':0})
    monkeypatch.setattr(cli,'build_daily_dossier',dossier);monkeypatch.setattr(cli,'export_browser',export)
    common=['--archive',str(tmp_path/'history'),'--manifest-sha256',SHA256,
            '--filings',str(tmp_path/'earnings_8k_dates.parquet'),'--filings-sha256',SHA256]
    assert cli.main(['dossier',*common,'--date','2020-03-16','--filings-offset','50'])==0
    assert dossier.last[1]['filings_path']==tmp_path/'earnings_8k_dates.parquet'
    assert dossier.last[1]['expected_filings_sha256']==SHA256 and dossier.last[1]['filings_offset']==50
    assert cli.main(['export',*common,'--output',str(tmp_path/'out.html')])==0
    assert export.last[1]['filings_path']==tmp_path/'earnings_8k_dates.parquet'
    assert export.last[1]['expected_filings_sha256']==SHA256
    assert 'filings_offset' not in export.last[1]


class TestExtend:
    def test_forwards_exact_parent_new_request_and_new_destination(self,monkeypatch,tmp_path,capsys):
        box=Recorder(result={'status':'EXTENDED','added_state_rows':5})
        monkeypatch.setattr(cli,'extend_archive',box,raising=False)
        source=write_text(tmp_path/'next.json',json.dumps(REQUEST))
        code,out,err=run_cli(['extend','--archive',str(tmp_path/'parent'),
            '--manifest-sha256',SHA256,'--input',str(source),'--output',str(tmp_path/'next')],capsys)
        assert code==0 and err==''
        assert box.last==((tmp_path/'parent',REQUEST,tmp_path/'next'),{'expected_parent_manifest_sha256':SHA256})
        assert json.loads(out)['status']=='EXTENDED'

    def test_no_new_data_receipt_is_not_written_as_archive(self,monkeypatch,tmp_path,capsys):
        monkeypatch.setattr(cli,'extend_archive',Recorder(result={'status':'NO_NEW_OBSERVATIONS','output_created':False}),raising=False)
        source=write_text(tmp_path/'next.json',json.dumps(REQUEST))
        code,out,err=run_cli(['extend','--archive',str(tmp_path/'parent'),
            '--manifest-sha256',SHA256,'--input',str(source),'--output',str(tmp_path/'next')],capsys)
        assert code==0 and json.loads(out)['output_created'] is False and not (tmp_path/'next').exists()



def test_cli_forwards_offline_transcript_catalog(monkeypatch,tmp_path,capsys):
    box=Recorder(result={'transcript_records':1});monkeypatch.setattr(cli,'export_browser',box)
    assert cli.main(['export','--archive',str(tmp_path/'archive'),'--manifest-sha256',SHA256,
        '--output',str(tmp_path/'out.html'),'--transcripts-catalog',str(tmp_path/'catalog.json'),
        '--transcripts-catalog-sha256',SHA256])==0
    assert box.last[1]['transcripts_catalog_path']==tmp_path/'catalog.json'
    assert box.last[1]['expected_transcripts_catalog_sha256']==SHA256



def test_cli_catalog_uses_bound_metadata_only_and_never_overwrites(tmp_path,capsys):
    from tests.test_market_memory_history_transcripts import payload
    from lib.dataos.web_workspace import load_workspace_config
    raw=payload();source=tmp_path/'stock_earning_call_transcripts.parquet';source.write_bytes(raw)
    registry=tmp_path/'registry.yml';registry.write_text('schema: dataset_registry.v1\ndatasets: []\n')
    config=tmp_path/'host.json';config.write_text(json.dumps({'schema_version':'mastermind.data_workspace_bindings/v1',
        'registry_path':str(registry),'roots':[{'alias':'fixture','path':str(tmp_path),'evidence_kind':'research_capture','note':'synthetic fixture'}]}))
    ws=load_workspace_config(config);version=ws.describe('fixture:'+source.name)['source']['file_version']
    output=tmp_path/'call-catalog.json'
    args=['transcripts-catalog','--config',str(config),'--ref','fixture:'+source.name,
          '--expected-version',version,'--output',str(output)]
    assert cli.main(args)==0
    report=json.loads(capsys.readouterr().out)
    assert report['records']==1 and report['body_columns_read'] is False
    stored=output.read_bytes();assert b'Original words' not in stored
    assert source.read_bytes()==raw
    assert cli.main(args)==1
    assert output.read_bytes()==stored and 'error' in json.loads(capsys.readouterr().err)
