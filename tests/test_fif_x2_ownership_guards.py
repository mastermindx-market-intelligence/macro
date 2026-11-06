"""tests/test_fif_x2_ownership_guards.py — spec gate 5 + seat rulings S1-S6.

No duplicate scheduler, no duplicate user-data authority, no macro DDL, no
mail sender, no second watchlist writer — and the ONE nightly step is shaped
and placed per the C5 census (after build_fundamental_forensics and every
render-critical step of daily.yml's engine job).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml

from engine import fif_saved_research_notifications as producer

ROOT = Path(__file__).resolve().parents[1]
MODULE_TOKEN = "run_fif_saved_research_notifications"
PRODUCER = ROOT / "engine" / "fif_saved_research_notifications.py"
RUNNER = ROOT / "scripts" / "run_fif_saved_research_notifications.py"
NEW_FILES = [
    PRODUCER,
    RUNNER,
    ROOT / "tests" / "test_fif_saved_research_notifications.py",
    ROOT / "tests" / "test_fif_x2_ownership_guards.py",
    ROOT / "tests" / "test_fif_watchstore_designated_list_js.py",
]

# The C5 census list: every render-critical step (builds/renders/publishes/
# commits/pushes site or data) of daily.yml's engine job from the
# build_fundamental_forensics step onward. The X2-n step must come after ALL
# of them. It is NOT the job's final step: the W2 timings finish step stays
# last (tests/test_nightly_timings.py) and the X2-n step sits directly ahead
# of it.
W2_FINISH_STEP = "timings ledger + 85% budget tripwire (W2)"
RENDER_CRITICAL_STEPS = [
        "publish Filing Forensics private state",
        "Sector-flip confirmation lens (Policy-Shock W1-C)",
        "Prophet × Stage forward-shadow (tag actual entries + nightly grade advance)",
        "checkpoint Prophet Stage-shadow accrual to main",
        "Prophet Live arming pass (provisional-close trigger pack -> R2)",
        "Prophet Live reconciler (intraday event spool -> forward ledger)",
        "TURN WATCH desk (early-surfacing deck — display tier)",
        "checkpoint core engine outputs to main (durable before tail desks)",
        "AD-1 — Daily EOD Options Intelligence Brief (build_options_intel_brief)",
        "OEU M-CMD — the Options workspace (build_options_command)",
        "OIP E1 — session digest, the Terminal→EOD bridge (build_session_digest)",
        "OIP PIT — durable episodes + H+60 and declared-session-close proxy accrual",
        "OIP campaign v2 — exact-contract revision and anchored-outcome accrual",
        "OIP catalyst links — bind the session's events to earnings/FOMC catalysts (context-only)",
        "Options Alpha — compose and publish the verified candidate pair",
        "XSR W1 — US fast-sector rotation lens (build_us_sector_rotation)",
        "US sector central intelligence (build_sector_central)",
        "Portfolio-Aware context artifact (build_portfolio_ctx)",
        "MLC W2b stance matrix (build_stance_matrix)",
        "FTR W9 grading pack (basket_turn.v1 cohort claims + tape_disagreement.v1)",
        "Polygon reference-universe cache (GICS sector + market cap for heatmap manifest)",
        "flow-signal ledger harvest + outcome grader (FS-0)",
        "build canada dashboard (S&P/TSX)",
        "build bitcoin vector + landing hub",
        "build crypto intelligence cockpit",
        "Demand Desk page (build_demand)",
        "US Buy Board ledger (snapshot today + retro-grade matured boards vs SPY/sector)",
        "ETF consensus board ledger (snapshot tonight's board + grade matured windows vs SPY)",
        "Opportunity timeline (durable Prophet candidate receipts for Terminal)",
        "Bottom Ledger (accrue bottom-class flags + mature at H=60; policy-free instrument)",
        "Calibration Hub (unified self-improvement observability; display-only)",
        "build macro snapshot (nw-macro-rail R5)",
        "build macro context page (nw-macro-rail R5)",
        "build spine index (neural-web W2)",
        "build reliability kernel estimates (neural-web W3)",
        "build covariance spine (R-ORTH PR-3)",
        "build kernel diagnostics (neural-web W3)",
        "build kernel half-lives (Signal Commons W2 — display-only)",
        "Confluence Graph (Neural Web W4 — display-only typed graph)",
        "Confluence Strength + Sequence + Discovery (Neural Web W4 \"the eye\" — R-V4-6/7/8)",
        "Alt-Data Brain (Claude-Opus convergence analyst; actionable + falsifiable)",
        "radar upgrade (build_radar_plus + IC)",
        "unified intelligence bundle (build_intelligence)",
        "brain briefing tunnel (build_briefing)",
        "Intelligence Hub (build_intel_hub)",
        "AI Daily Brief page (build_aibrief)",
        "AM Edition producer (build_am_edition)",
        "Mastermind snapshot page (build_mastermind)",
        "AI Desk page (build_ai_desk_page)",
        "recurring briefs producer (F11 — each subscription its brief or an honest miss)",
        "archive signal layer (append-only point-in-time model outputs; resilient)",
        "archive context snapshots (context PIT history — non-fatal)",
        "CPI net-liquidity artifact (data infrastructure — non-fatal)",
        "Neural Web liquidity-plumbing lobe (shadow-tier, non-fatal)",
        "Price Pressure lobe (DRL W1, display-tier, non-fatal)",
        "Release Radar coherent CPI target parity (truth substrate, non-fatal)",
        "Release Radar official-actual reconciliation (truth substrate, non-fatal)",
        "MRI release forecast producer (display-only, non-fatal)",
        "Inflation intelligence lobe (context-only, non-fatal)",
        "forward path board (RIC W7 P5, display-only, non-fatal)",
        "White House Watch — re-render page + inject site-wide alert banner",
        "build world state (neural-web W1)",
        "build bottom-sensor envelope (NW Rails B0)",
        "mature bottom sensors shadow (Amendment-3 forward audit — display-only)",
        "mature shadow book (stock-score forward audit; see config/dag.yml)",
        "entity/thesis/mechanism registry (neural-web — display-only crosswalk)",
        "build mechanism pathways (NW core-cognition W1 — MPC v1)",
        "build thematic state (TIL W0 — display/context only)",
        "grade thematic (TIL W6 — grading pack)",
        "Chronicle — market context timeline spine",
        "commit chronicle artifacts",
        "build mastermind context (NW bridge)",
        "build mastermind feedback summary (reverse bridge)",
        "build neuralweb health (PR-C — NW lobe-status surface)",
        "build neuralweb daily brief (PR-D — NW daily brief surface, engine phase)",
        "build attention_deterministic (PR-4 M2 — deterministic operator-attention items)",
        "build_evidence_clock (Global Evidence Clock v1)",
        "options_flow_attention reflex trigger (W-D — nightly EOD fold)",
        "commit engine outputs",
        "assemble machine-consumable feeds (site/feeds -> R2)",
        "publish heavy per-ticker stores to R2 (additive; no-op without creds)"]


def _daily_engine_steps() -> list[dict]:
    doc = yaml.safe_load((ROOT / ".github/workflows/daily.yml").read_text())
    return doc["jobs"]["engine"]["steps"]


def _fif_step(steps: list[dict]) -> tuple[int, dict]:
    hits = [(i, s) for i, s in enumerate(steps) if MODULE_TOKEN in str(s.get("run", ""))]
    assert len(hits) == 1, f"expected exactly one daily.yml engine step running {MODULE_TOKEN}"
    return hits[0]


# ---------------------------------------------------------------------------
# gate 5(a) — no new timer/service/cron owns this lane
# ---------------------------------------------------------------------------
def test_no_deploy_unit_mentions_the_lane():
    units = list((ROOT / "app" / "deploy").glob("*.timer")) +         list((ROOT / "app" / "deploy").glob("*.service"))
    assert units, "app/deploy unit glob unexpectedly found nothing"
    for unit in units:
        assert "fif_saved_research" not in unit.read_text(encoding="utf-8"), (
            f"{unit.name} mentions fif_saved_research")


def test_no_workflow_other_than_daily_runs_the_module_and_none_schedules_it():
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        mentions = "fif_saved_research" in text
        if wf.name == "daily.yml":
            assert mentions, "daily.yml must carry the one X2-n step"
            continue
        assert not mentions, (
            f"{wf.name} mentions fif_saved_research — only daily.yml may run it")


def test_no_workflow_adds_a_schedule_entry_for_the_lane():
    # The lane rides daily.yml's incumbent nightly schedule only: inside
    # daily.yml the token must appear exactly once and never inside an `on:`
    # block (no new cron/timer of its own).
    text = (ROOT / ".github" / "daily.yml").read_text(encoding="utf-8") \
        if (ROOT / ".github" / "daily.yml").exists() else \
        (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
    assert text.count(MODULE_TOKEN) == 1
    on_block = text.split("jobs:", 1)[0]
    assert MODULE_TOKEN not in on_block


# ---------------------------------------------------------------------------
# gate 5(b) — exactly ONE dag.yml step + ONE daily.yml step
# ---------------------------------------------------------------------------
def test_exactly_one_dag_step_runs_the_module():
    doc = yaml.safe_load((ROOT / "config" / "dag.yml").read_text())
    hits = []
    for lane in doc.get("lanes", []):
        for step in lane.get("steps", []):
            mods = [step.get("module", "")]
            for members in (step.get("cluster") or {}).values():
                mods.extend(m.split()[0] for m in members)
            if any(f".{MODULE_TOKEN}" in f" {m}" or m.endswith(f".{MODULE_TOKEN}")
                   for m in mods):
                hits.append((lane.get("job"), step.get("id")))
    assert hits == [("engine", "fif_saved_research_notifications")], hits


def test_exactly_one_daily_step_runs_the_module():
    steps = _daily_engine_steps()
    idx, step = _fif_step(steps)
    names = [s.get("name", "") for s in steps]
    assert names[-1] == W2_FINISH_STEP, "the W2 timings finish step stays the engine job's last step"
    assert idx == len(steps) - 2, "the X2-n step sits directly ahead of the W2 finish step"


# ---------------------------------------------------------------------------
# S2 — the daily step's shape and placement
# ---------------------------------------------------------------------------
def test_daily_step_shape_is_non_fatal_and_bounded():
    _, step = _fif_step(_daily_engine_steps())
    # Delivery-tail law (tests/test_push_retry.py) + bounded post-cancel
    # grace use: always(), and a 3-minute cap so a wedged enabled run can
    # never starve the W2 finish step that follows it.
    assert step.get("if") == "always()"
    assert step.get("timeout-minutes") == 3
    assert step.get("continue-on-error") is True
    run = step["run"]
    # Seat ruling X2-n r1 R2: a cancelled nightly skips before the module
    # runs, so the run line is the cancel-skip prefix, then the module.
    skip = (
        '[ "${{ job.status }}" = "cancelled" ] && '
        '{ echo "fif saved research notifications: job cancelled, skipping"; exit 0; }; '
    )
    assert run.startswith(skip)
    assert run[len(skip):].startswith(f"python -m scripts.{MODULE_TOKEN}")
    assert '|| echo "::warning::' in run and "non-fatal" in run


def test_daily_step_env_is_the_c4_names_plus_the_two_flags():
    _, step = _fif_step(_daily_engine_steps())
    env = step.get("env") or {}
    assert set(env) == {
        "SUPABASE_SERVICE_ROLE_KEY",
        "FIF_SAVED_RESEARCH_ENABLE",
        "ALERT_DRAIN_ENABLE",
    }
    assert env["SUPABASE_SERVICE_ROLE_KEY"] == "${{ secrets.SUPABASE_SERVICE_KEY }}"
    assert env["FIF_SAVED_RESEARCH_ENABLE"] == "${{ secrets.FIF_SAVED_RESEARCH_ENABLE }}"
    assert env["ALERT_DRAIN_ENABLE"] == "${{ secrets.ALERT_DRAIN_ENABLE }}"


def test_daily_step_sits_after_every_render_critical_step():
    steps = _daily_engine_steps()
    names = [s.get("name", "") for s in steps]
    idx, _ = _fif_step(steps)
    for rc_name in RENDER_CRITICAL_STEPS:
        assert rc_name in names, (
            f"C5 render-critical step {rc_name!r} no longer exists in the engine "
            "job — re-derive the census before moving the X2-n step")
        assert names.index(rc_name) < idx, (
            f"X2-n step must come after render-critical step {rc_name!r}")


# ---------------------------------------------------------------------------
# gate 5(c) — no macro DDL in the new files
# ---------------------------------------------------------------------------
def test_no_create_table_in_new_files():
    # The DDL token is assembled at runtime so this scanner never itself
    # contains the literal phrase it forbids.
    verb, noun = "cre" + "ate", "tab" + "le"
    pattern = re.compile(verb + r"\s+" + noun, re.IGNORECASE)
    for path in NEW_FILES:
        assert not pattern.search(path.read_text(encoding="utf-8")), (
            f"{path.name} contains DDL ({verb} {noun} is forbidden in the macro repo)")


# ---------------------------------------------------------------------------
# gate 5(d) — watchstore.js is the ONLY templates/*.js watchlist writer
# ---------------------------------------------------------------------------
def test_watchstore_is_the_only_templates_js_watchlist_writer():
    for js in sorted((ROOT / "templates").glob("*.js")):
        text = js.read_text(encoding="utf-8")
        writes = re.search(
            r"\.from\(\s*['\"]watchlists?['\"]\s*\)\s*\.(insert|update|delete|upsert)", text)
        if js.name == "watchstore.js":
            continue  # the designated owner
        assert not writes, f"{js.name} writes watchlists/watchlist_symbols"


# ---------------------------------------------------------------------------
# S5/P1 — the producer imports no mail sender and no app/ module
# ---------------------------------------------------------------------------
def test_producer_imports_no_mail_sender_and_no_app_module():
    tree = ast.parse(PRODUCER.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
    for module in sorted(imported):
        assert not module.startswith("app"), f"producer imports {module}"
        assert "mailer" not in module and "smtp" not in module, (
            f"producer imports a mail sender: {module}")
    source = PRODUCER.read_text(encoding="utf-8")
    assert "smtplib" not in source and "app.mailer" not in source


# ---------------------------------------------------------------------------
# cross-user reads (gate 3a, pure-function level)
# ---------------------------------------------------------------------------
def test_partition_never_reads_one_users_list_into_another_users_rows():
    lists = [
        {"id": "L-A", "user_id": "alice", "name": "Filing Forensics"},
        {"id": "L-B", "user_id": "bob", "name": "Filing Forensics"},
    ]
    symbols = [
        {"watchlist_id": "L-A", "symbol": "smci"},   # lower-case on the wire
        {"watchlist_id": "L-B", "symbol": "TSLA"},
    ]
    subs = producer.build_subscriptions(lists, symbols)
    assert subs == {"alice": {"SMCI"}, "bob": {"TSLA"}}
    inputs = producer.TriggerInputs(
        state_doc={"companies": {
            "SMCI": {"symbol": "SMCI", "cik": 1374360, "findings": [
                {"id": "f1", "priority": "high", "title_en": "Margin compression"}]},
            "TSLA": {"symbol": "TSLA", "cik": 1384158, "findings": []},
        }, "generated_at": "2026-10-12T00:00:00Z"},
    )
    pairs = producer.derive_events(subscriptions=subs, inputs=inputs)
    owners = {user for user, _event in pairs}
    assert owners == {"alice"}
    for user, event in pairs:
        assert user == "alice" and event.ticker == "SMCI"
