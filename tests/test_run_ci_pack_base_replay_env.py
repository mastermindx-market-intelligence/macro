"""Exact-base replay child environment: a non-capability allowlist that keeps
pytest's CI-mode failure messages so semantic failure atoms can match."""

from __future__ import annotations

from scripts import run_ci_pack


_RUNNER_PARENT_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/runner",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LC_TIME": "C",
    "CI": "true",
    "GITHUB_ACTIONS": "true",
    "GITHUB_TOKEN": "ghs_secret",
    "ACTIONS_RUNTIME_TOKEN": "runtime-secret",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "oidc-secret",
    "ACTIONS_ID_TOKEN_REQUEST_URL": "https://example.invalid/oidc",
    "ACTIONS_RESULTS_URL": "https://example.invalid/results",
    "GITHUB_WORKSPACE": "/home/runner/work/candidate",
    "GITHUB_SHA": "0" * 40,
    "GITHUB_HEAD_REF": "claude/candidate",
    "PYTHONPATH": "/home/runner/work/candidate",
    "VIRTUAL_ENV": "/home/runner/.venv",
    "RUNNER_OS": "Linux",
    "NO_COLOR": "1",
}


def test_replay_env_keeps_ci_so_pytest_prints_failure_reasons() -> None:
    # pytest only prints the ` - <reason>` tail of a `FAILED nodeid` short
    # summary line when `running_on_ci()` sees `CI`; the candidate run has it,
    # so a replay without it emits reason-less atoms that never match
    # (#10735 pack 11: candidate `FAILED x - AssertionError`, replay `FAILED x`).
    child = run_ci_pack._exact_base_replay_parent_env(_RUNNER_PARENT_ENV)
    assert child["CI"] == "true"
    assert "CI" in run_ci_pack.EXACT_BASE_REPLAY_SAFE_PARENT_ENV


def test_replay_env_drops_every_capability_and_candidate_binding() -> None:
    child = run_ci_pack._exact_base_replay_parent_env(_RUNNER_PARENT_ENV)
    for secret in (
        "GITHUB_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
        "ACTIONS_ID_TOKEN_REQUEST_URL",
        "ACTIONS_RESULTS_URL",
        "GITHUB_WORKSPACE",
        "GITHUB_SHA",
        "GITHUB_HEAD_REF",
        "GITHUB_ACTIONS",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "HOME",
    ):
        assert secret not in child, secret
    assert child == {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "LC_TIME": "C",
        "CI": "true",
        "RUNNER_OS": "Linux",
        "NO_COLOR": "1",
    }


def test_replay_env_allowlist_names_no_token_or_url_variable() -> None:
    for name in run_ci_pack.EXACT_BASE_REPLAY_SAFE_PARENT_ENV:
        upper = name.upper()
        assert not any(tok in upper for tok in ("TOKEN", "SECRET", "KEY", "URL", "GITHUB_")), name
