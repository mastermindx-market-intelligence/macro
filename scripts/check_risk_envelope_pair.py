"""Read-only settled Grey Deer source-copy coherence check.

This checks publication identity, not financial risk or source rights. It never
writes state, changes market posture, or retries a failed publisher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DATA_REL = Path("data/risk_envelope/latest.json")
SITE_REL = Path("site/riskdata/risk_envelope.json")
MARKET_REL = Path("data/market_state/latest.json")


@dataclass(frozen=True)
class PairCheck:
    status: str
    reason: str
    source_session: str | None = None
    bundle_id: str | None = None
    data_sha256: str | None = None
    site_sha256: str | None = None
    market_asof: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "OK"


def _read(path: Path) -> tuple[bytes, dict[str, Any]] | None:
    try:
        raw = path.read_bytes()
        item = json.loads(raw)
        if not isinstance(item, dict):
            return None
        return raw, item
    except (OSError, ValueError, UnicodeError):
        return None


def _read_git_blob(root: Path, ref: str, relative: Path) -> tuple[bytes, dict[str, Any]] | None:
    """Read exact committed bytes, never an uncommitted runner worktree copy."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "show", f"{ref}:{relative.as_posix()}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=15,
        )
        if proc.returncode != 0:
            return None
        item = json.loads(proc.stdout)
        if not isinstance(item, dict):
            return None
        return proc.stdout, item
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        return None


def check_pair(root: Path, *, git_ref: str | None = None) -> PairCheck:
    """Compare both settled copies and the source session with market state.

    A missing, invalid, or mismatched pair never falls back to the older copy.
    Source clocks and non-atomic publish failure are separate diagnostic causes.
    """
    if git_ref is not None and not (
        git_ref == "HEAD" or re.fullmatch(r"[0-9a-fA-F]{40}", git_ref)
    ):
        return PairCheck("INVALID", "unsupported_git_ref")
    read = (
        (lambda relative: _read(root / relative)) if git_ref is None
        else (lambda relative: _read_git_blob(root, git_ref, relative))
    )
    data = read(DATA_REL)
    site = read(SITE_REL)
    if data is None or site is None:
        return PairCheck("UNAVAILABLE", "risk_envelope_copy_missing_or_invalid")
    d_raw, d = data
    s_raw, s = site
    d_hash = hashlib.sha256(d_raw).hexdigest()
    s_hash = hashlib.sha256(s_raw).hexdigest()
    if d_raw != s_raw:
        return PairCheck(
            "DIVERGED", "settled_mirror_bytes_differ",
            data_sha256=d_hash, site_sha256=s_hash,
        )
    session = d.get("source_session")
    if not isinstance(session, str) or not session or d.get("as_of") != session:
        return PairCheck(
            "INVALID", "settled_source_session_invalid",
            data_sha256=d_hash, site_sha256=s_hash,
        )
    bundle = d.get("bundle_id")
    if not isinstance(bundle, str) or not bundle:
        return PairCheck(
            "INVALID", "settled_bundle_identity_missing",
            source_session=session, data_sha256=d_hash, site_sha256=s_hash,
        )
    market = read(MARKET_REL)
    if market is None:
        return PairCheck(
            "UNAVAILABLE", "market_state_missing_or_invalid",
            source_session=session, bundle_id=bundle,
            data_sha256=d_hash, site_sha256=s_hash,
        )
    market_asof = market[1].get("asof")
    if not isinstance(market_asof, str) or not market_asof:
        return PairCheck(
            "INVALID", "market_state_clock_invalid",
            source_session=session, bundle_id=bundle,
            data_sha256=d_hash, site_sha256=s_hash,
        )
    if session != market_asof:
        return PairCheck(
            "STALE", "envelope_market_session_mismatch",
            source_session=session, bundle_id=bundle,
            data_sha256=d_hash, site_sha256=s_hash,
            market_asof=market_asof,
        )
    return PairCheck(
        "OK", "settled_mirrors_match_current_market_session",
        source_session=session, bundle_id=bundle,
        data_sha256=d_hash, site_sha256=s_hash,
        market_asof=market_asof,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--git-ref", default=None,
        help="Read immutable committed-tree bytes at HEAD or a full 40-hex SHA; never read worktree overrides",
    )
    args = parser.parse_args(argv)
    result = check_pair(args.root, git_ref=args.git_ref)
    print(json.dumps(asdict(result), sort_keys=True, separators=(",", ":")))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
