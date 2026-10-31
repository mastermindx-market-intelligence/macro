"""Offline and network replay of pinned relationship source excerpts.

``verify_excerpt`` re-derives every hash the excerpt asserts, offline, from the
excerpt's own bytes.  ``replay_fetch`` goes further: it pulls the full public
document over the network and re-derives the document hash and the byte-span hash
against the pinned values, so a drifting or silently-edited filing cannot pass.

The CLI is offline by default; ``--network`` requires ``SEC_USER_AGENT`` and
self-limits to at most 10 requests per second.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from urllib.error import URLError

from engine.company_intelligence.relationships import (
    normalize_span,
    sha,
)

MAX_SPAN_BYTES = 2048
MIN_REQUEST_SECONDS = 0.11  # <= 10 requests/second


def verify_excerpt(excerpt: dict) -> list:
    """Offline problems list for one excerpt; [] means every hash re-derives."""
    problems: list = []
    accession = excerpt.get("accession")
    span = excerpt.get("span") or {}
    raw = span.get("raw")
    byte_start = span.get("byte_start")
    byte_end = span.get("byte_end")
    if not isinstance(raw, str):
        return [f"{accession}: span.raw missing"]
    raw_bytes = raw.encode("utf-8")
    if not isinstance(byte_start, int) or not isinstance(byte_end, int):
        problems.append(f"{accession}: span byte offsets missing")
    else:
        if len(raw_bytes) != byte_end - byte_start:
            problems.append(
                f"{accession}: span.raw is {len(raw_bytes)} bytes but "
                f"byte_end-byte_start is {byte_end - byte_start}"
            )
        if byte_end - byte_start > MAX_SPAN_BYTES:
            problems.append(
                f"{accession}: span of {byte_end - byte_start} bytes exceeds "
                f"{MAX_SPAN_BYTES}"
            )
        if byte_start < 0 or byte_end <= byte_start:
            problems.append(f"{accession}: span byte range is empty or negative")
    if sha(raw_bytes) != span.get("raw_sha256"):
        problems.append(f"{accession}: span.raw does not hash to raw_sha256")
    normalized = normalize_span(raw_bytes)
    if sha(normalized) != span.get("normalized_sha256"):
        problems.append(
            f"{accession}: normalized span does not hash to normalized_sha256"
        )
    if sha(span.get("normalized") or "") != span.get("normalized_sha256"):
        problems.append(
            f"{accession}: stored span.normalized does not hash to normalized_sha256"
        )
    for context in excerpt.get("xbrl_contexts") or []:
        context_ref = context.get("context_ref")
        context_raw = (context.get("raw") or "").encode("utf-8")
        ctx_start = context.get("byte_start")
        ctx_end = context.get("byte_end")
        if not isinstance(ctx_start, int) or not isinstance(ctx_end, int):
            problems.append(f"{accession}: xbrl context {context_ref} offsets missing")
        elif len(context_raw) != ctx_end - ctx_start:
            problems.append(
                f"{accession}: xbrl context {context_ref} is {len(context_raw)} "
                f"bytes but byte_end-byte_start is {ctx_end - ctx_start}"
            )
        if len(context_raw) > MAX_SPAN_BYTES:
            problems.append(
                f"{accession}: xbrl context {context_ref} exceeds {MAX_SPAN_BYTES}"
            )
        if sha(context_raw) != context.get("raw_sha256"):
            problems.append(
                f"{accession}: xbrl context {context_ref} does not hash to raw_sha256"
            )
    return problems


def replay_fetch(excerpt: dict, user_agent: str, fetch=None) -> list:
    """Network replay problems; ``fetch(url, headers) -> bytes`` is injectable."""
    problems: list = []
    accession = excerpt.get("accession")
    if fetch is None:
        def fetch(url, headers):  # noqa: E306
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()

    document = fetch(excerpt["url"], {"User-Agent": user_agent})
    span = excerpt["span"]
    byte_start = span["byte_start"]
    byte_end = span["byte_end"]
    if len(document) != excerpt.get("doc_byte_length"):
        problems.append(
            f"{accession}: fetched document is {len(document)} bytes, "
            f"doc_byte_length pins {excerpt.get('doc_byte_length')}"
        )
    if sha(document) != excerpt.get("doc_sha256"):
        problems.append(f"{accession}: fetched document does not hash to doc_sha256")
    span_bytes = document[byte_start:byte_end]
    if sha(span_bytes) != span.get("raw_sha256"):
        problems.append(
            f"{accession}: fetched bytes [{byte_start}:{byte_end}] do not hash to "
            "span.raw_sha256"
        )
    return problems


def _load_excerpts(sources_dir: str):
    """Every *.json excerpt under sources_dir, recursively (M2 nested layout).

    Order is the string order of the POSIX path relative to sources_dir, so a
    flat directory loads exactly as before.  A file that cannot be read or
    parsed becomes a stand-in record reported under its relative path.
    """
    root = Path(sources_dir)
    paths = sorted(
        (path for path in root.rglob("*.json") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    excerpts = []
    for path in paths:
        try:
            with open(path, "rb") as handle:
                excerpts.append(json.loads(handle.read().decode("utf-8")))
        except (OSError, ValueError) as error:
            excerpts.append(
                {
                    "accession": path.relative_to(root).as_posix(),
                    "_load_error": str(error),
                }
            )
    return excerpts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify pinned relationship source excerpts (offline by default)."
    )
    parser.add_argument(
        "--sources",
        required=True,
        help="directory of pinned source excerpt JSON files",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="also re-fetch each full document from SEC and re-derive its hash",
    )
    args = parser.parse_args(argv)

    excerpts = _load_excerpts(args.sources)
    if not excerpts:
        print(f"relationship_replay: no excerpt files under {args.sources}")
        return 1

    failures = 0
    user_agent = os.environ.get("SEC_USER_AGENT")
    if args.network and not user_agent:
        print(
            "relationship_replay: --network needs SEC_USER_AGENT in the environment "
            "(exit 2)"
        )
        return 2

    problems_total = 0
    for index, excerpt in enumerate(excerpts):
        accession = excerpt.get("accession", "?")
        if "_load_error" in excerpt:
            print(f"{accession}: unreadable excerpt JSON: {excerpt['_load_error']}")
            failures += 1
            problems_total += 1
            continue
        problems = verify_excerpt(excerpt)
        if args.network:
            if index:
                time.sleep(MIN_REQUEST_SECONDS)
            try:
                problems += replay_fetch(excerpt, user_agent)
            except (URLError, OSError, KeyError) as error:
                problems.append(f"{accession}: network replay failed: {error}")
        if problems:
            failures += 1
            problems_total += len(problems)
            for problem in problems:
                print(f"{problem}")
        else:
            print(f"{accession}: ok")

    print(
        f"relationship_replay: sources={len(excerpts)} failures={failures} "
        f"problems={problems_total} network={str(bool(args.network)).lower()}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
