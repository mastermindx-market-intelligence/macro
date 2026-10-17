"""Real Odds controller over the complete Jinja page and real synthetic producer.

Requires Node and jsdom (JSDOM_MODULE may name an already-installed module).
Missing runtime dependencies FAIL explicitly; this regression does not skip.
No network, real browser, live feed, or production-data mutation is performed.
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from engine.odds_lab import build_matrix

ROOT = Path(os.environ.get("ODDS_REPO", Path(__file__).resolve().parents[1]))


def _page_and_data(tmp_path):
    def frame(end):
        idx = pd.bdate_range(end=end, periods=300)
        close = [100 + i * .1 + (i % 11) * .2 for i in range(len(idx))]
        return pd.DataFrame({"open": close, "high": [v + 1 for v in close],
            "low": [v - 1 for v in close], "close": close,
            "volume": [1_000_000] * len(idx)}, index=idx)

    matrices = {t: build_matrix(t, frame(day)) for t, day in
                [("SPY", "2026-10-14"), ("OLD", "2026-10-01")]}
    # Execute only the actual catalog assembler and its actual max-date
    # assignment. Importing/running the complete IO-bearing builder is neither
    # needed nor claimed. Its external services are never contacted.
    tree = ast.parse((ROOT / "scripts/build_odds.py").read_text())
    catalog_function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_catalog")
    asof_assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
        and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "asof" and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name) and n.value.func.id == "max"]
    assert len(asof_assignments) == 1
    scope = {"matrices": matrices}
    exec(compile(ast.Module(body=[catalog_function, asof_assignments[0]], type_ignores=[]),
        str(ROOT / "scripts/build_odds.py"), "exec"), scope)
    catalog = scope["_catalog"]({}, matrices, {}, {}, scope["asof"])
    assert catalog["asof"] == "2026-10-14"
    assert matrices["OLD"]["asof"] == "2026-10-01"
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    html = env.get_template("odds.html.j2").render()
    html_path, data_path = tmp_path / "odds.html", tmp_path / "fixture.json"
    html_path.write_text(html, encoding="utf-8")
    data_path.write_text(json.dumps({"catalog": catalog, "matrices": matrices}), encoding="utf-8")
    return html_path, data_path


def test_selected_odds_history_freshness(tmp_path):
    node = shutil.which("node")
    assert node, "Node is required for the Odds full-controller regression"
    probe = subprocess.run([node, "-e", 'require(process.env.JSDOM_MODULE || "jsdom")'],
        env=os.environ, text=True, capture_output=True, timeout=15)
    assert probe.returncode == 0, (
        "Odds full-controller regression requires jsdom. Provide the approved dependency "
        "or set JSDOM_MODULE to an existing installation. This check does not skip.\n" + probe.stderr)
    html, data = _page_and_data(tmp_path)
    env = dict(os.environ, ODDS_HTML=str(html), ODDS_FIXTURE=str(data),
               ODDS_SOURCE=str(ROOT / "site/odds.js"))
    proc = subprocess.run([node, "--test", "--test-reporter=tap",
        str(Path(__file__).with_name("odds_freshness_runner.cjs"))],
        env=env, text=True, capture_output=True, timeout=90, cwd=ROOT)
    print(proc.stdout)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr


def test_odds_script_is_eligible_for_current_content_hash():
    # Whole canonical optimizer function + its actual regex constants, with no
    # rewrite. This isolated execution avoids importing unrelated config/IO.
    tree = ast.parse((ROOT / "lib/pages.py").read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "optimize_assets_text")
    # Resolve the function's repository-local helper/constant closure. No
    # production statement is transformed and unrelated page writers stay out.
    selected = [function]
    needed = {n.id for n in ast.walk(function) if isinstance(n, ast.Name)}
    while True:
        additions = []
        for node in tree.body:
            if node in selected:
                continue
            declared = {node.name} if isinstance(node, ast.FunctionDef) else {
                n.id for n in ast.walk(node) if isinstance(n, ast.Name)
                and isinstance(n.ctx, ast.Store)} if isinstance(node, (ast.Assign, ast.AnnAssign)) else set()
            if declared & needed:
                additions.append(node)
        if not additions:
            break
        selected.extend(additions)
        for node in additions:
            needed.update(n.id for n in ast.walk(node) if isinstance(n, ast.Name))
    selected = [node for node in tree.body if node in selected]
    import re
    from typing import Callable, Optional
    scope = {"re": re, "Callable": Callable, "Optional": Optional}
    exec(compile(ast.Module(body=selected, type_ignores=[]),
        str(ROOT / "lib/pages.py"), "exec"), scope)
    template = Environment(loader=FileSystemLoader(ROOT / "templates"),
        autoescape=True).get_template("odds.html.j2").render()
    digest = hashlib.sha256((ROOT / "site/odds.js").read_bytes()).hexdigest()[:8]
    rendered = scope["optimize_assets_text"](template, lambda url: digest if url == "odds.js" else None)
    tag = re.search(r'<script[^>]+src="odds\.js[^>]*>', rendered)
    print(json.dumps({"odds_script_sha256_prefix": digest, "optimized_tag": tag.group(0) if tag else None}))
    assert f'odds.js?v={digest}' in rendered
    assert 'odds.js?v=2"' not in rendered
