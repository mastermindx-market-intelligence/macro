"""Publication, freshness, and recovery pins for the T21 qualified path.

Source of the contract: research/crypto_science/CRYPTO_T21_PUBLICATION_CONTRACT_2026-10-12.md.
Static reads only. No builders, collectors, network, or data/ / site/ trees.
Generator bodies owned by open PR #8901 are existence checks.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

# ci-trigger-closure: data — names only; PR #8901 owns these generators' content
_PR8901_GENERATORS = {
    "site/crypto.html": "scripts/build_crypto.py",
    "site/vector.html": "scripts/build_vector.py",
    "site/crypto_cockpit.json": "scripts/build_vector.py",
    "site/crypto_class_state.json": "scripts/build_crypto.py",
    "site/crypto_asset_states.json": "scripts/build_crypto.py",
    "site/btc_options.json": "engine/btc_options.py",
    "site/vector_risk_strategy.json": "scripts/build_vector.py",
    "site/vector_timeline.json": "scripts/build_vector.py",
}

# T21 §2 stale_after_days rows whose adapters are outside the #8901 split.
_STALE_AFTER = (
    ("collectors/coinmetrics.py", "CoinMetricsAdapter", 4),
    ("collectors/coinbase.py", "CoinbaseAdapter", 2),
    ("collectors/crypto_misc.py", "FearGreedAdapter", 3),
    ("collectors/crypto_misc.py", "CoinGeckoAdapter", 3),
    ("collectors/crypto_misc.py", "CryptoUniverseAdapter", 3),
    ("collectors/crypto_misc.py", "MempoolAdapter", 3),
    ("collectors/crypto_misc.py", "DefiLlamaAdapter", 4),
    ("collectors/crypto_misc.py", "WikipediaBtcAdapter", 4),
    ("collectors/farside.py", "FarsideAdapter", 4),
)

_VECTOR_ONLY_LANES = (
    ".github/workflows/closing-bell.yml",
    ".github/workflows/earlyclose.yml",
    ".github/workflows/weekly.yml",
    ".github/workflows/sentinel.yml",
)


def _text(rel: str) -> str:
    path = ROOT / rel
    assert path.is_file(), rel
    return path.read_text(encoding="utf-8")


def _workflow(rel: str) -> dict:
    doc = yaml.safe_load(_text(rel))
    assert isinstance(doc, dict)
    return doc


def _on_block(doc: dict) -> dict:
    block = doc[True] if True in doc else doc.get("on")
    assert isinstance(block, dict)
    return block


def _job_steps(doc: dict, job_id: str) -> list[dict]:
    job = doc["jobs"][job_id]
    return [step for step in job.get("steps") or [] if isinstance(step, dict)]


def _run(step: dict) -> str:
    run = step.get("run")
    return run if isinstance(run, str) else ""


def _indices(steps: list[dict], pred) -> list[int]:
    return [index for index, step in enumerate(steps) if pred(step)]


def _class_int(rel: str, class_name: str, attr: str) -> int:
    tree = ast.parse(_text(rel))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for stmt in node.body:
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            if isinstance(stmt, ast.Assign):
                targets = list(stmt.targets)
                value = stmt.value
            elif isinstance(stmt, ast.AnnAssign):
                targets = [stmt.target]
                value = stmt.value
            if value is None:
                continue
            if any(isinstance(target, ast.Name) and target.id == attr for target in targets):
                parsed = ast.literal_eval(value)
                assert isinstance(parsed, int)
                return parsed
    raise AssertionError(f"{rel}:{class_name}.{attr} missing")


def _function(rel: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(_text(rel))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{rel}:{name} missing")


def _invocation_lines(text: str, module: str) -> list[int]:
    """Non-comment lines that invoke scripts.<module>."""
    found: list[int] = []
    pattern = re.compile(rf"\bscripts\.{re.escape(module)}\b")
    for index, line in enumerate(text.splitlines()):
        code = line.split("#", 1)[0]
        if pattern.search(code):
            found.append(index)
    return found


def test_engine_job_publishes_vector_then_crypto_then_stamps_then_commits() -> None:
    """T21 §4 steps 1–4. Step order is the engine job's real order.

    Substrings, cited from .github/workflows/daily.yml on this tree:
    - collect run contains ``python -m scripts.collect --exclude-group asia`` (:384)
    - engine ``needs`` includes ``collect`` (collect is the prior job, not a step)
    - name ``build bitcoin vector + landing hub`` / run ``python -m scripts.build_vector`` (:3626)
    - name ``build crypto intelligence cockpit`` / run ``python -m scripts.build_crypto`` (:3631)
    - run contains ``python -m scripts.optimize_assets`` (:4511, inside the whitehouse step)
    - name ``commit engine outputs`` / run ``bash scripts/ci/daily_engine_commit_outputs.sh`` (:4853-4855)
    """
    doc = _workflow(".github/workflows/daily.yml")
    collect_steps = _job_steps(doc, "collect")
    collect_hits = _indices(
        collect_steps,
        lambda step: "python -m scripts.collect --exclude-group asia" in _run(step),
    )
    assert collect_hits, "T21 §4: nightly collect command missing from the collect job"
    assert "collect" in (doc["jobs"]["engine"].get("needs") or []), (
        "T21 §4: engine job must run after collect"
    )

    steps = _job_steps(doc, "engine")
    vector = _indices(
        steps,
        lambda step: "build bitcoin vector + landing hub" in str(step.get("name") or "")
        and "python -m scripts.build_vector" in _run(step),
    )
    crypto = _indices(
        steps,
        lambda step: "build crypto intelligence cockpit" in str(step.get("name") or "")
        and "python -m scripts.build_crypto" in _run(step),
    )
    stamped = _indices(
        steps,
        lambda step: "python -m scripts.optimize_assets" in _run(step),
    )
    commit = _indices(
        steps,
        lambda step: str(step.get("name") or "") == "commit engine outputs"
        and "scripts/ci/daily_engine_commit_outputs.sh" in _run(step),
    )
    assert len(vector) == 1 and len(crypto) == 1 and len(stamped) == 1 and len(commit) == 1, (
        vector, crypto, stamped, commit,
    )
    order = (vector[0], crypto[0], stamped[0], commit[0])
    assert order == tuple(sorted(order)) and len(set(order)) == 4, (
        f"T21 §4: engine step indices must increase build_vector < build_crypto "
        f"< optimize_assets < commit, got {order}"
    )


def test_commit_script_stages_data_site_and_reports() -> None:
    """T21 §4 step 4. scripts/ci/daily_engine_commit_outputs.sh:64 stages the three trees."""
    text = _text("scripts/ci/daily_engine_commit_outputs.sh")
    # daily_engine_commit_outputs.sh:64 is `git add data/ site/ reports/`.
    staged: list[str] = []
    for line in text.splitlines():
        code = line.split("#", 1)[0].strip()
        if code.startswith("git add "):
            staged.extend(code.split()[2:])
    assert "data/" in staged and "site/" in staged and "reports/" in staged, (
        "T21 §4: nightly commit must stage data/, site/, and reports/"
    )


def test_live_crypto_quote_stale_after_65_minutes() -> None:
    """T21 §2 Live quotes. templates/live.js:87-93. Parse the default, not the whole line."""
    text = _text("templates/live.js")
    match = re.search(r"LIVE_CRYPTO_STALE_MIN\s*\|\|\s*(\d+)", text)
    assert match, "T21 §2: templates/live.js lost the crypto staleness default"
    assert int(match.group(1)) == 65, (
        "T21 §2: crypto quote staleness default must be 65 minutes"
    )


def test_vps_macro_update_runs_every_three_minutes() -> None:
    """T21 §1 and §4 step 5. app/deploy/setup.sh:74-75. Parse the cron fields."""
    text = _text("app/deploy/setup.sh")
    minutes = re.findall(
        r"(\*/\d+|\d+)\s+\*\s+\*\s+\*\s+\*\s+/usr/local/bin/macro-update\b",
        text,
    )
    assert minutes == ["*/3"], (
        "T21 §1: VPS pull cadence must be every 3 minutes"
    )


def test_daily_build_b_crons_are_the_et_pair() -> None:
    """T21 §2. .github/workflows/daily.yml:36-37. Once per night, EDT and EST."""
    schedule = _on_block(_workflow(".github/workflows/daily.yml")).get("schedule") or []
    crons = [entry.get("cron") for entry in schedule if isinstance(entry, dict)]
    assert crons == ["30 22 * * *", "30 23 * * *"], (
        "T21 §2: Build B cadence must stay the 18:30 America/New_York cron pair"
    )


@pytest.mark.parametrize(("rel", "class_name", "days"), _STALE_AFTER)
def test_crypto_adapter_stale_after_days(rel: str, class_name: str, days: int) -> None:
    """T21 §2 adapter table. Class attribute, not a whole-line string match."""
    assert _class_int(rel, class_name, "stale_after_days") == days, (
        f"T21 §2: {class_name}.stale_after_days must stay {days}"
    )


def test_collector_stale_status_is_wall_clock_age_past_the_budget() -> None:
    """T21 §2. collectors/base.py:671-675. ``stale`` when age exceeds stale_after_days."""
    fn = _function("collectors/base.py", "run_adapter")
    compared = False
    marked = False
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == "age"
            and any(isinstance(op, ast.Gt) for op in node.ops)
            and any(isinstance(comp, ast.Name) and comp.id == "stale_after_days" for comp in node.comparators)
        ):
            compared = True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "status"
                    and isinstance(node.value, ast.Constant)
                    and node.value.value == "stale"
                ):
                    marked = True
    assert compared and marked, (
        "T21 §2: collector stale status must compare wall-clock age to stale_after_days"
    )


def test_open_html_cache_is_sixty_seconds_must_revalidate() -> None:
    """T21 §1 HTML shells and §4 step 6. app/deploy/Caddyfile:423-437."""
    text = _text("app/deploy/Caddyfile")
    start = text.find("@open_html")
    assert start != -1, "T21 §1: @open_html matcher missing"
    window = text[start:start + 1800]
    match = re.search(r'header Cache-Control "([^"]+)"', window)
    assert match, "T21 §1: @open_html handle lost its Cache-Control header"
    header = match.group(1)
    assert re.search(r"\bmax-age=60\b", header) and "must-revalidate" in header, (
        "T21 §4: anonymous HTML must be public, max-age=60, must-revalidate"
    )


def test_btc_live_schedule_is_hourly_unless_the_vps_owns_quotes() -> None:
    """T21 §2 live plane. .github/workflows/btc-live.yml:30 and :41-44."""
    doc = _workflow(".github/workflows/btc-live.yml")
    crons = [
        entry.get("cron")
        for entry in (_on_block(doc).get("schedule") or [])
        if isinstance(entry, dict)
    ]
    assert crons == ["0 * * * *"], "T21 §2: btc-live cadence must stay hourly"
    snapshot = doc["jobs"]["snapshot"]
    guard = str(snapshot.get("if") or "")
    assert "VPS_LIVE_PRIMARY" in guard and "true" in guard, (
        "T21 §2: scheduled btc-live must stay off when the VPS live lane is primary"
    )


def test_r2_page_publish_does_not_list_crypto_or_vector_html() -> None:
    """T21 §4 gap 10. daily.yml:4863-4876 publishes other dirs; the pages stay on git."""
    steps = _job_steps(_workflow(".github/workflows/daily.yml"), "engine")
    hits = [
        step for step in steps
        if "python -m scripts.publish_r2 --dirs ohlc" in _run(step)
    ]
    assert len(hits) == 1
    match = re.search(r"--dirs\s+(\S+)", _run(hits[0]))
    assert match, "T21 §4: heavy-store publish lost its --dirs list"
    dirs = match.group(1).split(",")
    banned = [name for name in dirs if "crypto" in name or "vector" in name]
    assert not banned, (
        "T21 §4: crypto and vector pages are not an R2 publish surface"
    )


def test_served_artifact_generators_exist() -> None:
    """T21 §1 generation identity.

    Each served artifact's generator file is on disk. Stamp-writer text inside
    those generators is owned by PR #8901, so this check stops at existence.
    """
    missing = [
        f"{artifact} -> {generator}"
        for artifact, generator in _PR8901_GENERATORS.items()
        if not (ROOT / generator).is_file()
    ]
    assert not missing, missing


@pytest.mark.xfail(
    strict=True,
    reason="T21 gap 2: crypto as_of is max() of unequal series",
)
def test_crypto_data_through_is_the_btc_daily_bar() -> None:
    """T21 §4 gap 2. Correct contract: page data-through is the BTC daily, not max() of five series."""
    fn = _function("engine/crypto_market_state.py", "build_market_state")
    rhs = None
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "as_of" for target in node.targets):
            rhs = node.value
            break
    assert rhs is not None, "T21 gap 2: build_market_state lost as_of"
    calls_max = any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "max")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "max")
        )
        for node in ast.walk(rhs)
    )
    names = {node.id for node in ast.walk(rhs) if isinstance(node, ast.Name)}
    assert not calls_max and "btc" in names, (
        "T21 gap 2: data-through must be the BTC daily series and must not call max()"
    )


@pytest.mark.xfail(
    strict=True,
    reason="T21 gap 5: vector-only lanes publish vector.html without build_crypto",
)
def test_vector_only_lanes_call_build_crypto_after_build_vector() -> None:
    """T21 §3 / §4 gap 5. closing-bell, earlyclose, weekly, sentinel."""
    missing: list[str] = []
    for rel in _VECTOR_ONLY_LANES:
        text = _text(rel)
        vector_at = _invocation_lines(text, "build_vector")
        crypto_at = _invocation_lines(text, "build_crypto")
        if not vector_at or not crypto_at or crypto_at[0] <= vector_at[0]:
            missing.append(rel)
    assert not missing, (
        "T21 gap 5: each vector lane must call build_crypto after build_vector: "
        + ", ".join(missing)
    )


@pytest.mark.xfail(
    strict=True,
    reason="T21 gap 6: freshness_sentinel does not watch crypto or vector pages",
)
def test_freshness_sentinel_watches_crypto_and_vector_pages() -> None:
    """T21 §3 / §4 gap 6. Surfaces key on the pages, not on the bake clock."""
    text = _text("scripts/freshness_sentinel.py")
    assert "crypto.html" in text and "vector.html" in text, (
        "T21 gap 6: freshness_sentinel must name crypto.html and vector.html"
    )


@pytest.mark.xfail(
    strict=True,
    reason="T21 gap 7: render replay can restore an older data-through date",
)
def test_render_push_refuses_an_older_crypto_or_vector_data_through() -> None:
    """T21 §3 / §4 gap 7. render.yml:1391-1393 is the replay. engine-render.yml:967 is the sibling."""
    gaps: list[str] = []
    for rel in (".github/workflows/render.yml", ".github/workflows/engine-render.yml"):
        text = _text(rel)
        names_both = "site/crypto.html" in text and "site/vector.html" in text
        refuses_older = re.search(r"data-through|data_through|older than", text) is not None
        if not (names_both and refuses_older):
            gaps.append(rel)
    assert not gaps, (
        "T21 gap 7: render commit must refuse crypto.html and vector.html when "
        "data-through is older than origin/main: " + ", ".join(gaps)
    )


@pytest.mark.xfail(
    strict=True,
    reason="T21 gap 8: write_page is a non-atomic write_text",
)
def test_write_page_replaces_a_temp_file_in_the_same_directory() -> None:
    """T21 §3 / §4 gap 8. lib/pages.py:745. Correct contract: same-dir temp plus os.replace."""
    fn = _function("lib/pages.py", "write_page")
    attrs = [
        node.func.attr
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    names = [
        node.func.id
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "write_text" not in attrs, "T21 gap 8: write_page still calls write_text"
    assert "replace" in attrs or "replace" in names, (
        "T21 gap 8: write_page must os.replace a temp file in the same directory"
    )
