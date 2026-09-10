"""scripts/check_ui_visual_evidence.py — TP-0 Task 3: theme-parity evidence gate.

A material user-facing UI change (new lines in `templates/*.css`, a new inline
`<style` in a template, or a new runtime-style-injection signature in a
user-facing JS file under `templates/` or `site/`) must carry committed
dark/light visual evidence in both languages, desktop and mobile, so a human or
Opus reviewer can judge the design — not merely confirm the page opens.

THIS SCRIPT DOES NOT JUDGE TASTE. It checks two mechanical things only:

  1. Every material changed path is OWNED (listed verbatim in `changed_paths`)
     by at least one committed `EVIDENCE.yml` receipt under `mockups/refs/` or
     `mockups/evidence/`.
  2. The manifest that receipt points at is a real, existing
     ``mastermind.p0_evidence.v2`` capture (the canonical schema emitted by
     scripts/capture_page_evidence.py — see its ``entry`` dict construction),
     and every page in it carries all eight REST cells this gate requires:
     desktop/mobile x en/zh x dark/light, each genuinely captured with the
     requested theme/locale/viewport actually applied and its screenshot PNG
     present on disk. A page may ALSO carry `force_state` cells (an
     additional interaction state beyond the eight, e.g. sanctions_map's
     `theme_toggle_dark_to_light`) — those are outside the required matrix
     (never counted toward the eight), but each one still gets its own
     integrity floor: captured, PNG present on disk, sha256/byte-length match
     the recorded values, and pixel dimensions are sane. This is the same
     "is this evidence real" check as the rest cells get, not a taste
     judgment (MINOR-3).
  3. A manifest whose cells disagree on which tool captured them (a cell-level
     `capture_tool_module_sha256` differing from the manifest's top-level
     `tool.module_sha256`) must disclose every tool sha it used at the top
     level — the top-level field becomes a list once more than one tool
     revision is present (NIT-1). A page may optionally carry a
     `page_tree_sha` — the git tree/blob content address of the captured page
     bytes, which (unlike a commit sha) survives a squash merge; when present
     its shape is validated (NIT-B). This is a forward-compat field: no
     existing manifest is required to carry one.

NO SECOND EVIDENCE PLANE. This module never defines a screenshot cell, a page
identity, a capture lifecycle, or a manifest schema of its own. The ONLY new
artifact it understands is the receipt, and a receipt carries EXACTLY three
keys: ``schema`` (must equal ``mastermind.page_evidence_receipt.v1``),
``changed_paths``, and ``manifest``. An extra key on a receipt is rejected —
that is precisely how a second plane would start growing.

Material-change detection is DELIBERATELY MECHANICAL AND NARROW (three regex
shapes below). This guard fails closed, so widening it into anything resembling
a taste detector turns it into a fleet-wide block on ordinary PRs. Keep it
narrow. Do not extend this file to judge whether a design is good — CI checks
evidence existence and state identity only.

Defensive read note: on a FAILED capture, `capture_page_evidence.py` writes
only ``{"captured": False, "reason": ...}`` for that state row — every other
key (``file``, ``applied_theme``, ...) is simply absent. Every read here goes
through ``.get()``; never a direct index, or a red capture crashes the guard
instead of reporting it.

Usage::

    python3 scripts/check_ui_visual_evidence.py --diff-file /tmp/ui.diff
    git diff --unified=0 "$BASE_SHA" HEAD -- templates site | \\
        python3 scripts/check_ui_visual_evidence.py --diff-file -
    python3 scripts/check_ui_visual_evidence.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

try:
    import yaml
except ImportError:  # pragma: no cover — PyYAML is a standing repo dependency
    print("::error title=ui-visual-evidence::PyYAML is required (pip install pyyaml)", flush=True)
    raise

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# The two permitted schema literals this module understands. It never mints a
# third. See the ABSOLUTE PROHIBITION in the module docstring.
RECEIPT_SCHEMA = "mastermind.page_evidence_receipt.v1"
MANIFEST_SCHEMA = "mastermind.p0_evidence.v2"

RECEIPT_DIRS: tuple[str, ...] = ("mockups/refs", "mockups/evidence")
RECEIPT_FILENAME = "EVIDENCE.yml"

# The receipt's only permitted top-level keys. Anything else is a second
# evidence plane trying to grow inside this file and is rejected outright.
RECEIPT_ALLOWED_KEYS: frozenset[str] = frozenset({"schema", "changed_paths", "manifest"})

# capture_page_evidence.py VIEWPORTS: desktop=(1440,900), mobile=(390,844).
# `viewport_width` is the REQUESTED viewport (C1 ruling) — NOT the screenshot
# PNG's pixel `width`, which need not equal the viewport (full-page capture).
VIEWPORT_WIDTHS: dict[str, int] = {"desktop": 1440, "mobile": 390}
REQUIRED_VIEWPORTS: tuple[str, ...] = ("desktop", "mobile")
REQUIRED_LOCALES: tuple[str, ...] = ("en", "zh")
REQUIRED_THEMES: tuple[str, ...] = ("dark", "light")

# A git object sha: 40 hex chars (sha1, the default) or 64 hex chars (a sha256
# object-format repo). Used both by the mixed-tool reconciliation below and by
# the optional `page_tree_sha` forward-compat field (NIT-B).
_GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

# --- material-change detection -------------------------------------------
# Deliberately narrow. Three shapes only, matching the frozen spec exactly:
#   1. any added line in a templates/*.css file
#   2. an added inline <style in a template
#   3. an added runtime-style-injection signature in a user-facing .js file
STYLE_TAG_RE = re.compile(r"<style(?:\s|>)", re.IGNORECASE)
# Duplicates scripts/check_runtime_style_injection.py's own PATTERNS (own copy
# — this module owns no other file's constants, matching its self-contained
# convention). tests/test_check_ui_visual_evidence.py pins the two in
# agreement so a future change to the owner fails loudly instead of silently
# degrading this gate's material-change detection.
RUNTIME_STYLE_SIGNATURES: tuple[re.Pattern[str], ...] = (
    re.compile(r"createElement\(\s*['\"]style['\"]\s*\)"),
    re.compile(r"(?:style|css)\.textContent\s*="),
    # R8: broadened from `\.sheet\.insertRule\s*\(` — the canonical idiom is
    # `document.styleSheets[0].insertRule(...)`, never a literal
    # `.sheet.insertRule(`.
    re.compile(r"\.insertRule\s*\("),
    STYLE_TAG_RE,
)


# ---------------------------------------------------------------------------
# unified diff parsing (self-contained — this module owns no other file's
# parser; see the frozen build spec C2 correction this mirrors)
# ---------------------------------------------------------------------------


# C-style backslash escapes git uses inside a quoted diff path (see
# `quote.c`'s `quote_c_style`). Octal (`\NNN`) escapes are handled separately
# below since they encode raw BYTES of a UTF-8 sequence, not one escape per
# character. This module owns its own copy — see the module docstring's
# "self-contained" note; it does not import check_design_system.py's copy.
_GIT_QUOTE_ESCAPES: dict[str, int] = {
    "n": 0x0A, "t": 0x09, "a": 0x07, "b": 0x08, "f": 0x0C, "r": 0x0D, "v": 0x0B,
    "\\": 0x5C, '"': 0x22,
}


def _unquote_git_diff_path(quoted: str) -> str:
    """Decode a C-style-quoted git diff path: surrounding double quotes, the
    escapes in ``_GIT_QUOTE_ESCAPES``, and octal byte escapes (``\\NNN``) for
    non-ASCII bytes (e.g. ``\\303\\251`` for ``é``). Octal escapes are raw
    BYTES of a multi-byte UTF-8 sequence, so they accumulate into one byte
    buffer and are decoded as UTF-8 once at the end, never escape-by-escape.
    """
    if len(quoted) < 2 or quoted[0] != '"' or quoted[-1] != '"':
        return quoted
    body = quoted[1:-1]
    out = bytearray()
    i, n = 0, len(body)
    while i < n:
        ch = body[i]
        if ch == "\\" and i + 1 < n:
            nxt = body[i + 1]
            if nxt in "01234567":
                j = i + 1
                digits = ""
                while j < n and body[j] in "01234567" and len(digits) < 3:
                    digits += body[j]
                    j += 1
                out.append(int(digits, 8) & 0xFF)
                i = j
                continue
            mapped = _GIT_QUOTE_ESCAPES.get(nxt)
            if mapped is not None:
                out.append(mapped)
                i += 2
                continue
            out.extend(ch.encode("utf-8"))
            i += 1
            continue
        out.extend(ch.encode("utf-8"))
        i += 1
    return out.decode("utf-8", errors="replace")


def _normalize_diff_header_path(candidate: str) -> str:
    """Normalize the text after a ``+++ `` diff header marker (R1).

    Git appends a literal TAB after the path when the path contains a space
    — strip everything from the first TAB onward FIRST, because a
    quoted-AND-spaced path carries both the quotes and the trailing tab. Then,
    if what remains is wrapped in double quotes (git quotes any path with a
    space, control char, or non-ASCII byte), unquote it. Finally strip a
    leading ``a/``/``b/`` prefix. ``/dev/null`` passes through unchanged —
    the caller treats that literal as "no path" (pure deletion).
    """
    tab = candidate.find("\t")
    if tab != -1:
        candidate = candidate[:tab]
    if len(candidate) >= 2 and candidate[0] == '"' and candidate[-1] == '"':
        candidate = _unquote_git_diff_path(candidate)
    if candidate[:2] in ("a/", "b/"):
        candidate = candidate[2:]
    return candidate


def parse_added_lines(diff_text: str) -> dict[str, list[str]]:
    """Map each touched file to the literal content of its added lines.

    Self-contained unified-diff reader. Skips ``\\ No newline at end of file``
    (not a real line — counting it desyncs nothing here since we track content,
    not line numbers, but the marker must still never be treated as a path
    header or added content). Treats only a ``+++ `` line (with the trailing
    space, distinguishing the file header from a content line that happens to
    start with literal ``+++``) as introducing a new current path.

    The header text is run through ``_normalize_diff_header_path`` (R1) before
    use: git appends a literal TAB when the path contains a space, and quotes
    (with C-style/octal escapes) a path with a non-ASCII or control byte —
    naively testing ``header.startswith("b/")`` misses both (the tab rides
    along in the first case; the leading quote character defeats the test
    entirely in the second, silently setting ``path = None`` on a real path).
    """

    out: dict[str, list[str]] = {}
    path: str | None = None
    for raw in diff_text.splitlines():
        if raw.startswith("\\"):
            continue
        if raw.startswith("+++ "):
            header = _normalize_diff_header_path(raw[len("+++ "):])
            if header == "/dev/null":
                path = None  # pure deletion
            else:
                path = header
                out.setdefault(path, [])
            continue
        if raw.startswith("--- ") or raw.startswith("diff --git "):
            continue
        if path is None:
            continue
        if raw.startswith("+"):
            out[path].append(raw[1:])
    return out


def material_paths(added_lines: dict[str, list[str]]) -> set[str]:
    """Which touched paths carry a mechanically material UI change."""

    material: set[str] = set()
    for path, lines in added_lines.items():
        if not lines:
            continue
        if _is_material_css(path, lines):
            material.add(path)
        elif _is_material_inline_style(path, lines):
            material.add(path)
        elif _is_material_runtime_js(path, lines):
            material.add(path)
    return material


def _css_added_lines_have_substance(lines: list[str]) -> bool:
    """True when a file's ADDED CSS lines, walked IN ORDER, carry something
    that can change pixels (R4: a per-file state machine, not a line-local
    heuristic).

    This gate FAILS CLOSED on a material change, so "any added line in a
    templates CSS file is material" would demand a full eight-cell dual-theme
    evidence matrix for adding a comment or a blank line — a fleet-wide block on
    ordinary work, and the fastest way to get the whole guard disabled. A
    comment or blank line cannot change a rendered pixel, so it is not material.

    A LINE-LOCAL heuristic gets two shapes wrong, both against files that span
    multiple added lines:
      * ``* { margin: 0 }`` / ``*, *::before { box-sizing: border-box }`` — a
        universal-selector rule is real CSS, not a comment continuation, just
        because it happens to start with ``*`` (FALSE NEGATIVE: a global reset
        is exactly a pixel-changing change that must not be waved through).
      * a genuine ``/* ... */`` block comment split across several added
        lines — e.g. an unprefixed continuation line with no leading ``*`` at
        all — is comment on every line, not just the ones that look like it
        (FALSE POSITIVE: judging each line in isolation counts the comment's
        prose as CSS substance the moment it does not start with ``*``).

    So this walks ``lines`` in order carrying one ``in_comment`` flag: while
    inside a comment, everything up to the next ``*/`` is comment and only
    what follows it (on that same line) is live text; while outside, complete
    ``/* ... */`` spans are stripped and an unterminated ``/*`` opens the
    comment and truncates the rest of that line. There is no
    ``startswith("*")`` special case at all — the state machine's own
    open/close tracking is what makes ``* { margin: 0 }`` register as
    substance and a true continuation line (opened by a ``/*`` earlier in the
    SAME added-lines list) register as comment. A stray, locally-unopened
    ``*``/``*/`` line (the diff shows only a mid-comment fragment because the
    real opener is unchanged context outside this hunk) is therefore read as
    live text — genuinely ambiguous without seeing the whole file, and this
    gate resolves ambiguity toward MATERIAL, its documented fail-closed
    direction, never toward silently skipping evidence.
    """
    in_comment = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        text_parts: list[str] = []
        pos = 0
        n = len(stripped)
        while pos < n:
            if in_comment:
                end = stripped.find("*/", pos)
                if end == -1:
                    pos = n  # rest of the line is still comment
                else:
                    in_comment = False
                    pos = end + 2
                continue
            start = stripped.find("/*", pos)
            if start == -1:
                text_parts.append(stripped[pos:])
                pos = n
            else:
                text_parts.append(stripped[pos:start])
                end = stripped.find("*/", start + 2)
                if end == -1:
                    in_comment = True
                    pos = n  # unterminated: truncate the rest of this line
                else:
                    pos = end + 2
        if "".join(text_parts).strip():
            return True
    return False


def _is_material_css(path: str, lines: list[str]) -> bool:
    if not (path.startswith("templates/") and path.endswith(".css")):
        return False
    return _css_added_lines_have_substance(lines)


def _is_material_inline_style(path: str, lines: list[str]) -> bool:
    if not path.startswith("templates/"):
        return False
    return any(STYLE_TAG_RE.search(line) for line in lines)


def _is_material_runtime_js(path: str, lines: list[str]) -> bool:
    if not path.endswith(".js"):
        return False
    if not (path.startswith("templates/") or path.startswith("site/")):
        return False
    return any(sig.search(line) for line in lines for sig in RUNTIME_STYLE_SIGNATURES)


# ---------------------------------------------------------------------------
# receipt discovery + shape validation
# ---------------------------------------------------------------------------


class ReceiptRecord(NamedTuple):
    path: Path
    data: dict[str, Any] | None
    error: str | None


def _sparse_refusal(repo_root: Path) -> str | None:
    """The remedy line when this checkout cannot see ``mockups/`` at all (R9).

    Own copy — this module owns no other file's helper, matching the
    self-contained-diff-parsing convention above — but the same shape as
    ``scripts/check_runtime_style_injection.py``'s own ``_sparse_refusal``. In
    a sparse session worktree (policy R8) ``mockups/`` can be entirely
    omitted; without this check, ``discover_receipts`` would silently find
    ZERO receipts and every material change would report "no committed
    EVIDENCE.yml receipt owning it" — a FALSE RED over a tree this checkout
    was never asked to answer for, not a genuine missing-evidence finding.

    ``mockups/evidence/`` itself not existing in git YET is a separate,
    expected, normal state (a subdirectory that has simply never been
    created) — ``discover_receipts`` already handles that without crashing.
    This function only fires when ``mockups`` (the whole top-level tracked
    directory) is sparse-omitted, never on that narrower, expected absence.
    """
    try:
        from scripts.worktree_sparse import missing_dirs, remedy_line
    except Exception:  # noqa: BLE001 — never let the detector break the guard
        return None
    try:
        absent = [d for d in missing_dirs(repo_root) if d == "mockups"]
    except Exception:  # noqa: BLE001
        return None
    return remedy_line(absent) if absent else None


def discover_receipts(repo_root: Path) -> list[ReceiptRecord]:
    """Every ``EVIDENCE.yml`` under the two receipt dirs.

    Handles a missing ``mockups/evidence/`` (it does not exist in git yet)
    without crashing — that is the expected state, not an error.
    """

    records: list[ReceiptRecord] = []
    for rel_dir in RECEIPT_DIRS:
        base = repo_root / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob(RECEIPT_FILENAME)):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                records.append(ReceiptRecord(path, None, f"could not read: {exc}"))
                continue
            try:
                loaded = yaml.safe_load(text)
            except yaml.YAMLError as exc:
                records.append(ReceiptRecord(path, None, f"invalid YAML: {exc}"))
                continue
            if not isinstance(loaded, dict):
                records.append(ReceiptRecord(path, None, "top-level YAML must be a mapping"))
                continue
            records.append(ReceiptRecord(path, loaded, None))
    return records


def validate_receipt_shape(record: ReceiptRecord) -> list[str]:
    """Enforce the exactly-three-keys receipt contract. Never redefine cells."""

    assert record.data is not None
    data = record.data
    keys = set(data.keys())
    errors: list[str] = []
    extra = keys - RECEIPT_ALLOWED_KEYS
    missing = RECEIPT_ALLOWED_KEYS - keys
    if extra:
        errors.append(
            f"{record.path}: receipt carries unexpected key(s) {sorted(extra)} — "
            f"only {sorted(RECEIPT_ALLOWED_KEYS)} are permitted "
            "(a receipt maps changed paths to an existing manifest; it never "
            "redefines screenshot cells, provenance, or capture semantics)"
        )
    if missing:
        errors.append(f"{record.path}: receipt missing required key(s) {sorted(missing)}")
        return errors  # further checks would just re-report the same absence
    schema = data.get("schema")
    if schema != RECEIPT_SCHEMA:
        errors.append(f"{record.path}: receipt schema must be {RECEIPT_SCHEMA!r}, got {schema!r}")
    if not isinstance(data.get("changed_paths"), list):
        errors.append(f"{record.path}: changed_paths must be a list of path strings")
    if not isinstance(data.get("manifest"), str):
        errors.append(f"{record.path}: manifest must be a string path")
    return errors


def owners_for(changed_path: str, records: list[ReceiptRecord]) -> list[ReceiptRecord]:
    """Receipts whose ``changed_paths`` literally lists the exact path."""

    owners = []
    for record in records:
        if record.data is None:
            continue
        changed = record.data.get("changed_paths")
        if isinstance(changed, list) and changed_path in changed:
            owners.append(record)
    return owners


# ---------------------------------------------------------------------------
# manifest + rest-cell validation
# ---------------------------------------------------------------------------


def validate_manifest_evidence(record: ReceiptRecord, repo_root: Path) -> list[str]:
    assert record.data is not None
    manifest_rel = record.data.get("manifest")
    if not isinstance(manifest_rel, str):
        return [f"{record.path}: manifest must be a string path"]

    manifest_path = (repo_root / manifest_rel).resolve()
    if not manifest_path.exists():
        return [f"{record.path}: referenced manifest '{manifest_rel}' does not exist"]

    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_text)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{record.path}: referenced manifest '{manifest_rel}' could not be read/parsed: {exc}"]

    if not isinstance(manifest, dict):
        return [f"{record.path}: manifest '{manifest_rel}' top level must be an object"]

    schema = manifest.get("schema")
    if schema != MANIFEST_SCHEMA:
        return [
            f"{record.path}: manifest '{manifest_rel}' schema must be {MANIFEST_SCHEMA!r}, "
            f"got {schema!r}"
        ]

    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        return [f"{record.path}: manifest '{manifest_rel}' carries no pages"]

    findings: list[str] = []
    findings.extend(_validate_tool_hash_coverage(record.path, manifest_rel, manifest))
    for page in pages:
        findings.extend(_validate_page_cells(record.path, manifest_path, manifest_rel, page))
    return findings


def _validate_tool_hash_coverage(receipt_path: Path, manifest_rel: str,
                                  manifest: dict[str, Any]) -> list[str]:
    """NIT-1: a manifest whose cells were captured by more than one tool
    revision must disclose EVERY tool sha at the top level, not just the one
    recorded when the manifest was first created.

    A capture row may carry its own ``capture_tool_module_sha256`` (the tool
    that actually produced THAT screenshot) alongside the manifest-level
    ``tool.module_sha256`` (the tool as of the manifest's own header). When a
    manifest is re-captured incrementally — some cells refreshed under a
    newer tool revision, others left from an earlier capture — those two can
    silently disagree: the top-level field reads as one tool, but the truth
    is split cell-by-cell. That is a MIXED-TOOL manifest, and the disagreement
    must be visible at the top level (where a human skims first), not only by
    reading every cell. The fix is not to demand a single tool — repeated
    incremental capture is normal — but to require the top-level field become
    a LIST that covers every cell-level value once more than one is present.
    """
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        return []
    cell_shas: set[str] = set()
    for page in pages:
        if not isinstance(page, dict):
            continue
        states = page.get("states")
        if not isinstance(states, list):
            continue
        for state in states:
            if not isinstance(state, dict):
                continue
            sha = state.get("capture_tool_module_sha256")
            if isinstance(sha, str) and sha:
                cell_shas.add(sha)
    if not cell_shas:
        return []  # no per-cell tool identity recorded; nothing to reconcile

    tool = manifest.get("tool")
    top_sha = tool.get("module_sha256") if isinstance(tool, dict) else None

    if isinstance(top_sha, list):
        top_set = {s for s in top_sha if isinstance(s, str)}
        missing = sorted(cell_shas - top_set)
        if missing:
            return [
                f"{receipt_path}: manifest '{manifest_rel}' top-level tool.module_sha256 list "
                f"does not cover cell-level capture_tool_module_sha256 value(s) {missing} "
                "(a mixed-tool manifest's top-level field must list every tool sha used by any cell)"
            ]
        return []

    if isinstance(top_sha, str) and top_sha:
        extra = sorted(cell_shas - {top_sha})
        if extra:
            return [
                f"{receipt_path}: manifest '{manifest_rel}' is a mixed-tool manifest — cell-level "
                f"capture_tool_module_sha256 value(s) {extra} disagree with the single top-level "
                f"tool.module_sha256 {top_sha!r}; top-level tool.module_sha256 must be a list "
                "covering every cell-level value"
            ]
        return []

    return [
        f"{receipt_path}: manifest '{manifest_rel}' carries cell-level capture_tool_module_sha256 "
        f"value(s) {sorted(cell_shas)} but top-level tool.module_sha256 is missing/invalid "
        f"({top_sha!r})"
    ]


def _rest_cell_key(state: dict[str, Any]) -> tuple[Any, Any, Any] | None:
    if not isinstance(state, dict):
        return None
    if state.get("force_state") is not None:
        return None
    return (state.get("viewport"), state.get("locale"), state.get("theme"))


def _validate_page_cells(receipt_path: Path, manifest_path: Path, manifest_rel: str,
                          page: Any) -> list[str]:
    if not isinstance(page, dict):
        return [f"{receipt_path}: manifest '{manifest_rel}' carries a non-object page entry"]

    page_id = page.get("page_id", "<unknown-page>")
    states = page.get("states")
    if not isinstance(states, list):
        return [f"{receipt_path}: page '{page_id}' in '{manifest_rel}' has no states list"]

    rest_cells: dict[tuple[Any, Any, Any], dict[str, Any]] = {}
    force_state_cells: list[dict[str, Any]] = []
    for state in states:
        if not isinstance(state, dict):
            continue
        key = _rest_cell_key(state)
        if key is not None:
            rest_cells[key] = state
        elif state.get("force_state") is not None:
            force_state_cells.append(state)

    findings: list[str] = []
    for viewport in REQUIRED_VIEWPORTS:
        for locale in REQUIRED_LOCALES:
            for theme in REQUIRED_THEMES:
                findings.extend(
                    _validate_one_cell(receipt_path, manifest_path, manifest_rel, page_id,
                                        viewport, locale, theme, rest_cells.get((viewport, locale, theme)))
                )
    for state in force_state_cells:
        findings.extend(
            _validate_force_state_cell(receipt_path, manifest_path, manifest_rel, page_id, state)
        )
    findings.extend(
        _validate_optional_page_tree_sha(receipt_path, manifest_rel, page_id, page.get("page_tree_sha"))
    )
    return findings


def _validate_force_state_cell(receipt_path: Path, manifest_path: Path, manifest_rel: str,
                                page_id: Any, state: dict[str, Any]) -> list[str]:
    """MINOR-3: `_rest_cell_key` deliberately excludes a `force_state` cell
    (e.g. sanctions_map's `theme_toggle_dark_to_light`) from the REQUIRED
    viewport x locale x theme matrix — a force_state cell documents an
    additional, non-required interaction state, not one of the eight rest
    cells the gate demands on every page. That exclusion was previously total:
    a force_state cell received NO validation at all, so a corrupted or
    hand-edited force_state row (wrong sha, truncated PNG, deleted file)
    passed silently. This checks the same integrity floor a rest cell gets:
    captured, the PNG actually exists, its bytes match the recorded sha256
    and byte length, and its recorded pixel dimensions are sane (present,
    positive integers) — not a taste judgment, just "is this evidence real".
    """
    label = f"{page_id} force_state={state.get('force_state')!r}"
    findings: list[str] = []

    if state.get("captured") is not True:
        reason = state.get("reason", "not captured")
        findings.append(f"{receipt_path}: {label} was not captured ({reason})")
        return findings

    file_rel = state.get("file")
    if not file_rel:
        findings.append(f"{receipt_path}: {label} has no screenshot file recorded")
        return findings

    png_path = manifest_path.parent / file_rel
    if not png_path.exists():
        findings.append(
            f"{receipt_path}: {label} references screenshot '{file_rel}' which does not "
            f"exist at {png_path}"
        )
        return findings

    try:
        actual_bytes = png_path.read_bytes()
    except OSError as exc:
        findings.append(f"{receipt_path}: {label} screenshot '{file_rel}' could not be read: {exc}")
        return findings

    recorded_sha256 = state.get("sha256")
    actual_sha256 = hashlib.sha256(actual_bytes).hexdigest()
    if recorded_sha256 != actual_sha256:
        findings.append(
            f"{receipt_path}: {label} sha256={recorded_sha256!r} does not match the "
            f"screenshot's actual sha256 {actual_sha256!r}"
        )

    recorded_bytes = state.get("bytes")
    actual_byte_length = len(actual_bytes)
    if recorded_bytes != actual_byte_length:
        findings.append(
            f"{receipt_path}: {label} bytes={recorded_bytes!r} does not match the "
            f"screenshot's actual byte length {actual_byte_length}"
        )

    width = state.get("width")
    height = state.get("height")
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0 \
            or not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        findings.append(
            f"{receipt_path}: {label} has non-sane captured PNG pixel dimensions "
            f"(width={width!r}, height={height!r})"
        )

    return findings


def _validate_optional_page_tree_sha(receipt_path: Path, manifest_rel: str, page_id: Any,
                                      page_tree_sha: Any) -> list[str]:
    """NIT-B: capture manifests currently record only commit shas
    (``updated_sha`` / ``captured_sha``), which go unreachable once the
    branch that produced them is squash-merged — the manifest still names a
    sha, but `git show <sha>` can no longer resolve it. A git TREE/BLOB sha
    (the content address of the page bytes at capture time) stays reachable
    as long as the blob is referenced by ANY commit, squashed or not.

    This is forward-compat only: no existing manifest carries `page_tree_sha`
    yet (NIT-B explicitly forbids rewriting historical manifests beyond the
    NIT-1 metadata fix), so absence is never a finding. When a future capture
    DOES record one, this validates only its SHAPE — a 40- or 64-char
    lowercase hex git object id — catching a malformed value instead of
    silently accepting whatever a writer puts there.
    """
    if page_tree_sha is None:
        return []
    if not isinstance(page_tree_sha, str) or not _GIT_SHA_RE.match(page_tree_sha):
        return [
            f"{receipt_path}: manifest '{manifest_rel}' page '{page_id}' carries a malformed "
            f"page_tree_sha {page_tree_sha!r} (expected a 40- or 64-char lowercase hex git object sha)"
        ]
    return []


def _validate_one_cell(receipt_path: Path, manifest_path: Path, manifest_rel: str, page_id: Any,
                        viewport: str, locale: str, theme: str,
                        state: dict[str, Any] | None) -> list[str]:
    label = f"{page_id} {viewport}/{locale}/{theme}"
    if state is None:
        return [
            f"{receipt_path}: manifest '{manifest_rel}' page '{page_id}' is missing the "
            f"required rest cell {viewport}/{locale}/{theme}"
        ]

    findings: list[str] = []

    # Defensive .get() throughout: a FAILED capture row carries only
    # {"captured": False, "reason": ...} — every other key is absent.
    if state.get("captured") is not True:
        reason = state.get("reason", "not captured")
        findings.append(f"{receipt_path}: {label} was not captured ({reason})")
        return findings  # nothing else on a failed row is trustworthy to check

    if state.get("applied_theme") != theme:
        findings.append(
            f"{receipt_path}: {label} applied_theme={state.get('applied_theme')!r} "
            f"does not match the requested theme {theme!r}"
        )
    if state.get("applied_locale") != locale:
        findings.append(
            f"{receipt_path}: {label} applied_locale={state.get('applied_locale')!r} "
            f"does not match the requested locale {locale!r}"
        )

    expected_width = VIEWPORT_WIDTHS[viewport]
    if state.get("viewport_width") != expected_width:
        findings.append(
            f"{receipt_path}: {label} viewport_width={state.get('viewport_width')!r}, "
            f"expected {expected_width} (the REQUESTED viewport, not the PNG's pixel width)"
        )

    # Capture-integrity check (spec-permitted, not the identity assertion).
    if state.get("width") is None or state.get("height") is None:
        findings.append(f"{receipt_path}: {label} is missing captured PNG pixel dimensions (width/height)")

    file_rel = state.get("file")
    if not file_rel:
        findings.append(f"{receipt_path}: {label} has no screenshot file recorded")
    else:
        png_path = manifest_path.parent / file_rel
        if not png_path.exists():
            findings.append(
                f"{receipt_path}: {label} references screenshot '{file_rel}' which does not "
                f"exist at {png_path}"
            )

    return findings


# ---------------------------------------------------------------------------
# top-level evaluation
# ---------------------------------------------------------------------------


def evaluate(diff_text: str, repo_root: Path) -> list[str]:
    """Return the (deduped, order-preserving) list of red findings. Empty = pass."""

    added = parse_added_lines(diff_text)
    material = material_paths(added)
    if not material:
        return []

    # R9: refuse rather than false-red when this checkout cannot see
    # mockups/ at all (a sparse worktree). Scoped to the material-change
    # branch only — a non-material diff never touches mockups/ anyway, so a
    # sparse checkout must not refuse work that would have passed regardless.
    refusal = _sparse_refusal(repo_root)
    if refusal:
        return [f"ui-visual-evidence guard REFUSED: {refusal}"]

    records = discover_receipts(repo_root)
    findings: list[str] = []

    for changed_path in sorted(material):
        owners = owners_for(changed_path, records)
        if not owners:
            findings.append(
                f"material UI change '{changed_path}' has no committed EVIDENCE.yml receipt "
                f"owning it in changed_paths (searched {', '.join(RECEIPT_DIRS)})"
            )
            continue
        for record in owners:
            shape_errors = validate_receipt_shape(record)
            if shape_errors:
                findings.extend(shape_errors)
                continue
            findings.extend(validate_manifest_evidence(record, repo_root))

    seen: set[str] = set()
    deduped: list[str] = []
    for finding in findings:
        if finding not in seen:
            seen.add(finding)
            deduped.append(finding)
    return deduped


# ---------------------------------------------------------------------------
# --selftest — exercises the gate end-to-end on planted fixtures
# ---------------------------------------------------------------------------


def _selftest_state(viewport: str, locale: str, theme: str, *, captured: bool = True,
                     file: str = "shot.png", applied_theme: str | None = None,
                     applied_locale: str | None = None, viewport_width: int | None = None,
                     width: int | None = 1440, height: int | None = 900) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "viewport": viewport,
        "locale": locale,
        "theme": theme,
        "access": "anonymous",
        "viewport_width": VIEWPORT_WIDTHS[viewport] if viewport_width is None else viewport_width,
        "viewport_height": 900 if viewport == "desktop" else 844,
        "force_state": None,
    }
    if not captured:
        entry.update({"captured": False, "reason": "page did not load"})
        return entry
    entry.update({
        "captured": True,
        "file": file,
        "sha256": "a" * 64,
        "bytes": 999,
        "width": width,
        "height": height,
        "applied_theme": theme if applied_theme is None else applied_theme,
        "applied_locale": locale if applied_locale is None else applied_locale,
    })
    return entry


def _selftest_full_states() -> list[dict[str, Any]]:
    return [
        _selftest_state(viewport, locale, theme)
        for viewport in REQUIRED_VIEWPORTS
        for locale in REQUIRED_LOCALES
        for theme in REQUIRED_THEMES
    ]


def _selftest_write(root: Path, states: list[dict[str, Any]]) -> None:
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "pages": [{
            "page_id": "macro:selftest_page",
            "route": "/selftest.html",
            "states": states,
            "gaps": [],
        }],
    }
    manifest_dir = root / "mockups" / "evidence" / "selftest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for state in states:
        if state.get("captured") and state.get("file"):
            (manifest_dir / state["file"]).write_bytes(b"\x89PNG\r\n\x1a\nselftest")
    receipt = (
        f"schema: {RECEIPT_SCHEMA}\n"
        "changed_paths:\n"
        "  - templates/selftest_gate.css\n"
        "manifest: mockups/evidence/selftest/manifest.json\n"
    )
    (manifest_dir / "EVIDENCE.yml").write_text(receipt, encoding="utf-8")


def _selftest_diff() -> str:
    return (
        "diff --git a/templates/selftest_gate.css b/templates/selftest_gate.css\n"
        "--- a/templates/selftest_gate.css\n"
        "+++ b/templates/selftest_gate.css\n"
        "@@ -1,0 +2,1 @@\n"
        "+.selftest{color:#123456}\n"
    )


def run_selftest() -> int:
    """Plant fixtures and prove the gate reds on defects and passes on complete evidence."""

    print("running check_ui_visual_evidence selftest...", flush=True)
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="ui_visual_evidence_selftest_") as tmp:
        root = Path(tmp)
        _selftest_write(root, _selftest_full_states())
        diff = _selftest_diff()

        # 1. Complete evidence must pass.
        result = evaluate(diff, root)
        if result:
            failures.append(f"complete-evidence case unexpectedly red: {result}")

        # 2. A non-material diff needs no receipt at all.
        result = evaluate(
            "diff --git a/scripts/x.py b/scripts/x.py\n--- a/scripts/x.py\n+++ b/scripts/x.py\n"
            "@@ -1,0 +2,1 @@\n+print('x')\n",
            root,
        )
        if result:
            failures.append(f"non-material diff unexpectedly red: {result}")

    # 3. Missing receipt for a material change must red.
    with tempfile.TemporaryDirectory(prefix="ui_visual_evidence_selftest_") as tmp:
        root = Path(tmp)
        result = evaluate(_selftest_diff(), root)
        if not result:
            failures.append("material change with no receipt unexpectedly passed")

    # 4. Missing one light cell must red.
    with tempfile.TemporaryDirectory(prefix="ui_visual_evidence_selftest_") as tmp:
        root = Path(tmp)
        states = [s for s in _selftest_full_states() if not (s["viewport"] == "desktop" and s["theme"] == "light")]
        _selftest_write(root, states)
        result = evaluate(_selftest_diff(), root)
        if not result:
            failures.append("missing light cell unexpectedly passed")

    # 5. A mismatched applied_theme must red.
    with tempfile.TemporaryDirectory(prefix="ui_visual_evidence_selftest_") as tmp:
        root = Path(tmp)
        states = _selftest_full_states()
        for state in states:
            if state["viewport"] == "mobile" and state["theme"] == "dark" and state["locale"] == "en":
                state["applied_theme"] = "light"
        _selftest_write(root, states)
        result = evaluate(_selftest_diff(), root)
        if not result:
            failures.append("applied_theme mismatch unexpectedly passed")

    # 6. A deleted referenced PNG must red.
    with tempfile.TemporaryDirectory(prefix="ui_visual_evidence_selftest_") as tmp:
        root = Path(tmp)
        _selftest_write(root, _selftest_full_states())
        (root / "mockups" / "evidence" / "selftest" / "shot.png").unlink()
        result = evaluate(_selftest_diff(), root)
        if not result:
            failures.append("deleted screenshot PNG unexpectedly passed")

    # 7. A failed-capture row must red without raising.
    with tempfile.TemporaryDirectory(prefix="ui_visual_evidence_selftest_") as tmp:
        root = Path(tmp)
        states = _selftest_full_states()
        states[0] = {
            "viewport": states[0]["viewport"], "locale": states[0]["locale"],
            "theme": states[0]["theme"], "access": "anonymous",
            "viewport_width": VIEWPORT_WIDTHS[states[0]["viewport"]], "viewport_height": 900,
            "force_state": None, "captured": False, "reason": "selftest failure",
        }
        try:
            _selftest_write(root, states)
            result = evaluate(_selftest_diff(), root)
        except Exception as exc:  # pragma: no cover — this is exactly what must never happen
            failures.append(f"failed-capture row raised instead of reporting: {exc!r}")
        else:
            if not result:
                failures.append("failed-capture row unexpectedly passed")

    if failures:
        for failure in failures:
            print(f"::error title=ui-visual-evidence-selftest::{failure}", flush=True)
        return 1
    print("check_ui_visual_evidence selftest OK", flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None, *, stdin_text: str | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate material UI changes on committed dark/light evidence receipts."
    )
    parser.add_argument("--diff-file", help="Unified diff path, or '-' to read stdin.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repo root receipts/manifests resolve against.")
    parser.add_argument("--selftest", action="store_true", help="Run the built-in selftest and exit.")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if not args.diff_file:
        print("::error title=ui-visual-evidence::--diff-file PATH is required (or use --selftest)", flush=True)
        return 1

    if args.diff_file == "-":
        diff_text = stdin_text if stdin_text is not None else sys.stdin.read()
    else:
        # R5: errors="replace", matching check_design_system.py's own diff
        # read — a single Latin-1 (or otherwise non-UTF-8) byte in the diff
        # must produce a finding, never an uncaught UnicodeDecodeError.
        diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")

    findings = evaluate(diff_text, Path(args.repo_root))
    if findings:
        for finding in findings:
            print(f"::error title=ui-visual-evidence::{finding}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
