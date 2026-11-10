"""Same-date Prophet publication is idempotent and never rewrites origination history."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys

import pytest

from scripts import build_prophet as bp


@pytest.fixture
def published(tmp_path):
    root = tmp_path
    board = root / "site/factordata/us_standouts.json"
    board.parent.mkdir(parents=True)
    raw = b'{"as_of":"2026-11-03","eligible":159}\n'
    board.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    ledger_dir = root / "data/prophet"
    archive = ledger_dir / "origination_sources" / f"{digest}.json.gz"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    index = root / "site/prophet/index.json"
    index.parent.mkdir(parents=True)
    record = {
        "asof": "2026-11-04",
        "source_board_sha256": digest,
        "source_board_snapshot_path": f"data/prophet/origination_sources/{digest}.json.gz",
        "source_board_snapshot_encoding": "gzip",
        "intake": {"originated": 12},
        "plan_count": 875,
    }
    index.write_text(json.dumps(record), encoding="utf-8")
    return board, index, ledger_dir, archive, record


def check(published, *, asof="2026-11-04"):
    board, index, ledger_dir, _, _ = published
    return bp._already_published_same_date(
        asof=asof, board_path=board, index_path=index, ledger_dir=ledger_dir,
    )


def test_exact_same_date_source_is_no_write_idempotent(published):
    board, index, _, archive, _ = published
    before = (board.read_bytes(), index.read_bytes(), archive.read_bytes())
    assert check(published) is True
    assert (board.read_bytes(), index.read_bytes(), archive.read_bytes()) == before


def test_missing_prior_index_allows_first_run(published):
    published[1].unlink()
    assert check(published) is False


def test_next_date_allows_normal_publish_path(published):
    published[0].write_bytes(b'{"as_of":"2026-11-04"}\n')
    assert check(published, asof="2026-11-05") is False


def test_rebuilt_same_date_board_refuses_without_rebinding_history(published):
    board, index, _, archive, _ = published
    prior_index, prior_archive = index.read_bytes(), archive.read_bytes()
    board.write_bytes(b'{"as_of":"2026-11-03","already_open":true}\n')
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_SAME_DATE_SOURCE_VARIANT"):
        check(published)
    assert index.read_bytes() == prior_index
    assert archive.read_bytes() == prior_archive


def test_missing_archived_source_refuses(published):
    published[3].unlink()
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_SAME_DATE_SNAPSHOT_MISSING"):
        check(published)


def test_tampered_source_archive_refuses(published):
    published[3].write_bytes(gzip.compress(b'{"tampered":true}', mtime=0))
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_SAME_DATE_SNAPSHOT_HASH_MISMATCH"):
        check(published)


def test_invalid_index_refuses(published):
    published[1].write_text("{", encoding="utf-8")
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_PRIOR_INDEX_UNREADABLE"):
        check(published)


def test_unbound_snapshot_path_refuses(published):
    record = published[4].copy()
    record["source_board_snapshot_path"] = "../../repointed.json.gz"
    published[1].write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_SAME_DATE_SNAPSHOT_UNBOUND"):
        check(published)


def test_symlinked_index_refuses(published, tmp_path):
    index = published[1]
    target = tmp_path / "real-index.json"
    index.rename(target)
    index.symlink_to(target)
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_SAME_DATE_INDEX_SYMLINK"):
        check(published)


def test_symlinked_current_board_refuses(published, tmp_path):
    board = published[0]
    target = tmp_path / "real-source.json"
    board.rename(target)
    board.symlink_to(target)
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_SAME_DATE_CURRENT_SOURCE_UNAVAILABLE"):
        check(published)


def test_main_exits_before_ledger_or_snapshot_write_on_exact_replay(published, monkeypatch):
    board, index, ledger_dir, _, _ = published
    monkeypatch.setattr(bp, "STANDOUTS_PATH", board)
    monkeypatch.setattr(bp, "INDEX_PATH", index)
    monkeypatch.setattr(bp, "LEDGER_DIR", ledger_dir)
    monkeypatch.setattr(sys, "argv", ["build_prophet", "--date", "2026-11-04"])
    monkeypatch.setattr(bp, "_freeze_origination_source_board", lambda *a: pytest.fail("replay must not freeze"))
    assert bp.main() is None
    assert json.loads(index.read_text())["intake"]["originated"] == 12


def test_main_refuses_source_variant_before_ledger_or_snapshot_write(published, monkeypatch):
    board, index, ledger_dir, archive, _ = published
    board.write_bytes(b'{"as_of":"2026-11-03","already_open":true}\n')
    monkeypatch.setattr(bp, "STANDOUTS_PATH", board)
    monkeypatch.setattr(bp, "INDEX_PATH", index)
    monkeypatch.setattr(bp, "LEDGER_DIR", ledger_dir)
    monkeypatch.setattr(sys, "argv", ["build_prophet", "--date", "2026-11-04"])
    monkeypatch.setattr(bp, "_freeze_origination_source_board", lambda *a: pytest.fail("variant must not freeze"))
    before = (index.read_bytes(), archive.read_bytes())
    with pytest.raises(RuntimeError, match="REFUSED_PROPHET_SAME_DATE_SOURCE_VARIANT"):
        bp.main()
    assert (index.read_bytes(), archive.read_bytes()) == before
