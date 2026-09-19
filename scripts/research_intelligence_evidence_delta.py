"""One-shot private consumer for longitudinal Research Intelligence evidence deltas."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.research_intelligence.evidence_delta import compare_institutional_rio_evidence, summary

_MAX_INPUT_BYTES = 2 * 1024 * 1024


def _reject_constant(token: str) -> Any:
    raise ValueError(f"invalid JSON constant: {token}")


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _read_json(path_text: str) -> dict[str, Any]:
    path = Path(path_text).expanduser()
    if path.stat().st_size > _MAX_INPUT_BYTES:
        raise ValueError("RIO input exceeds bounded size")
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicates,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("RIO input must be a JSON object")
    return value


def _write_private_json(path_text: str, value: dict[str, Any]) -> None:
    path = Path(path_text).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except Exception:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare two grounded institutional RIOs without exposing source text"
    )
    parser.add_argument("--previous", required=True, help="older private RIO JSON")
    parser.add_argument("--current", required=True, help="newer private RIO JSON")
    parser.add_argument(
        "--topic-key",
        required=True,
        help="caller-selected topic context; hashed into the delta, not a topic authority",
    )
    parser.add_argument("--output", required=True, help="private full delta output path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        previous = _read_json(args.previous)
        current = _read_json(args.current)
        delta = compare_institutional_rio_evidence(
            previous,
            current,
            topic_key=args.topic_key,
        )
        _write_private_json(args.output, delta)
        print(
            json.dumps(
                {
                    "state": "ok",
                    "output": str(Path(args.output).expanduser()),
                    "summary": summary(delta),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        return 0
    except (OSError, UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"state": "error", "code": type(exc).__name__},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
