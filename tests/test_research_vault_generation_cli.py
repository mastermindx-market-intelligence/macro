"""Explicit producer identity and private/public catalog boundary at the CLI."""
import inspect
import json
import sys

import pytest

from engine.research_vault import ingest, r2_store
from scripts import ingest_research as cli


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


def test_identity_reaches_actual_engine_interface(invocation, monkeypatch):
    _, calls, _ = invocation
    monkeypatch.setattr(sys, "argv", ["ingest_research", *IDENTITY_ARGS])
    assert cli.main() == 0
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


def test_public_projection_preserves_private_bytes_and_nested_content(invocation, monkeypatch):
    mirror, _, summary = invocation
    item = {"id": "fixture", "producer_generation": "ordinary nested content"}
    private = json.dumps({"items": [item], "producer_generation": {"state": "COMPLETE"}}).encode()
    summary["catalog_bytes"] = private
    monkeypatch.setattr(sys, "argv", ["ingest_research", *IDENTITY_ARGS])
    assert cli.main() == 0
    assert summary["catalog_bytes"] == private
    assert json.loads((mirror / "catalog.json").read_bytes()) == {"items": [item]}


def test_legacy_public_snapshot_keeps_exact_bytes(invocation):
    mirror, _, summary = invocation
    summary["catalog_bytes"] = b'{ "items" : [] }\n\n'
    assert cli.main() == 0
    assert (mirror / "catalog.json").read_bytes() == summary["catalog_bytes"]


@pytest.mark.parametrize("invalid", [b'{invalid', b'\xff'])
def test_invalid_canonical_bytes_do_not_advance_existing_snapshot(invocation, invalid):
    mirror, _, summary = invocation
    mirror.mkdir()
    target = mirror / "catalog.json"
    target.write_bytes(b'{"items":[]}\n')
    summary["catalog_bytes"] = invalid
    assert cli.main() == 0
    assert target.read_bytes() == b'{"items":[]}\n'
