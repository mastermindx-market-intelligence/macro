"""Private operator CLI for versioned Research Intelligence artifacts.

Examples:
    python -m scripts.research_intelligence_store --local /tmp/rv put \
        --analysis analysis.json --source-body report.md
    python -m scripts.research_intelligence_store --local /tmp/rv show \
        --document-id REPORT
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.research_intelligence.projection import summary_points
from engine.research_intelligence.store import (
    ARTIFACT_MAX_BYTES,
    READ_SCHEMA,
    SOURCE_BODY_MAX_BYTES,
    ResearchIntelligenceStoreError,
    load_latest_research_intelligence,
    load_research_intelligence_version,
    persist_analysis,
    validate_analysis_for_persistence,
)
from engine.research_vault.r2_store import StrictConditionalWriteStore, build_store


def _emit(value: dict[str, Any], *, stream=sys.stdout) -> None:
    print(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        file=stream,
        flush=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Versioned private Research Intelligence store")
    parser.add_argument(
        "--local",
        metavar="DIR",
        help="use a local Research Vault store instead of configured R2",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    put = commands.add_parser(
        "put",
        help="re-ground one successful W1 analysis and persist its private artifact",
    )
    put.add_argument("--analysis", required=True, metavar="PATH")
    put.add_argument("--source-body", required=True, metavar="PATH")
    put.add_argument(
        "--expected-current-artifact-sha256",
        help="required exact predecessor when correcting an existing artifact",
    )

    show = commands.add_parser(
        "show",
        help="read the latest or one immutable Research Intelligence version",
    )
    show.add_argument("--document-id", required=True)
    show.add_argument(
        "--artifact-sha256",
        help="read this immutable artifact version instead of latest",
    )
    show.add_argument(
        "--private-rio",
        action="store_true",
        help="emit entitled private claims/evidence instead of the safe projection",
    )
    return parser


def _active_store(local_dir: str | None) -> StrictConditionalWriteStore:
    store = build_store(local_dir=local_dir)
    if store is None:
        raise ResearchIntelligenceStoreError(
            "store_unavailable",
            "Research Vault store is not configured",
        )
    if not isinstance(store, StrictConditionalWriteStore):
        raise ResearchIntelligenceStoreError(
            "store_incompatible",
            "Research Vault store lacks strict compare-and-swap",
        )
    return store


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"invalid JSON constant: {token}")


def _load_json_object(path_text: str) -> dict[str, Any]:
    path = Path(path_text).expanduser()
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ResearchIntelligenceStoreError(
            "analysis_input_unavailable",
            "analysis input file is unavailable",
        ) from exc
    if size > ARTIFACT_MAX_BYTES * 2:
        raise ResearchIntelligenceStoreError(
            "analysis_input_too_large",
            "analysis input file exceeds the operator boundary",
        )
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ResearchIntelligenceStoreError(
            "analysis_input_invalid",
            "analysis input file is not a JSON object",
        ) from exc
    if not isinstance(value, dict):
        raise ResearchIntelligenceStoreError(
            "analysis_input_invalid",
            "analysis input must be a JSON object",
        )
    return value


def _load_source_body(path_text: str) -> str:
    path = Path(path_text).expanduser()
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ResearchIntelligenceStoreError(
            "source_body_unavailable",
            "source body file is unavailable",
        ) from exc
    if size > SOURCE_BODY_MAX_BYTES:
        raise ResearchIntelligenceStoreError(
            "source_body_too_large",
            "source body file exceeds the operator boundary",
        )
    try:
        # TextIO defaults would rewrite CRLF/CR and invalidate exact W1 identity.
        with path.open(encoding="utf-8", newline="") as source:
            return source.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ResearchIntelligenceStoreError(
            "source_body_invalid",
            "source body file is not valid UTF-8 text",
        ) from exc


def _put(
    args: argparse.Namespace,
    store: StrictConditionalWriteStore,
    *,
    analysis: dict[str, Any],
    source_body: str,
) -> int:
    receipt = persist_analysis(
        store,
        analysis,
        source_body=source_body,
        expected_current_artifact_sha256=args.expected_current_artifact_sha256,
    )
    _emit(receipt.to_dict())
    return 0


def _show(args: argparse.Namespace, store: StrictConditionalWriteStore) -> int:
    if args.artifact_sha256:
        stored = load_research_intelligence_version(
            store,
            args.document_id,
            args.artifact_sha256,
        )
    else:
        stored = load_latest_research_intelligence(store, args.document_id)
    if stored is None:
        _emit(
            {
                "schema": READ_SCHEMA,
                "state": "missing",
                "document_id": args.document_id,
            }
        )
        return 3

    output: dict[str, Any] = {
        "schema": READ_SCHEMA,
        "state": "ok",
        "document_id": stored.document_id,
        "artifact_sha256": stored.artifact_sha256,
        "rio_sha256": stored.rio_sha256,
        "source_content_sha256": stored.source_content_sha256,
        "is_latest": stored.is_latest,
        "receipt": stored.receipt,
    }
    if args.private_rio:
        output.update({"view": "private_rio", "rio": stored.rio})
    else:
        output.update(
            {
                "view": "safe_summary",
                "summary_points": summary_points(stored.rio),
            }
        )
    _emit(output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "put":
            analysis = _load_json_object(args.analysis)
            source_body = _load_source_body(args.source_body)
            validate_analysis_for_persistence(
                analysis,
                source_body=source_body,
                expected_current_artifact_sha256=(
                    args.expected_current_artifact_sha256
                ),
            )
            store = _active_store(args.local)
            return _put(
                args,
                store,
                analysis=analysis,
                source_body=source_body,
            )
        store = _active_store(args.local)
        return _show(args, store)
    except ResearchIntelligenceStoreError as exc:
        _emit(
            {"schema": READ_SCHEMA, "state": "error", "code": exc.code},
            stream=sys.stderr,
        )
        return 2
    except (OSError, ValueError, TypeError) as exc:
        _emit(
            {
                "schema": READ_SCHEMA,
                "state": "error",
                "code": type(exc).__name__,
            },
            stream=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
