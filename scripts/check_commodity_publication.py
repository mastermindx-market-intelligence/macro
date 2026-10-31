"""Keep an accepted Commodities workspace from regressing during site publication.

This checks the publication envelope, not market-data freshness. The sole repair
copies one qualified, pinned accepted HTML blob. It runs no builder or collector.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import posixpath
import re
import subprocess
import sys
import tempfile

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.commodity_decision_workspace import PROJECTION_REVISION, SCHEMA  # noqa: E402
from scripts.check_site_asset_refs import _iter_refs  # noqa: E402

PAGE = "site/commodities.html"


class PublicationError(RuntimeError):
    """The candidate cannot be proved safe to publish."""


class UnsupportedProjection(PublicationError):
    """An explicit source/contract update is needed; never silently downgrade."""


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.mounts = 0
        self.payloads = 0
        self.payload_types = []
        self.in_payload = False
        self.closed_payloads = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "commodity-workspace":
            self.mounts += 1
        if tag == "script" and attrs.get("id") == "cw-data":
            self.payloads += 1
            self.payload_types.append(attrs.get("type", "").strip().lower())
            self.in_payload = True

    def handle_endtag(self, tag):
        if tag == "script" and self.in_payload:
            self.closed_payloads += 1
            self.in_payload = False

    def handle_data(self, data):
        if self.in_payload:
            self.parts.append(data)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def inspect_page(raw):
    """Validate the small display-only envelope; unavailable observations are valid."""
    try:
        text = raw.decode("utf-8")
        parsed = _Page()
        parsed.feed(text)
        parsed.close()
        if (parsed.mounts, parsed.payloads, parsed.closed_payloads) != (1, 1, 1):
            raise ValueError("expected exactly one workspace mount and JSON payload")
        if parsed.payload_types != ["application/json"]:
            raise ValueError("workspace payload must be application/json")
        payload = json.loads("".join(parsed.parts), object_pairs_hook=_unique_object,
                             parse_constant=_invalid_constant)
        if not isinstance(payload, dict):
            raise ValueError("workspace payload must be an object")
        schema = payload.get("schema")
        if isinstance(schema, str) and schema != SCHEMA:
            raise UnsupportedProjection(f"unsupported workspace schema: {schema}")
        if schema != SCHEMA:
            raise ValueError("workspace schema is missing")
        revision = payload.get("projection_revision")
        if type(revision) is not int or revision < 1:
            raise ValueError("projection revision must be a positive integer")
        if revision > PROJECTION_REVISION:
            raise UnsupportedProjection(f"unsupported projection revision: {revision}")
        if payload.get("display_only") is not True or payload.get("live") is not False:
            raise ValueError("workspace must remain display-only and non-live")
        research = payload.get("research")
        if (not isinstance(research, dict) or research.get("effect") != "export_only"
                or research.get("monitoring_active") is not False):
            raise ValueError("research must remain export-only with inactive monitoring")
        if not isinstance(payload.get("assets"), list):
            raise ValueError("workspace asset collection is missing")
        fingerprint = payload.get("fingerprint")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValueError("workspace fingerprint is malformed")
        return {"revision": revision, "fingerprint": fingerprint,
                "sha256": sha256(raw).hexdigest(), "text": text}
    except UnsupportedProjection:
        raise
    except (ValueError, UnicodeError) as exc:
        raise PublicationError(f"invalid workspace: {exc}") from exc


def _git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        raise PublicationError("Git read failed: " + result.stderr.decode(errors="replace")[:500].strip())
    return result.stdout


def _resolve(repo, ref):
    try:
        sha = _git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()
    except PublicationError as exc:
        raise PublicationError(f"cannot resolve accepted/candidate ref {ref!r}: {exc}") from exc
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise PublicationError("resolved commit identity is not a full SHA")
    return sha


def _blob(repo, commit):
    entry = _git(repo, "ls-tree", commit, "--", PAGE).decode().strip()
    if not entry.startswith(("100644 blob ", "100755 blob ")):
        raise PublicationError("accepted/candidate page is missing or is not a regular Git file")
    return _git(repo, "show", commit + ":" + PAGE)


def _asset_paths(text):
    paths = set()
    for ref in _iter_refs(text):
        if not ref.lower().endswith((".css", ".js")):
            continue
        path = posixpath.normpath("site/" + ref.lstrip("/"))
        if not path.startswith("site/") or "\\" in path:
            raise PublicationError(f"asset path escapes the published site: {ref}")
        paths.add(path)
    return paths


def _check_assets(repo, text, candidate_commit=None):
    paths = _asset_paths(text)
    if candidate_commit and paths:
        entries = _git(repo, "ls-tree", "-r", "-z", candidate_commit, "--", *sorted(paths))
        present = set()
        for entry in entries.split(b"\0"):
            if not entry:
                continue
            metadata, path = entry.split(b"\t", 1)
            if metadata.startswith((b"100644 blob ", b"100755 blob ")):
                present.add(path.decode())
        missing = paths - present
    else:
        site = (repo / "site").resolve()
        missing = {path for path in paths if not (repo / path).is_file()
                   or (repo / path).is_symlink()
                   or not (repo / path).resolve().is_relative_to(site)}
    if missing:
        raise PublicationError("missing publication asset(s): " + ", ".join(sorted(missing)))


def verify_publication(repo, accepted_ref, *, candidate_ref=None, heal=False):
    """Pin the fallback once, check worktree or exact Git candidate, optionally repair."""
    repo = Path(repo).resolve()
    if heal and candidate_ref:
        raise PublicationError("a Git candidate check is read-only; it cannot heal")
    accepted = _resolve(repo, accepted_ref)
    try:
        accepted_raw = _blob(repo, accepted)
        fallback = inspect_page(accepted_raw)
    except PublicationError as exc:
        raise PublicationError(f"accepted baseline requires reconciliation; page is not qualified: {exc}") from exc
    candidate_commit = _resolve(repo, candidate_ref) if candidate_ref else None
    destination = repo / PAGE
    if not candidate_commit:
        if (destination.is_symlink() or destination.parent.is_symlink()
                or destination.parent.resolve() != repo / "site"
                or not destination.parent.resolve().is_relative_to(repo)):
            raise PublicationError("candidate page requires the real site directory and a regular contained worktree path")
    candidate_raw = _blob(repo, candidate_commit) if candidate_commit else (
        destination.read_bytes() if destination.is_file() else b""
    )
    reason = None
    try:
        current = inspect_page(candidate_raw)
        if current["revision"] < max(PROJECTION_REVISION, fallback["revision"]):
            raise PublicationError("candidate projection revision regresses the required contract")
    except UnsupportedProjection:
        raise
    except PublicationError as exc:
        reason = str(exc)
        if not heal:
            raise PublicationError(f"candidate publication refused: {reason}") from exc
        if fallback["revision"] != PROJECTION_REVISION:
            raise PublicationError("accepted page revision cannot satisfy the required projection") from exc
        current = fallback

    # Check the assets in the actual candidate tree BEFORE writing any repair.
    # The existing full-site reference gate still runs after normalisation.
    _check_assets(repo, current["text"], candidate_commit)
    action = "kept"
    if reason:
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(prefix=".commodity-publication-", dir=destination.parent)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(accepted_raw)
            os.chmod(temporary, 0o644)
            os.replace(temporary, destination)
            temporary = None
            current = inspect_page(destination.read_bytes())
            if destination.read_bytes() != accepted_raw:
                raise PublicationError("repaired page differs from the pinned accepted blob")
            action = "restored"
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
    return {
        "schema": "mmx.commodities.publication_guard.v1", "action": action,
        "accepted_commit": accepted, "candidate_commit": candidate_commit,
        "page": PAGE, "page_sha256": current["sha256"],
        "projection_revision": current["revision"], "fingerprint": current["fingerprint"],
        "repair_reason": reason, "freshness_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-ref", default="origin/main")
    parser.add_argument("--heal-from", help="restore a regressed worktree page from this pinned accepted ref")
    parser.add_argument("--candidate-ref", help="read-only verification of the exact commit to be pushed")
    args = parser.parse_args(argv)
    if args.heal_from and args.candidate_ref:
        parser.error("--heal-from cannot be combined with --candidate-ref")
    try:
        result = verify_publication(Path.cwd(), args.heal_from or args.accepted_ref,
                                    candidate_ref=args.candidate_ref, heal=bool(args.heal_from))
    except (PublicationError, OSError) as exc:
        print(f"::error title=commodities publication refused::{exc}", flush=True)
        return 1
    if result["action"] == "restored":
        print("::notice title=commodities publication repaired::restored the qualified accepted page; market-data freshness is not inferred", flush=True)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
