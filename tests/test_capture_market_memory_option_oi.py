"""Sole-writer and credential guards for the W1B.5 availability canary."""

from __future__ import annotations

import json
import re
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
    assert captured.err == (
        "option-OI canary capture failed closed stage=unknown "
        "class=MarketMemoryOptionOiObservationError\n"
    )
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
    "persist": (cli.option_oi_store, "capture_option_oi_observation"),
}

_STAGE_FAILURE_MESSAGES = {
    "commit": (cli.MarketMemoryOptionOiCaptureCliError, "x"),
    "store_root": (cli.option_oi_store.MarketMemoryOptionOiStoreError, "x"),
    "resume": (cli.option_oi_store.MarketMemoryOptionOiStoreError, "x"),
    "pinned_sources": (cli.option_oi.MarketMemoryOptionOiObservationError, "x"),
    "credential": (cli.MarketMemoryOptionOiCaptureCliError, "x"),
    "persist": (cli.option_oi_store.MarketMemoryOptionOiStoreError, "x"),
}

# Build-stage failures the refinement reclassifies from the observation
# module's own literals and note; None means no status-class note is attached.
_STAGE_BUILD_FAILURES = {
    "credential": ("bearer token contains whitespace or control bytes", None),
    "fetch": (cli._TRANSPORT_FAILURE, None),
    "http_status_class": ("option-OI source did not return HTTP 200", "403"),
    "validate": ("option-OI body must be exact nonempty bytes within 4 MiB", None),
}


def _fail_the_named_dependency(monkeypatch: pytest.MonkeyPatch, stage: str) -> None:
    """Make exactly the dependency named by ``stage`` raise its typed failure."""
    target, attribute = _STAGE_FAILURE_TARGETS[stage]
    error_type, message = _STAGE_FAILURE_MESSAGES[stage]

    def fail(*_args: object, **_kwargs: object) -> object:
        raise error_type(message)

    monkeypatch.setattr(target, attribute, fail)


def _fail_the_build_stage(monkeypatch: pytest.MonkeyPatch, stage: str) -> None:
    """Make build raise the typed failure that ``stage``'s vocabulary names."""
    message, status_class = _STAGE_BUILD_FAILURES[stage]

    def fail(*_args: object, **_kwargs: object) -> object:
        failure = cli.option_oi.MarketMemoryOptionOiObservationError(message)
        if status_class is not None:
            failure.add_note(
                cli.option_oi.HTTP_STATUS_CLASS_NOTE_PREFIX + status_class
            )
        raise failure

    monkeypatch.setattr(
        cli.option_oi, "build_current_spy_option_oi_observation", fail
    )


@pytest.mark.parametrize(
    ("stage", "failure_kind"),
    (
        ("commit", "dependency"),
        ("store_root", "dependency"),
        ("resume", "dependency"),
        ("pinned_sources", "dependency"),
        ("credential", "dependency"),
        ("persist", "dependency"),
        ("credential", "build"),
        ("fetch", "build"),
        ("http_status_class", "build"),
        ("validate", "build"),
    ),
)
def test_cli_failure_line_names_the_failed_stage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    failure_kind: str,
) -> None:
    repository, store = _benign_capture_dependencies(tmp_path, monkeypatch)
    if failure_kind == "dependency":
        _fail_the_named_dependency(monkeypatch, stage)
        name = _STAGE_FAILURE_MESSAGES[stage][0].__name__
    else:
        _fail_the_build_stage(monkeypatch, stage)
        name = cli.option_oi.MarketMemoryOptionOiObservationError.__name__

    assert (
        cli.main(["--repository-root", str(repository), "--store-root", str(store)])
        == 1
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    expected = f"option-OI canary capture failed closed stage={stage} class={name}"
    if stage == "http_status_class":
        expected += " status_class=403"
    assert captured.err == expected + "\n"
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
    assert captured.err == (
        "option-OI canary capture failed closed stage=validate "
        "class=MarketMemoryOptionOiObservationError\n"
    )
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
    _fail_the_build_stage(monkeypatch, "http_status_class")

    with pytest.raises(
        cli.option_oi.MarketMemoryOptionOiObservationError
    ) as raised:
        cli.capture_current_option_oi_availability(repository, store_root=store)

    assert type(raised.value) is cli.option_oi.MarketMemoryOptionOiObservationError
    assert str(raised.value) == "option-OI source did not return HTTP 200"
    assert raised.value.__notes__ == [
        cli.option_oi.HTTP_STATUS_CLASS_NOTE_PREFIX + "403",
        "option-OI capture stage=http_status_class",
    ]


def test_cli_failure_line_is_secret_free_by_construction(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "SENTINELtok9f8e7d6c5b4a3"
    repository, store = _benign_capture_dependencies(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_read_systemd_bearer_token", lambda: sentinel)

    def leaky_build(*_args: object, **_kwargs: object) -> object:
        failure = cli.option_oi.MarketMemoryOptionOiObservationError(
            f"hostile {sentinel} Bearer {sentinel}"
        )
        failure.add_note(f"echo {sentinel}")
        raise failure

    monkeypatch.setattr(
        cli.option_oi, "build_current_spy_option_oi_observation", leaky_build
    )

    assert (
        cli.main(["--repository-root", str(repository), "--store-root", str(store)])
        == 1
    )

    captured = capsys.readouterr()
    assert sentinel not in captured.err
    assert sentinel not in captured.out
    assert "Bearer" not in captured.err
    assert "Bearer" not in captured.out
    assert captured.out == ""
    assert re.fullmatch(
        r"option-OI canary capture failed closed "
        r"stage=(commit|store_root|resume|pinned_sources|credential|fetch|"
        r"http_status_class|validate|persist|unknown) "
        r"class=[A-Za-z]+"
        r"( status_class=(401|403|429|3xx|4xx|5xx|other))?\n",
        captured.err,
    )


# The 403 response below is constructed exactly the way
# tests/test_market_memory_option_oi_observation.py builds one in its
# ``_http_response`` helper and ``ScriptedFetcher``; copied verbatim so the
# capture test never invents HttpResponse fields.
_COMPLETED_AT = "2026-08-10T19:00:00.123456Z"


def _canonical_entity(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _boundary_result(
    ticker: str, open_interest: object = 17, *, include_oi: bool = True
) -> dict:
    value: dict = {
        "details": {
            "ticker": ticker,
            "contract_type": "call",
            "shares_per_contract": 100,
        },
        "greeks": {"gamma": 0.01},
    }
    if include_oi:
        value["open_interest"] = open_interest
    return value


def _boundary_payload() -> dict:
    return {
        "status": "OK",
        "request_id": "safe-request-id",
        "results": [
            _boundary_result("O:SPY260821C00600000", 1_234_567),
            _boundary_result("O:SPY1260821P00500000", None),
            _boundary_result("O:SPYADJUSTED", include_oi=False),
        ],
        "next_url": (
            "https://api.massive.com/v3/snapshot/options/SPY?"
            "limit=250&cursor=safe-cursor"
        ),
    }


def _boundary_http_response(
    *,
    status: int = 200,
    url: str | None = None,
) -> cli.option_oi.HttpResponse:
    entity = _canonical_entity(_boundary_payload())
    return cli.option_oi.HttpResponse(
        status=status,
        url=cli.option_oi.SOURCE_URL if url is None else url,
        headers=(
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(entity))),
        ),
        body=entity,
        response_body_completed_at=_COMPLETED_AT,
    )


class BoundaryScriptedFetcher:
    def __init__(self, response: cli.option_oi.HttpResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
    ) -> cli.option_oi.HttpResponse:
        self.calls.append((method, url, dict(headers)))
        return self.response


def test_cli_http_status_class_survives_from_the_real_fetch_boundary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, store = _benign_capture_dependencies(tmp_path, monkeypatch)
    fetcher = BoundaryScriptedFetcher(_boundary_http_response(status=403))

    def build_via_real_fetch(*_args: object, **_kwargs: object) -> object:
        return cli.option_oi.fetch_current_spy_option_oi_response(
            bearer_token=TOKEN,
            fetcher=fetcher,
        )

    monkeypatch.setattr(
        cli.option_oi, "build_current_spy_option_oi_observation", build_via_real_fetch
    )

    assert (
        cli.main(["--repository-root", str(repository), "--store-root", str(store)])
        == 1
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "option-OI canary capture failed closed "
        "stage=http_status_class class=MarketMemoryOptionOiObservationError "
        "status_class=403\n"
    )
    assert len(fetcher.calls) == 1
    assert TOKEN not in captured.err


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
