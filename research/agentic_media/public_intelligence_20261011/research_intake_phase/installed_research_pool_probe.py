"""Read-only installed planner acceptance with isolated historical fixtures.

Run after protected landing: python -B probe.py /opt/macro reviewed-manifest.json.
No actual report is qualified, generated, staged or published by this probe.
"""
import contextlib
import copy
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

root = Path(sys.argv[1]).resolve()
expected = json.loads(Path(sys.argv[2]).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert {rel: sha(root / rel) for rel in expected} == expected, "reviewed source manifest drift"
sys.path.insert(0, str(root))
from engine.press import desk_planner as P, writer as W


def head():
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def snapshot():
    paths = [root / "config/press.yml", root / "data/press/published.jsonl",
             root / "data/research_vault/catalog.json"]
    paths += list((root / "data/press/staging").glob("*.json"))
    paths += list((root / "content/seo/blog").glob("*.md"))
    return {str(p.relative_to(root)): sha(p) for p in paths if p.is_file()}


cfg0 = P.load_config(root)
assert cfg0["desks"]["research_desk"]["candidate_pool"] == 8
assert cfg0["desks"]["research_desk"]["cadence_per_day"] == 1
assert cfg0["desks"]["research_note"]["cadence_per_day"] == 0
before_head, before = head(), snapshot()
controls = []
clock = date(2026, 7, 26)


def item(i):
    return {"id": f"pool-{i:02d}", "title": "Historical fixture: rates and households",
            "institution": "Fixture desk", "published_at": "2026-07-25T09:00:00Z",
            "summary_points": ["The desk reports household spending growth of 3 percent."],
            "pages": 8, "top_pick": False, "tags": [], "tickers": []}


with tempfile.TemporaryDirectory(prefix="mmx-research-pool-") as directory:
    parent = Path(directory)

    def fixture(name):
        path = parent / name
        (path / "data/research_vault").mkdir(parents=True)
        (path / "data/press/staging").mkdir(parents=True)
        cfg = copy.deepcopy(cfg0)
        # Only fixture destinations; the shipped production path definitions are unchanged.
        assert cfg["paths"]["staging_dir"] == "data/press/staging"
        assert cfg["paths"]["ledger"] == "data/press/published.jsonl"
        return path, cfg

    def plan(path, cfg, blocked=()):
        with contextlib.redirect_stdout(io.StringIO()):
            return P.plan(["research_desk", "research_note"], root=path, cfg=cfg,
                          as_of=clock.isoformat(), extra_blocked_refs=blocked)

    with patch.object(W, "write", side_effect=AssertionError("writer reached")) as writer:
        for ranked in (True, False):
            for mechanism in ("published", "staged", "explicit"):
                name = f"{mechanism}-{'ranked' if ranked else 'fallback'}"
                path, cfg = fixture(name)
                if not ranked:
                    cfg.pop("research_triage")
                    cfg["desks"]["research_desk"].pop("triage_tier")
                items = [item(i) for i in range(10)]
                catalog = path / "data/research_vault/catalog.json"
                catalog.write_text(json.dumps({"items": items}))
                with contextlib.redirect_stdout(io.StringIO()):
                    order, metadata = P._triage_order(cfg, clock, path, items)
                ids = order or [row["id"] for row in items]
                blocked = ["research_vault:" + rid for rid in ids[:8]]
                extra = []
                if mechanism == "published":
                    (path / cfg["paths"]["ledger"]).write_text(json.dumps({"sources": blocked}) + "\n")
                elif mechanism == "staged":
                    (path / cfg["paths"]["staging_dir"] / "held.json").write_text(
                        json.dumps({"id": "held", "status": "approval_required", "sources": blocked}))
                else:
                    extra = blocked

                def fixture_snapshot():
                    return {str(p.relative_to(path)): sha(p) for p in path.rglob("*") if p.is_file()}

                initial = fixture_snapshot()
                slots = plan(path, cfg, extra)
                assert [slot["sources"] for slot in slots] == [["research_vault:" + ids[8]]]
                assert slots[0]["desk"] == "research_desk"
                assert slots[0]["triage"]["rank"] == metadata.get(ids[8], {}).get("rank")
                assert initial == fixture_snapshot()
                controls.append(name)

        path, cfg = fixture("pool-bound")
        cfg.pop("research_triage")
        cfg["desks"]["research_desk"].pop("triage_tier")
        items = [item(i) for i in range(10)]
        for row in items[1:9]:
            row["summary_points"] = ["The current regime is a front-end signal."]
            assert not P._press_safe(row["summary_points"][0])
        catalog = path / "data/research_vault/catalog.json"
        catalog.write_text(json.dumps({"items": items}))
        assert plan(path, cfg, ["research_vault:pool-00"]) == []
        controls.append("eight-unblocked-candidate-budget-preserved")

        items = [dict(item(0), published_at="2026-07-27T09:00:00Z"),
                 dict(item(1), published_at="2026-07-04T09:00:00Z")]
        catalog.write_text(json.dumps({"items": items}))
        assert plan(path, cfg) == []
        controls.append("future-and-out-of-window-refusal")

        path, cfg = fixture("explicit-dossier")
        row = dict(item(0), tickers=["CAT", "MISSING", "CAT", "index", "../CAT", None])
        catalog = path / "data/research_vault/catalog.json"
        catalog.write_text(json.dumps({"items": [row]}))
        stocks = path / "site/stocks"
        stocks.mkdir(parents=True)
        for ticker in ("CAT", "UNRELATED", "index"):
            (stocks / f"{ticker}.html").write_text("<html></html>")
        initial_catalog = sha(catalog)
        slot, = plan(path, cfg)
        assert slot["story"]["tickers"] == ["CAT", "MISSING"]
        assert slot["sources"] == ["research_vault:pool-00"]
        assert slot["allowed_links"] == [slot["primary_source"]["url"],
            "https://www.mastermind-x.com/stocks/CAT.html"]
        assert sha(catalog) == initial_catalog
        from engine.press import validators as V
        for ticker, accepted in (("CAT", True), ("UNRELATED", False), ("MISSING", False)):
            draft = {"body_html": f'<p><a href="/stocks/{ticker}.html">Company</a></p>'}
            assert V.check_link_allowlist(draft, slot, cfg)["ok"] is accepted
        controls.append("explicit-source-dossier-only-and-validator-refusals")

        for raw in (None, "CAT", {"CAT": True}, []):
            row.update(title="Caterpillar CAT research", tickers=raw)
            catalog.write_text(json.dumps({"items": [row]}))
            slot, = plan(path, cfg)
            assert slot["story"]["tickers"] == []
            assert slot["allowed_links"] == [slot["primary_source"]["url"]]
        row["tickers"] = ["CAT"]
        catalog.write_text(json.dumps({"items": [row]}))
        cfg["public_link_prefixes"] = ["/research/"]
        slot, = plan(path, cfg)
        assert slot["story"]["tickers"] == ["CAT"]
        assert slot["allowed_links"] == [slot["primary_source"]["url"]]
        controls.append("no-inferred-ticker-and-public-prefix-preserved")

        catalog.write_text(json.dumps({"items": [item(0)]}))
        cfg["desks"]["research_desk"]["cadence_per_day"] = 0
        assert plan(path, cfg) == []
        controls.append("zero-cadence-and-dark-note-preserved")
        # The Brief consumes the original corrected Prophet ledger and clocks.
        from engine.chronicle.adapters import adapt_prophet_ledger
        from engine.press.validators import fact_tier_index
        from engine.prophet_integrity import LEDGER_QUARANTINE_SCHEMA
        path, cfg = fixture("prophet-scope")
        ledger = path / "data/prophet/ledger.jsonl"
        ledger.parent.mkdir(parents=True)
        chronicle = path / "data/chronicle/events.jsonl"
        chronicle.parent.mkdir(parents=True)
        row = {"schema": "prophet.ledger/v1", "id": "TEST-BULL-20260712",
               "asset": "TEST", "direction": "BULL", "outcome": "INVALIDATED",
               "stock_result_pct": -13.5521, "days_held": 14,
               "close_date": "2026-07-26", "asof": "2026-07-26",
               "signal_date": "2026-07-12", "signal_date_basis": "tier_event_date",
               "source_marker_date": "2026-07-12", "entry_date": "2026-07-12",
               "signal_provisional": True, "confirmed_date": None}
        ledger.write_text(json.dumps(row) + "\n")
        events, gap = adapt_prophet_ledger(path)
        assert not gap and len(events) == 1
        chronicle.write_text(json.dumps(events[0]) + "\n")
        def brief():
            return P.plan(["brief"], root=path, cfg=cfg, as_of=clock)
        slot, = brief()
        scope = slot["facts"][0]["context_relevance"]
        assert "provisional=true" in scope and "not executed trades" in scope
        assert "confirmation=not recorded" in scope and "closed=2026-07-26" in scope
        plain = copy.deepcopy(slot)
        plain["facts"][0].pop("context_relevance")
        assert fact_tier_index(slot) == fact_tier_index(plain)
        assert scope in W.build_prompt(slot, cfg)[1]
        controls.append("prophet-paper-plan-scope-without-new-receipt-credit")
        row.update(signal_date_basis="legacy_formation_alias", source_marker_date="2026-04-12")
        ledger.write_text(json.dumps(row) + "\n")
        slot, = brief()
        scope = slot["facts"][0]["context_relevance"]
        assert "source_marker=2026-04-12" in scope and "legacy alias is not a fresh signal" in scope
        controls.append("prophet-legacy-marker-clock-preserved")
        original = ledger.read_bytes()
        for field, value in (("outcome", "T1_HIT"), ("asof", "2026-07-27")):
            changed = dict(row, **{field: value})
            ledger.write_text(json.dumps(changed) + "\n")
            assert brief() == []
        ledger.write_bytes(original)
        (ledger.parent / "ledger_quarantine.json").write_text(json.dumps({
            "schema": LEDGER_QUARANTINE_SCHEMA, "count": 1,
            "quarantined": [{"id": row["id"], "reason": "fixture refusal"}]}))
        assert brief() == []
        controls.append("prophet-stale-future-quarantined-refused")
        (ledger.parent / 'ledger_quarantine.json').unlink()
        row.update(price_basis_date='2026-07-12', recorded_at='2026-07-13')
        ledger.write_text(json.dumps(row) + '\n')
        native_plan = {key: value for key, value in row.items() if key not in (
            'outcome', 'stock_result_pct', 'days_held', 'close_date')}
        native_plan.update(schema='prophet.trade_plan/v1', asof='2026-07-13',
            entry=51.8, invalidation=46.22, targets=[60.17, 68.54], trigger=51.8,
            entry_status='bounce_wait', authority_tier='display')
        plan_path = path / 'site/prophet/plans' / (row['id'] + '.json')
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text(json.dumps(native_plan))
        slot, = brief()
        detail, = [f for f in slot['facts'] if f['id'].startswith('prophet_plan_')]
        assert detail['values'] == ['51.8', '46.22', '60.17', '68.54']
        assert detail['dated'] == '2026-07-13'
        assert 'Historical paper-plan thresholds' in detail['text']
        assert 'not executed prices or achieved returns' in detail['context_relevance']
        assert detail['context_relevance'] in W.build_prompt(slot, cfg)[1]
        assert slot['source_revisions']['artifact:site/prophet/plans/' + plan_path.name] == 'sha256:' + sha(plan_path)
        controls.append('native-plan-thresholds-dated-limited-and-byte-bound')
        for field, value in (('asset', 'OTHER'), ('entry_date', '2026-07-14'),
                             ('asof', '2026-07-27'), ('integrity_status', 'quarantined'),
                             ('entry', True), ('targets', [44.0]),
                             ('origination_mode', 'outage_backfill_fixture')):
            plan_path.write_text(json.dumps(dict(native_plan, **{field: value})))
            assert brief() == []
        plan_path.write_text(json.dumps(native_plan))
        controls.append('native-plan-mismatch-future-quarantine-and-geometry-refusals')
        correction_path = ledger.parent / 'plan_corrections.jsonl'
        correction = {'schema': 'prophet.plan_correction/v1', 'id': row['id'] + ':price:fix',
            'corrects_id': row['id'], 'field': 'price_basis_date', 'old_value': None,
            'new_value': '2026-07-12', 'basis': 'Fixture native price session',
            'corrected_at': '2026-07-14', 'evidence': {'price_source': 'fixture'}}
        plan_path.write_text(json.dumps(dict(native_plan, price_basis_date=None)))
        correction_path.write_text(json.dumps(correction) + '\n')
        slot, = brief()
        assert 'artifact:data/prophet/plan_corrections.jsonl' in slot['source_revisions']
        correction['corrected_at'] = '2026-07-27'
        correction_path.write_text(json.dumps(correction) + '\n')
        assert brief() == []
        correction_path.unlink()
        plan_path.write_text(json.dumps(native_plan))
        controls.append('native-plan-correction-consumed-and-future-correction-refused')
        from engine import prophet_integrity as I
        original_loader = I.load_effective_plans
        def racing_read(repo):
            result = original_loader(repo)
            plan_path.write_text(json.dumps(dict(native_plan, entry=52.0)))
            return result
        with patch.object(I, 'load_effective_plans', side_effect=racing_read):
            assert brief() == []
        plan_path.write_text(json.dumps(native_plan))
        controls.append('native-plan-changed-input-refused')
        (plan_path.parent / 'alias.json').write_text(json.dumps(native_plan))
        assert brief() == []
        controls.append('native-plan-duplicate-identity-refused')
        assert writer.call_count == 0

assert before == snapshot() and before_head == head()
assert {rel: sha(root / rel) for rel in expected} == expected
print(json.dumps({"probe_passed": True, "controls": controls, "head": before_head,
    "execution_location": "installed_vps" if root == Path("/opt/macro") else "local_source",
    "checked_source_sha256": expected, "real_provider_calls": 0,
    "production_inputs_unchanged": True, "production_staging_writes": 0,
    "public_writes": 0, "d14_credit": 0,
    "scope": "Historical isolated planner fixtures; not source or publication approval"}, indent=2))
