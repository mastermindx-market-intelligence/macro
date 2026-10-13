"""Guard: no public surface may serve, render, upload, or link SNI material.

SNI-local DRAFT scanner. It is not an owner of Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research
Vault, or qledger/Evaluation. It consumes no issuer or security identifiers
(unknown identity stays unresolved / null) and does not feed a ranker, gate,
sizer, signal, escalation, or trade path. Every authority flag stays false;
a caller that tries to set one true is refused.

Scans templates/, app/ (excluding tests), and PUBLISH_SCRIPTS for the
substrings research/single_name_intelligence and
contracts/single_name_intelligence. Scans the same PUBLISH_SCRIPTS plus the
render/deploy workflows for copy/upload sources of the repo research/ tree
(research, research/, research/**). Does not scan generated site/ bytes or
R2 bucket contents.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]

# Relative paths of scripts that render, copy, or upload bytes toward a
# public origin (Caddy site.served, R2 object prefixes, committed site/).
PUBLISH_SCRIPTS: dict[str, str] = {
    "scripts/publish_r2.py": (
        "Uploads named site/ and data/ dirs to the R2 bucket (R2_BUCKET env)."
    ),
    "scripts/build_site.py": "Renders the public static dashboard into site/.",
    "scripts/ci/public_render.sh": (
        "CI lane that renders a small public HTML set and stages site/."
    ),
    "scripts/render_macro_fast.py": "Fast renderer for US/macro public pages.",
    "scripts/render_canada_fast.py": "Fast renderer for Canada public pages.",
    "scripts/render_china_fast.py": "Fast renderer for China public pages.",
    "scripts/render_hk_fast.py": "Fast renderer for HK public pages.",
    "scripts/render_stock_dashboard_fixture.py": (
        "Fixture renderer for stock-dashboard HTML."
    ),
    "app/deploy/update.sh": (
        "VPS deploy: rsyncs site/ onto Caddy's /opt/macro/site.served root."
    ),
    "scripts/publish_company_disclosure.py": (
        "Publishes company-disclosure artifacts toward the public data plane."
    ),
    "scripts/publish_company_institutional_context_r2.py": (
        "Uploads company institutional-context objects to R2."
    ),
    "scripts/publish_company_intelligence_r2.py": (
        "Uploads company-intelligence objects to R2."
    ),
    "scripts/publish_company_theme_exposure_r2.py": (
        "Uploads company theme-exposure objects to R2."
    ),
    "scripts/publish_control_room_active_builds.py": (
        "Publishes control-room active-build artifacts."
    ),
    "scripts/publish_earnings_evidence_graph_r2.py": (
        "Uploads earnings evidence-graph objects to R2."
    ),
    "scripts/publish_earnings_private_store.py": (
        "Publishes the earnings store; scanned so a research/ glob cannot ride."
    ),
    "scripts/publish_earnings_r2.py": "Uploads earnings objects to R2.",
    "scripts/publish_earnings_story_packets_r2.py": (
        "Uploads earnings story-packet objects to R2."
    ),
    "scripts/publish_fif_production_datasets.py": (
        "Publishes FIF production datasets toward R2/site."
    ),
    "scripts/publish_options_alpha_candidate_r2.py": (
        "Uploads options-alpha candidate objects to R2."
    ),
    "scripts/publish_oracle_panels.py": "Publishes oracle panel artifacts.",
    "scripts/close_pass_publish.py": "Close-pass publish lane.",
    "scripts/mirror_gex_state_r2.py": "Mirrors GEX state objects to R2.",
    "scripts/mirror_terminal_context_r2.py": (
        "Mirrors terminal-context objects to R2."
    ),
}

RENDER_DEPLOY_WORKFLOWS: tuple[str, ...] = (
    ".github/workflows/render.yml",
    ".github/workflows/engine-render.yml",
    ".github/workflows/daily.yml",
)

SNI_PATH_MARKERS: tuple[str, ...] = (
    "research/single_name_intelligence",
    "contracts/single_name_intelligence",
)

# Real internal references on a scanned surface go here with a reason.
# Empty: the 2026-10-13 census found none on templates/, app/, or PUBLISH_SCRIPTS.
ALLOWED: dict[str, str] = {}

_AUTHORITY_FLAGS: tuple[str, ...] = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "node_modules"}
_SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".pdf",
    ".parquet",
    ".bin",
    ".so",
}

# Copy/upload/sync/add of the repo research/ tree itself (not site/research/,
# not properties/research/, not a research/FOO.md comment citation).
_BROAD_GLOBS = (
    re.compile(r"research/\*\*"),
    re.compile(r"""['"]research/['"]"""),
    re.compile(
        r"(?:rsync|scp|(?<![\w.])cp\s|rclone|aws\s+s3\s+sync|git\s+add)"
        r"[^\n]*"
        r"(?<![\w./-])research(?:/\*\*|/|\s|$)",
        re.IGNORECASE,
    ),
    re.compile(r"copy(?:tree)?\s*\(\s*['\"]research"),
    re.compile(r"upload(?:_file|_dir)?\s*\(\s*['\"]research"),
    re.compile(r"--dirs\s+\S*\bresearch\b"),
)


class Hit(NamedTuple):
    path: str
    line: int
    text: str


def refuse_authority(**flags: object) -> None:
    """Refuse any attempt to arm a ranker/gate/sizer/signal/escalation/trade flag."""
    armed = [name for name in _AUTHORITY_FLAGS if flags.get(name) is True]
    if armed:
        raise ValueError(
            "SNI public-exposure guard has no authority path; "
            f"refusing True flags: {', '.join(armed)}"
        )


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_app_test(rel: Path) -> bool:
    parts_l = {p.lower() for p in rel.parts}
    if "tests" in parts_l:
        return True
    name = rel.name
    return name.startswith("test_") or name.endswith("_test.py")


def _iter_text_files(base: Path):
    if not base.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() in _SKIP_SUFFIXES:
                continue
            yield path


def _readlines(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return None


def public_references(root: Path) -> list[Hit]:
    """Return SNI path-string hits on templates/, app/ (no tests), PUBLISH_SCRIPTS."""
    root = Path(root)
    hits: list[Hit] = []
    seen: set[tuple[str, int]] = set()

    def consider(path: Path) -> None:
        lines = _readlines(path)
        if lines is None:
            return
        rel = _rel(path, root)
        for i, line in enumerate(lines, start=1):
            if not any(marker in line for marker in SNI_PATH_MARKERS):
                continue
            key = (rel, i)
            if key in seen:
                continue
            seen.add(key)
            hits.append(Hit(rel, i, line.strip()))

    templates = root / "templates"
    for path in _iter_text_files(templates):
        consider(path)

    app_root = root / "app"
    for path in _iter_text_files(app_root):
        rel_from_app = path.relative_to(app_root)
        if _is_app_test(rel_from_app):
            continue
        consider(path)

    for rel in PUBLISH_SCRIPTS:
        consider(root / rel)

    return hits


def broad_publish_globs(root: Path) -> list[Hit]:
    """Return copy/upload sources of research/, research/** on publish surfaces."""
    root = Path(root)
    hits: list[Hit] = []
    seen: set[tuple[str, int]] = set()
    targets = list(PUBLISH_SCRIPTS) + list(RENDER_DEPLOY_WORKFLOWS)
    for rel in targets:
        path = root / rel
        lines = _readlines(path)
        if lines is None:
            continue
        for i, line in enumerate(lines, start=1):
            if not any(pat.search(line) for pat in _BROAD_GLOBS):
                continue
            key = (rel, i)
            if key in seen:
                continue
            seen.add(key)
            hits.append(Hit(rel, i, line.strip()))
    return hits


def _unallowed(hits: list[Hit]) -> list[Hit]:
    return [h for h in hits if h.path not in ALLOWED]


def test_authority_flags_refuse_true() -> None:
    refuse_authority()
    refuse_authority(rank_authority=False, trade_authority=False)
    for name in _AUTHORITY_FLAGS:
        try:
            refuse_authority(**{name: True})
        except ValueError:
            continue
        raise AssertionError(f"expected refuse_authority({name}=True) to raise")


def test_real_tree_has_no_public_sni_references() -> None:
    leaked = _unallowed(public_references(REPO_ROOT))
    assert leaked == [], "PUBLIC-EXPOSURE blocker:\n" + "\n".join(
        f"{h.path}:{h.line}: {h.text[:200]}" for h in leaked
    )


def test_real_tree_has_no_broad_research_publish_globs() -> None:
    leaked = _unallowed(broad_publish_globs(REPO_ROOT))
    assert leaked == [], "BROAD-GLOB blocker:\n" + "\n".join(
        f"{h.path}:{h.line}: {h.text[:200]}" for h in leaked
    )


def test_positive_control_catches_poisoned_template_and_upload(tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    templates.mkdir(parents=True)
    (templates / "poison.html.j2").write_text(
        '<a href="/research/single_name_intelligence/x.md">\n',
        encoding="utf-8",
    )
    publish = tmp_path / "scripts" / "publish_r2.py"
    publish.parent.mkdir(parents=True)
    publish.write_text(
        's3.upload("research/**")\n',
        encoding="utf-8",
    )

    refs = public_references(tmp_path)
    assert refs, "poisoned template must be reported"
    assert any(
        h.path.endswith("poison.html.j2")
        and "research/single_name_intelligence" in h.text
        for h in refs
    ), refs

    globs = broad_publish_globs(tmp_path)
    assert globs, "poisoned research/** upload must be reported"
    assert any("research/**" in h.text for h in globs), globs
