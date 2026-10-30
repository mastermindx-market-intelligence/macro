"""China Divergence Radar — SPEC 2: the committed short-horizon record.

Renders the per-horizon block from a synthetic ``radar_ic.json`` payload and pins
``scripts/build_china_radar._load_radar_ic`` as a read-only loader. No ``data/``
read, no ``site/`` write, no builder ``build()``/``main()`` call, no network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

# ci-trigger-closure: data — the builder is read as text only, never imported
_BUILDER = _ROOT / "scripts/build_china_radar.py"

TEMPLATE = "china_radar.html.j2"

CAVEAT_EN = "provisional — windows overlap, still accruing"
CAVEAT_ZH = "初步——窗口重叠，仍在累积"

# Shape of the committed data/china_hub/radar_ic.json (schema china_radar_ic.v1,
# producer engine/china_radar_ic.py). `note` / `ic_all` are internal control
# vocabulary and must never reach the page.
IC = {
    "schema": "china_radar_ic.v1",
    "as_of": "2026-10-16",
    "n_events": 52,
    "ic_all": 0.0317,
    "note": "ACCRUING / DORMANT — Governor stays at trust=1.0 (identity).",
    "by_horizon": {
        "5": {
            "n_matured": 44,
            "by_sign": {"positive": {"n": 26, "dir_accuracy": 0.423},
                        "negative": {"n": 18, "dir_accuracy": 0.611}},
        },
        "10": {
            "n_matured": 42,
            "by_sign": {"positive": {"n": 25, "dir_accuracy": 0.4},
                        "negative": {"n": 17, "dir_accuracy": 0.588}},
        },
        "21": {
            "n_matured": 38,
            "by_sign": {"positive": {"n": 22, "dir_accuracy": 0.542},
                        "negative": {"n": 16, "dir_accuracy": 0.714}},
        },
    },
}


def _make_env():
    """Jinja env mirroring scripts/build_china_radar.py (shape copied from
    tests/test_china_radar_venue.py TestTemplateRender._make_env)."""
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    return env


def _radar():
    return {
        "schema": "china_radar.v1", "is_context_only": True,
        "asof": "2026-07-06", "built": "2026-07-06T00:00:00Z",
        "divergences": [], "in_line": [], "n_active": 0, "n_pairs": 0,
        "disclaimer_en": "Context only.", "disclaimer_zh": "仅供参考。",
    }


def _ledger():
    """The horizon block sits inside the ledger section, so a strip is required."""
    return {
        "schema": "china_radar_ledger.v1", "is_context_only": True,
        "n_total": 52, "n_resolved": 2, "hit_rate": 0.5, "n_open": 50,
        "rows": [{"fired_date": "2026-07-01", "signal_key": "sector_flow",
                  "sector_en": "Semiconductors", "sector_zh": "Semiconductors",
                  "sign": "negative", "rs_at_fire": 67.85, "fwd_rel": -21.13,
                  "status": "hit", "family": None}],
    }


def _render(ic=None):
    return _make_env().get_template(TEMPLATE).render(
        radar=_radar(), ledger=_ledger(), ic=ic)


def _write_ic(tmp_path, text):
    hub = tmp_path / "china_hub"
    hub.mkdir(parents=True, exist_ok=True)
    (hub / "radar_ic.json").write_text(text, encoding="utf-8")


def test_horizon_table_renders_committed_ic_shape():
    """The committed by_horizon block renders with its own as_of and caveat."""
    html = _render(ic=IC)
    assert "44" in html                      # 5d n_matured
    assert "42%" in html                     # 5d positive dir_accuracy 0.423
    assert "61%" in html                     # 5d negative dir_accuracy 0.611
    assert "26" in html and "18" in html     # the n behind each accuracy
    assert "2026-10-16" in html              # the artifact's own as_of
    assert ">5d<" in html and ">10d<" in html and ">21d<" in html
    assert "graded through" in html and "评分截至" in html
    assert CAVEAT_EN in html and CAVEAT_ZH in html
    assert "~3 months" in html and "(90 days)" in html
    assert "约3个月" in html and "90天" in html
    # internal control vocabulary never reaches the page
    assert "ACCRUING" not in html and "trust=1.0" not in html
    assert "ic_all" not in html and "0.0317" not in html


def _horizon_cells(html):
    """Cell text per horizon row of the Short-horizon record table, tags stripped."""
    import re
    i = html.index("短周期记录")
    table = html[i:html.index("</table>", i)]
    rows = {}
    for tr in table.split("<tr>")[2:]:
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                 for c in re.findall(r"<td>(.*?)</td>", tr, re.S)]
        rows[cells[0].split()[0]] = cells[1:]
    return rows


def test_horizon_rows_pin_each_cell():
    """Each row prints its own matured count and the n behind each sign's accuracy."""
    rows = _horizon_cells(_render(ic=IC))
    assert rows["5d"] == ["44", "42% (26)", "61% (18)"]
    assert rows["10d"] == ["42", "40% (25)", "59% (17)"]
    assert rows["21d"] == ["38", "54% (22)", "71% (16)"]


def test_no_ic_renders_nothing():
    """ic=None / {} / no by_horizon / empty by_horizon → no horizon section."""
    for ic in (None, {}, {"as_of": "2026-10-16"}, {"by_horizon": {}}):
        html = _render(ic=ic)
        assert "graded through" not in html
        assert "评分截至" not in html
        assert "provisional" not in html and CAVEAT_ZH not in html
        assert ">5d<" not in html
        assert "Accountability ledger" in html      # the strip still renders


def test_horizon_without_by_sign_is_skipped():
    """A horizon block with an empty by_sign renders no row and no empty shell."""
    ic = {"as_of": "2026-10-16", "by_horizon": {"5": {"n_matured": 2, "by_sign": {}}}}
    html = _render(ic=ic)
    assert ">5d<" not in html
    assert "<td>2</td>" not in html
    assert "graded through" not in html
    assert "Accountability ledger" in html


def test_load_radar_ic_returns_empty_on_bad_file(tmp_path, monkeypatch):
    from scripts import build_china_radar as b
    _write_ic(tmp_path, "{ not json")
    monkeypatch.setattr(b.config, "data_dir", lambda: tmp_path)
    assert not b._load_radar_ic()


def test_load_radar_ic_reads_the_file(tmp_path, monkeypatch):
    from scripts import build_china_radar as b
    _write_ic(tmp_path, json.dumps(
        {"schema": "china_radar_ic.v1", "as_of": "2026-10-16",
         "by_horizon": IC["by_horizon"]}, ensure_ascii=False))
    monkeypatch.setattr(b.config, "data_dir", lambda: tmp_path)
    got = b._load_radar_ic()
    assert isinstance(got, dict)
    assert got["as_of"] == "2026-10-16"
    assert got["by_horizon"]["5"]["n_matured"] == 44


def test_load_radar_ic_missing_file_is_empty(tmp_path, monkeypatch):
    from scripts import build_china_radar as b
    monkeypatch.setattr(b.config, "data_dir", lambda: tmp_path)
    assert b._load_radar_ic() == {}


def test_builder_never_calls_compute_ic():
    """The builder stays display-only: it reads the artifact, it never grades."""
    src = _BUILDER.read_text(encoding="utf-8")
    assert "compute_ic" not in src
    assert "china_radar_ic" not in src
    assert ".render(" in src
    call = src[src.index(".render("):][:200]
    assert "ic=" in call
    assert "ic=_load_radar_ic()" in src
