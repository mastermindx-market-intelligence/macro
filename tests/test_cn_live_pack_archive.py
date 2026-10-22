"""CN live-pack archive — the content-addressed N-1 record before every roll.

`publish_with_archive` writes `<prefix>/<intended_session>/<digest>.json`
FIRST and replaces `r2io.CN_PACK_KEY` only when that put succeeded (Decision
F7): the archived N-1 pack is the authority for first-event identity and
frozen score/rank, so a roll that cannot preserve it must not erase it. The
pack is stamped with the session it is armed FOR (the CN calendar) and the
board identity it froze from. Every put here is a recording fake — no test
touches R2.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from engine.prophet_live import r2io
import scripts.build_cn_live_pack as B

ROOT = Path(__file__).resolve().parent.parent
BASE_SHA = "d910e40604720e9e9fdd35a489c39e2ef1b6dfee"
FACTORDATA = "site/factordata/china_standouts.json"


def _series_end(last: str, n: int = 40) -> pd.Series:
    """Closes whose tip bar is exactly ``last`` (a weekday)."""
    idx = pd.bdate_range(end=pd.Timestamp(last), periods=n)
    return pd.Series([10.0 + 0.01 * (i % 5) for i in range(n)], index=idx)


def _gate(threshold: float = 5.0):
    def g(_ticker: str, close) -> dict:
        px = float(close.iloc[-1])
        buy = px >= threshold
        return {"eligible": True, "tier": "T2", "tier_cascade": "T2" if buy else None,
                "sub": "confirmed"}
    return g


def _payload(session: str = "2026-10-19") -> dict:
    return {"schema": "cn_prophet_live.armed/v1", "market": "CN",
            "names": {"600519.SS": {"score": 78.75}},
            "meta": {"as_of": "2026-10-16", "intended_session": session}}


def _recording_put(default: bool = True):
    """Fake ``put`` recording (key, canonical bytes, payload object) per call."""
    calls: list[tuple[str, bytes, object]] = []

    def put(key: str, payload, *, s3=None) -> bool:
        calls.append((key, json.dumps(payload, allow_nan=False, sort_keys=True,
                                      separators=(",", ":")).encode(), payload))
        return default

    put.calls = calls
    return put


def test_archive_key_is_prefix_session_digest() -> None:
    assert r2io.CN_PACK_ARCHIVE_PREFIX == "live_flow/cn_prophet_live_armed_archive"
    assert r2io.pack_archive_key("2026-10-19", "abc123") == (
        "live_flow/cn_prophet_live_armed_archive/2026-10-19/abc123.json")


def test_a1_archive_put_precedes_current_put_identical_bytes() -> None:
    put = _recording_put()
    payload = _payload()
    assert B.publish_with_archive(payload, put=put) is True
    assert len(put.calls) == 2
    first, second = put.calls
    assert first[0].startswith(r2io.CN_PACK_ARCHIVE_PREFIX + "/")
    assert second[0] == r2io.CN_PACK_KEY
    assert first[1] == second[1]          # byte-identical canonical JSON
    assert first[2] is payload and first[2] is second[2]   # the identical object


def test_a2_key_shape_and_digest_recomputes_after_removing_the_stamp() -> None:
    put = _recording_put()
    assert B.publish_with_archive(_payload(), put=put) is True
    key, body, _ = put.calls[0]
    parts = key.split("/")
    assert "/".join(parts[:-2]) == r2io.CN_PACK_ARCHIVE_PREFIX
    assert parts[-2] == "2026-10-19"
    stored = json.loads(body)["meta"]["pack_sha256"]
    assert parts[-1] == f"{stored}.json"
    assert key == r2io.pack_archive_key("2026-10-19", stored)
    doc = json.loads(body)
    del doc["meta"]["pack_sha256"]        # remove exactly that one field
    recomputed = hashlib.sha256(json.dumps(
        doc, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert recomputed == stored
    assert json.loads(put.calls[1][1])["meta"]["pack_sha256"] == stored


def test_a3_archive_failure_never_replaces_the_current_key(monkeypatch, capsys) -> None:
    put = _recording_put(default=False)
    assert B.publish_with_archive(_payload(), put=put) is False
    assert len(put.calls) == 1                       # the archive put only
    assert put.calls[0][0].startswith(r2io.CN_PACK_ARCHIVE_PREFIX + "/")
    assert "::error title=cn-live-pack::pack archive write failed - " \
           "current key NOT replaced" in capsys.readouterr().out

    # main(): monkeypatched build; PROPHET_LIVE_NO_PUBLISH makes the REAL
    # default put refuse the archive key before any client is built, so the
    # same refusal path runs end to end with no network.
    from scripts import build_china_library as bcl
    rows = [("600519.SS", _series_end("2026-10-16"), None, "Kweichow", "Consumer")]
    monkeypatch.setattr(bcl, "universe", lambda: rows)
    monkeypatch.setattr(bcl, "load_tradability_metadata",
                        lambda: {"mktcap_by": {}, "name_zh_by": {},
                                 "name_en_by": {}, "st_flag_by": {}})
    monkeypatch.setattr("engine.china_liquidity.liquidity_map", lambda ts: {})
    monkeypatch.setattr(B, "build", lambda **kw: _payload())
    monkeypatch.setenv("PROPHET_LIVE_NO_PUBLISH", "1")
    capsys.readouterr()
    assert B.main(["--publish"]) == 1
    out = capsys.readouterr().out
    assert "current key NOT replaced" in out
    assert out.count("refusing to write") == 1      # the archive key only
    assert r2io.CN_PACK_KEY not in out              # the current key was never attempted


def test_a4_intended_session_is_the_next_cn_calendar_session() -> None:
    # Friday 2026-10-16 → Monday 2026-10-19: a plain weekend hop, no closure
    # between (the announced CN 2026 slate has nothing after Oct 7).
    p = B.build(series={"600519.SS": _series_end("2026-10-16")},
                gate_fn=_gate(), frozen={})
    assert p["meta"]["intended_session"] == "2026-10-19"

    # Tip 2026-09-30 → 2026-10-08: National Day Golden Week. The closure dates
    # come from the announced CN 2026 slate, lib/exchange_holidays.py:88
    # ("National Day", "10-01 10-02 10-05 10-06 10-07"), which
    # lib/cn_calendar.holidays() prefers over its fallback rules
    # (lib/cn_calendar.py:121-123); 10-03/10-04 are that week's weekend.
    p2 = B.build(series={"600519.SS": _series_end("2026-09-30")},
                 gate_fn=_gate(), frozen={})
    assert p2["meta"]["intended_session"] == "2026-10-08"


def test_a5_identical_content_addresses_identically() -> None:
    payload = _payload()
    put1, put2 = _recording_put(), _recording_put()
    assert B.publish_with_archive(payload, put=put1) is True
    assert B.publish_with_archive(payload, put=put2) is True   # re-stamp is idempotent
    assert [c[0] for c in put1.calls] == [c[0] for c in put2.calls]
    assert put1.calls[0][1] == put2.calls[0][1]
    assert B.pack_digest(payload) == json.loads(
        put1.calls[0][1])["meta"]["pack_sha256"]

    other = _payload()
    other["names"]["600519.SS"]["score"] = 77.0
    put3 = _recording_put()
    assert B.publish_with_archive(other, put=put3) is True
    assert put3.calls[0][0] != put1.calls[0][0]     # different content, different key


def _write_board(root: Path, doc: object) -> bytes:
    p = root / FACTORDATA
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(doc).encode("utf-8")
    p.write_bytes(raw)
    return raw


def test_a6_source_board_identity_file_injected_none(tmp_path: Path) -> None:
    raw = _write_board(tmp_path, {
        "as_of": "2026-10-16",
        "buy": [{"ticker": "600519.SS", "name": "600519.SS",
                 "prophet": {"version": "cn_prophet_v4", "score": 78.75},
                 "board_rank": 1, "score_rank": 2}]})

    out = B.build(root=tmp_path, series={"600519.SS": _series_end("2026-10-16")},
                  gate_fn=_gate())
    assert out["meta"]["source_board"] == {
        "path": FACTORDATA, "as_of": "2026-10-16",
        "sha256": hashlib.sha256(raw).hexdigest()}

    receipt: dict = {}
    B.load_frozen(tmp_path, receipt_out=receipt)     # the projection receipt rides along
    assert receipt["path"] == FACTORDATA
    assert receipt["as_of"] == "2026-10-16"
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["projected"] == 1 and receipt["primary_rows"] == 1

    inj = B.build(series={"600519.SS": _series_end("2026-10-16")}, gate_fn=_gate(),
                  frozen={"600519.SS": {"prophet_score": 78.75, "prophet_rank": 1}})
    assert inj["meta"]["source_board"] == {"path": None, "reason": "injected"}

    none = B.build(root=tmp_path / "no-board", series={"600519.SS": _series_end(
        "2026-10-16")}, gate_fn=_gate())
    assert none["meta"]["source_board"] == {"path": None, "reason": "no_board"}

    _write_board(tmp_path, {"as_of": "not-a-date", "buy": [
        {"ticker": "600519.SS", "prophet": {"score": 78.75}, "board_rank": 1}]})
    refused = B.build(root=tmp_path, series={"600519.SS": _series_end("2026-10-16")},
                      gate_fn=_gate())
    assert refused["meta"]["source_board"] == {"path": None, "reason": "refused:as_of"}


def test_a7_base_publish_wrote_only_the_current_key(tmp_path, monkeypatch) -> None:
    """BASE proof: the pre-archive `main --publish` wrote exactly one key."""
    if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e",
                       f"{BASE_SHA}^{{commit}}"]).returncode != 0:
        pytest.skip(f"BASE {BASE_SHA[:8]} absent from this clone (shallow checkout)")
    src = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{BASE_SHA}:scripts/build_cn_live_pack.py"],
        capture_output=True, text=True, check=True).stdout
    mod_path = tmp_path / "_base_build_cn_live_pack.py"  # throwaway, outside the repo
    mod_path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_base_build_cn_live_pack", mod_path)
    base_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base_mod)

    from scripts import build_china_library as bcl
    rows = [("600519.SS", _series_end("2026-10-16"), None, "Kweichow", "Consumer")]
    published: list[str] = []
    monkeypatch.setattr(bcl, "universe", lambda: rows)
    monkeypatch.setattr(bcl, "load_tradability_metadata",
                        lambda: {"mktcap_by": {}, "name_zh_by": {},
                                 "name_en_by": {}, "st_flag_by": {}})
    monkeypatch.setattr("engine.china_liquidity.liquidity_map", lambda ts: {})
    monkeypatch.setattr(base_mod, "build", lambda **kw: _payload())
    monkeypatch.setattr(B.r2io, "put_json",
                        lambda key, payload, **kw: published.append(key) or True)

    assert base_mod.main(["--publish"]) == 0
    assert published == [r2io.CN_PACK_KEY]   # exactly one key — no archive existed
