#!/usr/bin/env python3
"""Gate: a P0B construction-input change must remint the browser receipts.

#7603 changed templates/hk.html.j2 without reminting
mockups/evidence/prophet-p0b-zero-fouc/mobile-layout*.json (still pinning the
prior digest), the same class as #7500 / site/navigation-refresh.css (healed
by #7597). Pure main then fails the receipt tests in
tests/test_stock_dashboard_first_frame.py, and every fresh merge-ref inherits
it. This guard is the GATE for that class.

The pinned set is derived at runtime FROM the committed receipts: each
mobile-layout*.json file's construction_inputs keys, loaded_assets keys, and
verifier.path, plus rendered-fixture.json's recipe input paths and the
fixture path the receipts bind. Template names are never hardcoded as the
live pin set.

Given a diff file-list: if any pinned path changed without a same-diff change
to every receipt that pins it, exit 1 naming the path and the remint command.
Exit 0 otherwise.

What the receipts PROVE vs what they PIN.  A receipt proves one browser run:
zero-FOUC first-frame layout, owner/degraded states and screenshots, measured
from the bytes it names.  It pins every one of those bytes, but the pins are
of two kinds.  LAYOUT-TIER pins can move what was measured: construction
inputs, the verifier, the rendered fixture and its recipe inputs, every CSS
file and font, the browser-data JSON, the composers, and every script that
writes into the page chrome or the first frame (theme, live, stocktable,
dashboard icons, the nav/account/logo scripts).  Moving one needs a browser
re-mint, and the gate keeps demanding it.  DIGEST-ONLY pins are the few
loaded scripts in REFRESHABLE_LOADED_ASSETS that have no write target in the
rendered fixture (each entry carries its reason, and
tests/test_stock_dashboard_first_frame.py re-proves the absence of every
target on each run).  #8763 (charts.js) and #8765 (tablesort.js) each spent
a full browser lane re-minting one of these digests; no layout measurement
moved in either (only the browser version and host-dependent screenshot
digests), yet each forced its siblings to merge main and re-mint again.

A digest-only change is closed without a browser by
`--refresh-digests`: it writes one sidecar per moved asset under
digest-refresh/, recording the new bytes next to the digest each receipt
actually measured.  The receipts are never edited, so they keep reporting
exactly what their browser run loaded, and the manifest digests over them do
not move.  Honest gap, kept visible in-tree: a sidecar asset's new bytes were
NOT browser-measured.  The sidecar says so (proof_class
digest_refresh_not_browser_measured), and the next browser re-mint retires it
(the gate reds a sidecar the receipts have caught up with until
--refresh-digests prunes it).  One file per asset means two sibling PRs that
touch different refreshable assets never conflict and merge in either order.
`--refresh-digests` refuses, writing nothing, while any layout-tier byte
differs from what the receipts measured.

Usage:
    python3 scripts/check_p0b_receipt_closure.py --diff-file /tmp/changed.txt
    git diff --name-only "$MB" HEAD | python3 scripts/check_p0b_receipt_closure.py --diff-file -
    python3 scripts/check_p0b_receipt_closure.py --refresh-digests
    python3 scripts/check_p0b_receipt_closure.py --selftest
Exit codes: 0 = closed / nothing pinned moved / refreshed / selftest passed
            1 = pinned path moved without its receipts or sidecar / selftest failed
            2 = cannot derive the pin set (missing receipts / sparse refuse), or
                --refresh-digests refused (layout-tier drift / foreign file)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Location of the receipts, not the pin set. The pin set is read from the
# JSON at runtime. Fallback glob is the same location the spec names.
EVIDENCE_DIR_REL = "mockups/evidence/prophet-p0b-zero-fouc"
RECEIPT_GLOB = "mobile-layout*.json"
FIXTURE_NAME = "rendered-fixture.json"
RECEIPT_SCHEMA = "mastermind.stock_dashboard_mobile_layout.v1"
FIXTURE_SCHEMA = "mastermind.stock_dashboard_rendered_fixture.v1"

# Events whose plan legitimately publishes the planner's `null` token: the
# main-role events in run_ci_pack.SUPPORTED_PLAN_ROLE_EVENTS (a main proof is a
# full-suite plan with no changed-file list) and the base replay, which hands
# its base-as-main child a `null` handle. There is no diff there, so this gate
# has nothing to close; whole-tree receipt consistency is the receipt tests'
# job (tests/test_stock_dashboard_first_frame.py). On every other event, above
# all `pull_request`, whose plan must carry an exact inventory, `null` means
# the planner failed, and the gate still refuses it. tests/test_ci_pack.py
# pins this set to the planner's table.
NO_DIFF_SUBJECT_EVENTS = frozenset(
    {"workflow_dispatch", "workflow_run", "schedule", "base_replay"}
)

# Digest-only tier.  A loaded script belongs here only when the rendered
# fixture gives it nothing to write into, so its bytes cannot move the first
# frame, the owner/degraded states, or the screenshots the receipts measure.
# Every reason below is re-proved against the rendered fixture by
# tests/test_stock_dashboard_first_frame.py, which also executes each script's
# bytes under node against a recording model of every measured page
# (test_digest_only_scripts_are_inert_on_every_measured_page).  An entry whose
# target appears in the fixture, or a script edit that writes to the page,
# reads past the model, claims a global or throws, reds that test, and the
# entry must then leave this table.
# Anything not named here (CSS, fonts, composers, chrome scripts, data) stays
# layout tier and still needs a browser re-mint.  Digest-only is a statement
# about the fixture the receipts measured, not about production: on the live
# HK page tablesort.js does enhance the populated sector table, but the
# fixture renders that table empty, so no receipt ever measured the effect,
# before or after a refresh.
REFRESHABLE_LOADED_ASSETS: dict[str, str] = {
    "site/charts.js": (
        "Plotly range-selector and locale helper: it acts only on "
        ".js-plotly-plot graph divs, and the rendered fixture has none. "
        "theme.js themeCharts touches the same divs, and only when Plotly is "
        "loaded."
    ),
    "site/chart_i18n.js": (
        "Relabels .js-plotly-plot graph divs from a page-defined "
        "window.__CHART_SWAP__ at load and on langchange, and only when "
        "Plotly is loaded; the rendered fixture has no such div and loads "
        "no Plotly."
    ),
    "site/tablesort.js": (
        "initAll enhances tables once, at DOMContentLoaded, and skips .tip, "
        ".sb-table, .st-table and tables with under two data rows; the "
        "rendered fixture has no eligible table, and composer tables exist "
        "only in the modal built on click, after initAll has run."
    ),
    "site/mtf.js": (
        "Paints only [data-mtf] nodes; the rendered fixture has none. theme.js "
        "re-runs hydrateMTF on a theme or language flip, which still finds "
        "none, and no composer calls renderMTF."
    ),
    "site/illus.js": (
        "Acts only on .ilx nodes; the rendered fixture has none. The "
        "templates call ilxReveal on the document at load and on a dialog "
        "when it opens, which still finds none, and no composer calls "
        "ilxMount or ilxReveal."
    ),
}

DIGEST_REFRESH_DIR_REL = f"{EVIDENCE_DIR_REL}/digest-refresh"
SIDECAR_SCHEMA = "mastermind.p0b_receipt_digest_refresh.v1"
SIDECAR_PROOF_CLASS = "digest_refresh_not_browser_measured"
REFRESH_TOOL = "python3 scripts/check_p0b_receipt_closure.py --refresh-digests"
SIDECAR_CLAIM = (
    "These bytes changed after the browser run that produced the receipts in "
    "measured_by. Layout, screenshots, console and behaviour were NOT "
    "re-measured against them; the receipts still report the bytes they "
    "loaded. The next browser re-mint measures the current bytes and retires "
    "this file."
)


def _posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _sparse_refusal(root: Path) -> str | None:
    """Refuse rather than pass vacuously when the evidence tree is omitted."""
    try:
        from scripts.worktree_sparse import missing_dirs, remedy_line
    except Exception:  # noqa: BLE001
        return None
    try:
        absent = [d for d in missing_dirs(root) if d == "mockups"]
    except Exception:  # noqa: BLE001
        return None
    return remedy_line(absent) if absent else None


def parse_changed_paths(text: str, *, null_is_no_diff: bool = False) -> set[str]:
    """Accept planner JSON, `git diff --name-only`, or a unified diff.

    Semantic packs publish their authoritative changed-path list as a JSON
    array through CI_CHANGED_FILES_FILE.  A configured planner sentinel
    (`null`) or malformed JSON must REFUSE rather than degrade to a harmless
    literal path and accidentally pass the closure gate.  The one exception is
    `null_is_no_diff`, which the caller sets only for NO_DIFF_SUBJECT_EVENTS:
    there `null` is the planner's documented full-suite token, not a failure.
    """
    stripped = text.strip()
    if stripped == "null":
        if null_is_no_diff:
            return set()
        raise ValueError("planner changed-file handle is null / unavailable")
    if stripped.startswith(("[", "{")):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed planner changed-file JSON: {exc}") from exc
        if not isinstance(parsed, list) or not all(isinstance(path, str) for path in parsed):
            raise ValueError("planner changed-file JSON must be an array of strings")
        return {path for path in parsed if path}
    lines = text.splitlines()
    if any(line.startswith("diff --git ") for line in lines):
        paths: set[str] = set()
        for line in lines:
            if not line.startswith("diff --git "):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            right = parts[-1]
            if right.startswith("b/"):
                right = right[2:]
            if right and right != "/dev/null":
                paths.add(right)
        return paths
    out: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        out.add(line)
    return out


def load_browser_receipts(root: Path) -> list[tuple[str, dict]]:
    """Return (repo-relative path, payload) for every committed P0B receipt."""
    evidence = root / EVIDENCE_DIR_REL
    if not evidence.is_dir():
        return []
    rows: list[tuple[str, dict]] = []
    for path in sorted(evidence.glob(RECEIPT_GLOB)):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("schema") != RECEIPT_SCHEMA:
            continue
        rows.append((_posix(path, root), payload))
    return rows


def load_fixture(root: Path, relpath: str) -> dict | None:
    path = root / relpath
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != FIXTURE_SCHEMA:
        return None
    return payload


def fixture_recipe_inputs(fixture: dict | None) -> set[str]:
    if not fixture:
        return set()
    paths: set[str] = set()
    markets = fixture.get("markets")
    if not isinstance(markets, dict):
        return paths
    for market in markets.values():
        if not isinstance(market, dict):
            continue
        for item in market.get("inputs") or []:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                paths.add(item["path"])
    return paths


def derive_pin_sets(root: Path) -> tuple[dict[str, set[str]], str | None]:
    """Map each receipt path to the paths it pins. Second value is a refuse reason."""
    receipts = load_browser_receipts(root)
    if not receipts:
        sparse = _sparse_refusal(root)
        if sparse:
            return {}, f"REFUSED: cannot derive the P0B pin set ({sparse})"
        return {}, (
            f"REFUSED: no {RECEIPT_SCHEMA} receipts under "
            f"{EVIDENCE_DIR_REL}/{RECEIPT_GLOB}"
        )

    pin_sets: dict[str, set[str]] = {}
    fixture_cache: dict[str, dict | None] = {}
    for relpath, payload in receipts:
        pins: set[str] = set()
        for key in ("construction_inputs", "loaded_assets"):
            block = payload.get(key)
            if isinstance(block, dict):
                pins.update(k for k in block if isinstance(k, str) and k)
        verifier = payload.get("verifier")
        if isinstance(verifier, dict) and isinstance(verifier.get("path"), str):
            pins.add(verifier["path"])
        fixture_row = payload.get("fixture_receipt")
        fixture_path = None
        if isinstance(fixture_row, dict) and isinstance(fixture_row.get("path"), str):
            fixture_path = fixture_row["path"]
            pins.add(fixture_path)
        if fixture_path:
            if fixture_path not in fixture_cache:
                fixture_cache[fixture_path] = load_fixture(root, fixture_path)
            pins.update(fixture_recipe_inputs(fixture_cache[fixture_path]))
        else:
            default_fixture = f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}"
            if default_fixture not in fixture_cache:
                fixture_cache[default_fixture] = load_fixture(root, default_fixture)
            pins.update(fixture_recipe_inputs(fixture_cache[default_fixture]))
        pin_sets[relpath] = pins
    return pin_sets, None


def remint_command(root: Path) -> str:
    """Name the remint recipe from the receipts themselves when possible."""
    receipts = load_browser_receipts(root)
    verifier = "scripts/verify_stock_dashboard_mobile_layout.cjs"
    fixture = f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}"
    recipe = "scripts/render_stock_dashboard_fixture.py"
    historical_head = None
    historical_tree = None
    assets = f"{EVIDENCE_DIR_REL}/inputs/browser-data"
    for _rel, payload in receipts:
        v = payload.get("verifier")
        if isinstance(v, dict) and isinstance(v.get("path"), str):
            verifier = v["path"]
        fr = payload.get("fixture_receipt")
        if isinstance(fr, dict) and isinstance(fr.get("path"), str):
            fixture = fr["path"]
        hb = payload.get("historical_baseline")
        if isinstance(hb, dict):
            if isinstance(hb.get("candidate_head"), str):
                historical_head = hb["candidate_head"]
            if isinstance(hb.get("candidate_tree"), str):
                historical_tree = hb["candidate_tree"]
        far = payload.get("fixture_assets_root")
        if isinstance(far, str) and far:
            assets = far
    loaded = load_fixture(root, fixture)
    if loaded:
        for path in sorted(fixture_recipe_inputs(loaded)):
            if path.endswith("render_stock_dashboard_fixture.py"):
                recipe = path
                break
    hist = ""
    if historical_head and historical_tree:
        hist = (
            f" --historical-head {historical_head}"
            f" --historical-tree {historical_tree}"
        )
    outs = " ".join(f"--out {rel}" for rel, _ in receipts) or (
        f"--out {EVIDENCE_DIR_REL}/mobile-layout.json"
    )
    return (
        f"python3 {recipe} --market all --out-dir DIR --receipt {fixture} && "
        f"node {verifier} --html DIR/<market>.html --site-dir site "
        f"--fixture-receipt {fixture} --fixture-assets-dir {assets} "
        f"--screenshot-dir {EVIDENCE_DIR_REL}{hist} ({outs})"
    )


def environment_hint(root: Path) -> str:
    """What a browser re-mint must reproduce, from the receipts themselves.

    The verifier already fixes its own rasterisation flags (no GPU, no LCD
    text, no subpixel positioning, no font hinting).  What it cannot fix is
    the browser build and the system fonts, and both move the layout numbers.
    """
    versions = sorted(
        {
            f"{b.get('engine', '?')} {b.get('version', '?')}"
            for _rel, payload in load_browser_receipts(root)
            if isinstance(b := payload.get("browser"), dict)
        }
    )
    built = ", ".join(versions) or "the build the receipts record"
    return (
        f"re-mint environment: the committed receipts were measured on {built}; "
        "layout numbers and screenshot digests reproduce only on that build with "
        "DejaVu Sans as the system sans font plus a CJK fallback, so pin both "
        "(--browser names the executable). After the re-mint, run "
        f"{REFRESH_TOOL} to prune the digest-refresh sidecars it retires."
    )


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def sidecar_relpath(asset: str) -> str:
    """One sidecar per asset, so sibling refreshes never touch the same file."""
    return f"{DIGEST_REFRESH_DIR_REL}/{asset.replace('/', '__')}.json"


def _receipt_fixture_path(payload: dict) -> str:
    row = payload.get("fixture_receipt")
    if isinstance(row, dict) and isinstance(row.get("path"), str):
        return row["path"]
    return f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}"


def _layout_pins(root: Path, payload: dict, fixture_cache: dict[str, dict | None]) -> set[str]:
    """Pins of one receipt that are never digest-only, whatever the table says."""
    pins: set[str] = set()
    block = payload.get("construction_inputs")
    if isinstance(block, dict):
        pins.update(k for k in block if isinstance(k, str) and k)
    verifier = payload.get("verifier")
    if isinstance(verifier, dict) and isinstance(verifier.get("path"), str):
        pins.add(verifier["path"])
    fixture_path = _receipt_fixture_path(payload)
    pins.add(fixture_path)
    if fixture_path not in fixture_cache:
        fixture_cache[fixture_path] = load_fixture(root, fixture_path)
    pins.update(fixture_recipe_inputs(fixture_cache[fixture_path]))
    return pins


def refreshable_measurements(
    root: Path, receipts: list[tuple[str, dict]] | None = None
) -> dict[str, dict[str, str]]:
    """``{asset: {receipt path: digest that receipt measured}}``, digest-only tier.

    A (receipt, asset) pair is digest-only when the asset is in
    REFRESHABLE_LOADED_ASSETS, the receipt loaded it, and the receipt does not
    also pin it as a construction input, verifier, fixture, or recipe input.
    """
    if receipts is None:
        receipts = load_browser_receipts(root)
    fixture_cache: dict[str, dict | None] = {}
    out: dict[str, dict[str, str]] = {}
    for relpath, payload in receipts:
        loaded = payload.get("loaded_assets")
        if not isinstance(loaded, dict):
            continue
        layout = _layout_pins(root, payload, fixture_cache)
        for asset in REFRESHABLE_LOADED_ASSETS:
            digest = loaded.get(asset)
            if isinstance(digest, str) and asset not in layout:
                out.setdefault(asset, {})[relpath] = digest
    return out


def build_sidecar(asset: str, current: str, measured_by: dict[str, str]) -> dict:
    return {
        "schema": SIDECAR_SCHEMA,
        "proof_class": SIDECAR_PROOF_CLASS,
        "path": asset,
        "sha256": current,
        "measured_by": dict(sorted(measured_by.items())),
        "claim": SIDECAR_CLAIM,
        "rationale": REFRESHABLE_LOADED_ASSETS[asset],
        "tool": REFRESH_TOOL,
    }


def render_sidecar(doc: dict) -> str:
    """Canonical bytes: a sidecar is valid only if it is exactly these."""
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _sidecar_status(root: Path) -> tuple[dict[str, dict], list[str]]:
    """Valid sidecars by asset, plus a finding for every file that is not one.

    Valid = the bytes are exactly what --refresh-digests derives from the
    current asset bytes and receipts, AND some receipt measured other bytes
    (a sidecar the receipts have caught up with is redundant, and reds until
    pruned, so retired debt cannot linger).
    """
    directory = root / DIGEST_REFRESH_DIR_REL
    if not directory.exists():
        return {}, []
    measurements = refreshable_measurements(root)
    by_name = {sidecar_relpath(asset): asset for asset in measurements}
    valid: dict[str, dict] = {}
    findings: list[str] = []
    for path in sorted(directory.iterdir()):
        rel = f"{DIGEST_REFRESH_DIR_REL}/{path.name}"
        if not path.is_file() or path.suffix != ".json":
            findings.append(
                f"UNKNOWN FILE IN DIGEST-REFRESH: {rel} is not a sidecar; only "
                f"{REFRESH_TOOL} writes into {DIGEST_REFRESH_DIR_REL}/"
            )
            continue
        asset = by_name.get(rel)
        if asset is None:
            findings.append(
                f"ORPHAN SIDECAR: {rel} names no digest-only asset a receipt "
                f"loads; run {REFRESH_TOOL} to prune it"
            )
            continue
        current = sha256_file(root / asset)
        measured = measurements[asset]
        if current is None:
            findings.append(f"SIDECAR FOR MISSING ASSET: {rel} vouches for {asset}, which is absent")
            continue
        if all(digest == current for digest in measured.values()):
            findings.append(
                f"REDUNDANT SIDECAR: {rel}: every receipt already measured the "
                f"current bytes of {asset}; run {REFRESH_TOOL} to prune it"
            )
            continue
        doc = build_sidecar(asset, current, measured)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = None
        if text != render_sidecar(doc):
            findings.append(
                f"STALE OR HAND-EDITED SIDECAR: {rel} is not what {REFRESH_TOOL} "
                f"derives from the current {asset} bytes and receipts"
            )
            continue
        valid[asset] = doc
    return valid, findings


def sidecar_findings(root: Path) -> list[str]:
    """Whole-tree sidecar consistency (diff-independent)."""
    return _sidecar_status(root)[1]


def effective_loaded_assets(root: Path, receipt_rel: str, payload: dict) -> dict[str, str]:
    """A receipt's loaded_assets with valid digest-refresh sidecars overlaid.

    The overlay applies only where the sidecar records the very digest this
    receipt measured, so a sidecar can never vouch for a receipt it did not
    start from.  The receipt payload itself is not modified.
    """
    loaded = payload.get("loaded_assets")
    effective = dict(loaded) if isinstance(loaded, dict) else {}
    valid, _findings = _sidecar_status(root)
    for asset, doc in valid.items():
        measured = doc["measured_by"].get(receipt_rel)
        if measured is not None and effective.get(asset) == measured:
            effective[asset] = doc["sha256"]
    return effective


def evaluate_rows(
    changed: set[str], pin_sets: dict[str, set[str]], root: Path | None = None
) -> list[tuple[str, str]]:
    """``(tier, finding)`` rows; tier is ``layout``, ``digest`` or ``sidecar``.

    Without ``root`` every pin is layout tier (the original contract).  With
    ``root``, a digest-only pin is closed when its current bytes equal the
    digest the receipt measured or a valid sidecar vouches for, and the
    digest-refresh tree is checked whenever the diff could have moved it.
    """
    rows: list[tuple[str, str]] = []
    measurements = refreshable_measurements(root) if root is not None else {}
    effective: dict[str, dict[str, str]] = {}
    receipts = dict(load_browser_receipts(root)) if root is not None else {}
    for relpath, pins in sorted(pin_sets.items()):
        if relpath in changed:
            continue
        for path in sorted(p for p in pins if p in changed):
            message = (
                f"PINNED PATH CHANGED WITHOUT RECEIPT: {path} is pinned by "
                f"{relpath}, which is not in the same diff"
            )
            if root is None:
                rows.append(("layout", message))
                continue
            if relpath in measurements.get(path, {}):
                if relpath not in effective:
                    effective[relpath] = effective_loaded_assets(
                        root, relpath, receipts.get(relpath, {})
                    )
                if sha256_file(root / path) == effective[relpath].get(path):
                    continue
                rows.append((
                    "digest",
                    f"{message}; digest-only tier: run {REFRESH_TOOL} and commit "
                    f"{sidecar_relpath(path)}",
                ))
            else:
                rows.append(("layout", f"{message}; layout tier: browser re-mint required"))
    if root is not None:
        watched = set().union(*pin_sets.values()) if pin_sets else set()
        watched.update(pin_sets)
        touches = any(
            path in watched or path.startswith(f"{DIGEST_REFRESH_DIR_REL}/")
            for path in changed
        )
        if touches:
            rows.extend(("sidecar", finding) for finding in sidecar_findings(root))
    return rows


def evaluate(
    changed: set[str], pin_sets: dict[str, set[str]], root: Path | None = None
) -> list[str]:
    """Return findings: pinned paths that moved without their receipts."""
    return [finding for _tier, finding in evaluate_rows(changed, pin_sets, root)]


def _browser_drift(root: Path, receipts: list[tuple[str, dict]]) -> list[str]:
    """Layout-tier bytes that differ from what the receipts measured."""
    measurements = refreshable_measurements(root, receipts)
    drift: list[str] = []
    seen_fixtures: set[str] = set()

    def check(path: str, digest: object, owner: str) -> None:
        if not isinstance(digest, str):
            return
        current = sha256_file(root / path)
        if current != digest:
            drift.append(
                f"{path}: {owner} measured {digest[:12]}, tree has "
                f"{current[:12] if current else 'no file'}"
            )

    for relpath, payload in receipts:
        for key in ("construction_inputs", "loaded_assets"):
            block = payload.get(key)
            if not isinstance(block, dict):
                continue
            for path, digest in sorted(block.items()):
                if key == "loaded_assets" and relpath in measurements.get(path, {}):
                    continue
                check(path, digest, relpath)
        for key in ("verifier", "fixture_receipt"):
            row = payload.get(key)
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                check(row["path"], row.get("sha256"), relpath)
        fixture_path = _receipt_fixture_path(payload)
        if fixture_path in seen_fixtures:
            continue
        seen_fixtures.add(fixture_path)
        fixture = load_fixture(root, fixture_path)
        for market in ((fixture or {}).get("markets") or {}).values():
            if not isinstance(market, dict):
                continue
            for item in market.get("inputs") or []:
                if isinstance(item, dict) and isinstance(item.get("path"), str):
                    check(item["path"], item.get("sha256"), fixture_path)
    return sorted(set(drift))


def refresh_digests(root: Path) -> tuple[int, list[str]]:
    """Browser-free, deterministic: re-mint only the digest-only tier.

    Writes or updates one sidecar per digest-only asset whose bytes moved,
    deletes sidecars the receipts have caught up with, and refuses (writing
    nothing) when any layout-tier byte moved or a foreign file sits in the
    sidecar directory.
    """
    sparse = _sparse_refusal(root)
    if sparse:
        return 2, [f"REFUSED: cannot refresh P0B digests ({sparse})"]
    receipts = load_browser_receipts(root)
    if not receipts:
        return 2, [
            f"REFUSED: no {RECEIPT_SCHEMA} receipts under {EVIDENCE_DIR_REL}/{RECEIPT_GLOB}"
        ]
    drift = _browser_drift(root, receipts)
    if drift:
        return 2, [
            "REFUSED: layout-tier bytes moved since the browser run; a digest "
            "refresh cannot close them, so nothing was written:",
            *(f"  {row}" for row in drift),
            f"re-mint with: {remint_command(root)}",
            environment_hint(root),
        ]
    directory = root / DIGEST_REFRESH_DIR_REL
    measurements = refreshable_measurements(root, receipts)
    by_name = {sidecar_relpath(asset): asset for asset in measurements}
    orphans: list[Path] = []
    if directory.exists():
        for path in sorted(directory.iterdir()):
            rel = f"{DIGEST_REFRESH_DIR_REL}/{path.name}"
            if rel in by_name:
                continue
            doc = None
            if path.is_file() and path.suffix == ".json":
                try:
                    doc = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    doc = None
            if isinstance(doc, dict) and doc.get("schema") == SIDECAR_SCHEMA:
                orphans.append(path)
                continue
            return 2, [
                f"REFUSED: {rel} is not a {SIDECAR_SCHEMA} sidecar; remove it by "
                "hand, nothing was written"
            ]
    plan: list[tuple[str, Path, str | None]] = []
    for asset, measured in sorted(measurements.items()):
        current = sha256_file(root / asset)
        if current is None:
            return 2, [f"REFUSED: {asset} is pinned by a receipt but missing; nothing was written"]
        target = root / sidecar_relpath(asset)
        if all(digest == current for digest in measured.values()):
            plan.append(("pruned" if target.exists() else "", target, None))
            continue
        text = render_sidecar(build_sidecar(asset, current, measured))
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError:
            existing = None
        plan.append(("unchanged" if existing == text else "wrote", target, text))
    lines: list[str] = []
    for verb, target, text in plan:
        rel = _posix(target, root) if target.exists() else f"{DIGEST_REFRESH_DIR_REL}/{target.name}"
        if verb == "pruned":
            target.unlink()
        elif verb == "wrote":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text or "", encoding="utf-8")
        if verb:
            lines.append(f"{verb} {rel}")
    for path in orphans:
        path.unlink()
        lines.append(f"pruned {DIGEST_REFRESH_DIR_REL}/{path.name} (orphan)")
    if directory.exists() and not any(directory.iterdir()):
        directory.rmdir()
    counts = {verb: sum(1 for row in plan if row[0] == verb) for verb in ("wrote", "unchanged", "pruned")}
    counts["pruned"] += len(orphans)
    lines.append(
        "p0b digest refresh: "
        + ", ".join(f"{count} {verb}" for verb, count in counts.items())
        + "; receipts and manifest untouched, no browser run"
    )
    return 0, lines


def run_selftest() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="check_p0b_receipt_closure_selftest_"))
    evidence = tmp / EVIDENCE_DIR_REL
    evidence.mkdir(parents=True)
    hk_receipt = evidence / "mobile-layout.json"
    ca_receipt = evidence / "mobile-layout-canada.json"
    fixture = evidence / FIXTURE_NAME
    pinned = "templates/zz-selftest.html.j2"
    fixture.write_text(
        json.dumps(
            {
                "schema": FIXTURE_SCHEMA,
                "proof_class": "rendered_fixture",
                "markets": {
                    "hk": {
                        "inputs": [
                            {"path": pinned, "sha256": "a" * 64},
                            {
                                "path": "scripts/render_stock_dashboard_fixture.py",
                                "sha256": "b" * 64,
                            },
                        ]
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    hk_receipt.write_text(
        json.dumps(
            {
                "schema": RECEIPT_SCHEMA,
                "construction_inputs": {pinned: "a" * 64},
                "loaded_assets": {"site/stock-dashboard.css": "c" * 64},
                "verifier": {
                    "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
                    "sha256": "d" * 64,
                },
                "fixture_receipt": {
                    "path": f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}",
                    "sha256": "e" * 64,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ca_receipt.write_text(
        json.dumps(
            {
                "schema": RECEIPT_SCHEMA,
                "construction_inputs": {"templates/zz-selftest-ca.html.j2": "f" * 64},
                "loaded_assets": {"site/stock-dashboard.css": "c" * 64},
                "verifier": {
                    "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
                    "sha256": "d" * 64,
                },
                "fixture_receipt": {
                    "path": f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}",
                    "sha256": "e" * 64,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    pin_sets, refuse = derive_pin_sets(tmp)
    if refuse or not pin_sets:
        print(f"selftest FAIL: could not derive pin sets: {refuse}")
        return 1
    if pinned not in pin_sets[f"{EVIDENCE_DIR_REL}/mobile-layout.json"]:
        print("selftest FAIL: construction input was not derived from the receipt")
        return 1

    # RED: pinned path alone.
    red = evaluate({pinned}, pin_sets)
    if not red:
        print("selftest FAIL: pinned-path-only diff unexpectedly passed")
        return 1

    # GREEN: pinned path plus every receipt that pins it (recipe inputs bind both).
    green = evaluate(
        {
            pinned,
            f"{EVIDENCE_DIR_REL}/mobile-layout.json",
            f"{EVIDENCE_DIR_REL}/mobile-layout-canada.json",
        },
        pin_sets,
    )
    if green:
        print(f"selftest FAIL: reminted receipts still red: {green}")
        return 1

    # GREEN: unrelated path.
    clean = evaluate({"engine/unrelated.py"}, pin_sets)
    if clean:
        print(f"selftest FAIL: unrelated path red: {clean}")
        return 1

    # The planner's `null` token: a main proof has no diff to close, and
    # anything else still refuses it.
    if parse_changed_paths("null\n", null_is_no_diff=True):
        print("selftest FAIL: a main-role null handle produced changed paths")
        return 1
    try:
        parse_changed_paths("null\n")
    except ValueError:
        pass
    else:
        print("selftest FAIL: a null handle passed without a main-role event")
        return 1

    failure = _selftest_digest_tier()
    if failure:
        print(f"selftest FAIL: {failure}")
        return 1

    print("check_p0b_receipt_closure selftest OK", flush=True)
    return 0


def _selftest_digest_tier() -> str | None:
    """Digest-only tier on a temp tree whose receipts carry real digests."""
    tmp = Path(tempfile.mkdtemp(prefix="check_p0b_receipt_closure_digest_selftest_"))
    evidence = tmp / EVIDENCE_DIR_REL
    template = "templates/zz-selftest.html.j2"
    css = "site/zz-selftest.css"
    charts, tablesort = "site/charts.js", "site/tablesort.js"
    files = {
        template: "<main>selftest</main>\n",
        css: "main{display:block}\n",
        charts: "/* charts */\n",
        tablesort: "/* tablesort */\n",
        "scripts/verify_stock_dashboard_mobile_layout.cjs": "// verifier\n",
    }
    for rel, text in files.items():
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(text, encoding="utf-8")

    def digest(rel: str) -> str:
        return sha256_file(tmp / rel) or ""

    evidence.mkdir(parents=True)
    fixture_rel = f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}"
    (tmp / fixture_rel).write_text(
        json.dumps(
            {
                "schema": FIXTURE_SCHEMA,
                "markets": {"hk": {"inputs": [{"path": template, "sha256": digest(template)}]}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    receipt_rels = [f"{EVIDENCE_DIR_REL}/mobile-layout.json", f"{EVIDENCE_DIR_REL}/mobile-layout-canada.json"]
    for rel in receipt_rels:
        (tmp / rel).write_text(
            json.dumps(
                {
                    "schema": RECEIPT_SCHEMA,
                    "construction_inputs": {template: digest(template)},
                    "loaded_assets": {rel_: digest(rel_) for rel_ in (css, charts, tablesort)},
                    "verifier": {
                        "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
                        "sha256": digest("scripts/verify_stock_dashboard_mobile_layout.cjs"),
                    },
                    "fixture_receipt": {"path": fixture_rel, "sha256": digest(fixture_rel)},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    pin_sets, refuse = derive_pin_sets(tmp)
    if refuse:
        return f"digest tier: could not derive pin sets: {refuse}"

    def gate(changed: set[str]) -> list[tuple[str, str]]:
        return evaluate_rows(changed, pin_sets, tmp)

    def append(rel: str, text: str) -> None:
        with (tmp / rel).open("a", encoding="utf-8") as handle:
            handle.write(text)

    if gate(set()) or refresh_digests(tmp)[0] != 0 or (tmp / DIGEST_REFRESH_DIR_REL).exists():
        return "digest tier: a clean tree was not clean, or refresh wrote into it"

    # The #7603 class: a layout-tier input moves alone. Red, and refresh refuses
    # without writing anything.
    original = (tmp / template).read_text(encoding="utf-8")
    append(template, "<p>moved</p>\n")
    if not any(tier == "layout" for tier, _ in gate({template})):
        return "digest tier: a template change was not layout-tier red"
    if refresh_digests(tmp)[0] != 2 or (tmp / DIGEST_REFRESH_DIR_REL).exists():
        return "digest tier: refresh did not refuse a template change cleanly"
    (tmp / template).write_text(original, encoding="utf-8")

    # A stylesheet is layout tier even though it is only a loaded asset.
    original = (tmp / css).read_text(encoding="utf-8")
    append(css, "main{margin:1px}\n")
    if refresh_digests(tmp)[0] != 2 or (tmp / DIGEST_REFRESH_DIR_REL).exists():
        return "digest tier: refresh did not refuse a stylesheet change"
    (tmp / css).write_text(original, encoding="utf-8")

    # Two siblings move different digest-only assets: each closes with its own
    # sidecar, the union is clean in either order, and no browser runs.
    append(charts, "/* sibling A */\n")
    if not all(tier == "digest" for tier, _ in gate({charts})) or not gate({charts}):
        return "digest tier: a charts.js change was not digest-tier red"
    if refresh_digests(tmp)[0] != 0:
        return "digest tier: refresh refused a digest-only change"
    sidecar_a = sidecar_relpath(charts)
    if gate({charts, sidecar_a}):
        return f"digest tier: charts.js plus its sidecar still red: {gate({charts, sidecar_a})}"
    append(tablesort, "/* sibling B */\n")
    if refresh_digests(tmp)[0] != 0:
        return "digest tier: refresh refused the second sibling"
    sidecar_b = sidecar_relpath(tablesort)
    union = gate({charts, sidecar_a, tablesort, sidecar_b})
    if union or sidecar_findings(tmp):
        return f"digest tier: the sibling union is red: {union}"
    for rel in receipt_rels:
        payload = json.loads((tmp / rel).read_text(encoding="utf-8"))
        effective = effective_loaded_assets(tmp, rel, payload)
        if effective.get(charts) != digest(charts) or effective.get(tablesort) != digest(tablesort):
            return "digest tier: effective digests do not reach the current bytes"

    # A hand-edited sidecar is not a sidecar.
    good = (tmp / sidecar_a).read_text(encoding="utf-8")
    (tmp / sidecar_a).write_text(good.replace(digest(charts), "0" * 64), encoding="utf-8")
    if not gate({sidecar_a}):
        return "digest tier: a hand-edited sidecar passed"
    (tmp / sidecar_a).write_text(good, encoding="utf-8")

    # A browser re-mint that measures the current bytes retires the sidecars;
    # leaving them behind reds until --refresh-digests prunes them.
    for rel in receipt_rels:
        payload = json.loads((tmp / rel).read_text(encoding="utf-8"))
        payload["loaded_assets"] = {rel_: digest(rel_) for rel_ in (css, charts, tablesort)}
        (tmp / rel).write_text(json.dumps(payload) + "\n", encoding="utf-8")
    if not gate(set(receipt_rels)):
        return "digest tier: a re-mint that left retired sidecars behind passed"
    if refresh_digests(tmp)[0] != 0 or (tmp / DIGEST_REFRESH_DIR_REL).exists():
        return "digest tier: refresh did not prune sidecars a re-mint retired"
    if gate(set(receipt_rels)):
        return "digest tier: a pruned re-mint is still red"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diff-file",
        help="Changed-path list (`git diff --name-only`) or a unified diff; '-' reads stdin.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_ROOT),
        help="Repo root the receipts resolve against.",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run the built-in selftest and exit.",
    )
    parser.add_argument(
        "--refresh-digests",
        action="store_true",
        help=(
            "Browser-free: write or prune digest-refresh sidecars for the "
            "digest-only assets, and refuse if any layout-tier byte moved."
        ),
    )
    parser.add_argument(
        "--event",
        default="",
        help=(
            "GitHub event that minted the changed-file handle (CI passes "
            "$GITHUB_EVENT_NAME). Deliberately never read from the environment, "
            "so a test run inside a CI job cannot inherit it. The planner's "
            "`null` token is accepted only for: "
            + ", ".join(sorted(NO_DIFF_SUBJECT_EVENTS))
            + "."
        ),
    )
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.refresh_digests:
        code, lines = refresh_digests(Path(args.repo_root))
        for line in lines:
            if code and line.startswith("REFUSED"):
                print(f"::error title=p0b-receipt-closure::{line}", flush=True)
            else:
                print(line, flush=True)
        return code

    if not args.diff_file:
        print(
            "::error title=p0b-receipt-closure::--diff-file PATH is required (or use --selftest)",
            flush=True,
        )
        return 1

    root = Path(args.repo_root)
    if args.diff_file == "-":
        diff_text = sys.stdin.read()
    else:
        try:
            diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(
                f"::error title=p0b-receipt-closure::could not read --diff-file: {exc}",
                flush=True,
            )
            return 1

    pin_sets, refuse = derive_pin_sets(root)
    if refuse:
        print(f"::error title=p0b-receipt-closure::{refuse}", flush=True)
        return 2

    null_is_no_diff = args.event in NO_DIFF_SUBJECT_EVENTS
    try:
        changed = parse_changed_paths(diff_text, null_is_no_diff=null_is_no_diff)
    except ValueError as exc:
        print(
            f"::error title=p0b-receipt-closure::REFUSED: {exc} "
            f"(event={args.event or 'unset'})",
            flush=True,
        )
        return 2
    if null_is_no_diff and diff_text.strip() == "null":
        print(
            f"::notice title=p0b-receipt-closure::{args.event} plan carries the "
            "planner's null handle (full suite, no changed-file list): no diff "
            "to close",
            flush=True,
        )
        return 0
    rows = evaluate_rows(changed, pin_sets, root)
    if not rows:
        return 0
    for _tier, finding in rows:
        print(f"::error title=p0b-receipt-closure::{finding}", flush=True)
    if any(tier == "layout" for tier, _ in rows):
        print(
            f"::error title=p0b-receipt-closure::re-mint with: {remint_command(root)}",
            flush=True,
        )
        print(f"::error title=p0b-receipt-closure::{environment_hint(root)}", flush=True)
    else:
        print(
            f"::error title=p0b-receipt-closure::refresh with: {REFRESH_TOOL} "
            f"(browser-free; commit the {DIGEST_REFRESH_DIR_REL}/ files it writes)",
            flush=True,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
