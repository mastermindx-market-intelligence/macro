"""tests/test_transmission_publish.py — TXI W4 site-publication adapter (deliverable A).

engine.transmission_publish.derive_display_subset() projects the canonical
transmission_chains.v1 artifact into the site/transmission_chains.json display subset.
These lock:
  - the published subset schema + every field the brief names, with bilingual labels
  - blast channels keep names + numeric cuts + the unevaluable bucket (a client rebuilds
    membership client-side); a dropped/proxy channel keeps its bilingual note
  - the one-render-lag note is stamped (build_site runs before the chains step)
  - display_only=True; the word "validated" never appears
  - ABSENT / empty / malformed input degrades to an empty chains list (never raises), so
    the build_site emit publishes nothing at all
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parent / "fixtures" / "transmission" / "chain_state.json"


@pytest.fixture()
def chain_state() -> dict:
    return json.loads(FIX.read_text(encoding="utf-8"))


def _subset(cs: dict) -> dict:
    from engine.transmission_publish import derive_display_subset
    return derive_display_subset(cs)


# ---------------------------------------------------------------------------
# Schema + bilingual labels
# ---------------------------------------------------------------------------
def test_subset_top_level_shape(chain_state):
    sub = _subset(chain_state)
    assert sub["schema"] == "transmission_chains_display.v1"
    assert sub["display_only"] is True
    assert sub["asof"] == chain_state["asof"]
    # substrate_asof passes through the {min,max} stamp
    assert sub["substrate_asof"] == chain_state["substrate"]["substrate_asof"]
    # lag_note is bilingual and non-empty (build_site publishes BEFORE the chains step)
    assert sub["lag_note"]["en"] and sub["lag_note"]["zh"]
    assert isinstance(sub["chains"], list) and len(sub["chains"]) == 4


def test_chain_fields_and_bilingual_labels(chain_state):
    sub = _subset(chain_state)
    ids = {c["id"] for c in sub["chains"]}
    assert "dollar_spike_em_multinational" in ids
    for c in sub["chains"]:
        assert set(("id", "label", "state", "tier", "hops", "blast", "caveats")).issubset(c)
        assert c["label"]["en"] and c["label"]["zh"], c["id"]
        assert c["tier"] == "hypothesis"
        assert c["state"] in ("dormant", "arming", "propagating", "expressed", "failed", "expired")
        assert isinstance(c["caveats"], list) and c["caveats"]


def test_hop_subset_bilingual_and_confirmed_dates(chain_state):
    sub = _subset(chain_state)
    dollar = next(c for c in sub["chains"] if c["id"] == "dollar_spike_em_multinational")
    assert len(dollar["hops"]) == 2
    h0, h1 = dollar["hops"]
    assert h0["confirmed"] is True and h0["asof"] == "2026-07-21"
    assert h1["confirmed"] is False and h1["asof"] is None
    for h in dollar["hops"]:
        assert set(("id", "label", "confirmed", "asof")).issubset(h)
        assert h["label"]["en"] and h["label"]["zh"]
        # the machine value receipts are NOT published in the subset
        assert "value_receipt" not in h


def test_blast_channels_keep_names_cuts_unevaluable_and_notes(chain_state):
    sub = _subset(chain_state)
    dollar = next(c for c in sub["chains"] if c["id"] == "dollar_spike_em_multinational")
    proxy = dollar["blast"]["em_commodity_sector_proxy"]
    assert proxy["n"] == 163
    assert proxy["unevaluable"] == 12               # missing-field bucket always carried
    assert "NVDA" in proxy["names"]                 # full ticker array preserved
    assert proxy["label"]["en"] and proxy["label"]["zh"]
    assert proxy["note"]["en"] and proxy["note"]["zh"]  # proxy note passes through bilingual
    # a channel with a printed numeric cut keeps it (client rebuilds membership from it)
    debt = dollar["blast"]["dollar_debt_burden"]
    assert debt["cuts"].get("financials.debt_to_assets") == 0.61
    # a dropped channel (resolved:false in the source) still emits, with its note
    credit = next(c for c in sub["chains"] if c["id"] == "credit_spreads_refinancing")
    dropped = credit["blast"]["floating_rate_debt"]
    assert dropped["n"] == 0 and dropped["unevaluable"] == 1615
    assert dropped["note"]["en"].startswith("DROPPED")


def test_dormant_chain_has_empty_blast(chain_state):
    sub = _subset(chain_state)
    vol = next(c for c in sub["chains"] if c["id"] == "vol_regime_deleveraging")
    assert vol["state"] == "dormant"
    assert vol["blast"] == {}


# ---------------------------------------------------------------------------
# Banned-vocab (CI-enforced elsewhere; belt-and-suspenders here)
# ---------------------------------------------------------------------------
def test_no_validated_claim_in_subset(chain_state):
    sub = _subset(chain_state)
    blob = json.dumps(sub, ensure_ascii=False).lower()
    assert "validated" not in blob


# ---------------------------------------------------------------------------
# Fail-open — absent / empty / malformed input never raises
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [{}, None, {"chains": None}, {"chains": "junk"}, 42, []])
def test_degrades_on_bad_input(bad):
    sub = _subset(bad)
    assert sub["display_only"] is True
    assert sub["chains"] == []
    assert sub["schema"] == "transmission_chains_display.v1"


def test_missing_hop_label_falls_back_to_hop_id():
    """A pre-W4 chain whose hops carry no `label` still publishes a non-blank label
    (the hop id), never invented copy."""
    cs = {
        "asof": "2026-07-23", "caveats": [],
        "chains": [{
            "chain": "legacy", "title": {"en": "Legacy", "zh": "旧链"},
            "state": "arming", "tier": "hypothesis",
            "hops": [{"id": "a->b", "from": "a", "to": "b", "confirmed": True, "asof": "2026-07-20"}],
            "blast": {},
        }],
    }
    sub = _subset(cs)
    h = sub["chains"][0]["hops"][0]
    assert h["label"] == {"en": "a->b", "zh": "a->b"}


# ---------------------------------------------------------------------------
# build_site emit path: absent artifact publishes NOTHING (no file, no error)
# ---------------------------------------------------------------------------
def test_build_site_skips_when_artifact_absent(tmp_path):
    """Mirror the build_site guard: when data/transmission/chain_state.json is absent,
    no site/transmission_chains.json is written and nothing raises."""
    site = tmp_path / "site"
    site.mkdir()
    data_dir = tmp_path / "data"
    cs_path = data_dir / "transmission" / "chain_state.json"
    # replicate the exact guard used in scripts/build_site.py
    wrote = False
    try:
        if cs_path.exists():
            from engine.transmission_publish import derive_display_subset
            _cs = json.loads(cs_path.read_text(encoding="utf-8"))
            _subset = derive_display_subset(_cs)
            if _subset.get("chains"):
                (site / "transmission_chains.json").write_text(json.dumps(_subset))
                wrote = True
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"emit path raised on absent artifact: {e}")
    assert wrote is False
    assert not (site / "transmission_chains.json").exists()


def test_build_site_emit_writes_valid_json_when_present(tmp_path, chain_state):
    """With the artifact present, the emit writes parseable JSON with chains."""
    site = tmp_path / "site"; site.mkdir()
    data_dir = tmp_path / "data" / "transmission"; data_dir.mkdir(parents=True)
    (data_dir / "chain_state.json").write_text(json.dumps(chain_state), encoding="utf-8")
    from engine.transmission_publish import derive_display_subset
    cs = json.loads((data_dir / "chain_state.json").read_text(encoding="utf-8"))
    subset = derive_display_subset(cs)
    (site / "transmission_chains.json").write_text(
        json.dumps(subset, ensure_ascii=False), encoding="utf-8")
    reloaded = json.loads((site / "transmission_chains.json").read_text(encoding="utf-8"))
    assert reloaded["schema"] == "transmission_chains_display.v1"
    assert len(reloaded["chains"]) == 4


# ---------------------------------------------------------------------------
# rev-1 — the `turn_watch` turn-watch annotation passes through to the site row
# ---------------------------------------------------------------------------
def _one_chain_state(chain_extra: dict) -> dict:
    return {
        "asof": "2026-08-07", "caveats": [],
        "chains": [{
            "chain": "real_rate_peak_gold_rerate",
            "title": {"en": "Real-rate peak → gold re-rates", "zh": "实际利率见顶 → 黄金估值修复"},
            "state": "arming", "tier": "hypothesis",
            "hops": [{"id": "a->b", "from": "a", "to": "b", "confirmed": False, "asof": None}],
            "blast": {},
            **chain_extra,
        }],
    }


def test_turn_watch_passes_through_to_the_site_row():
    tw = {"stalling": True,
          "label": {"en": "At the extreme, momentum fading", "zh": "处于极值、动能减弱"},
          "receipts": [{"series": "DFII10", "metric": "off_high_bp", "window": 10,
                        "value": 6.0, "op": "gte", "threshold": 4, "passed": True}]}
    row = _subset(_one_chain_state({"turn_watch": tw}))["chains"][0]
    assert row["turn_watch"]["stalling"] is True
    assert row["turn_watch"]["label"]["en"] and row["turn_watch"]["label"]["zh"]
    # the receipt rides along: it IS the Tier-2 disclosure behind the plain-word chip
    assert row["turn_watch"]["receipts"][0]["metric"] == "off_high_bp"


def test_turn_watch_absent_when_the_chain_carries_none():
    """A chain with no open episode / no `stall:` block emits no key at all — the subset must
    not invent a falsy annotation the client would have to special-case."""
    row = _subset(_one_chain_state({}))["chains"][0]
    assert "turn_watch" not in row
    # the fixture-backed (pre-rev-1) artifact likewise publishes no annotation
    cs = json.loads(FIX.read_text(encoding="utf-8"))
    assert all("turn_watch" not in c for c in _subset(cs)["chains"])


def test_turn_watch_passthrough_is_a_copy_not_an_alias():
    tw = {"stalling": False, "receipts": []}
    cs = _one_chain_state({"turn_watch": tw})
    row = _subset(cs)["chains"][0]
    row["turn_watch"]["stalling"] = True
    assert tw["stalling"] is False, "the projection must not mutate the canonical artifact"


# UIUX: scenario cards keep a compact glance tier without hiding the remaining asset.
def _scenario_ui_source():
    return (Path(__file__).resolve().parents[1] / 'templates/transmission.html.j2').read_text()


def _scenario_ui_render(headwinds, tailwinds, labels=None):
    from jinja2 import Environment
    source = _scenario_ui_source()
    start = source.index('<!-- ===================== SCENARIOS')
    end = source.index('<!-- ===================== STUDY SHELF', start)
    prefix = source[:source.index('<!DOCTYPE html>')]
    meta_start = source.index('{% set SC_META')
    meta = source[meta_start:source.index('} %}', meta_start) + 4]
    tx = {'transmission': labels or {}, 'scenarios': [{
        'key': 'real_up50', 'label': {'en': 'Example', 'zh': '示例'},
        'headwinds': headwinds, 'tailwinds': tailwinds}]}
    return Environment(autoescape=True).from_string(prefix + meta + source[start:end]).render(tx=tx)


def _scenario_ui_rows(n, positive=False):
    return [{'asset': f'ASSET{i}', 'label': f'Asset {i} (context)',
             'implied_move_pct': (1 if positive else -1) * (10-i)} for i in range(n)]


@pytest.mark.parametrize('side', ['headwinds', 'tailwinds'])
@pytest.mark.parametrize('count', [0, 1, 4, 5, 7])
def test_scenario_ui_disclosure_keeps_all_source_rows_in_order(side, count):
    import re
    rows = _scenario_ui_rows(count, side == 'tailwinds')
    html = _scenario_ui_render(rows if side == 'headwinds' else [],
                               rows if side == 'tailwinds' else [])
    assert html.count('class="sx-item"') == count
    assert re.findall(r'data-asset="([^"]+)"', html) == [r['asset'] for r in rows]
    assert html.count('<details class="sx-extra">') == int(count > 4)
    if count > 4:
        assert html.index('data-asset="ASSET3"') < html.index('<details class="sx-extra">')
        assert html.index('<details class="sx-extra">') < html.index('data-asset="ASSET4"')
        assert f'Show {count-4} more' in html and 'Show fewer' in html
        assert '再看' in html and '收起' in html
        assert '<details class="sx-extra" open' not in html
    else:
        assert 'Show fewer' not in html


def test_scenario_ui_reuses_canonical_chinese_asset_labels():
    row = {'asset': 'X', 'label': 'English name (context)', 'implied_move_pct': -2.5}
    html = _scenario_ui_render([row], [], {'X': {'label': {'en': row['label'], 'zh': '中文名称（背景）'}}})
    assert '<span class="l-en">English name</span>' in html
    assert '<span class="l-zh">中文名称</span>' in html
    assert '中文名称（背景）' not in html


def test_scenario_ui_prefers_explicit_labels_and_has_honest_fallback():
    rows = [{'asset': 'X', 'label': {'en': 'Preferred', 'zh': '明确名称'}, 'implied_move_pct': -1},
            {'asset': 'Y', 'label': 'Unmapped asset', 'implied_move_pct': -2}]
    html = _scenario_ui_render(rows, [], {'X': {'label': {'en': 'Old', 'zh': '旧名称'}}})
    assert '明确名称' in html and '旧名称' not in html
    assert '<span class="l-zh">Unmapped asset</span>' in html


def test_scenario_ui_escapes_labels_in_both_languages():
    row = {'asset': 'X', 'label': {'en': '<script>bad</script>', 'zh': '<img src=x>'}, 'implied_move_pct': -1}
    html = _scenario_ui_render([row], [])
    assert '<script>bad' not in html and '<img src=x>' not in html
    assert '&lt;script&gt;' in html and '&lt;img src=x&gt;' in html


def test_scenario_ui_retains_full_shared_scale_and_signed_values():
    import re
    head = _scenario_ui_rows(5)
    tail = [{'asset': 'PLUS', 'label': 'Positive', 'implied_move_pct': 20.0}]
    html = _scenario_ui_render(head, tail)
    widths = re.findall(r'class="[du]" style="width:([0-9.]+)%"', html)
    assert widths == ['50.0', '45.0', '40.0', '35.0', '30.0', '100.0']
    assert '-6.0%' in html and '+20.0%' in html
    assert 'not forecasts' in html and '并非预测' in html


def test_scenario_ui_controls_are_native_and_focus_visible():
    src = _scenario_ui_source()
    assert '.sx-extra>summary' in src and 'min-height:40px' in src
    assert '.sx-extra>summary:focus-visible{outline:2px solid currentColor;' in src
    assert '.sx-extra[open]>summary .sx-hide' in src
    assert '.sx-card .sx-item .nm{white-space:normal' in src
    block = src[src.index('<!-- ===================== SCENARIOS'):src.index('<!-- ===================== STUDY SHELF')]
    assert 'onclick=' not in block and 'addEventListener' not in block
    assert '<div class="sx-more">' not in block


def test_scenario_ui_published_css_matches_canonical_source():
    import re, hashlib
    root = Path(__file__).resolve().parents[1]
    html = (root / 'site/transmission.html').read_text()
    refs = re.findall(r'assets/css/([0-9a-f]{8})\.css\?v=\1', html)
    css = [root / 'site/assets/css' / (h + '.css') for h in refs]
    owned = [p for p in css if p.exists() and '.sx-extra>summary' in p.read_text()]
    assert len(owned) == 1
    raw = owned[0].read_bytes()
    assert hashlib.sha256(raw).hexdigest()[:8] == owned[0].stem
    style = re.search(r'<style>(.*?)</style>', _scenario_ui_source(), re.S).group(1)
    import ast
    from jinja2 import Environment
    builder = ast.parse((root / 'scripts/build_transmission.py').read_text())
    color_node = next(n for n in builder.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'C' for t in n.targets))
    canonical = Environment(autoescape=True).from_string(style).render(C=ast.literal_eval(color_node.value))
    assert raw.decode().strip() == canonical.strip()
