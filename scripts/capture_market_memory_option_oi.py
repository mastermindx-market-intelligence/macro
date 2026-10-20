"""Capture one private W1B.5 option-OI availability observation.

This is the sole production writer.  The endpoint, query, first-page bound,
entitlement record, completeness limits, authority, and store profile are fixed
by reviewed code.  The bearer token is accepted only from systemd's fixed
credential file and is never accepted through argv or an application env key.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from os import environ as _process_environment
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.neuralweb import market_memory_option_oi_observation as option_oi
from engine.neuralweb import market_memory_option_oi_store as option_oi_store

_COMMIT = re.compile(r"[a-f0-9]{40}(?:[a-f0-9]{24})?\Z")
_TOKEN = re.compile(r"[A-Za-z0-9._-]{16,512}\Z")
_CREDENTIAL_NAME = "massive-option-oi-api-key"
_MAX_CREDENTIAL_BYTES = 513


class MarketMemoryOptionOiCaptureCliError(RuntimeError):
    """The deployed process cannot establish one private canary capture."""


_CAPTURE_FAILURES = (
    MarketMemoryOptionOiCaptureCliError,
    option_oi.MarketMemoryOptionOiObservationError,
    option_oi_store.MarketMemoryOptionOiStoreError,
)
# The one journald failure line may name WHERE the capture failed closed, as a
# token from this closed vocabulary only -- never a message, provider byte,
# path, or credential.
_FAILURE_STAGES = frozenset(
    {
        "commit",
        "store_root",
        "resume",
        "pinned_sources",
        "credential",
        "fetch",
        "http_status_class",
        "validate",
        "persist",
    }
)
_STAGE_NOTE_PREFIX = "option-OI capture stage="
# Exact literals raised by market_memory_option_oi_observation; matched by
# equality only, so a reworded message degrades to "validate", never leaks.
_TRANSPORT_FAILURE = "explicit-credential option-OI request failed"
_CREDENTIAL_FAILURES = frozenset({
    "bearer token must be an explicit bounded ASCII string",
    "bearer token contains whitespace or control bytes",
})
_FAILURE_CLASSES = frozenset(cls.__name__ for cls in _CAPTURE_FAILURES)


def _repository_commit(repository_root: Path) -> str:
    git_env = {
        key: value
        for key, value in _process_environment.items()
        if not key.startswith("GIT_")
    }
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={repository_root}",
                "-C",
                str(repository_root),
                "rev-parse",
                "--verify",
                "HEAD^{commit}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=git_env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MarketMemoryOptionOiCaptureCliError(
            "cannot resolve the deployed repository commit"
        ) from exc
    commit = result.stdout.strip()
    if _COMMIT.fullmatch(commit) is None:
        raise MarketMemoryOptionOiCaptureCliError(
            "deployed repository commit is malformed"
        )
    return commit


def _read_systemd_bearer_token() -> str:
    directory_value = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory_value:
        raise MarketMemoryOptionOiCaptureCliError(
            "systemd credential directory is unavailable"
        )
    directory = Path(directory_value)
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        raise MarketMemoryOptionOiCaptureCliError(
            "systemd credential directory is inadmissible"
        )
    credential = directory / _CREDENTIAL_NAME
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(credential, flags)
    except OSError as exc:
        raise MarketMemoryOptionOiCaptureCliError(
            "fixed systemd option-OI credential is unavailable"
        ) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise MarketMemoryOptionOiCaptureCliError(
                "systemd option-OI credential is not a regular file"
            )
        body = os.read(descriptor, _MAX_CREDENTIAL_BYTES + 1)
    finally:
        os.close(descriptor)
    if not body or len(body) > _MAX_CREDENTIAL_BYTES or b"\x00" in body:
        raise MarketMemoryOptionOiCaptureCliError(
            "systemd option-OI credential has invalid byte length"
        )
    if body.endswith(b"\n"):
        body = body[:-1]
    if b"\n" in body or b"\r" in body:
        raise MarketMemoryOptionOiCaptureCliError(
            "systemd option-OI credential must contain one token"
        )
    try:
        token = body.decode("ascii")
    except UnicodeDecodeError as exc:
        raise MarketMemoryOptionOiCaptureCliError(
            "systemd option-OI credential must be ASCII"
        ) from exc
    if _TOKEN.fullmatch(token) is None:
        raise MarketMemoryOptionOiCaptureCliError(
            "systemd option-OI credential is malformed"
        )
    return token


def capture_current_option_oi_availability(
    repository_root: str | Path,
    *,
    store_root: str | Path | None = None,
) -> dict[str, Any]:
    """Fetch exactly one first page and durably capture source availability."""

    stage = "commit"
    try:
        root = Path(repository_root).expanduser().resolve()
        commit = _repository_commit(root)
        stage = "store_root"
        destination = (
            option_oi_store.validate_option_oi_store_root(
                Path(store_root).expanduser(), repository_root=root
            )
            if store_root is not None
            else option_oi_store.default_option_oi_store_root(root)
        )

        # A prepared record is already a durable first observation.  Resume it
        # entirely from private CAS before opening the systemd credential or making
        # a new request; otherwise a process crash could strand the original clock
        # behind a later network response with a different source identity.
        stage = "resume"
        resumed = option_oi_store.resume_pending_option_oi_captures(destination)
        if resumed:
            return _capture_result(
                resumed[-1],
                deployed_commit=commit,
                capture_action="resumed_pending",
                resumed_capture_count=len(resumed),
            )

        # The reviewed source semantics and entitlement are request preconditions,
        # not post-request decoration. Validate them before opening the systemd
        # credential; build() repeats the stable Git pin immediately before fetch.
        stage = "pinned_sources"
        option_oi.read_pinned_option_oi_sources(root, pinned_commit=commit)
        stage = "credential"
        bearer_token = _read_systemd_bearer_token()
        stage = "validate"
        bundle = option_oi.build_current_spy_option_oi_observation(
            root,
            pinned_commit=commit,
            bearer_token=bearer_token,
        )
        del bearer_token
        stage = "persist"
        stored = option_oi_store.capture_option_oi_observation(
            destination,
            bundle=bundle,
        )
        return _capture_result(
            stored,
            deployed_commit=commit,
            capture_action="captured_current",
            resumed_capture_count=0,
        )
    except _CAPTURE_FAILURES as exc:
        if stage == "validate" and type(exc) is option_oi.MarketMemoryOptionOiObservationError:
            if _failure_http_status_class(exc) != "unknown":
                stage = "http_status_class"
            elif str(exc) == _TRANSPORT_FAILURE:
                stage = "fetch"
            elif str(exc) in _CREDENTIAL_FAILURES:
                stage = "credential"
        exc.add_note(_STAGE_NOTE_PREFIX + stage)
        raise


def _capture_result(
    stored: option_oi_store.StoredOptionOiObservation,
    *,
    deployed_commit: str,
    capture_action: str,
    resumed_capture_count: int,
) -> dict[str, Any]:
    """Return one sanitized result for either new or crash-resumed evidence."""

    receipt = stored.capture_receipt
    source = stored.bundle.source_observation
    page = source["page_observation"]
    policy = receipt["evidence_policy"]
    authority = receipt["authority"]
    return {
        "schema": "market_memory.option_oi_capture_result.v1",
        "deployed_commit": deployed_commit,
        "source_commit": stored.bundle.pinned_inputs.pinned_sources.pinned_commit,
        "capture_action": capture_action,
        "resumed_capture_count": resumed_capture_count,
        "store_profile": option_oi_store.STORE_PROFILE,
        "generation_id": stored.generation_id,
        "capture_id": receipt["capture_id"],
        "source_observation_id": source["source_observation_id"],
        "probe_receipt_id": source["probe_receipt_id"],
        "available_at": receipt["clocks"]["available_at"],
        "first_observed_at": receipt["clocks"]["first_observed_at"],
        "page_observation": {
            "results_count": page["results_count"],
            "unique_vendor_ticker_count": page["unique_vendor_ticker_count"],
            "oi_presence_counts": dict(page["oi_presence_counts"]),
            "next_url_present": page["next_url_present"],
        },
        "scope": {
            "source_availability_only": policy["source_availability_only"],
            "future_only": policy["future_only"],
            "first_page_only": policy["first_page_only"],
            "intentionally_bounded": policy["intentionally_bounded"],
            "chain_complete": policy["chain_complete"],
            "contract_universe_complete": policy["contract_universe_complete"],
            "measurement_date_authenticated": policy["measurement_date_authenticated"],
            "open_interest_values_projected": policy["open_interest_values_projected"],
            "gex_projected": policy["gex_projected"],
        },
        "authority": {
            "context_only": authority["context_only"],
            "proposal_weight": authority["proposal_weight"],
            "may_rank": authority["may_rank"],
            "may_gate": authority["may_gate"],
            "may_size": authority["may_size"],
            "may_trade": authority["may_trade"],
            "may_execute": authority["may_execute"],
            "may_write_options_episode": authority["may_write_options_episode"],
            "may_append_outcome": authority["may_append_outcome"],
            "training_eligible": policy["training_eligible"],
            "promotion_eligible": policy["promotion_eligible"],
        },
    }


def _failure_stage(exc: BaseException) -> str:
    """Return the one fixed-vocabulary stage recorded on ``exc``, else ``unknown``."""

    notes = getattr(exc, "__notes__", None)
    if type(notes) is not list:
        return "unknown"
    stages = [
        note[len(_STAGE_NOTE_PREFIX) :]
        for note in notes
        if type(note) is str and note.startswith(_STAGE_NOTE_PREFIX)
    ]
    if len(stages) != 1 or stages[0] not in _FAILURE_STAGES:
        return "unknown"
    return stages[0]


def _failure_http_status_class(exc: BaseException) -> str:
    """Return the one fixed-vocabulary HTTP status class on ``exc``, else ``unknown``."""

    notes = getattr(exc, "__notes__", None)
    if type(notes) is not list:
        return "unknown"
    classes = [
        note[len(option_oi.HTTP_STATUS_CLASS_NOTE_PREFIX) :]
        for note in notes
        if type(note) is str
        and note.startswith(option_oi.HTTP_STATUS_CLASS_NOTE_PREFIX)
    ]
    if len(classes) != 1 or classes[0] not in option_oi.HTTP_STATUS_CLASSES:
        return "unknown"
    return classes[0]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture one private option-OI endpoint availability canary"
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=_ROOT,
        help="reviewed Macro checkout containing the pinned source contract",
    )
    parser.add_argument(
        "--store-root",
        type=Path,
        default=None,
        help="private option-OI store override (tests/operators only)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = capture_current_option_oi_availability(
            args.repository_root,
            store_root=args.store_root,
        )
    except _CAPTURE_FAILURES as exc:
        # The process has handled a bearer credential. Never let a nested
        # transport/parser cause or hostile provider byte reach journald.
        # The stage token is chosen from a closed vocabulary by this module.
        stage = _failure_stage(exc)
        name = type(exc).__name__ if type(exc).__name__ in _FAILURE_CLASSES else "other"
        line = f"option-OI canary capture failed closed stage={stage} class={name}"
        if stage == "http_status_class":
            line += f" status_class={_failure_http_status_class(exc)}"
        print(line, file=sys.stderr)
        return 1
    print(
        json.dumps(
            result,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
