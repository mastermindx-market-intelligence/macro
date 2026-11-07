#!/usr/bin/env python3
"""Gate changes to the inputs bound by the committed P0B browser receipts.

The live pin set comes from the receipts and their rendered-fixture recipe.
Construction inputs, browser/verifier/fixture bindings, fonts, CSS, callers and
unknown helper revisions remain strict: their receipt bindings must close the
change. Tablesort is always strict.

An optional digest-refresh exception requires one explicit complete helper
source vector and the exact raw receipt scene in QUALIFIED_DIGEST_SCENES.
The initial record contains only bytes already captured by its historical
receipts; it grants no exception to a changed helper. Future qualification is
an ordinary source-policy amendment, never an inference from a passing model.
The finite Node diagnostic is a regression aid, not a browser execution or a
universal proof of JavaScript equivalence.

A qualified sidecar explicitly records that its new bytes were not measured by
the browser. Unknown scenes use the raw receipt bindings without any overlay.
A proper new capture or accepted receipt composition can therefore deactivate
an old exception without requiring a new policy record. Full current receipt
self-binding tests still apply.

--refresh-digests plans every effect before writing. An inactive scene refuses
creation or rewriting. It may only retire a complete set of recognized owned
sidecars when all current strict input bindings match and every sidecar asset
is directly loaded with its current hash by at least one current receipt.
Foreign files, missing inputs, uncertain ownership and drift refuse all effects.
Pre-application checks are not a filesystem lock or an atomic I/O transaction.

Usage:
    python3 scripts/check_p0b_receipt_closure.py --diff-file /tmp/changed.txt
    python3 scripts/check_p0b_receipt_closure.py --refresh-digests
    python3 scripts/check_p0b_receipt_closure.py --selftest
Exit codes: 0 = closed / no relevant change / refreshed / retired / selftest passed
            1 = unclosed receipt or sidecar / selftest failed
            2 = missing or malformed inventory / sparse tree / refused refresh
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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
DEFAULT_VERIFIER = "scripts/verify_stock_dashboard_mobile_layout.cjs"
CHROMIUM_PIN_RE = re.compile(r'^const CHROMIUM_PIN = "([^"]+)";$', re.MULTILINE)

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

# Candidate helper roles, not a path-only exemption. Each active qualification
# binds all four source hashes and the exact outer receipt set. Unknown bytes,
# changed callers or scene inputs receive no exemption. The exact-source
# diagnostic covers a declared target-free fixture trace only; it cannot
# qualify arbitrary revisions, event roots, browser APIs or asynchronous work.
# CSS, fonts, composers, chrome scripts, data and tablesort remain strict.
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


# A qualification names one complete source vector and one exact recorded scene.
# This first record is baseline byte identity with the browser's captured helpers:
# no changed-helper equivalence or new browser measurement is claimed. A future
# edit, even a comment-only edit, is strict layout until an ordinary source-policy
# amendment qualifies the complete vector against the same captured scene.
# Passing the diagnostic VM never creates or extends this policy. Unknown scenes
# forbid new overlays. Only a separately validated strict retirement may delete
# recognized redundant sidecars; it never extends qualification.
QUALIFIED_DIGEST_SCENES: tuple[dict, ...] = ({'assets': {'site/chart_i18n.js': '23272c482c2b27f294f6e35f45a76dfe8e61bdd6cdc61e88e83a3cde47174315',
             'site/charts.js': '84a794395899da373f00ae59374aab93c3a41aee56ac55e973f2f960e95ed47c',
             'site/illus.js': '8e0a3779784525f15bb4a1b20e50f39ef4d0ddf243827f5ab609cfb08a69c620',
             'site/mtf.js': 'b62aea2f86b81a2d06e156c9e8f63f43804cd183868f209f3c450cdf2b39a1c0'},
  'basis': 'captured_helper_byte_identity_20261107',
  'receipts': {'mockups/evidence/prophet-p0b-zero-fouc/mobile-layout-canada.json': 'e0f6abed4c32ef07fb4b8046070b442b369eff2d396ac76ef6a3e68d334c22bb',
               'mockups/evidence/prophet-p0b-zero-fouc/mobile-layout.json': '550f6453121b29822a74fcc6fb43e13552b0601bf2e1401a248e51654919462b'}},)

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
        manifest = font_pin_manifest(payload)
        if manifest:
            pins.add(manifest)
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
    verifier = DEFAULT_VERIFIER
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


def font_pin_manifest(payload: dict) -> str | None:
    font_pin = payload.get("font_pin")
    if not isinstance(font_pin, dict):
        return None
    manifest = font_pin.get("manifest")
    if isinstance(manifest, dict) and isinstance(manifest.get("path"), str):
        return manifest["path"] or None
    return None



def verifier_chromium_pin(root: Path, verifier: str) -> str | None:
    try:
        text = (root / verifier).read_text(encoding="utf-8")
    except OSError:
        return None
    match = CHROMIUM_PIN_RE.search(text)
    return match.group(1) if match else None



def describe_browser(browser: dict) -> str:
    """One receipt's browser block as text: build, binary, Playwright, host."""
    text = f"{browser.get('engine', '?')} {browser.get('version', '?')}"
    extra = []
    executable = browser.get("executable")
    if isinstance(executable, dict) and executable.get("name"):
        extra.append(f"{executable['name']} sha256 {executable.get('sha256', '?')}")
    if browser.get("playwright"):
        extra.append(f"Playwright {browser['playwright']}")
    if browser.get("platform"):
        extra.append(f"{browser['platform']}/{browser.get('arch', '?')}")
    return f"{text} ({', '.join(extra)})" if extra else text



def environment_hint(root: Path) -> str:
    """Name the browser build and fonts a re-mint must reproduce."""
    receipts = load_browser_receipts(root)
    versions = sorted(
        {
            describe_browser(browser)
            for _rel, payload in receipts
            if isinstance(browser := payload.get("browser"), dict)
        }
    )
    verifier = DEFAULT_VERIFIER
    for _rel, payload in receipts:
        v = payload.get("verifier")
        if isinstance(v, dict) and isinstance(v.get("path"), str):
            verifier = v["path"]
    manifests = sorted({m for _rel, payload in receipts if (m := font_pin_manifest(payload))})
    built = ", ".join(versions) or "the build the receipts record"
    parts = [f"re-mint environment: the committed receipts were measured on {built}"]
    pin = verifier_chromium_pin(root, verifier)
    if pin:
        parts.append(
            f"{verifier} pins Chromium {pin}, its headless-shell binary, the "
            "Playwright release and the host platform, and refuses anything else "
            "(pass --browser with that build's chrome-headless-shell if Playwright "
            "resolves a different one)"
        )
    if manifests:
        parts.append(
            f"it serves only the fonts committed in {', '.join(manifests)} and "
            "refuses a receipt if any glyph falls back to a platform font "
            "(regenerate the subsets with scripts/build_p0b_font_pin.py)"
        )
    return "; ".join(parts)


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
    manifest = font_pin_manifest(payload)
    if manifest:
        pins.add(manifest)
    fixture_path = _receipt_fixture_path(payload)
    pins.add(fixture_path)
    if fixture_path not in fixture_cache:
        fixture_cache[fixture_path] = load_fixture(root, fixture_path)
    pins.update(fixture_recipe_inputs(fixture_cache[fixture_path]))
    return pins


def _receipt_inventory(
    root: Path, receipts: list[tuple[str, dict]] | None = None
) -> tuple[list[tuple[str, dict]], dict[str, str], list[str]]:
    """Parse and hash the same complete raw inventory; reject omitted bad files."""
    # Parse and hash the same bytes. A supplied earlier payload is only an
    # expected snapshot; it cannot be paired with another receipt's raw hash.
    expected_payloads = None if receipts is None else dict(receipts)
    bound_receipts: list[tuple[str, dict]] = []
    current_receipts: dict[str, str] = {}
    for path in sorted((root / EVIDENCE_DIR_REL).glob(RECEIPT_GLOB)):
        if (path.is_symlink() or not path.is_file()
                or not path.resolve().is_relative_to(root.resolve())):
            return [], {}, ["unqualified receipt inventory: nonregular or escaping receipt"]
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, ValueError, UnicodeDecodeError):
            return [], {}, ["unqualified receipt inventory: unreadable or malformed browser receipt"]
        if not isinstance(payload, dict) or payload.get("schema") != RECEIPT_SCHEMA:
            return [], {}, ["unqualified receipt inventory: malformed or extra browser receipt"]
        rel = path.relative_to(root).as_posix()
        current_receipts[rel] = hashlib.sha256(raw).hexdigest()
        bound_receipts.append((rel, payload))
    if not current_receipts:
        return [], {}, ["unqualified receipt inventory: no browser receipts"]
    if expected_payloads is not None and (
        expected_payloads != dict(bound_receipts) or len(receipts or []) != len(bound_receipts)
    ):
        return [], {}, ["receipt payload changed between parsing and qualification; no effects allowed"]
    return bound_receipts, current_receipts, []


def qualification_status(
    root: Path, receipts: list[tuple[str, dict]] | None = None
) -> tuple[dict[str, dict[str, str]], dict | None, list[str]]:
    """Exact source-vector/scene eligibility; inactivity always means strict pins."""
    receipts, current_receipts, errors = _receipt_inventory(root, receipts)
    if errors:
        return {}, None, errors
    current_assets = {path: sha256_file(root / path) for path in REFRESHABLE_LOADED_ASSETS}
    if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
           for value in [*current_receipts.values(), *current_assets.values()]):
        return {}, None, ["unqualified source or scene: an exact input is absent or unreadable"]
    matches = [
        row for row in QUALIFIED_DIGEST_SCENES
        if isinstance(row, dict)
        and row.get("receipts") == current_receipts
        and row.get("assets") == current_assets
        and isinstance(row.get("basis"), str) and row["basis"]
    ]
    if len(matches) != 1:
        return {}, None, [
            "unqualified source or receipt scene: expected one exact approved "
            "complete helper vector and outer receipt set, found " + str(len(matches))
        ]
    record = matches[0]
    fixture_cache: dict[str, dict | None] = {}
    measurements: dict[str, dict[str, str]] = {}
    for relpath, payload in receipts:
        loaded = payload.get("loaded_assets")
        if not isinstance(loaded, dict):
            return {}, None, [f"{relpath}: malformed loaded_assets"]
        layout = _layout_pins(root, payload, fixture_cache)
        for asset in REFRESHABLE_LOADED_ASSETS:
            digest = loaded.get(asset)
            if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) and asset not in layout:
                measurements.setdefault(asset, {})[relpath] = digest
    drift = _receipt_drift(root, receipts, measurements)
    if drift:
        return {}, None, drift
    return measurements, record, []


def refreshable_measurements(
    root: Path, receipts: list[tuple[str, dict]] | None = None
) -> dict[str, dict[str, str]]:
    """Only exact qualified vectors in their unchanged captured scene are eligible."""
    return qualification_status(root, receipts)[0]


def build_sidecar(asset: str, current: str, measured_by: dict[str, str], qualification: dict) -> dict:
    # Whole-vector eligibility was already checked. A sibling asset does not
    # change this asset sidecar identity once their union is explicitly qualified.
    binding = {"receipts": qualification["receipts"],
               "asset": {asset: qualification["assets"][asset]}}
    qualified_bytes = json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "schema": SIDECAR_SCHEMA,
        "proof_class": SIDECAR_PROOF_CLASS,
        "path": asset,
        "sha256": current,
        "measured_by": dict(sorted(measured_by.items())),
        "qualification_sha256": hashlib.sha256(qualified_bytes.encode("utf-8")).hexdigest(),
        "claim": SIDECAR_CLAIM,
        "rationale": REFRESHABLE_LOADED_ASSETS[asset],
        "tool": REFRESH_TOOL,
    }


def render_sidecar(doc: dict) -> str:
    """Canonical bytes: a sidecar is valid only if it is exactly these."""
    return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _sidecar_inventory(root: Path) -> tuple[dict[str, str] | None, str | None]:
    """Preflight every existing entry, including recognized sidecar names."""
    directory = root / DIGEST_REFRESH_DIR_REL
    if directory.is_symlink() or not directory.resolve().is_relative_to(root.resolve()):
        return None, "sidecar directory is a symlink or escapes the repository"
    if not directory.exists():
        return {}, None
    if not directory.is_dir():
        return None, "sidecar directory is not a directory"
    inventory: dict[str, str] = {}
    for path in sorted(directory.iterdir()):
        if (path.is_symlink() or not path.is_file()
                or not path.resolve().is_relative_to(root.resolve())):
            return None, f"sidecar target is not a contained regular file: {path.name}"
        digest = sha256_file(path)
        if digest is None:
            return None, f"sidecar target is unreadable: {path.name}"
        inventory[path.name] = digest
    return inventory, None


def _sidecar_status(root: Path) -> tuple[dict[str, dict], list[str]]:
    """Valid sidecars by asset, plus a finding for every file that is not one.

    Valid = the bytes are exactly what --refresh-digests derives from the
    current asset bytes and receipts, AND some receipt measured other bytes
    (a sidecar the receipts have caught up with is redundant, and reds until
    pruned, so retired debt cannot linger).
    """
    directory = root / DIGEST_REFRESH_DIR_REL
    _inventory, shape_error = _sidecar_inventory(root)
    if shape_error:
        return {}, ["INVALID SIDECAR TARGET: " + shape_error]
    if not _inventory:
        return {}, []
    measurements, qualification, errors = qualification_status(root)
    if errors:
        return {}, ["UNQUALIFIED SIDECAR SCENE: " + error for error in errors]
    assert qualification is not None
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
        doc = build_sidecar(asset, current, measured, qualification)
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


def _receipt_drift(root: Path, receipts: list[tuple[str, dict]],
                   measurements: dict[str, dict[str, str]]) -> list[str]:
    """Layout-tier bytes that differ from what the receipts measured."""
    drift: list[str] = []
    seen_fixtures: set[str] = set()

    def check(path: str, digest: object, owner: str) -> None:
        candidate = Path(path) if isinstance(path, str) else None
        if (candidate is None or candidate.is_absolute() or ".." in candidate.parts
                or candidate.as_posix() != path or not (root / candidate).resolve().is_relative_to(root.resolve())):
            drift.append(f"{owner}: noncanonical or escaping input path {path!r}")
            return
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            drift.append(f"{path}: {owner} has no valid SHA-256 input binding")
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
            if not isinstance(block, dict) or not block:
                drift.append(f"{relpath}: missing or malformed {key}")
                continue
            for path, digest in sorted(block.items()):
                if key == "loaded_assets" and relpath in measurements.get(path, {}):
                    continue
                check(path, digest, relpath)
        for key in ("verifier", "fixture_receipt"):
            row = payload.get(key)
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                check(row["path"], row.get("sha256"), relpath)
            else:
                drift.append(f"{relpath}: missing or malformed {key}")
        font_pin = payload.get("font_pin")
        if font_pin is not None:
            manifest = font_pin.get("manifest") if isinstance(font_pin, dict) else None
            path = font_pin_manifest(payload)
            digest = manifest.get("sha256") if isinstance(manifest, dict) else None
            if not path or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                drift.append(f"{relpath}: malformed font_pin.manifest; cannot establish layout bytes")
            else:
                check(path, digest, relpath)
        fixture_path = _receipt_fixture_path(payload)
        if fixture_path in seen_fixtures:
            continue
        seen_fixtures.add(fixture_path)
        fixture = load_fixture(root, fixture_path)
        if fixture is None:
            drift.append(f"{fixture_path}: missing or malformed recipe inventory")
        markets = (fixture or {}).get("markets")
        if not isinstance(markets, dict) or not markets:
            drift.append(f"{fixture_path}: missing or malformed recipe markets")
            continue
        for market in markets.values():
            inputs = market.get("inputs") if isinstance(market, dict) else None
            if not isinstance(inputs, list) or not inputs:
                drift.append(f"{fixture_path}: missing or malformed recipe inputs")
                continue
            for item in inputs:
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    drift.append(f"{fixture_path}: malformed recipe input")
                    continue
                check(item["path"], item.get("sha256"), fixture_path)
    return sorted(set(drift))


def _browser_drift(root: Path, receipts: list[tuple[str, dict]]) -> list[str]:
    """Explicit qualification failures and strict byte drift; neither permits writes."""
    measurements, _record, errors = qualification_status(root, receipts)
    return sorted(set(errors + _receipt_drift(root, receipts, measurements)))


def _retire_strict_sidecars(
    root: Path, receipts: list[tuple[str, dict]], qualification_errors: list[str]
) -> tuple[int, list[str]]:
    """Deletion-only retirement under complete current strict receipt bindings."""
    def refuse(reason: str) -> tuple[int, list[str]]:
        return 2, ["REFUSED: " + reason + "; nothing was written or pruned"]

    inventory, shape_error = _sidecar_inventory(root)
    if shape_error:
        return refuse(shape_error)
    if not inventory:
        return 2, ["REFUSED: inactive qualification; no refresh effects allowed", *qualification_errors]
    current, raw_hashes, errors = _receipt_inventory(root, receipts)
    errors += _receipt_drift(root, current, {})
    if errors:
        return 2, ["REFUSED: strict retirement inputs are not closed; nothing was written or pruned", *errors]
    directory = root / DIGEST_REFRESH_DIR_REL
    plan: list[Path] = []
    for path in sorted(directory.iterdir()):
        try:
            text = path.read_text(encoding="utf-8")
            doc = json.loads(text)
        except (OSError, ValueError, UnicodeDecodeError):
            return refuse(f"unrecognized sidecar {path.name}")
        asset = doc.get("path") if isinstance(doc, dict) else None
        measured = doc.get("measured_by") if isinstance(doc, dict) else None
        if (not isinstance(asset, str) or asset not in REFRESHABLE_LOADED_ASSETS
                or path.relative_to(root).as_posix() != sidecar_relpath(asset)
                or not isinstance(measured, dict) or not measured
                or not all(isinstance(p, str) and isinstance(d, str) and re.fullmatch(r"[0-9a-f]{64}", d)
                           for p, d in measured.items())):
            return refuse(f"unrecognized owned sidecar {path.name}")
        recognized = []
        for row in QUALIFIED_DIGEST_SCENES:
            if not isinstance(row, dict) or not isinstance(row.get("receipts"), dict) or not isinstance(row.get("assets"), dict):
                continue
            historical_hash = row["assets"].get(asset)
            if (not isinstance(historical_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", historical_hash)
                    or not set(measured) <= set(row["receipts"])):
                continue
            if text == render_sidecar(build_sidecar(asset, historical_hash, measured, row)):
                recognized.append(row)
        if not recognized:
            return refuse(f"sidecar {path.name} has no retained canonical qualification identity")
        if not any(set(row["receipts"]) <= set(raw_hashes) for row in recognized):
            return refuse(f"current receipt inventory is incomplete for {path.name}")
        loaded = [payload["loaded_assets"][asset] for _rel, payload in current if asset in payload["loaded_assets"]]
        actual = sha256_file(root / asset)
        if not loaded or any(digest != actual for digest in loaded):
            return refuse(f"{asset} is not directly covered by every applicable current receipt")
        plan.append(path)
    # Validate the complete current strict scene and all deletion targets again.
    confirmed, confirmed_hashes, errors = _receipt_inventory(root)
    errors += _receipt_drift(root, confirmed, {})
    inventory_after, shape_error = _sidecar_inventory(root)
    if (errors or confirmed_hashes != raw_hashes or dict(confirmed) != dict(current)
            or shape_error or inventory_after != inventory):
        return refuse("strict inputs or sidecar identities changed while planning")
    lines = []
    for path in plan:
        path.unlink()
        lines.append(f"retired {DIGEST_REFRESH_DIR_REL}/{path.name}")
    if directory.exists() and not any(directory.iterdir()):
        directory.rmdir()
    lines.append(
        f"p0b digest retirement: {len(plan)} owned sidecar(s) retired under current strict receipt bindings; "
        "qualification remains inactive; receipts untouched; no browser run"
    )
    return 0, lines


def refresh_digests(root: Path) -> tuple[int, list[str]]:
    """Validate a complete qualified refresh or a strict deletion-only retirement."""
    sparse = _sparse_refusal(root)
    if sparse:
        return 2, [f"REFUSED: cannot refresh P0B digests ({sparse})"]
    receipts = load_browser_receipts(root)
    if not receipts:
        return 2, [
            f"REFUSED: no {RECEIPT_SCHEMA} receipts under {EVIDENCE_DIR_REL}/{RECEIPT_GLOB}"
        ]
    _measurements, active, qualification_errors = qualification_status(root, receipts)
    if active is None or qualification_errors:
        return _retire_strict_sidecars(root, receipts, qualification_errors)
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
    measurements, qualification, errors = qualification_status(root, receipts)
    if errors or qualification is None:
        return 2, ["REFUSED: source/scene qualification changed; nothing was written", *errors]
    inventory_before, shape_error = _sidecar_inventory(root)
    if shape_error:
        return 2, ["REFUSED: " + shape_error + "; nothing was written"]
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
        if current != qualification["assets"].get(asset):
            return 2, [f"REFUSED: {asset} changed after qualification; nothing was written"]
        target = root / sidecar_relpath(asset)
        if all(digest == current for digest in measured.values()):
            plan.append(("pruned" if target.exists() else "", target, None))
            continue
        text = render_sidecar(build_sidecar(asset, current, measured, qualification))
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError:
            existing = None
        plan.append(("unchanged" if existing == text else "wrote", target, text))
    # Re-read the complete qualification after planning and before any write or prune.
    # This is a validation boundary, not a replacement repository lock or I/O journal.
    _current, confirmed, errors = qualification_status(root)
    if errors or confirmed != qualification or _current != measurements:
        return 2, ["REFUSED: source/scene changed while planning; nothing was written", *errors]
    inventory_after, shape_error = _sidecar_inventory(root)
    if shape_error or inventory_after != inventory_before:
        return 2, ["REFUSED: sidecar targets changed while planning; nothing was written", shape_error or "inventory changed"]
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
    font_manifest = f"{EVIDENCE_DIR_REL}/inputs/browser-data/p0b-font-pin/font-pin.json"
    (tmp / "scripts").mkdir()
    (tmp / DEFAULT_VERIFIER).write_text(
        'const CHROMIUM_PIN = "1.2.3.4";\n', encoding="utf-8"
    )
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
                "browser": {"engine": "chromium", "version": "1.2.3.4"},
                "font_pin": {"manifest": {"path": font_manifest, "sha256": "9" * 64}},
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

    # RED: a font-pin manifest edit moves glyph metrics, so it remints too.
    if not evaluate({font_manifest}, pin_sets):
        print("selftest FAIL: font-pin manifest change unexpectedly passed")
        return 1

    hint = environment_hint(tmp)
    for needle in ("chromium 1.2.3.4", "pins Chromium 1.2.3.4", font_manifest):
        if needle not in hint:
            print(f"selftest FAIL: environment hint lacks {needle!r}: {hint}")
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
    """Temporary synthetic policy declarations never escape the selftest."""
    global QUALIFIED_DIGEST_SCENES
    saved = QUALIFIED_DIGEST_SCENES
    QUALIFIED_DIGEST_SCENES = ()
    try:
        return _selftest_digest_tier_fixture()
    finally:
        QUALIFIED_DIGEST_SCENES = saved


def _selftest_digest_tier_fixture() -> str | None:
    """Digest-only tier on a temp tree whose receipts carry real digests."""
    tmp = Path(tempfile.mkdtemp(prefix="check_p0b_receipt_closure_digest_selftest_"))
    evidence = tmp / EVIDENCE_DIR_REL
    template = "templates/zz-selftest.html.j2"
    css = "site/zz-selftest.css"
    charts, mtf = "site/charts.js", "site/mtf.js"
    files = {
        template: "<main>selftest</main>\n",
        css: "main{display:block}\n",
        charts: "/* charts */\n",
        mtf: "/* mtf */\n",
        "scripts/verify_stock_dashboard_mobile_layout.cjs": "// verifier\n",
        "site/chart_i18n.js": "/* synthetic chart i18n */\n",
        "site/illus.js": "/* synthetic illus */\n",
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
                    "loaded_assets": {rel_: digest(rel_) for rel_ in (css, charts, mtf)},
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
    def qualify_synthetic() -> None:
        global QUALIFIED_DIGEST_SCENES
        row = {"basis": "synthetic_selftest_not_browser_evidence",
               "receipts": {p: digest(p) for p in receipt_rels},
               "assets": {p: digest(p) for p in REFRESHABLE_LOADED_ASSETS}}
        if row not in QUALIFIED_DIGEST_SCENES:
            QUALIFIED_DIGEST_SCENES += (row,)
    qualify_synthetic()
    pin_sets, refuse = derive_pin_sets(tmp)
    if refuse:
        return f"digest tier: could not derive pin sets: {refuse}"

    def gate(changed: set[str]) -> list[tuple[str, str]]:
        return evaluate_rows(changed, pin_sets, tmp)

    def append(rel: str, text: str) -> None:
        with (tmp / rel).open("a", encoding="utf-8") as handle:
            handle.write(text)
        if rel in REFRESHABLE_LOADED_ASSETS:
            qualify_synthetic()

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
    append(mtf, "/* sibling B */\n")
    if refresh_digests(tmp)[0] != 0:
        return "digest tier: refresh refused the second sibling"
    sidecar_b = sidecar_relpath(mtf)
    union = gate({charts, sidecar_a, mtf, sidecar_b})
    if union or sidecar_findings(tmp):
        return f"digest tier: the sibling union is red: {union}"
    for rel in receipt_rels:
        payload = json.loads((tmp / rel).read_text(encoding="utf-8"))
        effective = effective_loaded_assets(tmp, rel, payload)
        if effective.get(charts) != digest(charts) or effective.get(mtf) != digest(mtf):
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
        payload["loaded_assets"] = {rel_: digest(rel_) for rel_ in (css, charts, mtf)}
        (tmp / rel).write_text(json.dumps(payload) + "\n", encoding="utf-8")
    qualify_synthetic()
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
