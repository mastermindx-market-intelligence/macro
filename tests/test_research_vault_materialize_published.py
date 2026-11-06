"""Published-cohort preparation must only create immutable text derivatives."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
import yaml

from engine.research_vault import catalog, fulltext_store, fulltext_writer, ingest
from engine.research_vault import materialize_published as subject
from engine.research_vault.r2_store import LocalStore
from scripts import ingest_research as cli

RID = "desk-2026-10-13-synthetic"
PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
       b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
       b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
       b"trailer<</Root 1 0 R>>\n%%EOF\n")
DIGEST = hashlib.sha256(PDF).hexdigest()
BODY = "Synthetic bounded full document text. " * 100


class RecordingStore(LocalStore):
    def __init__(self, root):
        super().__init__(root)
        self.writes = []

    def put_bytes(self, key, data, content_type="application/octet-stream"):
        self.writes.append(("mutable", key))
        return super().put_bytes(key, data, content_type)

    def put_bytes_strict_conditional(self, key, data, *, expected_version,
                                    content_type="application/octet-stream"):
        self.writes.append((expected_version, key))
        return super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type)


def snapshot(store):
    return {str(p.relative_to(store.root)): p.read_bytes()
            for p in store.root.rglob("*") if p.is_file()}


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    store = RecordingStore(tmp_path / "store")
    document = {"schema": catalog.SCHEMA, "generated_at": "2026-10-13T00:00:00Z",
                "count": 1, "institutions": ["Desk"],
                "items": [{"id": RID, "title": "Synthetic", "institution": "Desk"}]}
    store.put_bytes(catalog.CATALOG_KEY, json.dumps(document).encode())
    store.put_bytes(f"research_vault/{RID}.pdf", PDF)
    store.put_bytes(fulltext_store.receipt_key(RID),
                    json.dumps({"id": RID, "content_sha256": DIGEST}).encode())
    db = tmp_path / "seed.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE documents (doc_id TEXT PRIMARY KEY, content_sha256 TEXT)")
        conn.execute("INSERT INTO documents VALUES (?, ?)", (RID, DIGEST))
    store.put_bytes(subject.CORPUS_KEY, db.read_bytes())
    store.writes.clear()
    monkeypatch.setattr(ingest, "extract_pdf_text", lambda _pdf: BODY)
    monkeypatch.setattr(ingest, "_pdftotext_available", lambda: True)
    return store, document


def test_actual_pass_creates_only_derivative_and_preserves_retained_scratch(seeded, tmp_path, monkeypatch):
    store, _ = seeded
    before = snapshot(store)
    scratch = tmp_path / "research_vault_corpus.sqlite"
    scratch.write_bytes(b"retained interrupted ordinary producer candidate")
    private_paths = []
    restore = ingest._restore_corpus

    def observed_restore(wrapped, path):
        private_paths.append(path)
        assert path.parent.stat().st_mode & 0o777 == 0o700
        return restore(wrapped, path)

    monkeypatch.setattr(subject.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(ingest, "_restore_corpus", observed_restore)
    result = subject.run(store)
    assert "error" not in result
    assert result["fulltext"]["materialized"] == 1
    assert result["fulltext"]["remaining"] == 0
    assert result["mutable_publications"] == 0 and result["reader_qualification"] is False
    key = fulltext_store.derivative_key(RID, DIGEST)
    assert store.writes == [(None, key)]
    after = snapshot(store)
    assert {key: after[key] for key in before} == before
    assert fulltext_store.decode_record(after[key], RID, DIGEST) is not None
    assert scratch.read_bytes() == b"retained interrupted ordinary producer candidate"
    assert private_paths and all(not path.parent.exists() for path in private_paths)
    store.writes.clear()
    repeat = subject.run(store)
    assert "error" not in repeat and repeat["fulltext"]["attempted"] == 0
    assert store.writes == []
    assert BODY not in json.dumps(result)


@pytest.mark.parametrize("bad", ["missing_catalog", "missing_corpus", "invalid_corpus", "missing_cohort", "missing_schema", "bad_digest", "adopted"])
def test_incomplete_or_adopted_source_refuses_before_derivative_write(seeded, tmp_path, bad):
    store, document = seeded
    if bad == "missing_catalog":
        (store.root / catalog.CATALOG_KEY).unlink()
    elif bad == "missing_corpus":
        (store.root / subject.CORPUS_KEY).unlink()
    elif bad == "invalid_corpus":
        store.put_bytes(subject.CORPUS_KEY, b"invalid SQLite")
    elif bad == "adopted":
        document["producer_generation"] = {"state": "BUILDING"}
        store.put_bytes(catalog.CATALOG_KEY, json.dumps(document).encode())
    else:
        path = store.root / subject.CORPUS_KEY
        with sqlite3.connect(path) as conn:
            if bad == "missing_schema":
                conn.execute("DROP TABLE documents")
                document.update(items=[], count=0, institutions=[])
                store.put_bytes(catalog.CATALOG_KEY, json.dumps(document).encode())
            elif bad == "bad_digest":
                conn.execute("UPDATE documents SET content_sha256='bad'")
            else:
                conn.execute("DELETE FROM documents")
    store.writes.clear()
    result = subject.run(store)
    assert result.get("error")
    assert not store.writes


def test_catalog_movement_during_extraction_prevents_creation(seeded, monkeypatch):
    store, document = seeded

    def move(_pdf):
        document["generated_at"] = "2026-10-13T01:00:00Z"
        LocalStore.put_bytes(store, catalog.CATALOG_KEY, json.dumps(document).encode())
        return BODY

    monkeypatch.setattr(ingest, "extract_pdf_text", move)
    result = subject.run(store)
    assert result["error"] == "catalog_moved"
    assert store.writes == []


def test_lost_create_response_is_error_without_same_pass_retry(seeded, monkeypatch):
    store, _ = seeded
    create = store.put_bytes_strict_conditional

    def uncertain(*args, **kwargs):
        create(*args, **kwargs)
        raise TimeoutError("synthetic lost reply")

    monkeypatch.setattr(store, "put_bytes_strict_conditional", uncertain)
    result = subject.run(store)
    assert result["error"] == "materialization_unavailable"
    assert result["fulltext"]["aborted"] == "store_unavailable"
    assert len(store.writes) == 1


@pytest.mark.parametrize("limit,reason", [("FULLTEXT_MAX", "cap"), ("FULLTEXT_BUDGET_S", "budget")])
def test_incumbent_zero_budget_or_cap_never_fetches_pdf(seeded, monkeypatch, limit, reason):
    store, _ = seeded
    monkeypatch.setattr(fulltext_writer, limit, 0)
    monkeypatch.setattr(ingest, "extract_pdf_text", lambda _: pytest.fail("budget must prevent extraction"))
    result = subject.run(store)
    assert "error" not in result and result["fulltext"]["aborted"] == reason
    assert result["fulltext"]["remaining"] == 1
    assert not store.writes


@pytest.mark.parametrize("key,version", [
    (catalog.CATALOG_KEY, None), (subject.CORPUS_KEY, None),
    (fulltext_store.receipt_key(RID), None), (f"research_vault/{RID}.pdf", None),
    (fulltext_store.FULLTEXT_PREFIX + "../../catalog.json", None),
    (fulltext_store.derivative_key(RID, DIGEST), "existing-version"),
])
def test_write_boundary_refuses_every_mutable_path(seeded, key, version):
    store, _ = seeded
    selected, _ = subject._snapshot(store)
    wrapped = subject._DerivativeOnlyStore(store, selected)
    with pytest.raises(subject.PublishedMaterializationUnavailable):
        wrapped.put_bytes_strict_conditional(key, b"forbidden", expected_version=version)
    with pytest.raises(subject.PublishedMaterializationUnavailable):
        wrapped.put_bytes(key, b"forbidden")
    assert not store.writes


def test_cli_bypasses_ordinary_ingest_and_repository_snapshots(seeded, tmp_path, monkeypatch, capsys):
    store, _ = seeded
    from engine.research_vault import r2_store
    monkeypatch.setattr(r2_store, "build_store", lambda **kwargs: store)
    monkeypatch.setattr(ingest, "run", lambda *args, **kwargs: pytest.fail("mutable ingest invoked"))
    mirror = tmp_path / "mirror"
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: mirror)
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--materialize-only"])
    assert cli.main() == 0
    assert not mirror.exists()
    assert '"materialized": 1' in capsys.readouterr().out


def test_cli_missing_store_is_failure_even_without_require_store(monkeypatch):
    from engine.research_vault import r2_store
    monkeypatch.setattr(r2_store, "build_store", lambda **kwargs: None)
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--materialize-only"])
    assert cli.main() == 1


@pytest.mark.parametrize("args", [["--dry-run"], ["--corpus", "unused"], ["--repo-dir", "unused"]])
def test_cli_rejects_conflicting_modes_before_building_store(monkeypatch, args):
    from engine.research_vault import r2_store
    monkeypatch.setattr(r2_store, "build_store", lambda **kwargs: pytest.fail("must reject before opening store"))
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--materialize-only", *args])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


@pytest.mark.parametrize("publish,bootstrap,expected", [("false", "false", 0), ("true", "false", 1), ("false", "true", 1)])
def test_workflow_mode_admission_and_same_lifecycle(publish, bootstrap, expected):
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/research-ingest.yml").read_text())
    assert workflow["concurrency"] == {"group": "research-ingest", "cancel-in-progress": False}
    assert workflow["jobs"]["ingest"]["timeout-minutes"] == 15
    steps = workflow["jobs"]["ingest"]["steps"]
    gate = steps[0]
    result = subprocess.run(["bash", "-c", gate["run"]], capture_output=True,
                            env={"MATERIALIZE_ONLY": "true", "PUBLISH_FORENSICS": publish,
                                 "BOOTSTRAP_FORENSICS": bootstrap}, timeout=10)
    assert result.returncode == expected
    salvage = next(step for step in steps if step.get("name") == "commit catalog snapshot (salvage-push)")
    assert "!inputs.materialize_only" in salvage["if"]
