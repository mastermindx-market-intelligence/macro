"""Focused timing-evidence tests for the Research Vault producer.

Canonical path: ``tests/test_research_vault_producer_timing.py``.

Covers the additive timing instrumentation only — no cap/budget/order/clock
policy is changed, and these tests hold the patch to that:

* ``fulltext_writer.materialize_pending`` — ``pre_pass_elapsed_s`` /
  ``budget_s`` / ``pass_elapsed_s`` are metadata-only, ``budget_s`` is the exact
  value the in-loop stop checks compare against, and telemetry adds exactly one
  trailing clock sample after the loop and none inside it (so stop decisions,
  candidate order and materializer-call counts are unchanged).
* ``ingest.run`` — the ``timing_s`` phase map and its single INFO metadata line,
  with phase-specific injected latency shrinking the materializer's effective
  budget through the shared 600 s run wall (the observed ~555 s pre-materializer
  consumption), and a dry run reporting only phases it actually entered.

The materializer-level tests are self-contained: the ``fulltext_store``
dependency is stubbed on the writer module and receipts are digest-only bytes,
so no real store, provider or credential is involved. The ``ingest.run`` tests
reuse the existing fulltext store test module's fixtures; when that module is
not importable they SKIP with an explicit reason rather than failing — those
skips are unverified, not passing.
"""
from __future__ import annotations

import logging
import time

import pytest

from engine.research_vault import fulltext_writer

try:  # the heavy producer module; absent in isolated replica environments
    from engine.research_vault import fulltext_store
    from engine.research_vault import ingest as ingest_mod
except Exception:  # pragma: no cover - replica environments only
    fulltext_store = None
    ingest_mod = None


def _import_existing_helpers():
    """Reuse the existing fulltext-store fixtures for the ingest.run tests."""
    import importlib

    for modname in ("tests.test_research_vault_fulltext_store",
                    "test_research_vault_fulltext_store"):
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        if all(hasattr(mod, name)
               for name in ("LocalStore", "_seed_inbox", "_text")):
            return mod
    return None


_EXISTING = _import_existing_helpers()

_NEEDS_INGEST = pytest.mark.skipif(
    ingest_mod is None or _EXISTING is None,
    reason="ingest module / existing fulltext-store fixtures not importable — "
           "unverified in this environment, not a pass",
)


# ── fakes ────────────────────────────────────────────────────────────────────

class _StubFulltextStoreModule:
    """Stand-in for the ``fulltext_store`` surface the pass touches.

    A receipt blob IS the digest bytes and ``parse_receipt_digest`` decodes
    them, so tests never depend on the real receipt schema.
    """

    FULLTEXT_MAX_BYTES = 1 << 20
    RECEIPT_MAX_BYTES = 1 << 16

    def list_derivatives(self, store):
        return frozenset(getattr(store, "derivatives", ()))

    @staticmethod
    def receipt_key(doc_id):
        return "rv/receipts/%s.json" % (doc_id,)

    @staticmethod
    def parse_receipt_digest(blob, _doc_id):
        try:
            return blob.decode("utf-8")
        except Exception:
            return None


class _FakeStore:
    """Strict-read-shaped store holding digest-only receipts."""

    def __init__(self, receipts=()):
        self.receipts = dict(receipts)
        self.derivatives = frozenset()
        self.reads = 0

    def validate_strict_conditional_write_capability(self):
        return True

    def list_prefix(self, _prefix):
        return []

    def get_bytes_strict_bounded(self, key, _max_bytes):
        self.reads += 1
        doc_id = key.replace("rv/receipts/", "").replace(".json", "")
        digest = self.receipts.get(doc_id)
        if digest is None:
            raise KeyError(key)
        return digest.encode("utf-8")


class _StepClock:
    """Fake monotonic clock: returns ``now``, then advances it by ``step``."""

    def __init__(self, start=0.0, step=0.0):
        self.now = float(start)
        self.step = float(step)

    def __call__(self):
        current = self.now
        self.now += self.step
        return current

    def advance(self, seconds):
        self.now += float(seconds)


class _CountingClock:
    """Constant clock that counts every sample the pass takes."""

    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return 0.0


def _item(doc_id, published="2026-08-01T00:00:00Z"):
    return {"id": doc_id, "published_at": published}


def _receipted(doc_ids, digest="ab"):
    store = _FakeStore({doc_id: digest * 32 for doc_id in doc_ids})
    return store


def _run_pass(store, items, store_module=None, **kwargs):
    """``materialize_pending`` with the stubbed store module and a counting
    default materializer; the result carries ``_materializer_calls``."""
    stub = store_module if store_module is not None else _StubFulltextStoreModule()
    real_store_module = fulltext_writer.fulltext_store
    fulltext_writer.fulltext_store = stub
    try:
        kwargs.setdefault("tool_available", lambda: True)
        calls: list[str] = []

        def _default_materializer(_store, report_id, *, expected_pdf_sha256):
            calls.append(report_id)
            return {"state": "materialized", "report_id": report_id}

        kwargs.setdefault("materializer", _default_materializer)
        kwargs.setdefault("run_started", 0.0)
        out = fulltext_writer.materialize_pending(
            store, {"items": items}, "missing.sqlite", **kwargs,
        )
        out["_materializer_calls"] = list(calls)
        return out
    finally:
        fulltext_writer.fulltext_store = real_store_module


# ── materialize_pending: the budget must come from the run wall ─────────────

def test_budget_shrinks_with_consumed_run_wall():
    """~555 s of pre-materializer run leaves 45 s: the 600 s run wall binds,
    not the 180 s pass budget, and the pass stops after one item."""
    store = _receipted(["note-0", "note-1"])
    out = _run_pass(
        store, [_item("note-0"), _item("note-1")],
        run_started=0.0, clock=_StepClock(start=555.0, step=40.0),
    )
    assert out["pre_pass_elapsed_s"] == pytest.approx(555.0)
    assert out["budget_s"] == pytest.approx(45.0)
    assert out["attempted"] == 1
    assert out["materialized"] == 1
    assert out["aborted"] == "budget"
    assert out["remaining"] == 1
    assert out["_materializer_calls"] == ["note-0"]
    # pass_start + two in-loop stop checks + one trailing sample, nothing more
    assert out["pass_elapsed_s"] == pytest.approx(120.0)


def test_full_pass_budget_caps_at_180_when_run_wall_is_fresh():
    """Same stop label, different binding wall: with the run just started the
    budget is the 180 s pass cap and the 600 s wall is irrelevant."""
    store = _receipted(["note-%d" % i for i in range(3)])
    out = _run_pass(
        store, [_item("note-%d" % i) for i in range(3)],
        run_started=0.0, clock=_StepClock(start=0.0, step=100.0),
    )
    assert out["pre_pass_elapsed_s"] == pytest.approx(0.0)
    assert out["budget_s"] == pytest.approx(180.0)
    assert out["attempted"] == 1
    assert out["aborted"] == "budget"
    assert out["remaining"] == 2
    assert out["pass_elapsed_s"] == pytest.approx(300.0)


def test_item_latency_consumes_shrunk_wall_not_cap():
    """Per-item cost (~a download + pdftotext) is paid out of the shrunken
    run-wall budget; the cap and candidate order stay untouched."""
    store = _receipted(["note-%d" % i for i in range(3)])
    clock = _StepClock(start=555.0)

    def _slow_materializer(_store, report_id, *, expected_pdf_sha256):
        clock.advance(30.0)
        return {"state": "materialized", "report_id": report_id}

    out = _run_pass(
        store, [_item("note-%d" % i) for i in range(3)],
        run_started=0.0, clock=clock, materializer=_slow_materializer,
    )
    assert out["budget_s"] == pytest.approx(45.0)
    assert out["attempted"] == 2
    assert out["materialized"] == 2
    assert out["aborted"] == "budget"
    assert out["remaining"] == 1
    assert out["pass_elapsed_s"] == pytest.approx(60.0)


def test_run_wall_already_spent_attempts_nothing():
    """Elapsed beyond the run wall: budget 0, zero attempts, zero writes."""
    store = _receipted(["note-a", "note-b"])
    out = _run_pass(
        store, [_item("note-a"), _item("note-b")],
        run_started=4000.0, clock=_StepClock(start=5000.0),
    )
    assert out["candidates"] == 2
    assert out["pre_pass_elapsed_s"] == pytest.approx(1000.0)
    assert out["budget_s"] == pytest.approx(0.0)
    assert out["attempted"] == 0
    assert out["aborted"] == "budget"
    assert out["remaining"] == 2
    assert out["_materializer_calls"] == []


# ── materialize_pending: telemetry must not perturb decisions ───────────────

def test_telemetry_takes_one_trailing_clock_sample_only():
    """Exactly one clock sample after the loop and none inside it: the stop
    checks consume the same samples they always did, and the materializer is
    called once per attempted item and never for telemetry."""
    store = _receipted(["note-%d" % i for i in range(3)])
    clock = _CountingClock()
    out = _run_pass(
        store, [_item("note-%d" % i) for i in range(3)],
        run_started=0.0, clock=clock,
    )
    assert clock.calls == 5  # pass_start + 3 stop checks + 1 trailing sample
    assert out["attempted"] == 3
    assert out["materialized"] == 3
    assert out["aborted"] is None
    assert out["pass_elapsed_s"] == pytest.approx(0.0)
    assert out["_materializer_calls"] == ["note-0", "note-1", "note-2"]


def test_cap_stop_semantics_unchanged_with_timing_fields():
    """The supplied cap-stop case: cap 1 stops after the newest item, with the
    timing fields riding along additively."""
    store = _receipted(["note-old", "note-new", "note-blank"])
    items = [
        _item("note-old", "2026-01-01T00:00:00Z"),
        _item("note-new", "2026-08-01T00:00:00Z"),
        _item("note-blank", ""),
    ]
    out = _run_pass(store, items, run_started=0.0,
                    clock=_StepClock(start=0.0), cap=1)
    assert out["attempted"] == 1
    assert out["aborted"] == "cap"
    assert out["remaining"] == 2
    assert out["_materializer_calls"] == ["note-new"]
    assert out["pre_pass_elapsed_s"] == pytest.approx(0.0)
    assert out["budget_s"] == pytest.approx(180.0)
    assert out["pass_elapsed_s"] == pytest.approx(0.0)


def test_stateful_clock_budget_stop_semantics_unchanged():
    """The supplied budget-stop case (150 s budget, 100 s per sample): the stop
    lands on the same item and the recorded budget is the same 150."""
    store = _receipted(["note-%d" % i for i in range(3)], digest="cd")
    out = _run_pass(
        store, [_item("note-%d" % i) for i in range(3)],
        run_started=0.0, clock=_StepClock(start=0.0, step=100.0),
        budget_s=150,
    )
    assert out["aborted"] == "budget"
    assert out["attempted"] == 1
    assert out["remaining"] == 2
    assert out["budget_s"] == pytest.approx(150.0)


# ── materialize_pending: degraded paths stay truthful ───────────────────────

def test_store_unavailable_before_candidates_reports_pre_pass_only():
    """Aborted before the pass opened: only the pre-pass wall is reported —
    no budget or pass elapsed is invented for a pass that never started."""
    stub = _StubFulltextStoreModule()
    stub.list_derivatives = lambda _store: None  # the pass never gets a store
    store = _receipted(["note-0"])
    out = _run_pass(store, [_item("note-0")], store_module=stub,
                    run_started=0.0, clock=_StepClock(start=555.0))
    assert out["aborted"] == "store_unavailable"
    assert out["pre_pass_elapsed_s"] == pytest.approx(555.0)
    assert "budget_s" not in out
    assert "pass_elapsed_s" not in out
    assert out["attempted"] == 0
    assert out["_materializer_calls"] == []


def test_tool_unavailable_reports_the_opened_pass_fields():
    """Aborted after the pass opened but before any item: pre-pass wall, the
    budget that WOULD have governed, and a zero-length pass elapsed."""
    store = _receipted(["note-0"])
    out = _run_pass(store, [_item("note-0")], run_started=0.0,
                    clock=_StepClock(start=0.0), tool_available=lambda: False)
    assert out["aborted"] == "tool_unavailable"
    assert out["pre_pass_elapsed_s"] == pytest.approx(0.0)
    assert out["budget_s"] == pytest.approx(180.0)
    assert out["pass_elapsed_s"] == pytest.approx(0.0)
    assert out["attempted"] == 0
    assert out["remaining"] == 1
    assert out["_materializer_calls"] == []


# ── ingest.run: phase map, metadata log, run-wall coupling ──────────────────

@_NEEDS_INGEST
def test_ingest_run_phase_timing_reaches_log_and_materializer_budget(
        tmp_path, monkeypatch, caplog):
    """Latency injected into one phase shows up in ``timing_s``, is printed by
    the single INFO metadata line, and shrinks the materializer's effective
    budget through the shared run wall."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text",
                        lambda _pdf: _EXISTING._text("ingested body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    clock = _StepClock(0.0)
    monkeypatch.setattr(time, "monotonic", clock)
    real_resync = ingest_mod._refresh_sidecars

    def _slow_resync(*args, **kwargs):
        clock.advance(120.0)  # one coarse phase pays 120 s of the run wall
        return real_resync(*args, **kwargs)

    monkeypatch.setattr(ingest_mod, "_refresh_sidecars", _slow_resync)

    store = _EXISTING.LocalStore(tmp_path / "store")
    _EXISTING._seed_inbox(store)
    with caplog.at_level(logging.INFO):
        summary = ingest_mod.run(store, tmp_path / "corpus.sqlite")

    timing = summary["timing_s"]
    assert timing["sidecar_resync_s"] == pytest.approx(120.0)
    for phase in ("restore_s", "catalog_read_s", "catalog_repair_s", "intake_s",
                  "reextract_s", "backfill_s", "publication_s"):
        assert phase in timing
        assert timing[phase] >= 0.0

    assert summary.get("catalog_published") is True
    assert summary["fulltext_pre_pass_elapsed_s"] == pytest.approx(120.0)
    assert summary["fulltext_budget_s"] == pytest.approx(180.0)
    assert "fulltext_aborted" not in summary
    assert summary["fulltext_materialized"] >= 1

    # the real incumbent INFO path carries both metadata lines
    assert "run phase timing" in caplog.text
    assert "sidecar_resync_s=120.000" in caplog.text
    assert "budget_s=180.0" in caplog.text


@_NEEDS_INGEST
def test_ingest_run_wall_exhausted_materializes_nothing(
        tmp_path, monkeypatch):
    """Phases consuming the whole 600 s run wall: the materializer opens on an
    effective budget of 0, attempts nothing, writes no derivatives, and leaves
    the publication semantics exactly as they were."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text",
                        lambda _pdf: _EXISTING._text("ingested body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    clock = _StepClock(0.0)
    monkeypatch.setattr(time, "monotonic", clock)
    real_resync = ingest_mod._refresh_sidecars

    def _slow_resync(*args, **kwargs):
        clock.advance(700.0)  # beyond the 600 s run wall
        return real_resync(*args, **kwargs)

    monkeypatch.setattr(ingest_mod, "_refresh_sidecars", _slow_resync)

    store = _EXISTING.LocalStore(tmp_path / "store")
    _EXISTING._seed_inbox(store)
    summary = ingest_mod.run(store, tmp_path / "corpus.sqlite")

    assert summary.get("catalog_published") is True
    assert "error" not in summary
    assert summary["timing_s"]["sidecar_resync_s"] == pytest.approx(700.0)
    assert summary["fulltext_pre_pass_elapsed_s"] == pytest.approx(700.0)
    assert summary["fulltext_budget_s"] == pytest.approx(0.0)
    assert summary["fulltext_candidates"] >= 1
    assert summary["fulltext_attempted"] == 0
    assert summary["fulltext_remaining"] == summary["fulltext_candidates"]
    assert summary["fulltext_aborted"] == "budget"
    assert store.list_prefix(fulltext_store.FULLTEXT_PREFIX) == []


@_NEEDS_INGEST
def test_ingest_dry_run_timing_reports_only_entered_phases(
        tmp_path, monkeypatch):
    """A dry run never publishes, reextracts or backfills: those phases are
    absent from ``timing_s`` rather than reported as zero, and no fulltext
    counters appear."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text",
                        lambda _pdf: _EXISTING._text("ingested body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    store = _EXISTING.LocalStore(tmp_path / "store")
    _EXISTING._seed_inbox(store)
    summary = ingest_mod.run(store, tmp_path / "corpus.sqlite", dry_run=True)

    timing = summary["timing_s"]
    assert isinstance(timing, dict)
    for phase in ("restore_s", "catalog_read_s", "catalog_repair_s",
                  "intake_s", "sidecar_resync_s"):
        assert phase in timing
        assert timing[phase] >= 0.0
    for absent in ("reextract_s", "backfill_s", "publication_s"):
        assert absent not in timing
    assert not any(key.startswith("fulltext_") for key in summary)


@_NEEDS_INGEST
def test_processed_index_is_separate_from_intake(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _pdf: _EXISTING._text("ingested body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    clock = _StepClock(0.0)
    monkeypatch.setattr(time, "monotonic", clock)
    original = ingest_mod._processed_index
    def slow_receipts(*args, **kwargs):
        clock.advance(555.0)
        return original(*args, **kwargs)
    monkeypatch.setattr(ingest_mod, "_processed_index", slow_receipts)
    store = _EXISTING.LocalStore(tmp_path / "store")
    _EXISTING._seed_inbox(store)
    summary = ingest_mod.run(store, tmp_path / "corpus.sqlite")
    assert summary["timing_s"]["processed_index_s"] == pytest.approx(555.0)
    assert summary["timing_s"]["intake_s"] == pytest.approx(0.0)
    assert summary["fulltext_pre_pass_elapsed_s"] == pytest.approx(555.0)
    assert summary["fulltext_budget_s"] == pytest.approx(45.0)


@_NEEDS_INGEST
def test_publication_subphase_timings_identify_cost_without_reordering(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _pdf: _EXISTING._text("body"))
    monkeypatch.setattr(ingest_mod, "_pdftotext_available", lambda: True)
    clock, order = _StepClock(), []
    monkeypatch.setattr(time, "monotonic", clock)
    def delay(owner, name, seconds):
        original = getattr(owner, name)
        def measured(*args, **kwargs):
            order.append(name)
            clock.advance(seconds)
            return original(*args, **kwargs)
        monkeypatch.setattr(owner, name, measured)
    delay(ingest_mod, "publish_corpus", 11)
    delay(ingest_mod.catalog_mod, "publish", 23)
    delay(ingest_mod, "_flush_receipts", 31)
    store = _EXISTING.LocalStore(tmp_path / "store")
    _EXISTING._seed_inbox(store)
    result = ingest_mod.run(store, tmp_path / "corpus.sqlite")
    assert order == ["publish_corpus", "publish", "_flush_receipts"]
    assert result["timing_s"]["corpus_publish_s"] == 11
    assert result["timing_s"]["catalog_publish_s"] == 23
    assert result["timing_s"]["receipt_flush_s"] == 31
    assert result["timing_s"]["publication_s"] == 65
    assert result["fulltext_pre_pass_elapsed_s"] == 65
    assert result["catalog_published"] is True and result["corpus_published"] is True
