#!/usr/bin/env python3
"""Build a deterministic research artifact without rewriting historical output.

A destination is create-only: identical replays are idempotent, whereas a
correction or another cutoff requires a different destination. Publication uses
an atomic hard link of a unique, complete sibling temporary file. A filesystem
that cannot provide that operation fails rather than falling back to overwrite.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
ROOT = _ROOT

from engine.macro_turnaround import (  # noqa: E402
    IndicatorSpec,
    MacroTurnaroundEngine,
    Observation,
    Phase,
    TurnaroundConfig,
    build_research_artifact,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {value}")


def _existing_matches(output: Path, content: bytes) -> bool:
    if output.is_symlink():
        raise ValueError("immutable output cannot be a symbolic link")
    try:
        existing = output.read_bytes()
    except FileNotFoundError:
        return False
    if existing != content:
        raise ValueError("immutable output already exists with different content; choose a new path")
    return True


def _assert_research_output_path(output: Path) -> None:
    """Keep research artifacts out of canonical data and generated product paths."""
    resolved = output.resolve(strict=False)
    for protected in (ROOT / "data", ROOT / "site"):
        protected_resolved = protected.resolve(strict=False)
        if resolved == protected_resolved or protected_resolved in resolved.parents:
            raise ValueError(
                "output must remain outside canonical data/ and generated site/ paths"
            )


def _publish_immutable(output: Path, content: bytes) -> None:
    _assert_research_output_path(output)
    if _existing_matches(output, content):
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Unlike replace()/rename(), link() cannot replace a winner from
            # another process. Readers only see the fully serialized artifact.
            os.link(temporary, output)
        except FileExistsError:
            if not _existing_matches(output, content):
                raise ValueError("immutable output changed during publication")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("input and output paths must be distinct")
        payload = json.loads(
            args.input.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(payload, dict):
            raise ValueError("input must be a JSON object")
        expected = {"as_of", "previous_phase", "config", "specs", "observations"}
        unknown = set(payload) - expected
        missing = expected - set(payload)
        if unknown or missing:
            raise ValueError(
                f"input fields mismatch; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}"
            )
        if not isinstance(payload["specs"], list):
            raise ValueError("specs must be a JSON array")
        if not isinstance(payload["observations"], dict):
            raise ValueError("observations must be a JSON object")
        for key, series in payload["observations"].items():
            if not isinstance(series, list):
                raise ValueError(f"observations[{key}] must be a JSON array")
        config = TurnaroundConfig.from_dict(payload["config"])
        specs = [IndicatorSpec.from_dict(item) for item in payload["specs"]]
        observations = {
            key: [Observation.from_dict(item) for item in values]
            for key, values in payload["observations"].items()
        }
        previous = (
            Phase(payload["previous_phase"])
            if payload["previous_phase"] is not None
            else None
        )
        assessment = MacroTurnaroundEngine(config).assess(
            observations, specs, payload["as_of"], previous_phase=previous,
        )
        artifact = build_research_artifact(assessment)
        content = (json.dumps(artifact, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
        _publish_immutable(args.output, content)
    except (OSError, TypeError, ValueError) as error:
        print(f"build_macro_turnaround_research: ERROR — {error}", file=sys.stderr)
        return 2
    print(
        "build_macro_turnaround_research: OK — "
        f"{artifact['phase']} as of {artifact['as_of']} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
