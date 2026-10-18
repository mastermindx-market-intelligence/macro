#!/usr/bin/env python3
"""Export a finite Shared Shell route projection from the canonical page registry.

The registry and site-access policy remain authoritative. This file adds no routes:
families expand only over git-tracked HTML at the recorded source revision.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from typing import Any
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import build_product_page_registry as registry_owner
SCHEMA = "mastermind.shared_shell_routes.v1"
PARAM = re.compile(r"<[^/<>]+>")
ANCHOR = re.compile(r"<a\b[^>]*\bhref=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.S)
TRANSLATION = re.compile(r"t\(\s*(['\"])(.*?)\1\s*,\s*(['\"])(.*?)\3\s*\)", re.S)
TEMPLATE_VAR = re.compile(r"\{\{.*?\}\}", re.S)


def normalized_path(value: str) -> bool:
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        return False
    if any(c in value for c in "\\?#") or re.search(r"[\x00-\x20\x7f]", value):
        return False
    return all(p not in (".", "..") for p in value.split("/"))


def family_pattern(route: str) -> re.Pattern[str]:
    parts = PARAM.split(route)
    return re.compile("^" + "[^/]+(?:/[^/]+)*".join(re.escape(part) for part in parts) + "$")


def navigation_labels(texts: list[str]) -> dict[str, dict[str, str]]:
    """Read bilingual names from the existing navigation source, never a second list."""
    out: dict[str, dict[str, str]] = {}
    for text in texts:
        for href, body in ANCHOR.findall(text):
            href = TEMPLATE_VAR.sub("", href)
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path.endswith(".html"):
                continue
            path = "/" + parsed.path.lstrip("./")
            labels = TRANSLATION.search(body)
            if labels and path not in out:
                out[path] = {"en": html.unescape(labels[2].strip()),
                             "zh": html.unescape(labels[4].strip())}
    return out


def derive_projection(registry: dict[str, Any], tracked_html: list[str],
                      deny: dict[str, Any], labels: dict[str, dict[str, str]],
                      *, registry_digest: str, inventory_ref: str,
                      document_paths: set[str] | None = None) -> dict[str, Any]:
    if registry.get("schema") != registry_owner.SCHEMA:
        raise ValueError("unrecognized canonical registry")
    if registry.get("sources", {}).get("macro", {}).get("sha") != inventory_ref:
        raise ValueError("registry and concrete HTML inventory must use the same Macro revision")
    if not isinstance(deny.get("exact"), (set, list, tuple)) or not isinstance(deny.get("prefixes"), (list, tuple)):
        raise ValueError("a parsed deny policy is required")
    rows = registry["pages"]
    exact: dict[str, dict[str, Any]] = {}
    families: list[tuple[re.Pattern[str], dict[str, Any]]] = []
    for row in rows:
        if row["repo"] != "macro":
            continue
        route = "/index.html" if row["route"] == "/" else row["route"]
        if row["route_kind"] == "family":
            families.append((family_pattern(route), row))
        else:
            if route in exact:
                raise ValueError("duplicate canonical Macro route: " + route)
            exact[route] = row

    paths: list[str] = []
    excluded: list[dict[str, str]] = []
    members: dict[str, list[str]] = {}
    for path in sorted(set(tracked_html)):
        if not normalized_path(path) or not path.endswith(".html"):
            raise ValueError("invalid concrete HTML path: " + str(path))
        row = exact.get(path)
        if row is None:
            matches = [r for pattern, r in families if pattern.fullmatch(path)]
            if len(matches) > 1:
                raise ValueError("ambiguous canonical family: " + path)
            row = matches[0] if matches else None
        reason = None
        if registry_owner._in_bucket(path, deny):
            reason = "serving_policy_denied"
        elif document_paths is not None and path not in document_paths:
            reason = "html_fragment"
        elif row is None:
            reason = "unregistered"
        elif row["lifecycle"] != "live":
            reason = "lifecycle_" + row["lifecycle"]
        elif row["access_shell"] != "anonymous" or row["payload_tier"] == "internal":
            reason = "not_a_public_document_shell"
        if reason:
            excluded.append({"path": path, "reason": reason})
            continue
        paths.append(path)
        members.setdefault(row["page_id"], []).append(path)

    native: list[str] = []
    native_excluded: list[dict[str, str]] = []
    for row in rows:
        if row["repo"] != "terminal":
            continue
        route = row["route"]
        if (row["lifecycle"] != "live" or row["access_shell"] == "admin"
                or PARAM.search(route) or route == "/"):
            native_excluded.append({"path": route, "reason": "retained_by_native_owner"})
        elif not normalized_path(route):
            raise ValueError("invalid native route: " + route)
        else:
            native.append(route)
    collisions = set(paths) & set(native)
    if collisions:
        raise ValueError("route collision: " + ", ".join(sorted(collisions)))

    directory: list[dict[str, Any]] = []
    for row in rows:
        candidates = members.get(row["page_id"], [])
        if row["repo"] == "macro" and candidates:
            # A family is represented by its concrete members, not an invented landing URL.
            # Company families remain searchable through the incumbent symbol picker.
            route = "/index.html" if row["route"] == "/" else row["route"]
            if PARAM.search(route):
                continue
            href, kind = route, "legacy"
        elif row["repo"] == "terminal" and row["route"] in native:
            href, kind = row["route"], "native"
            if href in ("/login", "/reset-password", "/invite", "/embed/chart"):
                continue
        else:
            continue
        stem = href.rsplit("/", 1)[-1].removesuffix(".html").replace("_", " ").replace("-", " ")
        fallback = stem.title() or "Mastermind"
        directory.append({
            "id": row["page_id"], "href": href, "kind": kind,
            "title": labels.get(href, {"en": fallback, "zh": fallback}),
            "group": row["nav_family"],
            "question": row["primary_user_question"],
            "payloadTier": row["payload_tier"],
        })
    directory.sort(key=lambda item: (item["title"]["en"].casefold(), item["href"]))
    return {
        "schema": SCHEMA, "generatedAt": registry["generated_at"],
        "sources": {"registrySha256": registry_digest, "macro": inventory_ref,
                    "terminal": registry["sources"]["terminal"].get("sha"),
                    "mastermind": registry["sources"]["mastermind"].get("sha")},
        "legacyPaths": paths, "nativePaths": sorted(set(native)),
        "directory": directory,
        "coverage": {"trackedHtml": len(set(tracked_html)), "legacyPaths": len(paths),
                     "excluded": excluded, "nativeExcluded": native_excluded,
                     "familyMembers": {key: len(value) for key, value in sorted(members.items())
                                       if len(value) > 1}},
    }


class DocumentProbe(HTMLParser):
    """Distinguish full HTML documents from fetched fragments without executing content."""
    document = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("html", "head"):
            self.document = True

    def handle_decl(self, decl: str) -> None:
        if re.match(r"doctype\s+html(?:\s|$)", decl, re.I):
            self.document = True


def is_html_document(prefix: bytes) -> bool:
    probe = DocumentProbe()
    probe.feed(prefix.decode("utf-8", errors="replace"))
    return probe.document


def document_inventory(root: Path, ref: str, paths: list[str]) -> set[str]:
    """Stream immutable blobs through one git process; retain at most an 8KB prefix."""
    result: set[str] = set()
    proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=root,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert proc.stdin is not None and proc.stdout is not None
    try:
        for path in paths:
            proc.stdin.write((ref + ":site" + path + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError("missing immutable HTML blob: " + path)
            remaining = int(header[2])
            prefix = proc.stdout.read(min(8192, remaining))
            remaining -= len(prefix)
            while remaining:
                chunk = proc.stdout.read(min(262144, remaining))
                if not chunk:
                    raise ValueError("truncated immutable HTML blob: " + path)
                remaining -= len(chunk)
            if proc.stdout.read(1) != b"\n":
                raise ValueError("invalid git batch delimiter")
            if is_html_document(prefix):
                result.add(path)
    finally:
        proc.stdin.close()
        proc.stdout.close()
        proc.wait()
    if proc.returncode:
        raise ValueError("git document inventory failed")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", type=Path, default=ROOT / "data/product_experience/page_registry.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = args.registry.read_bytes()
    registry = json.loads(raw)
    problems = registry_owner.validate(registry)
    if problems:
        raise ValueError("invalid canonical registry: " + "; ".join(problems[:5]))
    ref = registry["sources"]["macro"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("Macro source must be an immutable commit")
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", "site"], cwd=ROOT, text=True)
    paths = ["/" + f.removeprefix("site/") for f in files.splitlines()
             if f.startswith("site/") and f.endswith(".html")]
    # Read the deny policy and labels at the same source pin as the inventory.
    def source(path: str) -> str:
        return subprocess.check_output(["git", "show", ref + ":" + path], cwd=ROOT, text=True)
    import yaml
    policy = yaml.safe_load(source("config/site_access.yml")) or {}
    deny = policy.get("deny") or {}
    denied = {"exact": set(deny.get("exact") or []), "prefixes": tuple(deny.get("prefixes") or [])}
    labels = navigation_labels([source("templates/_navlinks.html.j2"),
                                source("templates/_public_nav.html.j2")])
    doc = derive_projection(registry, paths, denied, labels,
                            registry_digest=hashlib.sha256(raw).hexdigest(), inventory_ref=ref,
                            document_paths=document_inventory(ROOT, ref, paths))
    encoded = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text() != encoded:
            print("Shared Shell projection is stale; regenerate from the canonical registry")
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    gaps = sum(e["reason"] == "unregistered" for e in doc["coverage"]["excluded"])
    print(f"Shared Shell: {len(doc['legacyPaths'])} exact legacy paths, "
          f"{len(doc['nativePaths'])} native paths, {len(doc['directory'])} directory entries, "
          f"{gaps} unregistered HTML paths (not admitted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
