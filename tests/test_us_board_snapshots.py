"""The US board snapshots ledger reads as one stream over a frozen base and its parts.

``engine/us_board_snapshots.py`` owns the layout: ``snapshots.jsonl`` (frozen once
parts exist) followed by ``snapshots_parts/part-000001.jsonl``, ``part-000002.jsonl``, ...
These tests pin that no row is lost, merged, reordered or rewritten.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine import us_board_snapshots as ubs


def _row(as_of: str, pad: int = 0) -> str:
    return json.dumps({"as_of": as_of, "pad": "x" * pad}, separators=(",", ":"))


def _layout(tmp_path: Path, base: str, *parts: str) -> Path:
    led = tmp_path / "us_board_ledger"
    led.mkdir()
    b = led / "snapshots.jsonl"
    b.write_text(base, encoding="utf-8")
    if parts:
        d = led / ubs.PARTS_DIRNAME
        d.mkdir()
        for i, text in enumerate(parts, start=1):
            (d / f"part-{i:06d}.jsonl").write_text(text, encoding="utf-8")
    return b


# ---------------------------------------------------------------- reading


def test_without_parts_reads_exactly_like_the_single_file(tmp_path):
    text = _row("2026-10-15") + "\n" + _row("2026-10-16") + "\n"
    b = _layout(tmp_path, text)
    assert ubs.read_lines(b) == b.read_text().splitlines()
    with open(b, encoding="utf-8") as fh:
        assert list(ubs.iter_lines(b)) == list(fh)
    assert ubs.read_text(b) == text
    assert ubs.physical_paths(b) == [b]


def test_base_then_parts_in_numeric_order(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n" + _row("C") + "\n", _row("D") + "\n")
    got = [json.loads(x)["as_of"] for x in ubs.read_lines(b)]
    assert got == ["A", "B", "C", "D"]
    assert [json.loads(x)["as_of"] for x in ubs.iter_lines(b)] == got
    assert [p.name for p in ubs.physical_paths(b)] == [
        "snapshots.jsonl", "part-000001.jsonl", "part-000002.jsonl"]


def test_ten_parts_sort_numerically_not_by_listing_order(tmp_path):
    b = _layout(tmp_path, _row("base") + "\n", *[_row(f"p{i:02d}") + "\n" for i in range(1, 11)])
    got = [json.loads(x)["as_of"] for x in ubs.read_lines(b)]
    assert got == ["base"] + [f"p{i:02d}" for i in range(1, 11)]


def test_missing_ledger_is_empty_not_an_error(tmp_path):
    b = tmp_path / "us_board_ledger" / "snapshots.jsonl"
    assert ubs.exists(b) is False
    assert ubs.physical_paths(b) == []
    assert ubs.read_lines(b) == []
    assert list(ubs.iter_lines(b)) == []


def test_parts_without_the_base_are_refused(tmp_path):
    b = _layout(tmp_path, "", _row("B") + "\n")
    b.unlink()
    with pytest.raises(ubs.SnapshotLedgerError, match="without the base"):
        ubs.read_lines(b)
    with pytest.raises(ubs.SnapshotLedgerError):
        ubs.exists(b)


def test_a_gap_in_part_numbers_is_refused(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n", _row("C") + "\n")
    (b.parent / ubs.PARTS_DIRNAME / "part-000001.jsonl").unlink()
    with pytest.raises(ubs.SnapshotLedgerError, match="contiguous"):
        ubs.read_lines(b)


def test_an_unexpected_name_in_the_parts_dir_is_refused(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n")
    (b.parent / ubs.PARTS_DIRNAME / "part-1.jsonl").write_text(_row("Z") + "\n")
    with pytest.raises(ubs.SnapshotLedgerError, match="unexpected"):
        ubs.read_lines(b)


def test_hidden_files_in_the_parts_dir_are_skipped(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n")
    (b.parent / ubs.PARTS_DIRNAME / ".DS_Store").write_bytes(b"\x00\x01")
    assert [json.loads(x)["as_of"] for x in ubs.read_lines(b)] == ["A", "B"]


def test_symlinked_parts_are_refused(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n")
    outside = tmp_path / "outside.jsonl"
    outside.write_text(_row("C") + "\n")
    (b.parent / ubs.PARTS_DIRNAME / "part-000002.jsonl").symlink_to(outside)
    with pytest.raises(ubs.SnapshotLedgerError, match="regular file"):
        ubs.read_lines(b)


def test_a_symlinked_parts_dir_is_refused(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n")
    real = tmp_path / "elsewhere"
    real.mkdir()
    (real / "part-000001.jsonl").write_text(_row("B") + "\n")
    (b.parent / ubs.PARTS_DIRNAME).symlink_to(real, target_is_directory=True)
    with pytest.raises(ubs.SnapshotLedgerError, match="symlink"):
        ubs.read_lines(b)


# Without the next three guards these layouts raise OSError, and
# engine/prophet_board_since.py catches OSError around its ledger reads and
# returns [], so a broken layout would read as an empty board history.


def test_a_parts_path_that_is_a_file_is_refused(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n")
    (b.parent / ubs.PARTS_DIRNAME).write_text(_row("B") + "\n")
    with pytest.raises(ubs.SnapshotLedgerError, match="not a directory"):
        ubs.read_lines(b)


def test_a_part_that_is_a_directory_is_refused(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n")
    (b.parent / ubs.PARTS_DIRNAME / "part-000002.jsonl").mkdir()
    with pytest.raises(ubs.SnapshotLedgerError, match="regular file"):
        ubs.read_lines(b)


def test_a_base_that_is_a_directory_is_refused(tmp_path):
    b = tmp_path / "us_board_ledger" / "snapshots.jsonl"
    b.mkdir(parents=True)
    with pytest.raises(ubs.SnapshotLedgerError, match="base is not a file"):
        ubs.read_lines(b)


def test_a_torn_line_before_a_later_file_is_refused(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n" + '{"as_of":"tor', _row("B") + "\n")
    with pytest.raises(ubs.SnapshotLedgerError, match="newline"):
        ubs.read_lines(b)
    with pytest.raises(ubs.SnapshotLedgerError, match="newline"):
        list(ubs.iter_lines(b))


def test_a_torn_final_line_reads_like_the_single_file_did(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n" + '{"as_of":"tor')
    assert ubs.read_lines(b)[-1] == '{"as_of":"tor'
    assert list(ubs.iter_lines(b))[-1] == '{"as_of":"tor'


# ---------------------------------------------------------------- appending


def test_append_starts_the_base_when_there_is_no_ledger(tmp_path):
    b = tmp_path / "us_board_ledger" / "snapshots.jsonl"
    assert ubs.append_line(b, _row("A")) == b
    assert b.read_text() == _row("A") + "\n"


def test_append_stays_in_the_base_while_it_fits(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n")
    assert ubs.append_line(b, _row("B") + "\n", max_bytes=1000) == b
    assert ubs.read_lines(b) == [_row("A"), _row("B")]
    assert not (b.parent / ubs.PARTS_DIRNAME).exists()


def test_append_rolls_to_a_part_and_never_touches_the_base_again(tmp_path):
    b = _layout(tmp_path, _row("A", pad=60) + "\n")
    before = hashlib.sha256(b.read_bytes()).hexdigest()
    cap = b.stat().st_size + 10
    p1 = ubs.append_line(b, _row("B"), max_bytes=cap)
    assert p1 == b.parent / ubs.PARTS_DIRNAME / "part-000001.jsonl"
    # Even a row small enough to fit the base goes to the part once a part exists.
    tiny = '{"a":1}'
    assert ubs.append_line(b, tiny, max_bytes=10**6) == p1
    assert hashlib.sha256(b.read_bytes()).hexdigest() == before
    assert ubs.read_lines(b) == [_row("A", pad=60), _row("B"), tiny]


def test_append_opens_the_next_part_when_the_last_is_full(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B", pad=40) + "\n")
    p1 = b.parent / ubs.PARTS_DIRNAME / "part-000001.jsonl"
    p1_bytes = p1.read_bytes()
    target = ubs.append_line(b, _row("C", pad=40), max_bytes=len(p1_bytes) + 5)
    assert target.name == "part-000002.jsonl"
    assert p1.read_bytes() == p1_bytes
    assert [json.loads(x)["as_of"] for x in ubs.read_lines(b)] == ["A", "B", "C"]


def test_the_real_base_is_already_over_the_part_ceiling_so_the_first_append_rolls(tmp_path):
    # The tracked base was 88,488,651 B on 2026-10-16, above PART_MAX_BYTES (48 MiB):
    # with the default ceiling the very next row must open part-000001.
    assert 88_488_651 > ubs.PART_MAX_BYTES
    b = _layout(tmp_path, _row("A") + "\n")
    target = ubs.append_line(b, _row("B"), max_bytes=b.stat().st_size)
    assert target.name == "part-000001.jsonl"


def test_append_writes_the_same_bytes_the_old_writer_wrote(tmp_path):
    row = {"as_of": "2026-10-16", "names": ["A", "B"], "zh": "半导体"}
    line = json.dumps(row, separators=(",", ":"))
    b = tmp_path / "us_board_ledger" / "snapshots.jsonl"
    ubs.append_line(b, line)
    old = tmp_path / "old.jsonl"
    with old.open("a") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")
    assert b.read_bytes() == old.read_bytes()


def test_append_refuses_a_multi_line_row(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n")
    with pytest.raises(ubs.SnapshotLedgerError, match="single line"):
        ubs.append_line(b, _row("B") + "\n" + _row("C"))
    assert ubs.read_lines(b) == [_row("A")]


def test_append_refuses_a_row_with_a_carriage_return(tmp_path):
    # iter_lines (text mode) and read_lines (splitlines) both split on "\r",
    # so this one written row would read back as two.
    b = _layout(tmp_path, _row("A") + "\n")
    with pytest.raises(ubs.SnapshotLedgerError, match="single line"):
        ubs.append_line(b, _row("B") + "\r" + _row("C"))


def test_append_refuses_a_row_larger_than_a_part(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n")
    with pytest.raises(ubs.SnapshotLedgerError, match="ceiling"):
        ubs.append_line(b, _row("B", pad=200), max_bytes=100)


def test_append_refuses_to_follow_a_torn_final_line(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", '{"as_of":"tor')
    p1 = b.parent / ubs.PARTS_DIRNAME / "part-000001.jsonl"
    with pytest.raises(ubs.SnapshotLedgerError, match="torn"):
        ubs.append_line(b, _row("B"))
    assert p1.read_text() == '{"as_of":"tor'
    assert not (b.parent / ubs.PARTS_DIRNAME / "part-000002.jsonl").exists()


def test_append_refuses_a_gap_rather_than_writing_past_it(tmp_path):
    b = _layout(tmp_path, _row("A") + "\n", _row("B") + "\n", _row("C") + "\n")
    (b.parent / ubs.PARTS_DIRNAME / "part-000001.jsonl").unlink()
    with pytest.raises(ubs.SnapshotLedgerError):
        ubs.append_line(b, _row("D"))
