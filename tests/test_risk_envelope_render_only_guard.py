"""Render-only lanes cannot advance an uncommitted settled Risk Envelope."""
import json
import subprocess
from pathlib import Path

import pytest

from scripts import build_risk_envelope as producer

ROOT = Path(__file__).resolve().parents[1]
RENDER_ONLY_WORKFLOWS = (
    "render.yml",
    "engine-render.yml",
    "closing-bell.yml",
    "earlyclose.yml",
)


def _fixture(root: Path, *, session="2026-10-30", revision="settled"):
    env = {
        "schema": "mastermind.risk_envelope/v1",
        "revision": revision,
        "source_session": session,
        "as_of": session,
        "bundle_id": "source-bound-001",
        "data_state": "PARTIAL",
        "hazard_summary": {"stage": "FRAGILE"},
    }
    files = {}
    for name in ("data/risk_envelope/latest.json", "site/riskdata/risk_envelope.json"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(env, sort_keys=True) + "\n")
        files[name] = path
    market = root / "data/market_state/latest.json"
    market.parent.mkdir(parents=True, exist_ok=True)
    market.write_text(json.dumps({"asof": session}))
    return env, files, market


def _arm(monkeypatch, files):
    original = {name: path.read_bytes() for name, path in files.items()}
    checked = []

    def checked_git(cmd, **kwargs):
        assert cmd[:3] == ["git", "-C", cmd[2]]
        assert cmd[3] == "show"
        checked.append(cmd[-1])
        return original[cmd[-1].removeprefix("HEAD:")]

    monkeypatch.setenv("RISK_ENVELOPE_RENDER_READ_ONLY", "1")
    monkeypatch.setattr(producer.subprocess, "check_output", checked_git)

    def forbidden(*args, **kwargs):
        pytest.fail("render-only must never call the composer or write a settled artifact")

    monkeypatch.setattr(producer, "build", forbidden)
    monkeypatch.setattr(producer, "_atomic_write", forbidden)
    return original, checked


def test_committed_same_session_pair_is_reused_without_reissuance(tmp_path, monkeypatch):
    expected, files, _market = _fixture(tmp_path)
    _original, checked = _arm(monkeypatch, files)
    assert producer.write(tmp_path) == expected
    assert checked == [
        "HEAD:data/risk_envelope/latest.json",
        "HEAD:site/riskdata/risk_envelope.json",
    ]


@pytest.mark.parametrize("mutation", (
    "different_mirrors",
    "missing_public",
    "bad_json",
    "provisional",
    "wrong_schema",
    "wrong_session",
    "no_bundle",
    "market_clock_mismatch",
    "both_uncommitted",
))
def test_bad_or_provisional_pair_is_withheld_without_writes(tmp_path, monkeypatch, mutation):
    env, files, market = _fixture(tmp_path)
    original, _checked = _arm(monkeypatch, files)
    durable = files["data/risk_envelope/latest.json"]
    public = files["site/riskdata/risk_envelope.json"]
    if mutation == "different_mirrors":
        public.write_text('{"unmatched":true}')
    elif mutation == "missing_public":
        public.unlink()
    elif mutation == "bad_json":
        durable.write_text("not-json")
        public.write_text("not-json")
        # This fixture is committed but malformed: parsing must fail.
        monkeypatch.setattr(
            producer.subprocess, "check_output",
            lambda cmd, **kw: durable.read_bytes() if "data/risk_envelope" in cmd[-1] else public.read_bytes(),
        )
    elif mutation in {"provisional", "wrong_schema", "wrong_session", "no_bundle"}:
        if mutation == "provisional":
            env["revision"] = "live_provisional"
        elif mutation == "wrong_schema":
            env["schema"] = "untrusted"
        elif mutation == "wrong_session":
            env["source_session"] = "2026-10-20"
        else:
            env["bundle_id"] = ""
        data = (json.dumps(env, sort_keys=True) + "\n").encode()
        durable.write_bytes(data)
        public.write_bytes(data)
        monkeypatch.setattr(producer.subprocess, "check_output", lambda cmd, **kw: data)
    elif mutation == "market_clock_mismatch":
        market.write_text('{"asof":"2026-10-29"}')
    elif mutation == "both_uncommitted":
        # Two equal provisional worktree objects are not a committed settlement.
        data = durable.read_bytes().replace(b"source-bound-001", b"uncommitted-001")
        durable.write_bytes(data)
        public.write_bytes(data)
        assert data != original["data/risk_envelope/latest.json"]
    assert producer.write(tmp_path) == {}


def test_same_session_fresh_different_committed_bundles_are_withheld(tmp_path, monkeypatch):
    """Two valid Oct 30/FRESH settled envelopes are NOT a pair if bundles differ.

    This is the real post-nightly split found on main 2026-11-02.  The immutable
    HEAD preimages in _arm are distinct but individually valid: only pairwise
    equality permits a renderer to reuse a settled claim.
    """
    env, files, _market = _fixture(tmp_path)
    first, second = "durable-bundle-oct30", "public-bundle-oct30"
    for name, path in files.items():
        settled = dict(env, data_state="FRESH",
                       bundle_id=first if name.startswith("data/") else second)
        path.write_text(json.dumps(settled, sort_keys=True) + "\n")
    originals, checked = _arm(monkeypatch, files)
    assert originals["data/risk_envelope/latest.json"] != originals["site/riskdata/risk_envelope.json"]
    assert producer.write(tmp_path) == {}
    assert checked == []  # Refuse at pair equality before any HEAD acceptance.
    assert all(path.read_bytes() == originals[name] for name, path in files.items())


def test_missing_git_commit_is_not_treated_as_settlement(tmp_path, monkeypatch):
    _env, files, _market = _fixture(tmp_path)
    _arm(monkeypatch, files)

    def no_commit(*args, **kwargs):
        raise subprocess.CalledProcessError(128, ["git", "show"])

    monkeypatch.setattr(producer.subprocess, "check_output", no_commit)
    assert producer.write(tmp_path) == {}


def test_normal_nightly_write_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("RISK_ENVELOPE_RENDER_READ_ONLY", raising=False)
    env = {"schema": "mastermind.risk_envelope/v1", "revision": "settled"}
    outputs = []
    monkeypatch.setattr(producer, "build", lambda root, now: env)
    monkeypatch.setattr(producer, "_atomic_write", lambda path, payload: outputs.append((path, payload)))
    assert producer.write(tmp_path) is env
    assert [path for path, _ in outputs] == [
        tmp_path / "data/risk_envelope/latest.json",
        tmp_path / "site/riskdata/risk_envelope.json",
    ]
    assert outputs[0][1] == outputs[1][1]


def test_all_site_only_lanes_refuse_to_issue_settled_envelopes():
    for name in RENDER_ONLY_WORKFLOWS:
        content = (ROOT / ".github/workflows" / name).read_text()
        assert 'RISK_ENVELOPE_RENDER_READ_ONLY: "1"' in content, name
        assert "scripts.build_site" in content, name
    assert 'RISK_ENVELOPE_RENDER_READ_ONLY' not in (
        ROOT / ".github/workflows/daily.yml"
    ).read_text()
