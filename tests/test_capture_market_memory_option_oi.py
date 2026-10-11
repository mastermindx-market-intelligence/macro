"""Sole-writer and credential guards for the W1B.5 availability canary."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import capture_market_memory_option_oi as cli

TOKEN = "private-test-token-1234567890"


def _bundle() -> SimpleNamespace:
    return SimpleNamespace(
        pinned_inputs=SimpleNamespace(
            pinned_sources=SimpleNamespace(pinned_commit="1" * 40)
        ),
        source_observation={
            "source_observation_id": "mmoptionoisrc_" + "a" * 64,
            "probe_receipt_id": "mmoptionoiprobe_" + "b" * 64,
            "available_at": "2026-08-10T17:00:00.000000Z",
            "page_observation": {
                "results_count": 250,
                "unique_vendor_ticker_count": 250,
                "oi_presence_counts": {
                    "valid_nonnegative_integer": 249,
                    "null": 1,
                    "absent": 0,
                },
                "next_url_present": True,
            },
        },
    )


def _stored(bundle: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        generation_id="mmoptionoigeneration_" + "c" * 64,
        capture_receipt={
            "capture_id": "mmoptionoicapture_" + "d" * 64,
            "clocks": {
                "available_at": "2026-08-10T17:00:00.000000Z",
                "first_observed_at": "2026-08-10T17:00:01.000000Z",
            },
            "evidence_policy": {
                "source_availability_only": True,
                "future_only": True,
                "first_page_only": True,
                "intentionally_bounded": True,
                "chain_complete": False,
                "contract_universe_complete": False,
                "measurement_date_authenticated": False,
                "open_interest_values_projected": False,
                "gex_projected": False,
                "training_eligible": False,
                "promotion_eligible": False,
            },
            "authority": {
                "context_only": True,
                "proposal_weight": 0,
                "may_rank": False,
                "may_gate": False,
                "may_size": False,
                "may_trade": False,
                "may_execute": False,
                "may_write_options_episode": False,
                "may_append_outcome": False,
            },
        },
        bundle=bundle,
    )


def test_systemd_credential_reader_accepts_one_fixed_regular_ascii_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credentials = tmp_path / "credentials"
    credentials.mkdir()
    (credentials / cli._CREDENTIAL_NAME).write_bytes(TOKEN.encode() + b"\n")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(credentials))

    assert cli._read_systemd_bearer_token() == TOKEN


@pytest.mark.parametrize(
    "body",
    (
        b"",
        b"short\n",
        TOKEN.encode() + b"\nsecond\n",
        b"not allowed spaces in token\n",
        b"x" * 514,
        b"x" * 20 + b"\x00",
        "snowman-☃-credential".encode(),
    ),
)
def test_systemd_credential_reader_rejects_malformed_or_multiline_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    credentials = tmp_path / "credentials"
    credentials.mkdir()
    (credentials / cli._CREDENTIAL_NAME).write_bytes(body)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(credentials))

    with pytest.raises(cli.MarketMemoryOptionOiCaptureCliError):
        cli._read_systemd_bearer_token()


def test_systemd_credential_reader_has_no_application_env_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("MASSIVE_API_KEY", TOKEN)
    monkeypatch.setenv("POLYGON_API_KEY", TOKEN)

    with pytest.raises(
        cli.MarketMemoryOptionOiCaptureCliError,
        match="credential directory is unavailable",
    ):
        cli._read_systemd_bearer_token()


def test_systemd_credential_reader_rejects_file_and_directory_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    target = real / "target"
    target.write_text(TOKEN, encoding="ascii")
    (real / cli._CREDENTIAL_NAME).symlink_to(target)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(real))
    with pytest.raises(cli.MarketMemoryOptionOiCaptureCliError):
        cli._read_systemd_bearer_token()

    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(linked))
    with pytest.raises(
        cli.MarketMemoryOptionOiCaptureCliError,
        match="directory is inadmissible",
    ):
        cli._read_systemd_bearer_token()


def test_capture_wrapper_pins_git_uses_token_once_and_validates_unresolved_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    store = tmp_path / "operator-store"
    commit = "1" * 40
    bundle = _bundle()
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(cli, "_repository_commit", lambda root: commit)
    monkeypatch.setattr(cli, "_read_systemd_bearer_token", lambda: TOKEN)

    def read_sources(root: Path, *, pinned_commit: str) -> SimpleNamespace:
        calls.append(("read_sources", root, pinned_commit))
        return SimpleNamespace(pinned_commit=pinned_commit)

    def build(root: Path, *, pinned_commit: str, bearer_token: str) -> SimpleNamespace:
        calls.append(("build", root, pinned_commit, bearer_token))
        return bundle

    def validate(root: Path, *, repository_root: Path) -> Path:
        calls.append(("validate", root, repository_root))
        assert root == store
        return store.resolve()

    def capture(root: Path, *, bundle: SimpleNamespace) -> SimpleNamespace:
        calls.append(("capture", root, bundle))
        return _stored(bundle)

    def resume(root: Path) -> tuple[SimpleNamespace, ...]:
        calls.append(("resume", root))
        return ()

    monkeypatch.setattr(cli.option_oi, "build_current_spy_option_oi_observation", build)
    monkeypatch.setattr(cli.option_oi, "read_pinned_option_oi_sources", read_sources)
    monkeypatch.setattr(cli.option_oi_store, "validate_option_oi_store_root", validate)
    monkeypatch.setattr(
        cli.option_oi_store, "resume_pending_option_oi_captures", resume
    )
    monkeypatch.setattr(cli.option_oi_store, "capture_option_oi_observation", capture)

    result = cli.capture_current_option_oi_availability(
        repository,
        store_root=store,
    )

    assert calls == [
        ("validate", store, repository.resolve()),
        ("resume", store.resolve()),
        ("read_sources", repository.resolve(), commit),
        ("build", repository.resolve(), commit, TOKEN),
        ("capture", store.resolve(), bundle),
    ]
    encoded = json.dumps(result, sort_keys=True)
    assert TOKEN not in encoded
    assert result == {
        "schema": "market_memory.option_oi_capture_result.v1",
        "deployed_commit": commit,
        "source_commit": commit,
        "capture_action": "captured_current",
        "resumed_capture_count": 0,
        "store_profile": cli.option_oi_store.STORE_PROFILE,
        "generation_id": "mmoptionoigeneration_" + "c" * 64,
        "capture_id": "mmoptionoicapture_" + "d" * 64,
        "source_observation_id": "mmoptionoisrc_" + "a" * 64,
        "probe_receipt_id": "mmoptionoiprobe_" + "b" * 64,
        "available_at": "2026-08-10T17:00:00.000000Z",
        "first_observed_at": "2026-08-10T17:00:01.000000Z",
        "page_observation": {
            "results_count": 250,
            "unique_vendor_ticker_count": 250,
            "oi_presence_counts": {
                "valid_nonnegative_integer": 249,
                "null": 1,
                "absent": 0,
            },
            "next_url_present": True,
        },
        "scope": {
            "source_availability_only": True,
            "future_only": True,
            "first_page_only": True,
            "intentionally_bounded": True,
            "chain_complete": False,
            "contract_universe_complete": False,
            "measurement_date_authenticated": False,
            "open_interest_values_projected": False,
            "gex_projected": False,
        },
        "authority": {
            "context_only": True,
            "proposal_weight": 0,
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_trade": False,
            "may_execute": False,
            "may_write_options_episode": False,
            "may_append_outcome": False,
            "training_eligible": False,
            "promotion_eligible": False,
        },
    }


def test_pending_capture_resumes_before_credential_or_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    store = tmp_path / "store"
    store.mkdir()
    commit = "1" * 40
    bundle = _bundle()
    stored = _stored(bundle)
    calls: list[tuple[object, ...]] = []

    monkeypatch.setattr(cli, "_repository_commit", lambda root: commit)
    monkeypatch.setattr(
        cli.option_oi_store,
        "validate_option_oi_store_root",
        lambda root, *, repository_root: store,
    )

    def resume(root: Path) -> tuple[SimpleNamespace, ...]:
        calls.append(("resume", root))
        return (stored,)

    def forbidden_credential() -> str:
        raise AssertionError("credential must not be opened during recovery")

    def forbidden_fetch(*args: object, **kwargs: object) -> SimpleNamespace:
        raise AssertionError("network/build must not run during recovery")

    monkeypatch.setattr(
        cli.option_oi_store, "resume_pending_option_oi_captures", resume
    )
    monkeypatch.setattr(cli, "_read_systemd_bearer_token", forbidden_credential)
    monkeypatch.setattr(
        cli.option_oi, "build_current_spy_option_oi_observation", forbidden_fetch
    )

    result = cli.capture_current_option_oi_availability(
        repository,
        store_root=store,
    )

    assert calls == [("resume", store)]
    assert result["capture_action"] == "resumed_pending"
    assert result["resumed_capture_count"] == 1
    assert result["source_commit"] == commit
    assert result["first_observed_at"] == "2026-08-10T17:00:01.000000Z"


def test_cli_prints_one_finite_canonical_private_receipt(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = {
        "schema": "market_memory.option_oi_capture_result.v1",
        "source_availability_only": True,
    }
    monkeypatch.setattr(
        cli,
        "capture_current_option_oi_availability",
        lambda *args, **kwargs: expected,
    )

    assert cli.main(["--repository-root", "/tmp/reviewed"]) == 0
    body = capsys.readouterr().out
    assert (
        body
        == json.dumps(
            expected,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )
    assert json.loads(body) == expected


def test_cli_sanitizes_nested_credential_bearing_failures(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> dict:
        try:
            raise RuntimeError(f"transport echoed Bearer {TOKEN}")
        except RuntimeError as cause:
            raise cli.option_oi.MarketMemoryOptionOiObservationError(
                "explicit-credential option-OI request failed"
            ) from cause

    monkeypatch.setattr(cli, "capture_current_option_oi_availability", fail)

    assert cli.main(["--repository-root", "/tmp/reviewed"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "option-OI canary capture failed closed stage=unknown\n"
    assert TOKEN not in captured.err


def _benign_capture_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Install the wrapper test's benign dependencies; return repo and store."""
    repository = tmp_path / "repo"
    repository.mkdir()
    store = tmp_path / "operator-store"
    bundle = _bundle()
    monkeypatch.setattr(cli, "_repository_commit", lambda root: "1" * 40)
    monkeypatch.setattr(cli, "_read_systemd_bearer_token", lambda: TOKEN)
    monkeypatch.setattr(
        cli.option_oi,
        "read_pinned_option_oi_sources",
        lambda root, *, pinned_commit: SimpleNamespace(pinned_commit=pinned_commit),
    )
    monkeypatch.setattr(
        cli.option_oi,
        "build_current_spy_option_oi_observation",
        lambda root, *, pinned_commit, bearer_token: bundle,
    )
    monkeypatch.setattr(
        cli.option_oi_store,
        "validate_option_oi_store_root",
        lambda root, *, repository_root: store.resolve(),
    )
    monkeypatch.setattr(
        cli.option_oi_store, "resume_pending_option_oi_captures", lambda root: ()
    )
    monkeypatch.setattr(
        cli.option_oi_store,
        "capture_option_oi_observation",
        lambda root, *, bundle: _stored(bundle),
    )
    return repository, store


_STAGE_FAILURE_TARGETS = {
    "commit": (cli, "_repository_commit"),
    "store_root": (cli.option_oi_store, "validate_option_oi_store_root"),
    "resume": (cli.option_oi_store, "resume_pending_option_oi_captures"),
    "pinned_sources": (cli.option_oi, "read_pinned_option_oi_sources"),
    "credential": (cli, "_read_systemd_bearer_token"),
    "transport": (cli.option_oi, "build_current_spy_option_oi_observation"),
    "http_status": (cli.option_oi, "build_current_spy_option_oi_observation"),
    "observe": (cli.option_oi, "build_current_spy_option_oi_observation"),
    "persist": (cli.option_oi_store, "capture_option_oi_observation"),
}

_STAGE_FAILURE_MESSAGES = {
    "commit": (cli.MarketMemoryOptionOiCaptureCliError, "x"),
    "store_root": (cli.option_oi_store.MarketMemoryOptionOiStoreError, "x"),
    "resume": (cli.option_oi_store.MarketMemoryOptionOiStoreError, "x"),
    "pinned_sources": (cli.option_oi.MarketMemoryOptionOiObservationError, "x"),
    "credential": (cli.MarketMemoryOptionOiCaptureCliError, "x"),
    "transport": (
        cli.option_oi.MarketMemoryOptionOiObservationError,
        "explicit-credential option-OI request failed",
    ),
    "http_status": (
        cli.option_oi.MarketMemoryOptionOiObservationError,
        "option-OI source did not return HTTP 200",
    ),
    "observe": (
        cli.option_oi.MarketMemoryOptionOiObservationError,
        "option-OI body must be exact nonempty bytes within 4 MiB",
    ),
    "persist": (cli.option_oi_store.MarketMemoryOptionOiStoreError, "x"),
}


def _fail_the_named_dependency(monkeypatch: pytest.MonkeyPatch, stage: str) -> None:
    """Make exactly the dependency named by ``stage`` raise its typed failure."""
    target, attribute = _STAGE_FAILURE_TARGETS[stage]
    error_type, message = _STAGE_FAILURE_MESSAGES[stage]

    def fail(*_args: object, **_kwargs: object) -> object:
        raise error_type(message)

    monkeypatch.setattr(target, attribute, fail)


@pytest.mark.parametrize(
    "stage",
    (
        "commit",
        "store_root",
        "resume",
        "pinned_sources",
        "credential",
        "transport",
        "http_status",
        "observe",
        "persist",
    ),
)
def test_cli_failure_line_names_the_failed_stage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    repository, store = _benign_capture_dependencies(tmp_path, monkeypatch)
    _fail_the_named_dependency(monkeypatch, stage)

    assert (
        cli.main(["--repository-root", str(repository), "--store-root", str(store)])
        == 1
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"option-OI canary capture failed closed stage={stage}\n"
    assert TOKEN not in captured.err


def test_cli_failure_line_never_carries_the_exception_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, store = _benign_capture_dependencies(tmp_path, monkeypatch)

    def leaky_build(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise cli.option_oi.MarketMemoryOptionOiObservationError(
            f"provider echoed Bearer {TOKEN}"
        )

    monkeypatch.setattr(
        cli.option_oi, "build_current_spy_option_oi_observation", leaky_build
    )

    assert (
        cli.main(["--repository-root", str(repository), "--store-root", str(store)])
        == 1
    )

    captured = capsys.readouterr()
    assert captured.err == "option-OI canary capture failed closed stage=observe\n"
    assert TOKEN not in captured.err
    assert "Bearer" not in captured.err


def test_failure_stage_rejects_missing_foreign_or_ambiguous_notes() -> None:
    unnoted = ValueError("no stage note")
    assert cli._failure_stage(unnoted) == "unknown"

    foreign = ValueError("foreign stage note")
    foreign.add_note("option-OI capture stage=evil")
    assert cli._failure_stage(foreign) == "unknown"

    ambiguous = ValueError("two stage notes")
    ambiguous.add_note("option-OI capture stage=commit")
    ambiguous.add_note("option-OI capture stage=persist")
    assert cli._failure_stage(ambiguous) == "unknown"

    unambiguous = ValueError("one stage note")
    unambiguous.add_note("option-OI capture stage=credential")
    assert cli._failure_stage(unambiguous) == "credential"


def test_capture_function_keeps_the_original_exception_with_one_stage_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, store = _benign_capture_dependencies(tmp_path, monkeypatch)
    _fail_the_named_dependency(monkeypatch, "http_status")

    with pytest.raises(
        cli.option_oi.MarketMemoryOptionOiObservationError
    ) as raised:
        cli.capture_current_option_oi_availability(repository, store_root=store)

    assert type(raised.value) is cli.option_oi.MarketMemoryOptionOiObservationError
    assert str(raised.value) == "option-OI source did not return HTTP 200"
    assert raised.value.__notes__ == ["option-OI capture stage=http_status"]


def test_repository_commit_rejects_noncanonical_git_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="HEAD\n"),
    )
    with pytest.raises(
        cli.MarketMemoryOptionOiCaptureCliError,
        match="commit is malformed",
    ):
        cli._repository_commit(tmp_path)


def test_repository_commit_scopes_git_safe_directory_to_the_exact_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(args: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((args, kwargs))
        return SimpleNamespace(stdout="a" * 40 + "\n")

    monkeypatch.setattr(cli.subprocess, "run", run)
    monkeypatch.setenv("GIT_DIR", "/foreign/repository/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/foreign/repository")

    assert cli._repository_commit(tmp_path) == "a" * 40
    assert [call[0] for call in calls] == [
        [
            "git",
            "-c",
            f"safe.directory={tmp_path}",
            "-C",
            str(tmp_path),
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        ]
    ]
    git_env = calls[0][1]["env"]
    assert isinstance(git_env, dict)
    assert not any(key.startswith("GIT_") for key in git_env)


def test_production_cli_exposes_no_source_scope_or_credential_override() -> None:
    source = Path(cli.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "--url",
        "--fetcher",
        "--pinned-commit",
        "--available-at",
        "--session",
        "--measurement-date",
        "--next-url",
        "--limit",
        "--api-key",
        "MASSIVE_API_KEY",
        "POLYGON_API_KEY",
        "build_polygon_gex",
        "polygon_options",
    ):
        assert forbidden not in source
    assert source.count('os.environ.get("CREDENTIALS_DIRECTORY")') == 1
    assert "os.getenv" not in source
