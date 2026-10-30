"""Fail-closed settled Grey Deer mirror diagnostics without a writer side effect."""
from __future__ import annotations

import json
import subprocess
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


def _commit_fixture(root: Path) -> None:
    for args in (
        ("init", "-q"),
        ("config", "user.name", "Risk Pair Fixture"),
        ("config", "user.email", "risk-pair-fixture@example.invalid"),
        ("add", "data/risk_envelope/latest.json", "site/riskdata/risk_envelope.json", "data/market_state/latest.json"),
        ("commit", "-q", "-m", "settled fixture"),
    ):
        subprocess.run(("git", "-C", str(root), *args), check=True, capture_output=True)


def test_git_commit_identity_ignores_uncommitted_runner_override(tmp_path):
    _fixture(tmp_path)
    _commit_fixture(tmp_path)
    site = tmp_path / "site/riskdata/risk_envelope.json"
    site.write_text('{"source_session":"2026-10-20"}', encoding="utf-8")
    assert check_pair(tmp_path).status == "DIVERGED"
    result = check_pair(tmp_path, git_ref="HEAD")
    assert result.status == "OK"
    assert result.reason == "mirror_bytes_and_market_session_match_settlement_unverified"
    assert result.settlement_proven is False
    assert main(["--root", str(tmp_path), "--git-ref", "HEAD"]) == 0


def test_git_commit_detects_published_asymmetry_after_worktree_repair(tmp_path):
    _fixture(tmp_path)
    site = tmp_path / "site/riskdata/risk_envelope.json"
    site.write_text('{"source_session":"2026-10-20"}', encoding="utf-8")
    _commit_fixture(tmp_path)
    data = tmp_path / "data/risk_envelope/latest.json"
    site.write_bytes(data.read_bytes())
    assert check_pair(tmp_path).status == "OK"
    result = check_pair(tmp_path, git_ref="HEAD")
    assert result.status == "DIVERGED"
    assert result.reason == "settled_mirror_bytes_differ"
    assert main(["--root", str(tmp_path), "--git-ref", "HEAD"]) == 1


def test_git_commit_reader_rejects_invalid_refs_and_missing_commits(tmp_path):
    _fixture(tmp_path)
    _commit_fixture(tmp_path)
    assert check_pair(tmp_path, git_ref="HEAD:bad/path").reason == "unsupported_git_ref"
    assert check_pair(tmp_path, git_ref="0" * 40).status == "UNAVAILABLE"


def test_original_precommit_and_new_exact_commit_checks_remain_distinct():
    script = Path(__file__).resolve().parents[1] / "scripts/ci/daily_engine_commit_outputs.sh"
    content = script.read_text(encoding="utf-8")
    assert "python -m scripts.check_risk_envelope_pair --root ." in content
    assert "python -m scripts.check_risk_envelope_pair --root . --git-ref HEAD" in content
    assert content.index("if push_do origin") < content.index("--git-ref HEAD") < content.index("push_won; exit 0")


def test_provisional_close_cannot_obtain_settlement_from_equal_hashes(tmp_path):
    _fixture(tmp_path)
    # The closing-bell pointer can have the same market date while still
    # being provisional; date and bytes alone cannot create settlement.
    for p in (tmp_path / "data/risk_envelope/latest.json", tmp_path / "site/riskdata/risk_envelope.json"):
        payload = json.loads(p.read_text(encoding="utf-8"))
        payload["revision"] = "settled"
        p.write_text(json.dumps(payload, sort_keys=True) + "\\n", encoding="utf-8")
    m = tmp_path / "data/market_state/latest.json"
    m.write_text(json.dumps({"asof": "2026-10-29", "provisional": True}), encoding="utf-8")
    result = check_pair(tmp_path)
    assert result.status == "OK"  # mirror identity only, not admissible source
    assert result.settlement_proven is False
    assert "settlement_unverified" in result.reason
