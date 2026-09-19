"""Operator CLI for the private Research Intelligence model benchmark.

No provider call is made here. Prepare emits the exact W1 prompt for an
operator-authorized model surface; score re-grounds the returned text through
W1 and emits only hashes/counts/scores; aggregate compares those safe receipts.
"""
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

from engine.research_intelligence.benchmark import (
    aggregate_results,
    build_benchmark_request,
    score_raw_output,
)

_MAX_JSON_BYTES = 2 * 1024 * 1024
_MAX_BODY_BYTES = 8 * 1024 * 1024
_MAX_OUTPUT_BYTES = 2 * 1024 * 1024


def _reject_constant(token: str) -> Any:
    raise ValueError(f"invalid JSON constant: {token}")


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _read_text(path_text: str, *, maximum: int) -> str:
    path = Path(path_text).expanduser()
    size = path.stat().st_size
    if size > maximum:
        raise ValueError(f"input exceeds {maximum} byte boundary")
    return path.read_text(encoding="utf-8")


def _read_json(path_text: str) -> dict[str, Any]:
    text = _read_text(path_text, maximum=_MAX_JSON_BYTES)
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicates,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON input must be an object")
    return value


def _write_json(path_text: str, value: dict[str, Any], *, private: bool) -> None:
    """Atomically publish JSON; private prompt material is never briefly world-readable."""
    path = Path(path_text).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"
    mode = 0o600 if private else 0o644
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
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
        description="Prepare and score source-bound RIO model benchmark cases"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser(
        "prepare",
        help="emit the exact private W1 request for an authorized interactive model run",
    )
    prepare.add_argument("--case", required=True)
    prepare.add_argument("--source-body", required=True)
    prepare.add_argument("--output", required=True)

    score = sub.add_parser(
        "score",
        help="re-ground one raw model output and emit a quote-free score receipt",
    )
    score.add_argument("--case", required=True)
    score.add_argument("--source-body", required=True)
    score.add_argument("--model-output", required=True)
    score.add_argument("--candidate-label", required=True)
    score.add_argument(
        "--observation",
        help="optional benchmark_observation.v1 JSON with latency/token/cost measurements",
    )
    score.add_argument("--output", required=True)

    aggregate = sub.add_parser(
        "aggregate",
        help="aggregate quote-free score receipts across candidate models",
    )
    aggregate.add_argument("results", nargs="+")
    aggregate.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            case = _read_json(args.case)
            body = _read_text(args.source_body, maximum=_MAX_BODY_BYTES)
            request = build_benchmark_request(case, body)
            _write_json(args.output, request, private=True)
            print(
                json.dumps(
                    {
                        "state": "ok",
                        "case_id": request["case_id"],
                        "source_content_sha256": request["source_content_sha256"],
                        "gold_contract_sha256": request["gold_contract_sha256"],
                        "prompt_sha256": request["prompt_sha256"],
                        "output": str(Path(args.output).expanduser()),
                        "visibility": "private_source_bound",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0

        if args.command == "score":
            case = _read_json(args.case)
            body = _read_text(args.source_body, maximum=_MAX_BODY_BYTES)
            raw_output = _read_text(args.model_output, maximum=_MAX_OUTPUT_BYTES)
            observation = _read_json(args.observation) if args.observation else None
            result = score_raw_output(
                case,
                body,
                raw_output,
                candidate_label=args.candidate_label,
                observation=observation,
            )
            _write_json(args.output, result, private=False)
            print(
                json.dumps(
                    {
                        "state": result["state"],
                        "case_id": result["case_id"],
                        "candidate_label": result["candidate_label"],
                        "overall_score": result["overall_score"],
                        "observation_present": result.get("observation") is not None,
                        "output": str(Path(args.output).expanduser()),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0 if result["state"] == "ok" else 3

        results = [_read_json(path) for path in args.results]
        aggregate = aggregate_results(results)
        _write_json(args.output, aggregate, private=False)
        print(
            json.dumps(
                {
                    "state": "ok",
                    "candidate_count": len(aggregate["candidates"]),
                    "case_set_sha256": aggregate["case_set_sha256"],
                    "output": str(Path(args.output).expanduser()),
                },
                sort_keys=True,
                separators=(",", ":"),
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
