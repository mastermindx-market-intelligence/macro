"""Catalog rows missing from the corpus — ingest._backfill_missing_rows.

The receipted-doc gap the body re-extraction pass cannot see: a catalog item
with no corpus row is invisible to body search, and a receipt is never deleted,
so ingest never reaches it again. These tests drive the repair directly and,
in T10, through run() against a published corpus that was restored the way the
hourly job restores it.

No R2. LocalStore + a monkeypatched extractor, same idiom as the body
re-extraction section of tests/test_research_vault.py.
"""
from __future__ import annotations

import copy
import sqlite3
from pathlib import Path

from engine.research_vault import corpus as corpus_mod
from engine.research_vault import ingest as ingest_mod
from engine.research_vault.r2_store import LocalStore
from tests.test_research_vault import _MINIMAL_PDF, _seed_pdf


# Long enough that text_facts classifies 'full' with or without a measured
# page count (>=500 absolute, >=200 chars/page). The token is absent from
# every catalog title/summary/institution used below, so a search hit can
# only come from the inserted body.
_LONG_BODY = (
    "zyxbackfilltoken hyperscaler capacity dominates the credible pipeline. " * 12
)


def _item(doc_id: str, **overrides) -> dict:
    item = {
        "id": doc_id,
        "title": f"Title {doc_id}",
        "institution": "Bernstein",
        "side": "sell",
        "desk": "",
        "published_at": "2026-07-21T14:00:00Z",
        "summary_points": ["A published bullet."],
        "tags": [],
        "tickers": [],
        "top_pick": False,
        "pages": None,
        "language": "en",
        "needs_metadata": False,
    }
    item.update(overrides)
    return item


def _catalog(*items: dict) -> dict:
    return {"schema": "research_vault.catalog.v1", "items": list(items)}


def _put_pdf(store, doc_id: str, pdf_bytes: bytes | None = None) -> None:
    store.put_bytes(
        f"{ingest_mod.VAULT_PREFIX}{doc_id}.pdf",
        _MINIMAL_PDF if pdf_bytes is None else pdf_bytes,
        "application/pdf",
    )


def _open(tmp_path: Path):
    return corpus_mod.open_db(tmp_path / "corpus.sqlite")


def _row(conn, doc_id: str):
    return conn.execute(
        "SELECT title, body, text_layer, char_count FROM documents WHERE doc_id=?",
        (doc_id,),
    ).fetchone()


def test_t1_absent_catalog_row_is_inserted_and_searchable(tmp_path, monkeypatch):
    """Pin: search finds the body-only token, and the stored title is the
    catalog title (a filename-shaped one, which title.resolve would rewrite)."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    conn = _open(tmp_path)
    # Filename furniture. resolve() would clean this; the backfill must not.
    title = "2026 07 24 Pmi Fall Seven Times Get Up Eight en"
    item = _item("bf-t1", title=title, summary_points=["Not the body token."])
    _put_pdf(store, "bf-t1")

    out = ingest_mod._backfill_missing_rows(store, _catalog(item), conn)

    assert out["rows"] == 1 and out["candidates"] == 1
    row = _row(conn, "bf-t1")
    assert row["text_layer"] == "full"
    assert row["char_count"] == len(_LONG_BODY)
    assert row["title"] == title
    hits = corpus_mod.search(conn, "zyxbackfilltoken")
    assert [h["id"] for h in hits] == ["bf-t1"]
    conn.close()


def test_t2_missing_vault_pdf_writes_no_row(tmp_path, monkeypatch):
    """Pin: pdf_missing==1 and the doc_id is still absent. A storage gap is
    not turned into a corpus fact."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    conn = _open(tmp_path)

    out = ingest_mod._backfill_missing_rows(store, _catalog(_item("bf-t2")), conn)

    assert out["pdf_missing"] == 1
    assert out["rows"] == 0
    assert _row(conn, "bf-t2") is None
    conn.close()


def test_t3_store_raise_aborts_without_raising(tmp_path, monkeypatch):
    """Pin: aborted=='store_unavailable' and rows==0. The raise must not escape."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    _put_pdf(store, "bf-t3")

    class RaisingStore(LocalStore):
        def get_bytes_strict(self, key: str):
            raise ConnectionError(f"bucket unreachable for {key}")

    raising = RaisingStore(store.root)
    conn = _open(tmp_path)

    out = ingest_mod._backfill_missing_rows(raising, _catalog(_item("bf-t3")), conn)

    assert out["aborted"] == "store_unavailable"
    assert out["rows"] == 0
    assert _row(conn, "bf-t3") is None
    conn.close()


def test_t4_extractor_none_aborts_as_tool_unavailable(tmp_path, monkeypatch):
    """Pin: aborted=='tool_unavailable' and rows==0. None is a host fault, not
    an empty document."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: None)
    store = LocalStore(tmp_path / "store")
    _put_pdf(store, "bf-t4")
    conn = _open(tmp_path)

    out = ingest_mod._backfill_missing_rows(store, _catalog(_item("bf-t4")), conn)

    assert out["aborted"] == "tool_unavailable"
    assert out["rows"] == 0
    assert _row(conn, "bf-t4") is None
    conn.close()


def test_t5_cap_keeps_the_two_newest(tmp_path, monkeypatch):
    """Pin: rows==2, remaining==1, and the inserted ids are the two newest
    published_at values. The undated item sorts last, so a date-ASC or
    id-ASC cap would insert it and fail this assertion."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    conn = _open(tmp_path)
    items = [
        _item("a-mid", published_at="2026-03-01T00:00:00Z"),
        _item("b-undated", published_at=""),
        _item("m-newest", published_at="2026-09-01T00:00:00Z"),
    ]
    for it in items:
        _put_pdf(store, it["id"])

    out = ingest_mod._backfill_missing_rows(store, _catalog(*items), conn, cap=2)

    assert out["rows"] == 2
    assert out["remaining"] == 1
    present = {
        r[0] for r in conn.execute("SELECT doc_id FROM documents").fetchall()
    }
    assert present == {"m-newest", "a-mid"}
    conn.close()


def test_t6_budget_stops_after_the_first_item(tmp_path, monkeypatch):
    """Pin: rows==1 and remaining==candidates-1 once the clock passes the
    budget after the first attempt."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    conn = _open(tmp_path)
    items = [
        _item("bf-older", published_at="2026-01-01T00:00:00Z"),
        _item("bf-mid", published_at="2026-06-01T00:00:00Z"),
        _item("bf-newest", published_at="2026-09-01T00:00:00Z"),
    ]
    for it in items:
        _put_pdf(store, it["id"])
    ticks = [0.0, 0.0, ingest_mod.BACKFILL_BUDGET_S + 1.0]
    seen = {"n": 0}

    def clock():
        value = ticks[min(seen["n"], len(ticks) - 1)]
        seen["n"] += 1
        return value

    out = ingest_mod._backfill_missing_rows(
        store, _catalog(*items), conn, clock=clock)

    assert out["rows"] == 1
    assert out["remaining"] == out["candidates"] - 1
    assert _row(conn, "bf-newest") is not None
    assert _row(conn, "bf-mid") is None and _row(conn, "bf-older") is None
    conn.close()


def test_t7_existing_corpus_row_is_not_a_candidate_and_is_untouched(
        tmp_path, monkeypatch):
    """Pin: the pre-existing id is not a candidate (candidates counts only the
    missing sibling) and its body, title, and text_layer stay byte-identical.
    The extractor returns a different body, so a re-upsert would fail this."""
    original = "The ORIGINAL published body must survive byte for byte."
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    conn = _open(tmp_path)
    existing = _item("bf-existing", title="Original Catalog Title")
    missing = _item("bf-missing-sibling", title="Sibling That Is Absent")
    corpus_mod.upsert(conn, existing, original, facts={
        "text_layer": "full", "char_count": len(original), "language": "en",
    })
    before = _row(conn, "bf-existing")
    _put_pdf(store, "bf-existing")
    _put_pdf(store, "bf-missing-sibling")

    out = ingest_mod._backfill_missing_rows(
        store, _catalog(existing, missing), conn)

    assert out["candidates"] == 1
    assert out["rows"] == 1
    assert _row(conn, "bf-missing-sibling") is not None
    after = _row(conn, "bf-existing")
    assert after["body"] == before["body"] == original
    assert after["title"] == before["title"] == "Original Catalog Title"
    assert after["text_layer"] == before["text_layer"] == "full"
    conn.close()


def test_t8_catalog_item_and_store_keys_are_unchanged(tmp_path, monkeypatch):
    """Pin: the catalog item equals its deepcopy, and the store key set is
    identical. rows==1 proves the pass wrote a corpus row while doing neither."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    conn = _open(tmp_path)
    item = _item(
        "bf-t8",
        title="Untouched Catalog Title",
        summary_points=["nested", "bullets"],
        tags=["macro"],
        tickers=["HG"],
    )
    _put_pdf(store, "bf-t8")
    snapshot = copy.deepcopy(item)
    keys_before = set(store.list_prefix(""))

    out = ingest_mod._backfill_missing_rows(store, _catalog(item), conn)

    assert out["rows"] == 1
    assert item == snapshot
    assert set(store.list_prefix("")) == keys_before
    conn.close()


def test_t9_second_call_after_a_full_drain_has_no_candidates(
        tmp_path, monkeypatch):
    """Pin: the second call returns candidates==0. The first call's rows==1
    is what makes a no-op implementation fail this test."""
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    conn = _open(tmp_path)
    _put_pdf(store, "bf-t9")
    cat = _catalog(_item("bf-t9"))

    first = ingest_mod._backfill_missing_rows(store, cat, conn)
    second = ingest_mod._backfill_missing_rows(store, cat, conn)

    assert first["rows"] == 1 and first["candidates"] == 1
    assert second["candidates"] == 0
    assert second["rows"] == 0
    conn.close()


def test_t10_run_backfills_a_receipted_row_missing_from_the_published_corpus(
        tmp_path, monkeypatch):
    """Pin: run() reports backfill_rows==1 and the published corpus contains
    the row; a dry run has no backfill_* keys and leaves that corpus unchanged.

    The degraded corpus is a real ingest whose store copy then loses one row —
    the same restore path run() uses — not a hand-built substitute.
    """
    monkeypatch.setattr(ingest_mod, "extract_pdf_text", lambda _b: _LONG_BODY)
    store = LocalStore(tmp_path / "store")
    corpus_path = tmp_path / "corpus.sqlite"
    _seed_pdf(store, "research_inbox/keeper.pdf", {
        "id": "bf-keeper",
        "title": "Keeper Rates Weekly",
        "institution": "UBS",
        "published_at": "2026-09-20T09:00:00Z",
        "summary_points": ["Keeper stays in the corpus."],
    })
    _seed_pdf(store, "research_inbox/missing.pdf", {
        "id": "bf-missing",
        "title": "Missing Copper Outlook",
        "institution": "Bernstein",
        "published_at": "2026-09-21T09:00:00Z",
        "summary_points": ["This row is deleted from the published corpus."],
    })

    first = ingest_mod.run(store, corpus_path)
    assert first["ingested"] == 2, first.get("error")
    assert store.exists(ingest_mod._receipt_key("bf-missing"))
    assert store.exists(f"{ingest_mod.VAULT_PREFIX}bf-missing.pdf")

    # Drop the receipted document's corpus row and publish that degraded
    # corpus. run() restores the store copy, so the edit has to be published
    # or the next run would put the row back from the previous snapshot.
    conn = corpus_mod.open_db(corpus_path)
    conn.execute("DELETE FROM documents WHERE doc_id=?", ("bf-missing",))
    conn.commit()
    conn.close()
    assert ingest_mod.publish_corpus(store, corpus_path)
    degraded = store.get_bytes(ingest_mod.CORPUS_KEY)
    # Prove the published bytes themselves are missing the row before run().
    degraded_path = tmp_path / "degraded.sqlite"
    degraded_path.write_bytes(degraded)
    raw = sqlite3.connect(degraded_path)
    assert raw.execute(
        "SELECT doc_id FROM documents WHERE doc_id=?", ("bf-missing",)
    ).fetchone() is None
    assert raw.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    raw.close()

    dry = ingest_mod.run(store, corpus_path, dry_run=True)
    assert not any(key.startswith("backfill_") for key in dry)
    assert store.get_bytes(ingest_mod.CORPUS_KEY) == degraded
    conn = corpus_mod.open_db(corpus_path)
    assert _row(conn, "bf-missing") is None
    conn.close()

    summary = ingest_mod.run(store, corpus_path)
    assert summary.get("error") is None, summary.get("error")
    assert summary["backfill_rows"] == 1

    published_path = tmp_path / "published.sqlite"
    published_path.write_bytes(store.get_bytes(ingest_mod.CORPUS_KEY))
    published = sqlite3.connect(published_path)
    found = published.execute(
        "SELECT title, body FROM documents WHERE doc_id=?", ("bf-missing",)
    ).fetchone()
    published.close()
    assert found is not None
    assert found[0] == "Missing Copper Outlook"
    assert "zyxbackfilltoken" in found[1]
