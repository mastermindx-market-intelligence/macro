"""Fail-closed settled Grey Deer mirror diagnostics without a writer side effect."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.check_risk_envelope_pair import check_pair, main


def _fixture(root: Path, *, session: str = "2026-10-29", copy: str = "both") -> None:
    payload = {"source_session": session, "as_of": session, "bundle_id": "bundle-1", "data_state": "FRESH"}
    for name in ("data/risk_envelope/latest.json", "site/riskdata/risk_envelope.json"):
        if copy != "both" and copy not in name:
            continue
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    m = root / "data/market_state/latest.json"
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(json.dumps({"asof": session}), encoding="utf-8")


def test_pair_current_session_passes(tmp_path):
    _fixture(tmp_path)
    r = check_pair(tmp_path)
    assert r.status == "OK"
    assert r.source_session == "2026-10-29"
    assert r.market_asof == "2026-10-29"
    assert r.data_sha256 == r.site_sha256
    assert main(["--root", str(tmp_path)]) == 0


def test_different_clocks_fail_instead_of_using_older_fresh_snapshot(tmp_path):
    _fixture(tmp_path)
    d = tmp_path / "data/risk_envelope/latest.json"
    d.write_text(json.dumps({"source_session": "2026-10-20", "as_of": "2026-10-20", "bundle_id": "old", "data_state": "FRESH"}))
    r = check_pair(tmp_path)
    assert r.status == "DIVERGED"
    assert r.reason == "settled_mirror_bytes_differ"
    assert main(["--root", str(tmp_path)]) == 1


def test_same_values_but_different_bytes_fail(tmp_path):
    _fixture(tmp_path)
    p = tmp_path / "site/riskdata/risk_envelope.json"
    p.write_text(p.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
    assert check_pair(tmp_path).status == "DIVERGED"


def test_missing_copy_is_unavailable_not_calm(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "data/risk_envelope/latest.json").unlink()
    assert check_pair(tmp_path).status == "UNAVAILABLE"


def test_invalid_json_copy_is_unavailable(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "site/riskdata/risk_envelope.json").write_text("invalid-json", encoding="utf-8")
    assert check_pair(tmp_path).status == "UNAVAILABLE"


def test_matching_old_pair_is_stale_against_market_state(tmp_path):
    _fixture(tmp_path, session="2026-10-20")
    (tmp_path / "data/market_state/latest.json").write_text('{"asof":"2026-10-29"}')
    r = check_pair(tmp_path)
    assert r.status == "STALE"
    assert r.market_asof == "2026-10-29"


def test_pair_without_bundle_identity_is_invalid(tmp_path):
    _fixture(tmp_path)
    for p in (tmp_path / "data/risk_envelope/latest.json", tmp_path / "site/riskdata/risk_envelope.json"):
        j = json.loads(p.read_text(encoding="utf-8"))
        j.pop("bundle_id")
        p.write_text(json.dumps(j, sort_keys=True) + "\n", encoding="utf-8")
    assert check_pair(tmp_path).status == "INVALID"


def test_degraded_pair_can_be_current_without_fabricating_hazard(tmp_path):
    _fixture(tmp_path)
    for p in (tmp_path / "data/risk_envelope/latest.json", tmp_path / "site/riskdata/risk_envelope.json"):
        j = json.loads(p.read_text(encoding="utf-8"))
        j["data_state"] = "DEGRADED"
        j["hazard_summary"] = {"stage": None}
        p.write_text(json.dumps(j, sort_keys=True) + "\n", encoding="utf-8")
    r = check_pair(tmp_path)
    assert r.status == "OK"
    assert "risk" not in r.reason


def test_market_state_missing_fails_closed(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "data/market_state/latest.json").unlink()
    assert check_pair(tmp_path).status == "UNAVAILABLE"
