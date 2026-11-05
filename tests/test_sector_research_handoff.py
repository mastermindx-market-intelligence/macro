"""B09 — every Sector Central group row carries a source-bound handoff.

The free payload rows (data["sectors"] / data["baskets"]) gain a
``research_handoff`` (schema sector_central.research_handoff.v1): canonical
subject/kind, an immutable per-row snapshot digest, source/generation/clock,
evidence mode, return context, and explicit not_supplied statements wherever
the native source states no relationship — a Dossier or Research receiver
binds without guessing and without the producer inventing links.

Pins (synthetic rows/payloads only):
  * sector / basket / producer-href rows resolve the right subject kind,
    destinations and return_context.href (bridge-shaped, uppercase ticker);
  * content_sha256 is stable across runs, moves with any row value, and
    ignores the research_handoff key itself (re-attachment is idempotent);
  * a tickerless row ships canonical_entity_ref null + not_supplied;
  * relationships stay not_supplied unless the row itself carries the field;
  * research is receiver_not_bound (the page's Research link still targets
    Time Machine — binding a receiver is a named follow-on, not this lane);
  * one poison row gets the unavailable/handoff_error stub and strands no
    neighbour;
  * a stubbed main() publishes rows with handoffs, keeps every Act-Now board
    row out of the free files, and changes no other payload key versus a
    no-handoff run;
  * no field named score / rank / signal / win rate / recommendation appears.
"""
from __future__ import annotations

import json

import pytest


# ── synthetic rows / payloads ─────────────────────────────────────────────────

def _sector_row() -> dict:
    """A row as published in data["sectors"] (engine/sector_cycles.py:1119)."""
    return {"id": "xlk", "ticker": "XLK", "kind": "sector", "name": "Technology",
            "name_zh": "科技", "group": "Tech", "conviction": {"score": 61}}


def _basket_row() -> dict:
    """A row as published in data["baskets"] (engine/sector_cycles.py:1174)."""
    return {"id": "b-gold_miners", "ticker": "", "kind": "basket",
            "name": "Gold Miners", "name_zh": "金矿", "group": "Thematic"}


def _publication() -> dict:
    return {
        "schema": "sector_central.publication.v1",
        "as_of": "2026-10-18",
        "built_utc": "2026-10-19T01:02:03Z",
        "secondary_sources": {
            "si_handoff": {"status": "ok"},
            "action_board": {"status": "absent"},
        },
    }


def _build(row: dict) -> dict:
    from engine.sector_research_handoff import build_handoff
    return build_handoff(row, publication=_publication(), session="2026-10-18")


# ── subject kind / destinations / return context ─────────────────────────────

def test_sector_row_kind_destinations_and_return_href():
    h = _build(_sector_row())
    s = h["subject"]
    assert s["kind"] == "sector" == s["native_kind"]
    assert s["id"] == "xlk"
    assert s["name_en"] == "Technology" and s["name_zh"] == "科技"
    assert s["canonical_entity_ref"] == "XLK"
    assert s["canonical_status"] == "supplied"
    # resolution stays with the receiver's US_SECTOR_PAGE table — ticker only
    assert h["destinations"]["detail"] == {"kind": "native_sector_page",
                                           "ticker": "XLK"}
    assert h["destinations"]["prophet"] == \
        "us_stocks.html?si_sector=XLK#sector-prophet-context"
    # exactly the bridge's return href: uppercase group id, #map anchor
    rc = h["return_context"]
    assert rc == {"route": "sector_central.html", "query": {"g": "XLK"},
                  "hash": "#map", "href": "sector_central.html?g=XLK#map"}


def test_basket_row_kind_destinations_and_return_href():
    h = _build(_basket_row())
    s = h["subject"]
    assert s["kind"] == "basket" == s["native_kind"]
    assert s["id"] == "b-gold_miners"
    # basket rows carry no native ticker (etf_proxy "") — explicit, not guessed
    assert s["canonical_entity_ref"] is None
    assert s["canonical_status"] == "not_supplied"
    # the page builds basket hrefs with the b- prefix stripped (template :3294)
    assert h["destinations"]["detail"] == {
        "kind": "basket_page", "href": "basket/gold_miners.html"}
    assert h["destinations"]["prophet"] is None  # bridge is sector-kind only
    assert h["return_context"]["href"] == \
        "sector_central.html?g=b-gold_miners#map"


def test_producer_href_row_uses_row_href_verbatim():
    row = {**_sector_row(), "href": "special/tech-depth.html?x=1"}
    h = _build(row)
    assert h["destinations"]["detail"] == {
        "kind": "producer_href", "href": "special/tech-depth.html?x=1"}
    assert h["destinations"]["detail_reason"] is None
    # subject identity stays source-bound even when the drill target is producer-
    # supplied
    assert h["subject"]["kind"] == "sector"


def test_sector_row_without_ticker_detail_null_with_reason():
    row = _sector_row()
    del row["ticker"]
    h = _build(row)
    assert h["destinations"]["detail"] is None
    assert h["destinations"]["detail_reason"]
    assert h["destinations"]["prophet"] is None


# ── snapshot digest ───────────────────────────────────────────────────────────

def test_content_sha256_stable_sensitive_and_handoff_blind():
    from engine.sector_research_handoff import attach_handoffs
    d1 = _build(_sector_row())["snapshot"]["content_sha256"]
    d2 = _build(_sector_row())["snapshot"]["content_sha256"]
    assert d1 == d2 and len(d1) == 64  # stable across runs

    moved = _sector_row()
    moved["name"] = "Information Technology"
    assert _build(moved)["snapshot"]["content_sha256"] != d1  # any value moves it

    # the handoff key itself is invisible to the digest — idempotent re-attach
    annotated = _build(_sector_row())
    row = {**_sector_row(), "research_handoff": annotated}
    assert _build(row)["snapshot"]["content_sha256"] == d1
    data = {"as_of": "2026-10-18", "publication": _publication(),
            "sectors": [_sector_row()], "baskets": []}
    attach_handoffs(data)
    first = data["sectors"][0]["research_handoff"]["snapshot"]["content_sha256"]
    attach_handoffs(data)  # re-attach over the annotated row
    again = data["sectors"][0]["research_handoff"]["snapshot"]["content_sha256"]
    assert first == again == d1


def test_snapshot_generation_copied_from_publication():
    h = _build(_sector_row())["snapshot"]
    assert h["artifact"] == "sectordata/sector_central.json"
    assert h["session"] == "2026-10-18"
    assert h["clock"] == "settled_daily_session"
    assert h["generation"] == {"as_of": "2026-10-18",
                               "built_utc": "2026-10-19T01:02:03Z"}


def test_source_methods_and_dossier_blocks():
    h = _build(_sector_row())
    assert h["source"]["producer"] == "engine/sector_central.py"
    assert h["source"]["publication_schema"] == "sector_central.publication.v1"
    # names and statuses only — never a copy of the per-source records
    assert h["source"]["secondary_sources"] == {"si_handoff": "ok",
                                                "action_board": "absent"}
    assert h["methods"]["evidence_mode"] == "descriptive"
    assert h["methods"]["claim"] == "no_recommendation"
    assert h["methods"]["methods_ref"] is None
    assert h["methods"]["methods_status"] == "not_bound"  # no methods anchor on page
    assert h["dossier"] == {
        "status": "adapter_only",
        "read_model": "sector_dossier_read_model.v1",
        "missing": ["governance", "authority_caps", "input_receipts",
                    "dossier_hash"],
    }


# ── explicit non-relationships ────────────────────────────────────────────────

def test_relationships_not_supplied_unless_row_carries_field():
    h = _build(_sector_row())
    assert h["relationships"]["parent_sector"] == {"status": "not_supplied"}
    assert h["relationships"]["members"] == {"status": "not_supplied"}

    supplied = _build({**_sector_row(), "parent_sector": "xlf",
                       "members": ["XLK", "AAPL"]})
    assert supplied["relationships"]["parent_sector"] == {
        "status": "supplied", "ref": "parent_sector"}
    assert supplied["relationships"]["members"] == {
        "status": "supplied", "ref": "members"}


def test_research_destination_receiver_not_bound():
    h = _build(_sector_row())
    assert h["destinations"]["research"] is None
    assert h["destinations"]["research_status"] == "receiver_not_bound"


# ── attach: poison row + summary counts ───────────────────────────────────────

def test_poison_row_gets_stub_and_neighbours_unaffected():
    from engine.sector_research_handoff import attach_handoffs
    poison = {**_sector_row(), "id": "xlf",
              "unserializable": {1, 2}}  # a set breaks canonical json.dumps
    good = _sector_row()
    basket = _basket_row()
    data = {"as_of": "2026-10-18", "publication": _publication(),
            "sectors": [good, poison], "baskets": [basket]}
    summary = attach_handoffs(data)
    assert data["sectors"][0]["research_handoff"]["schema"] == \
        "sector_central.research_handoff.v1"
    assert data["sectors"][1]["research_handoff"] == {
        "schema": "sector_central.research_handoff.v1",
        "status": "unavailable", "reason": "handoff_error"}
    assert data["baskets"][0]["research_handoff"]["subject"]["kind"] == "basket"
    assert summary["rows"] == 3 and summary["unavailable"] == 1
    assert summary["arrays"] == {"sectors": {"rows": 2, "unavailable": 1},
                                 "baskets": {"rows": 1, "unavailable": 0}}


# ── main() end-to-end (publication-test stub pattern) ─────────────────────────

class _StubTemplate:
    def render(self, **kwargs):
        return "<html>stub</html>"


class _StubEnvironment:
    def __init__(self, *args, **kwargs):
        self.globals = {}

    def get_template(self, name):
        return _StubTemplate()


def _run_main(monkeypatch, tmp_path, *, attach: bool) -> dict:
    """Drive scripts.build_sector_central.main() against a tmp site (engine,
    grader, flows board, accumulation and Jinja env stubbed — the B10 pattern).
    ``attach=False`` neuters the handoff step for the baseline comparison."""
    import lib.config as config_mod
    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    monkeypatch.setattr(
        config_mod, "load",
        lambda: {"storage": {"site_dir": "site"},
                 "sector_central_gate": {"gated": True, "preview_rows": 1}})

    site = tmp_path / "site"
    (site / "basketdata").mkdir(parents=True, exist_ok=True)
    board = {"as_of": "2026-10-18", "action_board": {"buy_now": [
        {"slug": "FREE-ROW-A", "name": "Free Row A"},
        {"slug": "LOCKED-ROW-B", "name": "Locked Row B"},
        {"slug": "LOCKED-ROW-C", "name": "Locked Row C"},
    ]}}
    (site / "basketdata" / "action_board.json").write_text(
        json.dumps(board), encoding="utf-8")

    import engine.sector_central as sc
    monkeypatch.setattr(sc, "compute", lambda: {
        "as_of": "2026-10-18", "asof": "2026-10-18",
        "sectors": [
            {"id": "xlk", "ticker": "XLK", "kind": "sector", "name": "Technology",
             "name_zh": "科技", "group": "Tech"},
            {"id": "xlf", "ticker": "XLF", "kind": "sector", "name": "Financials",
             "name_zh": "金融", "group": "Fin"},
        ],
        "baskets": [
            {"id": "b-gold_miners", "ticker": "", "kind": "basket",
             "name": "Gold Miners", "name_zh": "金矿", "group": "Thematic"},
        ],
    })
    import engine.sector_central_grader as cg
    monkeypatch.setattr(cg, "append_central_log", lambda data: 0)
    monkeypatch.setattr(cg, "grade", lambda: {"available": True})

    import scripts.build_sector_central as bsc
    monkeypatch.setattr(bsc, "Environment", _StubEnvironment)
    monkeypatch.setattr(bsc, "_flows_section_html", lambda: "<div>flows</div>")
    monkeypatch.setattr(bsc, "_accumulation_rows", lambda: ([], None))
    if not attach:
        import engine.sector_research_handoff as srh
        monkeypatch.setattr(srh, "attach_handoffs",
                            lambda data: {"rows": 0, "unavailable": 0})
    assert bsc.main() == 0
    return json.loads(
        (site / "sectordata" / "sector_central.json").read_text(encoding="utf-8"))


def test_main_writes_handoffs_no_board_rows_no_other_key_changes(
        tmp_path, monkeypatch):
    free = _run_main(monkeypatch, tmp_path, attach=True)

    # every published row carries a handoff, in BOTH free files
    for arr in ("sectors", "baskets"):
        for row in free[arr]:
            h = row["research_handoff"]
            assert h["schema"] == "sector_central.research_handoff.v1"
            assert h["snapshot"]["content_sha256"]
            assert h["destinations"]["research"] is None
    site = tmp_path / "site"
    js = (site / "sector_central_data.js").read_text(encoding="utf-8")
    assert "research_handoff" in js
    assert "receiver_not_bound" in js

    # the publication counter is the frozen shape
    assert free["publication"]["research_handoff"] == {"version": 1, "rows": 3,
                                                       "unavailable": 0}

    # no Act-Now board row rides along — the split stays the gate
    free_text = json.dumps(free)
    for locked in ("LOCKED-ROW-B", "LOCKED-ROW-C"):
        assert locked not in free_text and locked not in js

    # no other payload key changes vs a no-handoff run (built_utc is volatile)
    baseline = _run_main(monkeypatch, tmp_path, attach=False)

    def normalized(doc: dict) -> dict:
        doc = json.loads(json.dumps(doc))
        doc["publication"].pop("research_handoff", None)
        doc["publication"].pop("built_utc", None)
        for arr in ("sectors", "baskets"):
            for row in doc.get(arr) or []:
                row.pop("research_handoff", None)
        return doc

    assert normalized(free) == normalized(baseline)
    assert all("research_handoff" not in r
               for r in baseline["sectors"] + baseline["baskets"])


# ── vocabulary fence ──────────────────────────────────────────────────────────

def test_no_score_rank_signal_win_rate_or_recommendation_field_names():
    def key_names(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield str(k).lower()
                yield from key_names(v)
        elif isinstance(node, list):
            for v in node:
                yield from key_names(v)

    banned = {"score", "rank", "signal", "win_rate", "win rate", "win-rate",
              "recommendation"}
    for row in (_sector_row(), _basket_row()):
        for key in key_names(_build(row)):
            assert key not in banned, f"banned field name in handoff: {key}"
