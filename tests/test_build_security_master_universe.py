"""The identity universe admits the mid- and small-cap breadth constituents.

Pins DEC-ITP-ISSUER-UNIVERSE-ADMITS-R1-CONSTITUENTS-2026-10-07 (ITP A8):
``load_universe()`` reads ``data/midcap_breadth/constituents.parquet`` and
``data/smallcap_breadth/constituents.parquet`` exactly as it reads
``data/breadth/constituents.parquet`` (same ``exists()`` guard, same index
handling, ``first_seen`` None), and the nightly seam treats a missing mid/small
file exactly as it treats a missing ``CONSTITUENTS``: a non-fatal refusal that
keeps the last-good artifacts.  Hermetic: every input is a tmp fixture, and the
nightly cases refuse pre-flight, before any build runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_security_master as BUILD  # noqa: E402

SOURCES = dict(
    CONSTITUENTS="breadth.constituents",
    MIDCAP_CONSTITUENTS="midcap_breadth.constituents",
    SMALLCAP_CONSTITUENTS="smallcap_breadth.constituents",
)


def _constituents(path: Path, tickers: list[str]) -> Path:
    index = pd.Index(tickers, name="symbol")
    pd.DataFrame(dict(name=list(tickers)), index=index).to_parquet(path)
    return path


@pytest.fixture
def isolated_universe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    membership = tmp_path / "membership.json"
    membership.write_text(json.dumps(dict(baskets=dict())))
    monkeypatch.setattr(BUILD, "CONSTITUENTS", _constituents(tmp_path / "large.parquet", ["AAA", " bbb "]))
    monkeypatch.setattr(BUILD, "MIDCAP_CONSTITUENTS", _constituents(tmp_path / "mid.parquet", ["MIDX", "AAA"]))
    monkeypatch.setattr(BUILD, "SMALLCAP_CONSTITUENTS", _constituents(tmp_path / "small.parquet", ["smlx"]))
    monkeypatch.setattr(BUILD, "MEMBERSHIP", membership)
    return tmp_path


def test_the_new_inputs_are_root_relative_beside_constituents() -> None:
    assert BUILD.CONSTITUENTS == BUILD.ROOT / "data" / "breadth" / "constituents.parquet"
    assert BUILD.MIDCAP_CONSTITUENTS == BUILD.ROOT / "data" / "midcap_breadth" / "constituents.parquet"
    assert BUILD.SMALLCAP_CONSTITUENTS == BUILD.ROOT / "data" / "smallcap_breadth" / "constituents.parquet"


def test_load_universe_admits_a_mid_and_a_small_ticker_with_their_sources(isolated_universe: Path) -> None:
    universe = BUILD.load_universe()
    assert sorted(universe) == ["AAA", "BBB", "MIDX", "SMLX"]
    assert universe["MIDX"] == dict(sources=["midcap_breadth.constituents"], first_seen=None)
    assert universe["SMLX"] == dict(sources=["smallcap_breadth.constituents"], first_seen=None)
    assert universe["BBB"] == dict(sources=["breadth.constituents"], first_seen=None)
    # A name on two lists carries both sources, in read order, and still no first_seen.
    assert universe["AAA"] == dict(
        sources=["breadth.constituents", "midcap_breadth.constituents"], first_seen=None,
    )


@pytest.mark.parametrize("attr", sorted(SOURCES))
def test_load_universe_skips_any_missing_constituents_file_the_same_way(
    isolated_universe: Path, monkeypatch: pytest.MonkeyPatch, attr: str,
) -> None:
    monkeypatch.setattr(BUILD, attr, isolated_universe / "does-not-exist.parquet")
    universe = BUILD.load_universe()
    assert universe, "the other two lists still load"
    assert all(SOURCES[attr] not in row["sources"] for row in universe.values())
    for other in set(SOURCES) - set([attr]):
        assert any(SOURCES[other] in row["sources"] for row in universe.values()), other


@pytest.mark.parametrize("attr", sorted(SOURCES))
def test_nightly_refuses_identically_on_any_missing_constituents_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], attr: str,
) -> None:
    missing = tmp_path / ("missing-" + attr.lower() + ".parquet")
    monkeypatch.setattr(BUILD, attr, missing)
    assert BUILD.run_nightly_refresh(tmp_path) == 0
    out = capsys.readouterr().out
    assert "::warning title=security-master-nightly::missing identity input(s)" in out
    assert str(missing) in out
    assert not (tmp_path / BUILD.MASTER_NAME).exists()
    assert not (tmp_path / BUILD.RECEIPT_NAME).exists()
