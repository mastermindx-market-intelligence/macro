#!/usr/bin/env python3
"""Assemble the existing v2 evidence schema from actual Browser capture records.

This script performs no browser interaction, network request, image conversion,
or screenshot generation. It verifies the recorded PNGs and the observed state,
then writes manifest.json and the existing three-key EVIDENCE.yml receipt.
All 12 required captures and this package's two accepted mobile UI views must exist.
Use --check-only while captures are arriving; incomplete input produces no files.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import sys
from urllib.parse import urlsplit


PACKAGE = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE.parents[2]
ADAPTER = PACKAGE / "capture-browser.js"
ADAPTER_SHA256 = "38ea551fb8df7caa013ef1280583eefdab944ba216bb8cf4ea21e4feeac23e29"
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")
FORCES = {
    "news_hover": ("hover", "#ndDensity"),
    "news_focus": ("focus", "#ndSearch"),
    "company_buffered": ("focus", "#ndCompanyUpdates"),
    "story_warning": ("focus", "#ndDetailClose"),
}
EXTRA_CELLS = {
    ("mobile", "en", "dark", "company_buffered"),
    ("mobile", "zh", "light", "story_warning"),
}
UNACCEPTED_OPTIONAL_CELLS = (
    ("desktop", "en", "dark", "company_buffered"),
    ("desktop", "zh", "light", "company_buffered"),
)
METRIC_KEYS = (
    "document_height_px", "section_count", "heading_counts",
    "duplicate_heading_texts", "panel_count", "visible_word_count",
    "long_paragraph_count", "raw_slug_hits", "raw_slug_hit_count",
    "todo_placeholder_hits", "todo_placeholder_hit_count", "horizontal_overflow",
    "elements_wider_than_viewport", "console_error_count", "request_count",
    "payload_bytes_total", "asof_present", "source_present", "screenshot_completion",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PENDING_RE = re.compile(r"^([1-9][0-9]*)\s+(?:new story groups\b|个新增事件组)")
MAX_STATE_LAG_SECONDS = 60


class InvalidEvidence(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidEvidence(message)


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def timestamp(value: object, label: str) -> datetime:
    require(isinstance(value, str), f"{label}: timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEvidence(f"{label}: invalid timestamp") from exc
    require(parsed.tzinfo is not None, f"{label}: timestamp needs a timezone")
    return parsed.astimezone(timezone.utc)


def relative_path(value: object, label: str) -> PurePosixPath:
    require(isinstance(value, str) and bool(value), f"{label}: missing path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in value,
            f"{label}: expected a relative path without traversal")
    return path


def package_file(value: object, label: str) -> Path:
    path = (PACKAGE / relative_path(value, label)).resolve()
    require(path.is_relative_to(PACKAGE), f"{label}: path escapes evidence package")
    require(path.is_file(), f"{label}: file does not exist: {value}")
    return path


def load_object(path: Path) -> tuple[dict, bytes]:
    body = path.read_bytes()
    require(len(body) <= 2_000_000, f"{path.name}: metadata exceeds 2 MB")
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidEvidence(f"{path.name}: invalid JSON") from exc
    require(isinstance(value, dict), f"{path.name}: expected a JSON object")
    return value, body


def nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_rect(value: object, viewport: str, label: str) -> None:
    require(isinstance(value, dict), f"{label}: observed surface dimensions missing")
    for field, maximum in zip(("width", "height"), VIEWPORTS[viewport]):
        size = value.get(field)
        require(type(size) in (int, float) and math.isfinite(size) and 0 < size <= maximum,
                f"{label}: {field} is invalid or exceeds the observed viewport")
        if viewport == "mobile":
            require(size == maximum, f"{label}: the mobile surface was not full viewport {field}")


def check_ui_state(ui_state: dict, observed: dict, force: str, viewport: str,
                   captured_at: datetime, label: str) -> dict:
    """Bind the separate actual DOM observation to its nearby capture record.

    These checks verify only the recorded preview state. They do not turn a
    connected label, illustrative source link, or screenshot into production
    source, entitlement, transport-latency, or corroboration evidence.
    """
    state_at = timestamp(ui_state.get("captured_at"), label)
    lag = (captured_at - state_at).total_seconds()
    require(0 <= lag <= MAX_STATE_LAG_SECONDS,
            f"{label}: UI observation must precede capture by no more than {MAX_STATE_LAG_SECONDS} seconds")
    require(ui_state.get("url") == observed["url"], f"{label}: UI observation URL differs from capture")
    require(ui_state.get("theme") == observed["applied_theme"],
            f"{label}: UI observation theme differs from capture")
    if "locale" in ui_state:
        require(ui_state["locale"] == observed["applied_locale"],
                f"{label}: UI observation locale differs from capture")
    require(ui_state.get("connection_state") == "connected",
            f"{label}: the observed preview connection was not connected")
    summary = {"state_to_capture_delay_seconds": lag, "connection_state": "connected"}
    if force == "company_buffered":
        for field in ("company_open", "pending_visible", "pending_focus", "pending_focus_visible"):
            require(ui_state.get(field) is True, f"{label}: required company state {field} was not observed")
        dialogs = ui_state.get("visible_dialogs")
        require(isinstance(dialogs, list) and len(dialogs) == 1
                and isinstance(dialogs[0], dict) and dialogs[0].get("id") == "ndCompany",
                f"{label}: company must be the single observed visible dialog")
        check_rect(ui_state.get("company_rect"), viewport, label)
        require(nonempty_text(ui_state.get("connection_text"))
                and ui_state["connection_text"] == observed.get("company_connection"),
                f"{label}: company connection text differs between observations")
        pending_text = ui_state.get("pending_text")
        pending = PENDING_RE.match(pending_text.strip()) if nonempty_text(pending_text) else None
        require(pending is not None, f"{label}: a positive buffered group count was not observed")
        pending_count = int(pending.group(1))
        if "pending_count" in ui_state:
            require(type(ui_state["pending_count"]) is int and ui_state["pending_count"] == pending_count,
                    f"{label}: pending count differs from the displayed label")
        rows = ui_state.get("rows")
        require(isinstance(rows, list) and len(rows) == 3
                and all(isinstance(row, dict) and nonempty_text(row.get("headline")) for row in rows),
                f"{label}: the reviewed company view requires three visible nonempty row headlines")
        require(len({row["headline"] for row in rows}) == len(rows),
                f"{label}: company row headlines are duplicated")
        groups = ui_state.get("expanded_groups")
        require(isinstance(groups, list) and bool(groups), f"{label}: no expanded reporting group observed")
        group_summaries = []
        for group in groups:
            require(isinstance(group, dict), f"{label}: malformed expanded group observation")
            members, links = group.get("members"), group.get("source_links")
            require(type(members) is int and members >= 2 and isinstance(links, list)
                    and len(links) == members,
                    f"{label}: expanded members must match at least two observed source links")
            hrefs, hosts = set(), set()
            for link in links:
                require(isinstance(link, dict) and nonempty_text(link.get("title"))
                        and nonempty_text(link.get("href")), f"{label}: source link identity is incomplete")
                parsed = urlsplit(link["href"])
                require(parsed.scheme in ("http", "https") and bool(parsed.hostname)
                        and not parsed.username and not parsed.password,
                        f"{label}: source link is not an observed HTTP(S) destination")
                hrefs.add(link["href"])
                hosts.add(parsed.hostname)
            require(len(hrefs) == members, f"{label}: expanded source links are duplicated")
            group_summaries.append({"members": members, "source_link_count": len(hrefs),
                                    "source_link_hosts": sorted(hosts)})
        summary.update({"visible_row_count": len(rows), "buffered_group_count": pending_count,
                        "expanded_groups": group_summaries, "visible_dialog": "ndCompany"})
    elif force == "story_warning":
        for field in ("warning_visible", "story_modal", "close_focus", "close_focus_visible"):
            require(ui_state.get(field) is True, f"{label}: required story state {field} was not observed")
        require(nonempty_text(ui_state.get("warning_text")), f"{label}: visible warning text is missing")
        check_rect(ui_state.get("story_rect"), viewport, label)
        summary.update({"warning_visible": True, "story_modal": True, "close_focus_visible": True})
    else:
        raise InvalidEvidence(f"{label}: no additional UI state verifier for {force!r}")
    return summary


def read_capture(path: Path, not_before: datetime | None) -> tuple:
    raw, metadata_bytes = load_object(path)
    requested, observed, image = (raw.get(k) for k in ("requested", "observed", "image"))
    require(all(isinstance(x, dict) for x in (requested, observed, image)),
            f"{path.name}: requested/observed/image objects are required")
    name = path.name.removesuffix(".capture.json")
    require(requested.get("name") == name, f"{path.name}: capture name differs from filename")
    viewport, locale, theme = (requested.get(k) for k in ("viewport", "locale", "theme"))
    require(viewport in VIEWPORTS and locale in LOCALES and theme in THEMES,
            f"{name}: unsupported viewport/locale/theme")
    require(requested.get("access") == "anonymous", f"{name}: this package is anonymous only")
    width, height = VIEWPORTS[viewport]
    for key, expected in (("viewport_width", width), ("viewport_height", height)):
        require(type(requested.get(key)) is int and requested[key] == expected,
                f"{name}: requested {key} differs from the canonical viewport")
        require(type(observed.get(key)) is int and observed[key] == expected,
                f"{name}: observed {key} differs from the requested viewport")
    require(observed.get("applied_theme") == theme and observed.get("applied_locale") == locale,
            f"{name}: observed theme/locale mismatch")
    captured_at = timestamp(observed.get("captured_at"), name)
    if not_before is not None:
        require(captured_at >= not_before, f"{name}: capture predates --not-before")
    url = observed.get("url")
    require(isinstance(url, str), f"{name}: observed URL is missing")
    parsed = urlsplit(url)
    require(parsed.scheme in ("http", "https") and bool(parsed.hostname)
            and not parsed.username and not parsed.password, f"{name}: invalid observed URL")

    force = requested.get("force_state")
    state = {
        "viewport": viewport, "locale": locale, "theme": theme, "access": "anonymous",
        "viewport_width": width, "viewport_height": height, "force_state": force,
        "captured": True, "applied_theme": observed["applied_theme"],
        "applied_locale": observed["applied_locale"],
        "capture_tool_module_sha256": ADAPTER_SHA256,
    }
    if force is None:
        require(requested.get("kind") in (None, ""), f"{name}: rest cell declares an interaction")
    else:
        require(force in FORCES, f"{name}: undeclared force state {force!r}")
        kind, selector = FORCES[force]
        require(requested.get("kind") == kind and requested.get("selector") == selector,
                f"{name}: interaction differs from the capture plan")
        require(observed.get("target_present") is True, f"{name}: interaction target absent")
        require(observed.get(f"{kind}_applied") is True, f"{name}: {kind} did not apply")
        if kind == "focus":
            require(observed.get("focus_visible") is True, f"{name}: visible keyboard focus absent")
        state["applied_force_state"] = force
    recorded_tool = raw.get("capture_tool_module_sha256", ADAPTER_SHA256)
    require(recorded_tool == ADAPTER_SHA256,
            f"{name}: mixed adapter revision requires explicit provenance review")

    png_path = package_file(image.get("file"), name)
    png = png_path.read_bytes()
    require(len(png) >= 33 and png[:8] == b"\x89PNG\r\n\x1a\n"
            and png[12:16] == b"IHDR", f"{name}: invalid PNG header")
    png_width, png_height = struct.unpack(">II", png[16:24])
    require(png_width > 0 and png_height > 0, f"{name}: invalid PNG dimensions")
    for key, value in (("sha256", digest(png)), ("bytes", len(png)),
                       ("width", png_width), ("height", png_height)):
        require(image.get(key) == value, f"{name}: recorded PNG {key} mismatch")
        state[key] = value
    state["file"] = png_path.relative_to(PACKAGE).as_posix()
    native = raw.get("native_screenshot")
    require(isinstance(native, dict), f"{name}: native screenshot provenance missing")
    require(native.get("format") == "JPEG" and native.get("pixel_preserving_png_reencode") is True,
            f"{name}: unexpected native-to-PNG provenance; review the actual conversion")
    require(isinstance(native.get("sha256"), str) and SHA256_RE.fullmatch(native["sha256"])
            and type(native.get("bytes")) is int and native["bytes"] > 0,
            f"{name}: native screenshot identity is incomplete")

    record = {
        "capture_metadata": path.name, "capture_metadata_sha256": digest(metadata_bytes),
        "captured_at": observed["captured_at"], "url": url,
        "native_screenshot": native,
    }
    inputs = [(path, digest(metadata_bytes)), (png_path, digest(png))]
    companion = PACKAGE / f"{name}.state.json"
    if force in ("company_buffered", "story_warning"):
        require(companion.is_file(), f"{name}: additional UI view requires {companion.name}")
    if companion.is_file():
        ui_state, companion_bytes = load_object(companion)
        require(bool(ui_state), f"{companion.name}: empty UI observation")
        record.update({"state_evidence": companion.name, "state_evidence_sha256": digest(companion_bytes)})
        inputs.append((companion, digest(companion_bytes)))
        if force in ("company_buffered", "story_warning"):
            record["checked_ui_observation"] = check_ui_state(
                ui_state, observed, force, viewport, captured_at, companion.name)
    if force == "company_buffered":
        require(observed.get("visible_dialog") == "ndCompany"
                and observed.get("company_update_visible") is True,
                f"{name}: company dialog or buffered-arrivals control was not observed")
    if force == "story_warning":
        require(observed.get("visible_dialog") is None,
                f"{name}: another native dialog obscured the story view")
    return (viewport, locale, theme, force), state, record, observed, captured_at, inputs


def expected_cells() -> set[tuple]:
    rest = {(v, l, t, None) for v in VIEWPORTS for l in LOCALES for t in THEMES}
    interactions = {("desktop", "en", t, f) for t in THEMES for f in ("news_hover", "news_focus")}
    return rest | interactions | EXTRA_CELLS


def assemble(args: argparse.Namespace) -> tuple[dict, str, list]:
    require(ADAPTER.is_file() and digest(ADAPTER.read_bytes()) == ADAPTER_SHA256,
            "capture-browser.js differs from the actual v1 capture adapter; do not relabel older captures")
    not_before = timestamp(args.not_before, "--not-before") if args.not_before else None
    paths = sorted(PACKAGE.glob("*.capture.json"))
    require(bool(paths), "no actual *.capture.json records found")
    captures, seen, failures, inputs = [], set(), [], [(ADAPTER, ADAPTER_SHA256)]
    for path in paths:
        try:
            captured = read_capture(path, not_before)
            key = captured[0]
            require(key not in seen, f"{path.name}: duplicate canonical state {key}")
            require(key in expected_cells(), f"{path.name}: capture is outside this reviewed 14-cell plan")
            seen.add(key)
            captures.append(captured)
            inputs.extend(captured[5])
        except (InvalidEvidence, OSError) as exc:
            failures.append(str(exc))
    for key in sorted(expected_cells() - seen, key=str):
        failures.append(f"missing captured state: {key}")
    require(not failures, "\n".join(failures))
    def origin(capture: tuple) -> str:
        parsed = urlsplit(capture[3]["url"])
        return f"{parsed.scheme}://{parsed.netloc}"

    origins = sorted({origin(capture) for capture in captures})
    primary_origin = origin(min(captures, key=lambda capture: capture[4]))
    require(all(urlsplit(c[3]["url"]).path == args.route for c in captures),
            "observed capture path differs from --route")
    captures.sort(key=lambda c: (c[0][0] != "desktop", c[0][1], c[0][2], c[0][3] or ""))
    states = [c[1] for c in captures]
    metrics = {key: None for key in METRIC_KEYS}
    metrics.update({"screenshot_completion": 1.0, "measured_in": None, "by_viewport": {}})
    for viewport in VIEWPORTS:
        rest = next(c for c in captures if c[0][0] == viewport and c[0][3] is None)
        observed = rest[3]
        document_width = observed.get("document_width")
        overflow = document_width > observed["viewport_width"] if isinstance(document_width, (int, float)) else None
        metrics["by_viewport"][viewport] = {
            "document_height_px": observed.get("document_height_px"),
            "horizontal_overflow": overflow, "elements_wider_than_viewport": None,
        }
    gaps = [{"dimension": "access", "value": level, "captured": False,
             "reason": "Authenticated access states are outside this anonymous capture package."}
            for level in ("free", "essential", "pro")]
    gaps.extend({"dimension": "measurement", "value": field, "captured": False,
                 "reason": "The Browser capture adapter did not collect this metric; no zero/error-free claim is made."}
                for field in ("console_errors", "failed_responses", "request_count", "payload_bytes_total"))
    gaps.extend({"dimension": "force_state", "value": force, "viewport": viewport,
                 "locale": locale, "theme": theme, "captured": False,
                 "reason": "This optional desktop company view was not accepted. The release owner reported preview group-request timeouts and UI clearing during capture attempts. No accepted PNG exists; the view is excluded from captured states and totals."}
                for viewport, locale, theme, force in UNACCEPTED_OPTIONAL_CELLS)
    page = {
        "page_id": args.page_id or args.route.strip("/").replace("/", "_") or "root",
        "route": args.route, "registry_route": args.route, "route_kind": "explicit_override",
        "states": states, "metrics": metrics, "console_errors": [], "failed_responses": [], "gaps": gaps,
    }
    if args.page_html:
        html_path = Path(args.page_html).resolve()
        html = html_path.read_bytes()
        page["page_tree_sha"] = hashlib.sha1(b"blob " + str(len(html)).encode() + b"\0" + html).hexdigest()
        inputs.append((html_path, digest(html)))
    force_states = [{"name": name, "kind": kind, "value": selector,
                     "attribute": None, "spec": f"{name}:{kind}({selector})"}
                    for name, (kind, selector) in FORCES.items()]
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tool": {"module_ref": ADAPTER.relative_to(REPO_ROOT).as_posix(),
                 "version": "1", "module_sha256": ADAPTER_SHA256, "user_agent": None},
        "target": {"kind": "base_url", "base_url": primary_origin, "site_dir": None,
                   "resolved_sha_or_none": None, "resolved_gitdir_or_none": None,
                   "resolved_sha_source": "base_url records the earliest actual capture origin; all actual endpoints are listed in honesty.served_origins and each capture URL is retained. Browser URLs do not attest a repository commit or byte equality across origins. An optional page_tree_sha identifies supplied HTML bytes."},
        "axes": {"viewports": {name: list(size) for name, size in VIEWPORTS.items()},
                 "locales": list(LOCALES), "themes": list(THEMES), "access": ["anonymous"],
                 "force_states": force_states},
        "selection": {"mode": "explicit_routes", "explicit_routes": [args.route],
                      "registry": None, "registry_rows": None, "max_pages": 1, "selected": 1,
                      "priority": None, "repo": None, "note": "One explicit Browser route; registry filters were not applied."},
        "excluded": [], "outcome": "captured",
        "totals": {"pages": 1, "states_attempted": len(states), "states_captured": len(states)},
        "honesty": {
            "access": "The actual capture records declare anonymous access; authenticated tiers remain gaps.",
            "gaps": "Unmeasured metrics remain null and missing screenshots prevent assembly.",
            "authority": "Actual Browser-plugin screenshots and DOM observations were assembled into the existing v2 schema. The standalone capture_page_evidence.py CLI was not executed.",
            "force_states": "Force definitions record real hover or visible keyboard focus after normal UI interactions. Company and warning context is preserved in actual companion state observations, without synthetic DOM emulation.",
            "capture_context": args.context_note,
            "capture_plan": "The accepted package contains eight mandatory rest cells, four mandatory desktop/en hover/focus cells across both themes, and two additional mobile UI views. Two self-imposed optional desktop company views remain explicit gaps after three unsuccessful preview capture attempts reported by the release owner. Totals and screenshot_completion describe the selected final records, not all earlier preview operations. No mandatory cell or integrity requirement was removed.",
            "capture_records": [c[2] for c in captures],
            "served_origins": [{"base_url": served_origin,
                                "capture_metadata": [c[2]["capture_metadata"] for c in captures
                                                     if origin(c) == served_origin]}
                               for served_origin in origins],
            "capture_window": {"first": min(c[4] for c in captures).isoformat(),
                               "last": max(c[4] for c in captures).isoformat()},
            "screenshot_encoding": "Native JPEG identities and pixel-preserving PNG re-encoding are transcribed from native_screenshot metadata. Saved PNG digests, byte lengths and dimensions are independently checked; original JPEG bytes are not reconstructed by this assembler.",
            "measurement_scope": "No browser user-agent, console completeness, request-count or network-byte claim is inferred from screenshots. Raw companion observations remain unchanged.",
            "company_source_scope": "Company views contain illustrative records from a controlled preview. The checks establish the recorded connected UI state, visible buffered count, three visible rows and expanded source links. They do not establish production entitlements, publisher coverage, source independence, delivery latency or row stability over time. The actual observed source hosts are retained in checked_ui_observation.",
            "assembly": {"module_ref": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
                         "module_sha256": digest(Path(__file__).read_bytes())},
        },
        "pages": [page],
    }
    changed = sorted({str(relative_path(p, "--changed-path")) for p in args.changed_path})
    require(all(not any(c in p for c in "*?[]") for p in changed), "changed paths must be literal, not glob patterns")
    manifest_rel = (PACKAGE / "manifest.json").relative_to(REPO_ROOT).as_posix()
    receipt = "schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n"
    receipt += "".join(f"  - {json.dumps(path)}\n" for path in changed)
    receipt += f"manifest: {json.dumps(manifest_rel)}\n"
    return manifest, receipt, inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed-path", action="append", required=True,
                        help="Exact material path owned by this receipt; repeat for each path.")
    parser.add_argument("--route", default="/news.html")
    parser.add_argument("--page-id", help="Existing registry page ID, if known; otherwise use canonical explicit-route synthesis.")
    parser.add_argument("--page-html", help="Optional actual captured HTML file whose Git blob ID will be recorded.")
    parser.add_argument("--not-before", help="Reject captures older than this observed UTC/offset timestamp.")
    parser.add_argument("--context-note", action="append", required=True,
                        help="Factual served-page/fixture context; repeat as needed. This is provenance, not a production claim.")
    parser.add_argument("--check-only", action="store_true", help="Validate all inputs without writing manifest or receipt.")
    args = parser.parse_args()
    try:
        manifest, receipt, inputs = assemble(args)
        for path, expected in inputs:
            require(digest(path.read_bytes()) == expected, f"{path.name}: evidence changed during assembly")
        if not args.check_only:
            manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
            for name, body in (("manifest.json", manifest_bytes), ("EVIDENCE.yml", receipt.encode())):
                temporary = PACKAGE / f".{name}.assembling"
                temporary.write_bytes(body)
                temporary.replace(PACKAGE / name)
        print(json.dumps({"validated": True, "cells": manifest["totals"]["states_captured"],
                          "mandatory_cells": 12, "additional_ui_cells": 2,
                          "unaccepted_optional_ui_cells": len(UNACCEPTED_OPTIONAL_CELLS),
                          "written": [] if args.check_only else ["manifest.json", "EVIDENCE.yml"]}))
        return 0
    except (InvalidEvidence, OSError) as exc:
        print(f"Evidence assembly refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
