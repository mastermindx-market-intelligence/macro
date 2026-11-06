"""Original-source -> incumbent producer -> typed JSON -> immutable book tests."""
from datetime import date
import json
from pathlib import Path
import shutil
import pandas as pd
from engine.neuralweb import bottom_sensors as sensor
from scripts import build_bottom_sensors as publisher
from scripts import build_qa_bottom_sensors as page

CUTOFF="2026-11-05T22:00:00Z"


def inputs():
    gate={"tier_cascade":"T2","ticks":1,"asof":"2026-11-04"}
    row={"ticker":"ABC", "signal":{"above200":False,"asof":"2026-11-04"},
         "coiled":{"coiled":True,"fire":True,"star":False},
         "hold":{"state":"intact","days_basing":2,"ret_since_anchor_pct":1.2},
         "conviction":{"alignment":{"knife":.2}}}
    return gate,row


def build_row(root, monkeypatch, *, row=None, price_last="2026-11-04", decision=CUTOFF):
    gate,normal=inputs()
    values=pd.Series([100.0]*125+[101.0],index=pd.bdate_range(end=price_last,periods=126))
    monkeypatch.setattr(sensor,"_load_close",lambda *args:values)
    return sensor._build_row("ABC",gate,normal if row is None else row,{},pd.DataFrame(),
        date(2026,11,5),root,sg_asof="2026-11-05",standouts_as_of="2026-11-05",decision_at=decision)


def evidence(row):
    context=json.loads(row["pivot_context_json"])
    return context,{x["field"]:x for x in context["evidence"]}


def test_below_ma_does_not_hide_early_turn(tmp_path,monkeypatch):
    row=build_row(tmp_path,monkeypatch);ctx,ev=evidence(row)
    assert ev["above200"]["value"] is False and ev["above200"]["state"]=="observed"
    assert ev["coiled_fire"]["value"] is True
    assert ev["dist_21d_low_pct"]["as_of"]=="2026-11-04"
    assert ev["trigger_tier"]["as_of"]=="2026-11-04"
    assert ctx["probability"] is None and ctx["action_authority"]=="none"
    assert row["labels_version"]=="labels_v2"


def test_raw_missing_not_legacy_false_default(tmp_path,monkeypatch):
    _,raw=inputs();raw.pop("coiled")
    row=build_row(tmp_path,monkeypatch,row=raw);ctx,ev=evidence(row)
    assert ev["coiled"]["value"] is None and ev["coiled_fire"]["value"] is None
    assert ev["above200"]["value"] is False


def test_future_price_vintage_not_live_evidence(tmp_path,monkeypatch):
    row=build_row(tmp_path,monkeypatch,price_last="2026-11-06");ctx,ev=evidence(row)
    assert ev["dist_21d_low_pct"]["value"] is None
    assert ev["dist_21d_low_pct"]["state"]=="future"
    assert ev["coiled_fire"]["value"] is True


def test_original_dates_not_replaced_when_stale(tmp_path,monkeypatch):
    row=build_row(tmp_path,monkeypatch,decision="2026-11-20T22:00:00Z");ctx,ev=evidence(row)
    assert ctx["quality"]=="unavailable"
    assert ev["coiled_fire"]["state"]=="stale"
    assert ev["coiled_fire"]["as_of"]=="2026-11-04"


def test_end_to_end_existing_publisher_capture_and_page(tmp_path,monkeypatch):
    row=build_row(tmp_path,monkeypatch)
    frame=pd.DataFrame([row]).set_index("symbol")
    frame.attrs.update(as_of="2026-11-04",labels_version="labels_v2")
    monkeypatch.setattr(publisher,"assemble",lambda root:frame)
    assert publisher.build(tmp_path)==0
    payload=json.loads((tmp_path/'site/neuralwebdata/bottom_sensors.json').read_text())
    emitted=payload['rows'][0]
    assert 'pivot_context_json' not in emitted
    assert emitted['pivot_context']==json.loads(row['pivot_context_json'])
    flat=pd.read_parquet(tmp_path/'data/neuralweb/bottom_sensors.parquet')
    assert isinstance(flat.iloc[0]['pivot_context_json'],str)
    book=tmp_path/'data/shadow/bottom_sensors_geometry_book.jsonl'
    saved=json.loads(book.read_text().splitlines()[0])
    assert saved['pivot_context']==emitted['pivot_context']
    assert saved['pivot_recorded_at'] and len(saved['pivot_context_sha256'])==64
    initial=book.read_bytes()
    assert publisher.build(tmp_path)==0
    assert book.read_bytes()==initial
    templates=tmp_path/'templates';templates.mkdir()
    source=Path(__file__).resolve().parents[1]/'templates/qa_bottom_sensors.html.j2'
    shutil.copyfile(source,templates/source.name)
    (templates/'_site_nav.html.j2').write_text('')
    monkeypatch.setattr(page,'write_page',lambda path,html:path.write_text(html))
    html=page.build(tmp_path).read_text()
    assert 'data-pivot-symbol="ABC"' in html
    assert 'not a live entry signal' in html
    assert '2026-11-05T22:00:00Z' in html
