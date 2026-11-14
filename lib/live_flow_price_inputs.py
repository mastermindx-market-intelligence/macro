"""Materialize display-only prior closes from the existing published Yahoo store.

This reads protected Macro main through the runtime's existing Git origin. It
does not collect prices, change the runtime checkout, or run a Flow cycle.
Source dates, Git publication identity and retrieval time remain distinct.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from lib.nyse_calendar import is_session, last_session_on_or_before

SCHEMA = "live_flow.prior_close_inputs.v1"
RELATIVE_PATH = Path("live_flow_state/prior_close_inputs.json")
SOURCE_REF = "refs/mastermind/live-flow-prior-close"
ORIGINS = frozenset({
    "git@github.com:mastermindx-market-intelligence/macro.git",
    "https://github.com/mastermindx-market-intelligence/macro.git",
})
ROOT_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9.]{0,31}\Z")
MAX_BLOB_BYTES = 2 * 1024 * 1024


def _prior_session(session_date: str) -> str:
    if not isinstance(session_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", session_date):
        raise ValueError("Flow session must be an ISO calendar date")
    session = date.fromisoformat(session_date)
    if not is_session(session):
        raise ValueError("Flow session is not a NYSE session")
    return last_session_on_or_before(session - timedelta(days=1)).isoformat()


def _document(path: Path, session_date: str) -> dict | None:
    try:
        if path.stat().st_size > 256 * 1024:
            return None
        value = json.loads(path.read_text())
        if (value.get("schema") != SCHEMA
                or value.get("session_date") != session_date
                or value.get("source_session") != _prior_session(session_date)
                or not re.fullmatch(r"[0-9a-f]{40}", value.get("source_git_sha", ""))
                or not isinstance(value.get("prices"), dict)):
            return None
        return value
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def load_prior_close(data_dir: Path, root: str, session_date: str) -> float | None:
    """Read one exact-session, source-bound value; stale/invalid stays unknown."""
    document = _document(data_dir / RELATIVE_PATH, session_date)
    if document is None:
        return None
    entry = document["prices"].get(root)
    if not isinstance(entry, dict):
        return None
    value = entry.get("close_price")
    try:
        valid_price = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid_price = False
    if (not valid_price
            or entry.get("source_session") != document["source_session"]
            or entry.get("source_path") != f"data/yahoo/{root}.parquet"
            or type(entry.get("source_bytes")) is not int
            or not 0 < entry["source_bytes"] <= MAX_BLOB_BYTES
            or not isinstance(entry.get("source_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", entry["source_sha256"])):
        return None
    return float(value)


def sync_prior_closes(repo: Path, data_dir: Path, roots: list[str],
                      session_date: str, *, timeout: float = 120) -> dict:
    """One bounded read of the incumbent publication, only at natural startup.

    A failed fetch/timeout preserves the old artifact. Individual unavailable
    prices remain explicit gaps. The reader independently requires the exact
    prior session, so retained old data can never silently become current.
    """
    import pandas as pd
    from lib.live_flow_prior_close import select_prior_close

    source_session = _prior_session(session_date)
    roots = list(dict.fromkeys(roots))
    if (not roots or len(roots) > 256
            or any(not isinstance(root, str) or not ROOT_PATTERN.fullmatch(root)
                   for root in roots)
            or not math.isfinite(timeout) or not 0 < timeout <= 120):
        raise ValueError("invalid bounded Flow price-input request")
    output = data_dir / RELATIVE_PATH
    prior = _document(output, session_date)
    if (prior is not None and prior.get("requested_roots") == roots
            and not prior.get("unavailable")
            and all(load_prior_close(data_dir, root, session_date) is not None
                    for root in roots)):
        return {"status": "already_current", "available": len(prior["prices"]),
                "unavailable": prior.get("unavailable", {})}
    deadline = time.monotonic() + timeout

    def git(*args: str) -> bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("prior-close source read exceeded its bound")
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "remote.origin.promisor=true",
             "-c", "remote.origin.partialclonefilter=blob:none", *args],
            check=True, capture_output=True, timeout=remaining,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        ).stdout

    # The origin is an existing credential/resource binding, not caller input.
    if git("remote", "get-url", "origin").decode().strip() not in ORIGINS:
        raise ValueError("prior-close source origin is not canonical Macro")
    git("fetch", "--filter=blob:none", "--depth=1", "--no-tags",
        "--no-write-fetch-head", "origin", f"+refs/heads/main:{SOURCE_REF}")
    sha = git("rev-parse", "--verify", SOURCE_REF + "^{commit}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("invalid published source revision")
    prices, unavailable = {}, {}
    for root in roots:
        reference = f"{sha}:data/yahoo/{root}.parquet"
        try:
            size = int(git("cat-file", "-s", reference))
            if not 0 < size <= MAX_BLOB_BYTES:
                unavailable[root] = "source_size_out_of_bounds"
                continue
            raw = git("show", reference)
            if len(raw) != size:
                raise ValueError("source byte length changed")
            value = select_prior_close(pd.read_parquet(io.BytesIO(raw)), session_date)
            if value is None:
                unavailable[root] = "exact_prior_price_unavailable"
                continue
            prices[root] = {
                "close_price": value, "source_session": source_session,
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "source_bytes": size, "source_path": f"data/yahoo/{root}.parquet",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        except subprocess.CalledProcessError:
            unavailable[root] = "published_blob_unavailable"
        except TimeoutError:
            raise
        except (ValueError, TypeError, OSError):
            unavailable[root] = "published_frame_invalid"
    document = {
        "schema": SCHEMA, "session_date": session_date,
        "source_session": source_session, "source_git_sha": sha,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "requested_roots": roots, "prices": prices, "unavailable": unavailable,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=output.parent,
                                         prefix=".prior-close-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, allow_nan=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"status": "complete" if not unavailable else "partial",
            "source_git_sha": sha, "available": len(prices),
            "unavailable": unavailable}
