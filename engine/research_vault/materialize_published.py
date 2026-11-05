"""Bounded immutable derivative work inside the existing serialized producer.

Never publishes a catalog, corpus, receipt, PDF or repository mirror. This is a
legacy-catalog preparation path; a generation-bearing catalog belongs to its
adopted writer and refuses here. It never establishes reader qualification.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import tempfile
import time

from engine.research_vault import catalog, fulltext_store, fulltext_writer, ingest
from engine.research_vault.producer_generation import CATALOG_MAX_BYTES, CORPUS_MAX_BYTES, CORPUS_KEY


class PublishedMaterializationUnavailable(RuntimeError):
    pass


def _snapshot(store):
    selected = store.get_bytes_strict_bounded_versioned(catalog.CATALOG_KEY, CATALOG_MAX_BYTES)
    if (selected is None or type(selected.data) is not bytes
            or not 0 < len(selected.data) <= CATALOG_MAX_BYTES
            or type(selected.version) is not str or not selected.version):
        raise PublishedMaterializationUnavailable("catalog_unavailable")
    document = catalog.parse_strict(selected.data)
    if "producer_generation" in document:
        raise PublishedMaterializationUnavailable("adopted_writer_required")
    return selected, document


class _DerivativeOnlyStore:
    def __init__(self, store, selected):
        self.store, self.selected = store, selected

    def assert_current(self):
        observed = self.store.get_bytes_strict_bounded_versioned(
            catalog.CATALOG_KEY, CATALOG_MAX_BYTES)
        if (observed is None or observed.data != self.selected.data
                or observed.version != self.selected.version):
            raise PublishedMaterializationUnavailable("catalog_moved")

    def get_bytes_strict(self, key):
        raw = self.store.get_bytes_strict(key)
        if key == CORPUS_KEY and (type(raw) is not bytes or not 0 < len(raw) <= CORPUS_MAX_BYTES):
            raise PublishedMaterializationUnavailable("corpus_unavailable")
        return raw

    def get_bytes_strict_bounded(self, key, bound):
        return self.store.get_bytes_strict_bounded(key, bound)

    def list_prefix(self, prefix):
        return self.store.list_prefix(prefix)

    def validate_strict_conditional_write_capability(self):
        return self.store.validate_strict_conditional_write_capability()

    def put_bytes(self, *args, **kwargs):
        raise PublishedMaterializationUnavailable("mutable_write_forbidden")

    def put_bytes_strict_conditional(self, key, data, *, expected_version,
                                    content_type="application/octet-stream"):
        if fulltext_store._split_derivative_key(key) is None or expected_version is not None:
            raise PublishedMaterializationUnavailable("mutable_write_forbidden")
        self.assert_current()
        return self.store.put_bytes_strict_conditional(
            key, data, expected_version=None, content_type=content_type)


def run(store) -> dict:
    """Run one incumbent capped pass. Caller owns workflow concurrency/lifecycle."""
    started = time.monotonic()
    result = {"schema":"research_vault.published_materialization_pass.v1",
              "mutable_publications":0, "reader_qualification":False}
    try:
        selected, document = _snapshot(store)
        guarded = _DerivativeOnlyStore(store, selected)
        # A private per-invocation copy never replaces the ordinary producer's
        # retained scratch image, including an interrupted publication candidate.
        with tempfile.TemporaryDirectory(prefix="research-vault-materialize-") as temporary:
            corpus_path = Path(temporary) / "corpus.sqlite"
            if ingest._restore_corpus(guarded, corpus_path) != "restored":
                raise PublishedMaterializationUnavailable("corpus_unavailable")
            corpus_path.chmod(0o600)
            # A valid SQLite envelope alone is insufficient: never silently
            # treat a missing documents table or a missing digest as no work.
            connection = sqlite3.connect(corpus_path.as_uri() + "?mode=ro&immutable=1", uri=True)
            try:
                shas = dict(connection.execute("SELECT doc_id, content_sha256 FROM documents"))
            finally:
                connection.close()
            if any(not fulltext_writer._valid_sha(shas.get(item["id"]))
                   for item in document["items"]):
                raise PublishedMaterializationUnavailable("corpus_cohort_unavailable")
            guarded.assert_current()
            result["catalog_sha256"] = hashlib.sha256(selected.data).hexdigest()
            result["catalog_count"] = len(document["items"])
            result["corpus_bytes"] = corpus_path.stat().st_size
            result["fulltext"] = fulltext_writer.materialize_pending(
                guarded, document, corpus_path, run_started=started, clock=time.monotonic)
            guarded.assert_current()
        if (result["fulltext"].get("aborted") not in (None, "cap", "budget")
                or result["fulltext"].get("failed")):
            result["error"] = "materialization_unavailable"
    except Exception as exc:
        result["error"] = (str(exc) if type(exc) is PublishedMaterializationUnavailable
                           else "source_unavailable")
    result["elapsed_seconds"] = time.monotonic() - started
    return result
