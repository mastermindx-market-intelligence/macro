#!/usr/bin/env python3
"""Emit a review cue for one successful publication, never a route admission.

The incumbent publisher supplies its exact successful old/new commits. Only
changed HTML blobs are classified by the existing exporter. A changed policy
explicitly requires a full owner review; this bounded probe cannot certify it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import export_shared_shell_routes as exporter  # noqa: E402
import yaml  # noqa: E402

SOURCE_PATHS = {
    "registry": "data/product_experience/page_registry.json",
    "access_policy": "config/site_access.yml",
    "exporter": "scripts/export_shared_shell_routes.py",
}
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.PIPE)


def _commit(ref: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("publication identity must be an exact lowercase commit SHA")
    if git("rev-parse", "--verify", ref + "^{commit}").decode().strip() != ref:
        raise ValueError("publication identity must name a commit directly")
    return ref


def _ancestor(before: str, after: str) -> None:
    subprocess.run(["git", "merge-base", "--is-ancestor", before, after],
                   cwd=ROOT, check=True, capture_output=True)


def _sources(ref: str) -> tuple[dict, dict[str, bytes]]:
    raw = {name: git("show", ref + ":" + path) for name, path in SOURCE_PATHS.items()}
    registry = json.loads(raw["registry"])
    if not isinstance(registry, dict):
        raise ValueError("canonical registry must be an object")
    sources = registry.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("canonical source bindings are missing")
    for name in ("macro", "terminal", "mastermind"):
        source = sources.get(name)
        if (not isinstance(source, dict)
                or not re.fullmatch(r"[0-9a-f]{40}", source.get("sha") or "")
                or ("available" in source and source["available"] is not True)):
            raise ValueError("unqualified canonical source: " + name)
    problems = exporter.registry_owner.validate(registry)
    if problems:
        raise ValueError("invalid canonical registry: " + "; ".join(problems[:5]))
    return registry, raw


def _project(ref: str, registry: dict, raw: dict[str, bytes], paths: list[str]) -> dict:
    policy = yaml.safe_load(raw["access_policy"])
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise ValueError("serving policy must be an object")
    deny = policy.get("deny")
    if deny is None:
        deny = {}
    if not isinstance(deny, dict) or any(
        not isinstance(deny.get(key, []), list)
        or not all(isinstance(value, str) for value in deny.get(key, []))
        for key in ("exact", "prefixes")
    ):
        raise ValueError("serving deny policy must contain string lists")
    return exporter.derive_projection(
        registry, paths,
        {"exact": set(deny.get("exact") or []), "prefixes": tuple(deny.get("prefixes") or [])},
        {}, registry_digest=hashlib.sha256(raw["registry"]).hexdigest(),
        inventory_ref=registry["sources"]["macro"]["sha"],
        document_paths=exporter.document_inventory(ROOT, ref, paths) if paths else set(),
    )


def publication_delta(before: str, after: str) -> dict | None:
    """Return a changed-path review cue, or None for no membership/policy change."""
    before, after = _commit(before), _commit(after)
    if before == after:
        raise ValueError("a successful publication needs distinct old/new commits")
    _ancestor(before, after)
    _ancestor(after, "origin/main")
    registries, source_bytes = {}, {}
    for ref in (before, after):
        registries[ref], source_bytes[ref] = _sources(ref)
    policy_changed = {name: source_bytes[before][name] != source_bytes[after][name]
                      for name in SOURCE_PATHS}
    if Path(exporter.__file__).read_bytes() != source_bytes[after]["exporter"]:
        raise ValueError("loaded exporter differs from the successful publication source")
    sides: dict[str, list[str]] = {before: [], after: []}
    tokens = git("diff", "--name-status", "-z", "--no-renames", before, after, "--", "site/").split(b"\0")
    if tokens[-1:] == [b""]:
        tokens.pop()
    if len(tokens) % 2:
        raise ValueError("invalid immutable changed-path inventory")
    changed = []
    for index in range(0, len(tokens), 2):
        status, path = tokens[index].decode(), tokens[index + 1].decode()
        if not path.endswith(".html"):
            continue
        route = "/" + path.removeprefix("site/")
        if not path.startswith("site/") or not exporter.normalized_path(route):
            raise ValueError("unsafe changed HTML path")
        if status not in ("A", "D", "M", "T"):
            raise ValueError("unsupported committed path status: " + status)
        changed.append(route)
        if status != "A":
            sides[before].append(route)
        if status != "D":
            sides[after].append(route)
    if not changed and not any(policy_changed.values()):
        return None
    # A changed classifier cannot truthfully classify the old side with its new
    # rules. Retain that source-change cue without inventing a membership diff.
    projections = ({ref: {"legacyPaths": [], "coverage": {"excluded": []}}
                    for ref in (before, after)} if policy_changed["exporter"] else
                   {ref: _project(ref, registries[ref], source_bytes[ref], sides[ref])
                    for ref in (before, after)})
    old, new = projections[before], projections[after]
    added = sorted(set(new["legacyPaths"]) - set(old["legacyPaths"]))
    removed = sorted(set(old["legacyPaths"]) - set(new["legacyPaths"]))
    if not added and not removed and not any(policy_changed.values()):
        return None
    return {
        "schema": "mastermind.shared_shell_publication_delta.v1",
        "before": before, "after": after,
        "scope": "changed_html_only; not a complete catalog or served-host proof",
        "review_required": True, "accepted": False,
        "changed_html_count": len(changed), "added": added, "removed": removed,
        "allowed_before": old["legacyPaths"], "allowed_after": new["legacyPaths"],
        "excluded_before": old["coverage"]["excluded"],
        "excluded_after": new["coverage"]["excluded"],
        "policy_changed": policy_changed,
        "full_inventory_review_required": any(policy_changed.values()),
        "membership_comparison": ("not_computed_exporter_changed" if policy_changed["exporter"]
                                  else "compared_changed_html"),
        "source_sha256": {
            side: {name: hashlib.sha256(raw).hexdigest() for name, raw in source_bytes[ref].items()}
            for side, ref in (("before", before), ("after", after))
        },
        "owner_action": [
            "At the existing compatibility/release integration boundary, consume this exact run artifact; artifact delivery is not pickup.",
            "Reconcile the protected Terminal branch, any live catalog writer, and last-installed inventory before opening one reviewed batch.",
            f"git show {after}:data/product_experience/page_registry.json > <owned-registry-file>",
            f"python3 scripts/export_shared_shell_routes.py --registry <owned-registry-file> --inventory-ref {after} --output <owned-Terminal-candidate>",
            "Review the complete generated delta and negative controls through the existing protected source/release path; do not auto-admit or deploy.",
        ],
    }


def emit(before: str, after: str, output: Path) -> bool:
    if output.exists() or output.is_symlink():
        raise ValueError("refusing to replace an existing publication receipt")
    cue = publication_delta(before, after)
    if cue is None:
        return False
    encoded = (json.dumps(cue, ensure_ascii=False, indent=2) + "\n").encode()
    if len(encoded) > MAX_ARTIFACT_BYTES:
        raise ValueError("publication review cue exceeds bounded artifact size")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
        # link is atomic and refuses an existing destination, including races.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        changed = emit(args.before, args.after, args.output)
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print("Shared Shell publication cue refused: " + str(error), file=sys.stderr)
        return 1
    print("Shared Shell consumer review required; retained cue: " + str(args.output)
          if changed else "Shared Shell: no changed-path membership or source-policy delta")
    return 3 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
