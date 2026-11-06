"""Explicit producer identity and private/public catalog boundary at the CLI."""
import inspect
import json
import sys

import pytest

from engine.research_vault import ingest, r2_store
from scripts import ingest_research as cli
from engine.research_vault.generation_evidence import FileGenerationEvidence, EvidenceUnavailable, read_evidence


COMMIT = "0123456789abcdef0123456789abcdef01234567"
RUN = "actions-123456789-attempt-1"
IDENTITY_ARGS = ["--generation-source-commit", COMMIT, "--generation-run", RUN]


@pytest.fixture
def invocation(monkeypatch, tmp_path):
    mirror = tmp_path / "mirror"
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: mirror)
    monkeypatch.setattr(sys, "argv", ["ingest_research"])
    store, calls = object(), []
    signature = inspect.signature(ingest.run)
    summary = {"ingested": 0, "skipped": 0, "failed": 0, "needs_metadata": 0,
               "corpus_published": True, "catalog_published": True,
               "catalog_bytes": b"", "error": None, "receipts_unflushed": 0}

    def run(actual_store, path, **kwargs):
        signature.bind(actual_store, path, **kwargs)
        assert actual_store is store
        calls.append(kwargs)
        return summary

    monkeypatch.setattr(ingest, "run", run)
    monkeypatch.setattr(r2_store, "build_store", lambda **kwargs: store)
    return mirror, calls, summary


def test_identity_reaches_actual_engine_interface(invocation, monkeypatch, tmp_path):
    _, calls, _ = invocation
    monkeypatch.setattr(sys, "argv", ["ingest_research", *IDENTITY_ARGS, "--generation-evidence-path", str(tmp_path / "original.jsonl")])
    assert cli.main() == 0
    evidence = calls[0].pop("generation_evidence")
    assert type(evidence) is FileGenerationEvidence and evidence._fd is None
    assert evidence.identity == {"source_commit": COMMIT, "run": RUN}
    assert calls == [{"dry_run": False,
                      "generation_identity": {"source_commit": COMMIT, "run": RUN}}]


def test_legacy_call_does_not_infer_identity(invocation, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    monkeypatch.setenv("GITHUB_RUN_ID", "123456789")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    assert cli.main() == 0
    assert invocation[1] == [{"dry_run": False}]


@pytest.mark.parametrize("args", [
    ["--generation-source-commit", COMMIT], ["--generation-run", RUN],
    ["--generation-source-commit", "a" * 39, "--generation-run", RUN],
    ["--generation-source-commit", "g" * 40, "--generation-run", RUN],
    ["--generation-source-commit", COMMIT.upper(), "--generation-run", RUN],
    ["--generation-source-commit", "", "--generation-run", RUN],
    ["--generation-source-commit", COMMIT, "--generation-run", ""],
    ["--generation-source-commit", COMMIT, "--generation-run", "   "],
    ["--generation-source-commit", COMMIT, "--generation-run", " " + RUN],
    ["--generation-source-commit", COMMIT, "--generation-run", RUN + "\n"],
    [*IDENTITY_ARGS, "--dry-run"], [*IDENTITY_ARGS, "--materialize-only"],
])
def test_invalid_identity_refuses_before_store_access(invocation, monkeypatch, args):
    monkeypatch.setattr(r2_store, "build_store",
                        lambda **kwargs: pytest.fail("store opened before argument validation"))
    monkeypatch.setattr(sys, "argv", ["ingest_research", *args])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert invocation[1] == []


def test_public_projection_preserves_private_bytes_and_nested_content(invocation, monkeypatch, tmp_path):
    mirror, _, summary = invocation
    item = {"id": "fixture", "producer_generation": "ordinary nested content"}
    private = json.dumps({"items": [item], "producer_generation": {"state": "COMPLETE"}}).encode()
    summary["catalog_bytes"] = private
    monkeypatch.setattr(sys, "argv", ["ingest_research", *IDENTITY_ARGS, "--generation-evidence-path", str(tmp_path / "original.jsonl")])
    assert cli.main() == 0
    assert summary["catalog_bytes"] == private
    assert json.loads((mirror / "catalog.json").read_bytes()) == {"items": [item]}


def test_legacy_public_snapshot_keeps_exact_bytes(invocation):
    mirror, _, summary = invocation
    summary["catalog_bytes"] = b'{ "items" : [] }\n\n'
    assert cli.main() == 0
    assert (mirror / "catalog.json").read_bytes() == summary["catalog_bytes"]


@pytest.mark.parametrize("name", ["rv%2Fprivate", "rv?private", "rv#private"])
def test_excerpt_projection_reads_the_named_corpus_not_uri_decoy(invocation, monkeypatch, tmp_path, name):
    import sqlite3
    from urllib.parse import unquote, urlsplit
    from engine.research_vault import excerpt

    mirror, _, summary = invocation
    named = tmp_path / name / "corpus.sqlite"
    decoy = Path(unquote(urlsplit(f"file:{named}?mode=ro").path))
    assert decoy != named
    for path, marker in [(named, 7), (decoy, 9)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.execute(f"PRAGMA user_version={marker}")
        connection.close()
    summary["catalog_bytes"] = b'{"items":[{"id":"fixture"}]}'
    monkeypatch.setattr(excerpt, "snapshot", lambda connection, ids: {
        "fixture": [str(connection.execute("PRAGMA user_version").fetchone()[0])]})
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--corpus", str(named)])
    assert cli.main() == 0
    assert json.loads((mirror / "excerpts.json").read_bytes())["excerpts"] == {"fixture": ["7"]}


@pytest.mark.parametrize("invalid", [b'{invalid', b'\xff'])
def test_invalid_canonical_bytes_do_not_advance_existing_snapshot(invocation, invalid):
    mirror, _, summary = invocation
    mirror.mkdir()
    target = mirror / "catalog.json"
    target.write_bytes(b'{"items":[]}\n')
    summary["catalog_bytes"] = invalid
    assert cli.main() == 0
    assert target.read_bytes() == b'{"items":[]}\n'


def _generation_args(path):
    return ["ingest_research", *IDENTITY_ARGS, "--generation-evidence-path", str(path)]


@pytest.mark.parametrize("args", [IDENTITY_ARGS, ["--generation-evidence-path", "somewhere"],
    [*IDENTITY_ARGS, "--generation-evidence-path", ""],
    [*IDENTITY_ARGS, "--generation-evidence-path", "  "],
    [*IDENTITY_ARGS, "--generation-evidence-path", "somewhere", "--dry-run"],
    [*IDENTITY_ARGS, "--generation-evidence-path", "somewhere", "--materialize-only"]])
def test_evidence_argument_errors_touch_neither_file_nor_store(invocation, monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["ingest_research", *args])
    monkeypatch.setattr(FileGenerationEvidence, "create", lambda *a, **k: pytest.fail("file touched"))
    monkeypatch.setattr(r2_store, "build_store", lambda **k: pytest.fail("store touched"))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


def test_header_and_open_sink_precede_store_and_engine(invocation, monkeypatch, tmp_path):
    path = tmp_path / "original.jsonl"
    actual_store = object()
    def build(**kwargs):
        header = json.loads(path.read_bytes().splitlines()[0])
        assert header["event"]["payload"]["identity"] == {"source_commit": COMMIT, "run": RUN}
        with pytest.raises(EvidenceUnavailable):
            read_evidence(path, expected_identity={"source_commit": COMMIT, "run": RUN})
        return actual_store
    signature = inspect.signature(ingest.run)
    def run(store, corpus_path, **kwargs):
        signature.bind(store, corpus_path, **kwargs)
        assert store is actual_store
        assert kwargs["generation_evidence"]._fd is not None
        return invocation[2]
    monkeypatch.setattr(r2_store, "build_store", build)
    monkeypatch.setattr(ingest, "run", run)
    monkeypatch.setattr(sys, "argv", _generation_args(path))
    assert cli.main() == 0
    assert len(read_evidence(path, expected_identity={"source_commit": COMMIT, "run": RUN})) == 1


@pytest.mark.parametrize("kind", ["existing", "missing_parent", "public_mirror", "source", "public_symlink"])
def test_unavailable_or_public_evidence_refuses_before_store(invocation, monkeypatch, tmp_path, kind):
    path = tmp_path / "original.jsonl"
    original = b"do not truncate"
    if kind == "existing":
        path.write_bytes(original)
    elif kind == "missing_parent":
        path = tmp_path / "missing" / "original.jsonl"
    elif kind in ("public_mirror", "public_symlink"):
        invocation[0].mkdir(mode=0o700)
        path = invocation[0] / "original.jsonl"
        if kind == "public_symlink":
            alias = tmp_path / "alias"
            alias.symlink_to(invocation[0], target_is_directory=True)
            path = alias / "original.jsonl"
    elif kind == "source":
        fake = tmp_path / "source"; fake.mkdir(mode=0o700)
        monkeypatch.setattr(cli, "__file__", str(fake / "scripts" / "ingest_research.py"))
        path = fake / "original.jsonl"
    monkeypatch.setattr(r2_store, "build_store", lambda **k: pytest.fail("store touched"))
    monkeypatch.setattr(sys, "argv", _generation_args(path))
    assert cli.main() == 1
    if kind == "existing": assert path.read_bytes() == original
    else: assert not path.exists()


@pytest.mark.parametrize("failure", ["engine", "missing_store", "store_exception", "process_exit"])
def test_original_journal_closes_after_every_pipeline_exit(invocation, monkeypatch, tmp_path, failure):
    path = tmp_path / "original.jsonl"
    if failure == "missing_store": monkeypatch.setattr(r2_store, "build_store", lambda **k: None)
    elif failure == "store_exception":
        def bad_store(**k): raise RuntimeError("store construction failed")
        monkeypatch.setattr(r2_store, "build_store", bad_store)
    else:
        def failed(*a, **k):
            if failure == "process_exit": raise SystemExit(17)
            raise RuntimeError("synthetic engine failure")
        monkeypatch.setattr(ingest, "run", failed)
    monkeypatch.setattr(sys, "argv", _generation_args(path))
    if failure == "process_exit":
        with pytest.raises(SystemExit): cli.main()
    else: assert cli.main() == 1
    assert len(read_evidence(path, expected_identity={"source_commit": COMMIT, "run": RUN})) == 1


def test_close_failure_is_nonzero_and_never_retried(invocation, monkeypatch, tmp_path):
    path = tmp_path / "original.jsonl"
    original = FileGenerationEvidence.close
    calls = []
    def failed_close(self):
        calls.append(1)
        original(self)
        raise EvidenceUnavailable("synthetic lost close return")
    monkeypatch.setattr(FileGenerationEvidence, "close", failed_close)
    monkeypatch.setattr(sys, "argv", _generation_args(path))
    assert cli.main() == 1
    assert calls == [1]
    assert path.exists()


def test_real_ingestion_carries_private_journal_to_complete(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    from engine.research_vault import catalog, corpus, fulltext_writer
    now = datetime(2026, 10, 13, tzinfo=timezone.utc)
    item = {"id": "desk-synthetic", "title": "Synthetic note", "institution": "Desk"}
    store = r2_store.LocalStore(tmp_path / "store")
    initial = tmp_path / "initial.sqlite"
    conn = corpus.open_db(initial)
    corpus.upsert(conn, item, "synthetic body only", facts={"content_sha256": "a" * 64, "text_layer": "full"})
    conn.close()
    doc = {"schema": catalog.SCHEMA, "generated_at": now.isoformat(), "count": 1,
           "institutions": ["Desk"], "items": [item]}
    store.put_bytes(catalog.CATALOG_KEY, json.dumps(doc).encode())
    store.put_bytes("research_vault/corpus.sqlite", initial.read_bytes())
    monkeypatch.setattr(r2_store, "build_store", lambda **k: store)
    monkeypatch.setattr(ingest, "_list_inbox_pdfs", lambda _: [])
    monkeypatch.setattr(fulltext_writer, "materialize_pending", lambda *a, **k: {"aborted": None})
    mirror = tmp_path / "public"
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: mirror)
    journal = tmp_path / "original.jsonl"
    monkeypatch.setattr(sys, "argv", _generation_args(journal))
    assert cli.main() == 0
    events = read_evidence(journal, expected_identity={"source_commit": COMMIT, "run": RUN})
    assert events[-1]["kind"] == "terminal" and events[-1]["payload"]["state"] == "COMPLETE"
    assert any(e["kind"] == "publication_plan" and e["payload"]["catalog_base64"] for e in events)
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]["state"] == "COMPLETE"
    assert "producer_generation" not in json.loads((mirror / "catalog.json").read_bytes())
    assert not (mirror / "original.jsonl").exists()


# Original capture output must not alter the producer result.
import hashlib
from pathlib import Path
@pytest.mark.parametrize("outcome", ["ok", "failed", "exception", "interrupted"])
def test_original_run_emits_only_its_capture_digest_after_close(tmp_path, monkeypatch, capsys, outcome):
    path = tmp_path / "journal.jsonl"
    identity = {"source_commit": "a" * 40, "run": "synthetic-original"}
    original_close = FileGenerationEvidence.close
    closed = []
    def close(sink):
        original_close(sink)
        closed.append(sink)
    monkeypatch.setattr(FileGenerationEvidence, "close", close)
    def run(a, gen_src, gen_run, sink, *args):
        sink.append("write_intent", {"private_body": "PRIVATE_JOURNAL_SENTINEL"})
        if outcome == "exception":
            raise RuntimeError("synthetic failure")
        if outcome == "interrupted":
            raise KeyboardInterrupt
        return 0 if outcome == "ok" else 1
    monkeypatch.setattr(cli, "_run_pipeline", run)
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: tmp_path / "mirror")
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--generation-source-commit", identity["source_commit"],
        "--generation-run", identity["run"], "--generation-evidence-path", str(path)])
    if outcome == "interrupted":
        with pytest.raises(KeyboardInterrupt):
            cli.main()
    else:
        assert cli.main() == (0 if outcome == "ok" else 1)
    output = capsys.readouterr().out
    notices = [s for s in output.splitlines() if s.startswith("ingest_research: original_capture_sha256=")]
    assert notices == ["ingest_research: original_capture_sha256=" + hashlib.sha256(path.read_bytes()).hexdigest()]
    assert len(closed) == 1 and closed[0]._fd is None
    assert "PRIVATE_JOURNAL_SENTINEL" not in output and str(path) not in output


def test_failed_close_emits_no_capture_and_never_retries_close(tmp_path, monkeypatch, capsys):
    original_close = FileGenerationEvidence.close
    calls = []
    def close(sink):
        original_close(sink)
        sink._capture_sha256 = None
        calls.append(True)
        raise EvidenceUnavailable("synthetic close failure")
    monkeypatch.setattr(FileGenerationEvidence, "close", close)
    monkeypatch.setattr(cli, "_run_pipeline", lambda *a: 0)
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: tmp_path / "mirror")
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--generation-source-commit", "a"*40,
        "--generation-run", "synthetic-original", "--generation-evidence-path", str(tmp_path / "journal.jsonl")])
    assert cli.main() == 1
    assert calls == [True]
    assert "original_capture_sha256=" not in capsys.readouterr().out


@pytest.mark.parametrize("outcome", ["ok", "failed", "exception", "interrupted", "system_exit"])
@pytest.mark.parametrize("write_error", [BrokenPipeError, ValueError])
def test_capture_notice_failure_preserves_original_lane_result(tmp_path, monkeypatch, capsys, outcome, write_error):
    import builtins
    original_print = builtins.print
    notices = []
    def fail_notice(*args, **kwargs):
        if args and str(args[0]).startswith("ingest_research: original_capture_sha256="):
            notices.append(args[0])
            raise write_error("synthetic capture output unavailable")
        return original_print(*args, **kwargs)
    monkeypatch.setattr(cli, "print", fail_notice, raising=False)
    def pipeline(*args):
        if outcome == "exception":
            raise RuntimeError("ORIGINAL_INGEST_FAILURE")
        if outcome == "interrupted":
            raise KeyboardInterrupt
        if outcome == "system_exit":
            raise SystemExit(17)
        return 0 if outcome == "ok" else 1
    monkeypatch.setattr(cli, "_run_pipeline", pipeline)
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: tmp_path / "mirror")
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--generation-source-commit", "a"*40,
        "--generation-run", "synthetic-original", "--generation-evidence-path", str(tmp_path/"journal.jsonl")])
    if outcome == "interrupted":
        with pytest.raises(KeyboardInterrupt):cli.main()
    elif outcome == "system_exit":
        with pytest.raises(SystemExit) as stopped:cli.main()
        assert stopped.value.code == 17
    else:
        assert cli.main() == (0 if outcome == "ok" else 1)
    output = capsys.readouterr().out
    if outcome == "exception":assert "ORIGINAL_INGEST_FAILURE" in output
    assert "synthetic capture output unavailable" not in output
    assert len(notices) == 1


# Original invocation owns its working corpus and all restore sidecars.
import stat
def args(journal):
    return ["ingest_research", "--generation-source-commit", "a"*40, "--generation-run", "original-run",
            "--generation-evidence-path", str(journal)]


def test_generation_owns_new_private_workspace_and_preserves_shared_scratch(tmp_path, monkeypatch):
    journal = tmp_path / "original.jsonl"
    old = tmp_path / "shared"
    old.mkdir()
    names = ["research_vault_corpus.sqlite", "research_vault_corpus.sqlite-wal",
             "research_vault_corpus.sqlite-shm", "research_vault_corpus.sqlite-journal",
             "research_vault_corpus.sqlite.restore.tmp"]
    for name in names:
        (old/name).write_bytes(b"preserved original bytes")
    monkeypatch.setattr(cli.tempfile, "gettempdir", lambda: str(old))
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: tmp_path / "mirror")
    observed = []
    def pipeline(a, *rest):
        path = Path(a.corpus) if a.corpus else Path(cli.tempfile.gettempdir()) / "research_vault_corpus.sqlite"
        observed.append(path)
        assert path == tmp_path / "original.jsonl.workspace" / "corpus.sqlite"
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        assert not path.exists() and not path.parent.is_symlink()
        path.write_bytes(b"new synthetic work")
        return 0
    monkeypatch.setattr(cli, "_run_pipeline", pipeline)
    monkeypatch.setattr(sys, "argv", args(journal))
    assert cli.main() == 0 and len(observed) == 1
    assert all((old/name).read_bytes() == b"preserved original bytes" for name in names)
    assert observed[0].read_bytes() == b"new synthetic work"  # retained, never auto-cleaned
    assert cli.main() == 1 and len(observed) == 1  # original identity cannot silently restart


def test_generation_corpus_override_refuses_before_journal_or_store(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [*args(tmp_path/'original.jsonl'), "--corpus", str(tmp_path/'claimed.sqlite')])
    monkeypatch.setattr(FileGenerationEvidence, "create", lambda *a, **k: pytest.fail("journal opened"))
    monkeypatch.setattr(cli, "_run_pipeline", lambda *a: pytest.fail("pipeline started"))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


@pytest.mark.parametrize("existing", ["directory", "symlink", "file"])
def test_existing_workspace_is_preserved_and_never_adopted(tmp_path, monkeypatch, capsys, existing):
    journal = tmp_path / "original.jsonl"
    workspace = tmp_path / "original.jsonl.workspace"
    source = tmp_path / "preserved"
    source.mkdir()
    (source/'corpus.sqlite').write_bytes(b"incumbent")
    if existing == "directory":
        workspace.mkdir()
        (workspace/'corpus.sqlite').write_bytes(b"incumbent")
    elif existing == "symlink":
        workspace.symlink_to(source, target_is_directory=True)
    else:
        workspace.write_bytes(b"incumbent")
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: tmp_path/'mirror')
    monkeypatch.setattr(cli, "_run_pipeline", lambda *a: pytest.fail("pipeline started"))
    monkeypatch.setattr(sys, "argv", args(journal))
    assert cli.main() == 1
    output = capsys.readouterr()
    assert str(workspace) not in output.out + output.err
    assert (source/'corpus.sqlite').read_bytes() == b"incumbent"
    assert (workspace.read_bytes() if existing == "file" else (workspace/'corpus.sqlite').read_bytes()) == b"incumbent"


@pytest.mark.parametrize("failure", [OSError, RuntimeError])
def test_private_path_resolution_failure_does_not_disclose_path(tmp_path, monkeypatch, capsys, failure):
    journal = tmp_path / "PRIVATE_ORIGINAL_PATH.jsonl"
    original_resolve = Path.resolve
    def resolve(path, *a, **kw):
        if path == journal:
            raise failure("private path: " + str(journal))
        return original_resolve(path, *a, **kw)
    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(sys, "argv", args(journal))
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: tmp_path / "mirror")
    monkeypatch.setattr(cli, "_run_pipeline", lambda *a: pytest.fail("store path entered"))
    assert cli.main() == 1
    output = capsys.readouterr()
    assert "PRIVATE_ORIGINAL_PATH" not in output.out + output.err
    assert not journal.exists()
