"""Route-boundary tests for the authenticated beta evaluation transport.

These prove only this router's auth ordering, zero-parameter grammar, status
framing, frozen-header binding and byte-exact pass-through, mounted alone on
a throwaway repository root. They are NOT live evaluation proof — the frozen
harness's own contract tests live in tests/test_prophet_beta_evaluation.py,
and the nightly isolation contract is pinned at the bottom of this file
against the real extracted workflow script.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

URL = "/api/prophet/beta-evaluation/v1"
ROOT = Path(__file__).resolve().parents[1]
HEADER_REL = "research/prophet_v4/beta_first_evaluation/protocol_header_v1.json"
ARTIFACT_REL = "site/prophet/beta_evaluation.json"

HEADER_BYTES = b'{"protocol_id":"prophet-beta-first-evaluation-v1","frozen_for":"tests"}\n'
HEADER_SHA = hashlib.sha256(HEADER_BYTES).hexdigest()


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def artifact_bytes(header_sha: str = HEADER_SHA) -> bytes:
    body = (
        '{"schema": "prophet.beta_evaluation/v1", '
        '"view": "STRATEGY_EVALUATION_VIEW", '
        '"protocol": {"header_sha256": "%s"}, '
        '"headline": ["descriptive only"], '
        '"may_trade": false}\n' % header_sha
    )
    return body.encode("utf-8")


@pytest.fixture
def repo(tmp_path) -> Path:
    """A throwaway repository root with a bound artifact and frozen header."""
    (tmp_path / "research/prophet_v4/beta_first_evaluation").mkdir(parents=True)
    (tmp_path / HEADER_REL).write_bytes(HEADER_BYTES)
    (tmp_path / "site/prophet").mkdir(parents=True)
    (tmp_path / ARTIFACT_REL).write_bytes(artifact_bytes())
    return tmp_path


@pytest.fixture
def route(monkeypatch, repo):
    mod = importlib.import_module("app.prophet_beta_evaluation")
    monkeypatch.setattr(mod, "_REPO_ROOT", repo)
    return mod


@pytest.fixture
def client(route):
    app = FastAPI()
    app.include_router(route.router)
    app.dependency_overrides[route.require_site_full_user] = lambda: {"id": "paid-fixture"}
    with TestClient(app) as test_client:
        yield test_client


# ── module and registration ──────────────────────────────────────────────────

def test_beta_evaluation_route_module_is_available():
    assert importlib.util.find_spec("app.prophet_beta_evaluation"), (
        "beta evaluation transport is absent"
    )


def test_router_is_registered_on_the_real_app():
    """The real application answers the route with auth, not 404."""
    import app.main as main

    with TestClient(main.app) as real:
        response = real.get(URL)
    assert response.status_code in (401, 403), response.text
    private(response)


def test_route_uses_the_canonical_site_full_dependency():
    """The entitlement gate is the shared Prophet dependency, not a new one."""
    from app import prophet_beta_evaluation as mod

    from app.prophet_lab import require_site_full_user

    assert mod.require_site_full_user is require_site_full_user


# ── auth ordering ────────────────────────────────────────────────────────────

class _SpyRoot:
    """Records every file read the handler performs (repo root stand-in)."""

    def __init__(self, base: Path):
        self.base = base
        self.reads: list[str] = []

    def __truediv__(self, rel: str) -> "_SpyPath":
        return _SpyPath(self.base / rel, rel, self)


class _SpyPath:
    def __init__(self, real: Path, rel: str, spy: "_SpyRoot"):
        self._real, self._rel, self._spy = real, rel, spy

    def read_bytes(self) -> bytes:
        self._spy.reads.append(self._rel)
        return self._real.read_bytes()


@pytest.mark.parametrize("denial", [401, 403])
def test_real_auth_chain_denies_before_any_file_read(route, monkeypatch, repo, denial):
    """401/403 win over every later concern, and no artifact/header byte is read."""
    import app.main as main
    import app.paywall as paywall

    calls: list[str] = []

    def authenticate(_authorization):
        calls.append("authenticate")
        if denial == 401:
            raise HTTPException(401, "missing bearer token")
        return {"id": "free-fixture"}

    def entitle(_user, *, always=False):
        assert always is True
        calls.append("entitle")
        raise HTTPException(403, "site_full required")

    monkeypatch.setattr(main, "require_user", authenticate)
    monkeypatch.setattr(paywall, "enforce_site_full", entitle)
    spy = _SpyRoot(repo)
    monkeypatch.setattr(route, "_REPO_ROOT", spy)
    app = FastAPI()
    app.include_router(route.router)
    with TestClient(app) as boundary:
        response = boundary.get(URL, params={"anything": "else"})
    assert response.status_code == denial
    assert calls == (["authenticate"] if denial == 401
                     else ["authenticate", "entitle"])
    assert spy.reads == []  # auth failure precedes any file read
    private(response)


# ── the one success shape ────────────────────────────────────────────────────

def test_served_artifact_is_byte_equivalent_with_private_headers(client, repo):
    raw = (repo / ARTIFACT_REL).read_bytes()
    response = client.get(URL)
    assert response.status_code == 200
    assert response.content == raw  # exact stored bytes, no reshaping
    assert response.headers["content-type"].startswith("application/json")
    private(response)


def test_each_request_rereads_the_artifact(client, repo):
    assert client.get(URL).status_code == 200
    fresh = artifact_bytes().replace(b"descriptive only", b"second generation")
    (repo / ARTIFACT_REL).write_bytes(fresh)
    again = client.get(URL)
    assert again.status_code == 200
    assert again.content == fresh  # no caching between calls


# ── private outages, never a partial or stale-looking 200 ────────────────────

def _reason(client):
    response = client.get(URL)
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "evaluation_unavailable"
    private(response)
    return body["reason"]


def test_missing_artifact_is_a_private_outage(client, repo):
    (repo / ARTIFACT_REL).unlink()
    assert _reason(client) == "artifact_unavailable"


def test_unparsable_artifact_is_a_private_outage(client, repo):
    (repo / ARTIFACT_REL).write_bytes(b'{"schema": "prophet.beta_evaluation/v1",')
    assert _reason(client) == "artifact_unparsable"


def test_wrong_schema_artifact_is_a_private_outage(client, repo):
    (repo / ARTIFACT_REL).write_bytes(
        b'{"schema": "prophet.beta_evaluation/v2", "protocol": {}}\n')
    assert _reason(client) == "schema_mismatch"


def test_non_object_artifact_is_a_private_outage(client, repo):
    (repo / ARTIFACT_REL).write_bytes(b'[1, 2, 3]\n')
    assert _reason(client) == "schema_mismatch"


def test_header_hash_mismatch_is_a_private_outage(client, repo):
    # Artifact claims a header hash that the committed header does not have.
    (repo / ARTIFACT_REL).write_bytes(artifact_bytes(header_sha="0" * 64))
    assert _reason(client) == "protocol_header_mismatch"


def test_artifact_without_bound_hash_is_a_private_outage(client, repo):
    (repo / ARTIFACT_REL).write_bytes(
        b'{"schema": "prophet.beta_evaluation/v1", "protocol": {}}\n')
    assert _reason(client) == "protocol_header_mismatch"


def test_missing_frozen_header_is_a_private_outage(client, repo):
    (repo / HEADER_REL).unlink()
    assert _reason(client) == "protocol_header_unavailable"


def test_outage_reasons_disclose_no_paths(client, repo):
    (repo / ARTIFACT_REL).unlink()
    response = client.get(URL)
    assert str(repo) not in response.text
    assert "site/prophet" not in response.text


# ── the caller chooses nothing ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "query",
    [
        "?refresh=1",
        "?asof=2026-11-09",
        "?" + "&".join(["level=L0"] * 2),
        # daily-brief pins are not accepted here either
        "?source_sha256=sha256:" + "a" * 64,
        "?root=/private",
    ],
)
def test_no_query_parameter_is_honoured(client, repo, query):
    response = client.get(URL + query)
    assert response.status_code == 400
    assert response.json() == {"error": "INVALID_QUERY"}
    private(response)


# ── the real committed artifact and header are consistent ────────────────────

def test_committed_artifact_is_bound_to_the_committed_header():
    """The shipped site/prophet/beta_evaluation.json passes its own gate."""
    mod = importlib.import_module("app.prophet_beta_evaluation")
    artifact = ROOT / ARTIFACT_REL
    header = ROOT / HEADER_REL
    if not artifact.is_file():
        pytest.skip("artifact not committed in this checkout")
    import json

    parsed = json.loads(artifact.read_text(encoding="utf-8"))
    assert parsed["schema"] == mod._EXPECTED_SCHEMA
    assert parsed["protocol"]["header_sha256"] == hashlib.sha256(
        header.read_bytes()
    ).hexdigest()


# ── nightly step isolation contract ─────────────────────────────────────────

NIGHTLY = ROOT / "scripts" / "ci" / "daily_engine_prophet_nightly.sh"
CHECKPOINT = ROOT / "scripts" / "ci" / "daily_engine_prophet_checkpoint.sh"


def _eval_block() -> str:
    """The beta-evaluation segment of the real nightly script, verbatim."""
    lines = NIGHTLY.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if "::group::prophet beta-first evaluation" in line)
    end = next(i for i in range(start + 1, len(lines))
               if "::endgroup::" in lines[i])
    return "\n".join(lines[start + 1:end]) + "\n"


def _sandbox(tmp_path: Path) -> Path:
    """A repository-shaped sandbox whose parquet inputs are unreadable dummies.

    Every input the eval block checks for exists, so the step proceeds to run
    the real runner — which then fails on the dummy price bytes. That is the
    failure-containment path under test.
    """
    repo = tmp_path / "sandbox"
    (repo / "site/prophet").mkdir(parents=True)
    (repo / "data/breadth").mkdir(parents=True)
    (repo / "data/yahoo").mkdir(parents=True)
    (repo / "research/prophet_v4/beta_first_evaluation").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    (repo / "site/prophet/index.json").write_text("{}\n")
    (repo / "data/prophet").mkdir()
    (repo / "data/prophet/ledger.jsonl").write_text('{"id":"x"}\n')
    for rel in ("data/breadth/sp1500_pit_membership.parquet",
                "data/breadth/sp1500_pit_sectors.parquet",
                "data/yahoo/SPY.parquet"):
        (repo / rel).write_bytes(b"not a parquet\n")
    # Real frozen header bytes so the runner's refusal cannot fire before the
    # price read: the failure must come from the unreadable dummy inputs.
    (repo / HEADER_REL).write_bytes((ROOT / HEADER_REL).read_bytes())
    # A previously committed artifact that must survive the failed step.
    (repo / ARTIFACT_REL).write_bytes(b'{"schema":"previous-night"}\n')
    # The real runner, copied so its own ROOT resolves to the sandbox.
    (repo / "scripts/run_prophet_beta_evaluation.py").write_text(
        (ROOT / "scripts/run_prophet_beta_evaluation.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return repo


def _run_eval_block(repo: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)  # engine.prophet_beta_evaluation from the repo
    env["PROPHET_EVAL_PRICES"] = str(repo / "data/yahoo")
    # An exec wrapper (not a symlink): venv resolution follows the wrapper's
    # target, keeping the test interpreter's site-packages visible.
    shim = repo / "bin"
    shim.mkdir(exist_ok=True)
    shim.joinpath("python").write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8"
    )
    shim.joinpath("python").chmod(0o755)
    env["PATH"] = f"{shim}:{env['PATH']}"
    return subprocess.run(
        ["bash", "-c", _eval_block()], cwd=repo, env=env, check=False,
        capture_output=True, text=True, timeout=180,
    )


def test_nightly_eval_failure_is_contained_and_previous_artifact_kept(tmp_path):
    repo = _sandbox(tmp_path)
    previous = (repo / ARTIFACT_REL).read_bytes()

    result = _run_eval_block(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "prophet beta evaluation" in result.stdout  # the non-fatal warning
    # The previously committed artifact is preserved byte-for-byte...
    assert (repo / ARTIFACT_REL).read_bytes() == previous
    # ...and no atomic-write temp sibling is left behind.
    assert list((repo / "site/prophet").glob(".beta_evaluation.tmp.*")) == []


def test_nightly_eval_block_skips_cleanly_when_an_input_is_missing(tmp_path):
    repo = _sandbox(tmp_path)
    (repo / "data/yahoo/SPY.parquet").unlink()
    previous = (repo / ARTIFACT_REL).read_bytes()

    result = _run_eval_block(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "missing on this runner" in result.stdout
    assert "skipping regeneration" in result.stdout
    assert (repo / ARTIFACT_REL).read_bytes() == previous


def test_nightly_eval_block_cleans_stale_temp_siblings(tmp_path):
    repo = _sandbox(tmp_path)
    stale = repo / "site/prophet/.beta_evaluation.tmp.999999"
    stale.write_text("half-written")
    (repo / "data/yahoo/SPY.parquet").unlink()  # skip path still cleans temps

    result = _run_eval_block(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not stale.exists()


def test_nightly_eval_runs_after_the_build_and_inside_the_manifest_scope():
    """The eval must sit after build_prophet's receipt and before the delta
    manifest, so its output is hashed and checkpoint-published like the index."""
    text = NIGHTLY.read_text(encoding="utf-8")
    build_i = text.index("python -m scripts.build_prophet 2>&1")
    receipt_i = text.index('"schema": "prophet.origination_receipt/v1"')
    eval_i = text.index("::group::prophet beta-first evaluation")
    manifest_i = text.index("before.get(path, 'MISSING')")
    assert build_i < receipt_i < eval_i < manifest_i


def test_evaluation_artifact_is_checkpoint_allowlisted_and_hashed_twice():
    nightly = NIGHTLY.read_text(encoding="utf-8")
    assert nightly.count('"site/prophet/beta_evaluation.json"') == 2  # baseline + delta
    allowlist = CHECKPOINT.read_text(encoding="utf-8")
    allowlist = allowlist.split('case "$rel" in', 1)[1].split("*)", 1)[0]
    assert "site/prophet/beta_evaluation.json" in allowlist


def test_evaluation_artifact_is_forbidden_on_public_r2_like_the_index():
    """DEC:B1-PROPHET-PUBLIC-SPLIT terms: never reachable from public R2."""
    import scripts.build_prophet as bp

    assert "prophet/index.json" in bp.R2_PUBLIC_FORBIDDEN_KEYS
    assert "prophet/beta_evaluation.json" in bp.R2_PUBLIC_FORBIDDEN_KEYS
    assert bp.R2_HEALTH_KEY not in bp.R2_PUBLIC_FORBIDDEN_KEYS


# ── runner write atomicity ───────────────────────────────────────────────────

def test_runner_write_is_atomic_and_cleans_up_on_failure(tmp_path, monkeypatch):
    from scripts.run_prophet_beta_evaluation import write_artifact_atomic

    out = tmp_path / "beta_evaluation.json"
    out.write_text('{"schema":"previous"}\n')

    write_artifact_atomic(out, '{"schema":"fresh"}\n')
    assert out.read_text(encoding="utf-8") == '{"schema":"fresh"}\n'
    assert list(tmp_path.glob(".beta_evaluation.tmp.*")) == []

    # A failure at the rename must leave the previous bytes and no temp file.
    import scripts.run_prophet_beta_evaluation as runner

    def broken_replace(_src, _dst):
        raise OSError("disk went away")
    monkeypatch.setattr(runner.os, "replace", broken_replace)
    with pytest.raises(OSError):
        write_artifact_atomic(out, '{"schema":"half-written"}\n')
    assert out.read_text(encoding="utf-8") == '{"schema":"fresh"}\n'
    assert list(tmp_path.glob(".beta_evaluation.tmp.*")) == []


def test_runner_header_refusal_never_touches_the_output(tmp_path, monkeypatch):
    """A header-hash drift aborts before any write: the artifact is kept."""
    from engine import prophet_beta_evaluation as ev

    out = tmp_path / "beta_evaluation.json"
    out.write_text('{"schema":"previous-night"}\n')
    original = out.read_bytes()

    orig = ev.verify_header
    monkeypatch.setattr(ev, "verify_header", lambda p: orig(p, "0" * 64))
    import scripts.run_prophet_beta_evaluation as runner

    with pytest.raises(ev.HeaderMismatch):
        runner.main(["--prices-dir", str(tmp_path), "--out", str(out)])
    assert out.read_bytes() == original
