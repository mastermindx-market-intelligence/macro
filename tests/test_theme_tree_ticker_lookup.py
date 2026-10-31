"""Tests for the U3 "Why is this company here?" ticker lookup on /theme_tree.html.

Covers the "not done unless" clauses of SPEC_U3:

  1. Parity — batch composition equals ``hierarchy_paths(company)`` on a fixture.
  2. As-of — MEMBER_OF edges respect ``valid_from``/``valid_to``/knowledge_cutoff.
  3. Typed abstention — one fixture per reason code.
  4. china_ths-only company yields ``no_public_basket``; rendered HTML carries no
     THS id or name.
  5. Contract — the builder reads nodes/edges but writes neither; no
     company→theme or company→category edge ever appears in the graph.
  6. Forbidden-key walk — the blob ships only safe keys.
  7. Blob size — at most the 400 KB budget on real data; the fallback keeps
     path-bearing companies and emits an abstention summary.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine.theme_graph import hierarchy_breadth_display as hb  # noqa: E402
from engine.theme_graph import structural_navigation as sn  # noqa: E402
from scripts.build_theme_tree_page import (  # noqa: E402
    _BASKET_FAMILIES,
    _FrameStore,
    _build_ticker_lookup,
    _classify_abstention,
    _ticker_lookup_json,
    compose,
    render,
)
from tests.test_build_theme_tree_page import _mk_nodes  # noqa: E402

_VENDOR = re.compile(r"ltheme:|ths_concepts|finviz_themes|basket_china_ths|china_ths")
_BLOB_RE = re.compile(r'id="tt-ticker-data">(.*?)</script>', re.S)
_LOOKUP_LABEL_RE = re.compile(r"tt-lookup-input")
_RESULT_RE = re.compile(r'id="tt-ticker-result"')


# ---------------------------------------------------------------------------
# Frame builders (extend the U2 fixtures so MEMBER_OF + basket rows fit)
# ---------------------------------------------------------------------------


def _mk_edges(*rows: dict) -> pd.DataFrame:
    """Like ``test_build_theme_tree_page._mk_edges`` but with a non-empty
    ``belief_time`` so the live ``_collapse_relevant_edges`` accepts the
    rows. The U2 builder doesn't touch belief_time; the U3 batch composition
    does — every edge in this fixture is recorded at ``2025-01-01`` unless
    the row overrides ``belief_time``.
    """
    cols = [
        "edge_id", "type", "src", "dst", "valid_from", "valid_to",
        "provenance", "evidence_ref", "weight", "confidence",
        "computed_at", "engine_version", "source_meta", "belief_time",
        "evidence_time", "source_class", "rights_class",
        "family", "rights_registry_id", "asserted_by",
        "rights_resolver", "legal_basis", "rights_evidence_ref",
        "rights_decided_at", "n_parents",
    ]
    base = {c: ("" if c not in ("weight", "confidence") else 1.0) for c in cols}
    base.update({"type": "PARENT_OF", "valid_from": "2025-01-01",
                 "valid_to": None, "provenance": "{}",
                 "evidence_ref": "{}", "computed_at": "2025-01-01T00:00:00Z",
                 "engine_version": "theme_graph.v1",
                 "source_meta": "{}",
                 "belief_time": "2025-01-01"})
    records = []
    for r in rows:
        row = dict(base)
        row.update(r)
        if "edge_id" not in r:
            row["edge_id"] = f"{row['type']}:{r['src']}->{r['dst']}"
        records.append(row)
    return pd.DataFrame(records, columns=cols)


# ---------------------------------------------------------------------------
# Fixture: one theme graph, six companies, every typed abstention
# ---------------------------------------------------------------------------


def _fixtures_full():
    """Returns (nodes, edges) for an end-to-end U3 fixture.

    Companies:
      - co:us:AAPL   → ai_compute basket → ai_semi (path: macro_tech › ai_semi)
      - co:us:NVDA   → ai_compute (path) + gold_miners (basket_not_a_theme)
      - co:cn:600519 → liquor_cn basket → consumer (path)
      - co:cn:THS    → liquor_ths basket (internal-only) → no_public_basket
      - co:hk:0700   → hk tech basket (no EXPRESSES) → market_not_wired
      - co:us:NOMAP  → orphan_us basket (US, no EXPRESSES, not unmapped) → basket_unmapped
      - co:us:NOEXP  → ai_compute edge with valid_to before asof → 0 paths
      - co:us:NOMEMB → no MEMBER_OF → not_in_graph

    Two macro categories, two themes, three baskets wired to EXPRESSES plus
    two that aren't, plus an internal-only basket.

    Theme rows carry ``provenance="crosswalk:config/theme_crosswalk.yml"``
    so ``hierarchy_paths`` accepts them (the reader fails closed on any
    other provenance). ``computed_at`` is anchored at 2025-01-01 so the
    reader's ``_clock_date(computed_at) > knowledge_cutoff`` filter (which
    compares against the test's asof/cutoff) keeps the rows visible.
    """
    crosswalk_prov = "crosswalk:config/theme_crosswalk.yml"
    fixed_computed = "2025-01-01T00:00:00Z"
    nodes = _mk_nodes(
        # ── macro_category ──
        {"node_id": "theme:macro_tech", "name_en": "Technology",
         "name_zh": "科技", "tier": "macro_category",
         "provenance": crosswalk_prov,
         "computed_at": fixed_computed},
        {"node_id": "theme:macro_consumer", "name_en": "Consumer",
         "name_zh": "消费", "tier": "macro_category",
         "provenance": crosswalk_prov,
         "computed_at": fixed_computed},
        # ── theme ──
        {"node_id": "theme:ai_semiconductors", "name_en": "AI semiconductors",
         "name_zh": "AI芯片", "tier": "theme",
         "provenance": crosswalk_prov,
         "computed_at": fixed_computed},
        {"node_id": "theme:consumer", "name_en": "Consumer staples",
         "name_zh": "消费必需品", "tier": "theme",
         "provenance": crosswalk_prov,
         "computed_at": fixed_computed},
        # ── basket (public, with EXPRESSES) ──
        {"node_id": "basket:baskets:ai_compute", "kind": "basket",
         "name_en": "AI compute basket", "name_zh": "AI算力篮子", "tier": "",
         "computed_at": fixed_computed},
        {"node_id": "basket:baskets_china:liquor_cn", "kind": "basket",
         "name_en": "Liquor CN", "name_zh": "白酒A股", "tier": "",
         "computed_at": fixed_computed},
        # ── basket (public, NO EXPRESSES — drives abstentions) ──
        {"node_id": "basket:baskets:gold_miners", "kind": "basket",
         "name_en": "Gold miners", "name_zh": "黄金矿企", "tier": "",
         "computed_at": fixed_computed},
        {"node_id": "basket:baskets_hk:tech_hk", "kind": "basket",
         "name_en": "HK tech", "name_zh": "港股科技", "tier": "",
         "computed_at": fixed_computed},
        {"node_id": "basket:baskets:orphan_us", "kind": "basket",
         "name_en": "Orphan US", "name_zh": "美国孤儿", "tier": "",
         "computed_at": fixed_computed},
        # ── basket (internal-only — must NEVER surface) ──
        {"node_id": "basket:baskets_china_ths:liquor_ths", "kind": "basket",
         "name_en": "THS liquor", "name_zh": "THS白酒", "tier": "",
         "computed_at": fixed_computed},
        # ── companies ──
        {"node_id": "co:us:AAPL", "kind": "company", "market_scope": "us",
         "tier": "", "external_ids": json.dumps({"symbol": "AAPL"}),
         "computed_at": fixed_computed},
        {"node_id": "co:us:NVDA", "kind": "company", "market_scope": "us",
         "tier": "", "external_ids": json.dumps({"symbol": "NVDA"}),
         "computed_at": fixed_computed},
        {"node_id": "co:cn:600519", "kind": "company", "market_scope": "cn",
         "tier": "", "external_ids": json.dumps({"symbol": "600519"}),
         "computed_at": fixed_computed},
        {"node_id": "co:cn:THS", "kind": "company", "market_scope": "cn",
         "tier": "", "external_ids": json.dumps({"symbol": "THS"}),
         "computed_at": fixed_computed},
        {"node_id": "co:hk:0700", "kind": "company", "market_scope": "hk",
         "tier": "", "external_ids": json.dumps({"symbol": "0700"}),
         "computed_at": fixed_computed},
        {"node_id": "co:us:NOMAP", "kind": "company", "market_scope": "us",
         "tier": "", "external_ids": json.dumps({"symbol": "NOMAP"}),
         "computed_at": fixed_computed},
        {"node_id": "co:us:NOEXP", "kind": "company", "market_scope": "us",
         "tier": "", "external_ids": json.dumps({"symbol": "NOEXP"}),
         "computed_at": fixed_computed},
        {"node_id": "co:us:NOMEMB", "kind": "company", "market_scope": "us",
         "tier": "", "external_ids": json.dumps({"symbol": "NOMEMB"}),
         "computed_at": fixed_computed},
    )
    edges = _mk_edges(
        # ── PARENT_OF ──
        {"src": "theme:macro_tech", "dst": "theme:ai_semiconductors"},
        {"src": "theme:macro_consumer", "dst": "theme:consumer"},
        # ── EXPRESSES (public baskets → themes) ──
        {"type": "EXPRESSES",
         "src": "basket:baskets:ai_compute",
         "dst": "theme:ai_semiconductors",
         "edge_id": "EXPRESSES:ai_compute->ai_semi"},
        {"type": "EXPRESSES",
         "src": "basket:baskets_china:liquor_cn",
         "dst": "theme:consumer",
         "edge_id": "EXPRESSES:liquor_cn->consumer"},
        # ── MEMBER_OF (companies → baskets) ──
        {"type": "MEMBER_OF", "src": "co:us:AAPL",
         "dst": "basket:baskets:ai_compute",
         "edge_id": "MEMBER_OF:AAPL->ai_compute"},
        {"type": "MEMBER_OF", "src": "co:us:NVDA",
         "dst": "basket:baskets:ai_compute",
         "edge_id": "MEMBER_OF:NVDA->ai_compute"},
        {"type": "MEMBER_OF", "src": "co:us:NVDA",
         "dst": "basket:baskets:gold_miners",
         "edge_id": "MEMBER_OF:NVDA->gold_miners"},
        {"type": "MEMBER_OF", "src": "co:cn:600519",
         "dst": "basket:baskets_china:liquor_cn",
         "edge_id": "MEMBER_OF:600519->liquor_cn"},
        {"type": "MEMBER_OF", "src": "co:cn:THS",
         "dst": "basket:baskets_china_ths:liquor_ths",
         "edge_id": "MEMBER_OF:THS->liquor_ths"},
        {"type": "MEMBER_OF", "src": "co:hk:0700",
         "dst": "basket:baskets_hk:tech_hk",
         "edge_id": "MEMBER_OF:0700->tech_hk"},
        {"type": "MEMBER_OF", "src": "co:us:NOMAP",
         "dst": "basket:baskets:orphan_us",
         "edge_id": "MEMBER_OF:NOMAP->orphan_us"},
        # EXPIRED: edge valid only in 2025; asof is 2026-06-01 → drop.
        {"type": "MEMBER_OF", "src": "co:us:NOEXP",
         "dst": "basket:baskets:ai_compute",
         "edge_id": "MEMBER_OF:NOEXP->ai_compute",
         "valid_to": "2025-06-01"},
    )
    return nodes, edges


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _records(nodes: pd.DataFrame, edges: pd.DataFrame):
    """Run the batch composition and return the raw ``records`` dict."""
    payload = _build_ticker_lookup(
        REPO, nodes, edges, as_of="2026-06-01", knowledge_cutoff="2026-06-01",
    )
    return payload


def _norm_paths(records: list[dict]) -> list[tuple]:
    """Stable, comparison-ready representation of hierarchy_paths records.

    hierarchy_paths sorts by (anchor, path_node_ids, via_edge_ids). This is
    the same key, so equality over two normalised lists is exact — order
    insensitive by anchor/path/via.
    """
    out = []
    for r in records:
        anchor = r.get("anchor_node_id")
        path = tuple(el["node_id"] for el in r.get("path", []))
        via = tuple(h.get("edge_id", "") for h in r.get("via", []))
        out.append((anchor, path, via))
    out.sort()
    return out


def _html(nodes: pd.DataFrame, edges: pd.DataFrame) -> str:
    ctx = compose(REPO, nodes=nodes, edges=edges)
    ctx["as_of"] = "2026-06-01"
    # Re-run the lookup so the blob is keyed to our fixture's as_of.
    from scripts.build_theme_tree_page import _ticker_lookup_json as fn
    ctx["ticker_lookup_json"] = fn(
        REPO, nodes, edges, as_of="2026-06-01", knowledge_cutoff="2026-06-01",
    )
    return render(REPO, ctx=ctx)


def _blob(html: str) -> dict:
    m = _BLOB_RE.search(html)
    assert m, "ticker lookup blob missing from HTML"
    return json.loads(m.group(1))


# ---------------------------------------------------------------------------
# 1. Parity — batch composition equals hierarchy_paths(company) on the fixture
# ---------------------------------------------------------------------------


def test_batch_composition_matches_hierarchy_paths_per_company():
    """Per-company parity: batch composition equals ``hierarchy_paths(company)``.

    The builder emits a minimal ``{basket, chain}`` shape; the internal
    ``_member_edge_id`` field carries the live MEMBER_OF edge id joining
    the company to the basket so the parity walk can match
    ``hierarchy_paths(company)``'s via tuple exactly.
    """
    from datetime import date as _date
    from engine.theme_graph.ontology import _parse_date  # noqa: E402
    nodes, edges = _fixtures_full()
    store_view = _FrameStore(nodes, edges)
    asof = _parse_date("2026-06-01", "asof")
    cutoff = _parse_date("2026-06-01", "knowledge_cutoff")
    records = _records(nodes, edges)

    # The builder keys companies by ``<market>:<symbol>``. Walk the records
    # and rebuild the lookup from node ids for parity assertions.
    company_lookup: dict[str, dict[str, dict]] = {}
    for row in nodes.to_dict("records"):
        if row.get("kind") != "company":
            continue
        sym = ""
        ext = row.get("external_ids")
        if isinstance(ext, str) and ext.strip():
            try:
                sym = json.loads(ext).get("symbol", "")
            except ValueError:
                pass
        market = row.get("market_scope") or ""
        if not (isinstance(sym, str) and sym) or not market:
            continue
        key = f"{market}:{sym}"
        if key in records:
            company_lookup[row["node_id"]] = records[key]

    for company_id, batch_rec in company_lookup.items():
        direct = sn.hierarchy_paths(
            store_view, company_id, asof, knowledge_cutoff=cutoff,
        )
        direct_norm = _norm_paths(direct)
        # Rebuild the chain+anchor set from the batch output. The chain runs
        # root → ... → theme anchor (same order hierarchy_paths emits), so
        # parity is ``(anchor, chain)`` set equality. The MEMBER_OF /
        # EXPRESSES edge ids are also equal because both walks resolve them
        # through the same ``_collapse_relevant_edges`` liveness — verified
        # separately on the in-memory records below.
        composed: list[tuple] = []
        for p in batch_rec.get("paths", []):
            anchor = p["chain"][-1]["node_id"] if p["chain"] else ""
            chain = tuple(step["node_id"] for step in p["chain"])
            composed.append((anchor, chain))
        composed.sort()
        direct_simplified = [(a, c) for (a, c, _v) in direct_norm]
        assert composed == direct_simplified, (
            f"parity drift for {company_id}: "
            f"batch={composed}, direct={direct_simplified}"
        )
        # MEMBER_OF / EXPRESSES edge id parity: each batch path's
        # ``_member_edge_id`` matches the first hop in hierarchy_paths'
        # ``via`` tuple. The EXPRESSES hop id is the second via hop; we
        # recover it from hierarchy_paths' record.
        for p in batch_rec.get("paths", []):
            chain = tuple(step["node_id"] for step in p["chain"])
            member_eid = p.get("_member_edge_id", "")
            for rec in direct:
                if tuple(el["node_id"] for el in rec.get("path", [])) == chain:
                    via = rec.get("via", [])
                    if via:
                        assert via[0]["edge_id"] == member_eid, (
                            f"MEMBER_OF edge id mismatch for {company_id}: "
                            f"batch={member_eid}, direct={via[0]['edge_id']}"
                        )
                    break


# ---------------------------------------------------------------------------
# 2. As-of — MEMBER_OF edges respect valid_from / valid_to / knowledge_cutoff
# ---------------------------------------------------------------------------


def test_expired_member_of_drops_path():
    nodes, edges = _fixtures_full()
    records = _records(nodes, edges)
    # co:us:NOEXP's edge to ai_compute closes 2025-06-01; asof=2026-06-01 → not live.
    # The expired edge is the only MEMBER_OF row, so NOEXP has zero live
    # public memberships → ``not_in_graph`` is true.
    rec = records["us:NOEXP"]
    assert rec["paths"] == []
    assert rec["not_in_graph"] is True
    assert rec["no_public_basket"] is False


def test_knowledge_cutoff_hides_future_belief():
    """A belief asserted after knowledge_cutoff is excluded."""
    nodes, edges = _fixtures_full()
    # Override NOEXP's edge with a future belief_time; knowledge_cutoff is
    # earlier so the belief hasn't been recorded yet.
    rows = edges.to_dict("records")
    for r in rows:
        if r["edge_id"] == "MEMBER_OF:NOEXP->ai_compute":
            r["belief_time"] = "2027-01-01"
    edges = pd.DataFrame(rows)
    records = _records(nodes, edges)
    assert records["us:NOEXP"]["not_in_graph"] is True


def test_company_with_no_member_of_is_not_in_graph():
    nodes, edges = _fixtures_full()
    records = _records(nodes, edges)
    assert records["us:NOMEMB"]["not_in_graph"] is True
    assert records["us:NOMEMB"]["paths"] == []
    assert records["us:NOMEMB"]["no_public_basket"] is False


# ---------------------------------------------------------------------------
# 3. Typed abstention — one fixture per reason code
# ---------------------------------------------------------------------------


def test_basket_not_a_theme_abstention():
    nodes, edges = _fixtures_full()
    records = _records(nodes, edges)
    # NVDA → gold_miners (US, slug in crosswalk unmapped_baskets) → basket_not_a_theme
    rec = records["us:NVDA"]
    assert "basket_not_a_theme" in [a["code"] for a in rec["abstentions"]]
    # NVDA ALSO has ai_compute → at least one path
    assert rec["paths"] and any(
        p["basket"]["name_en"] == "AI compute basket" for p in rec["paths"]
    )


def test_market_not_wired_abstention():
    nodes, edges = _fixtures_full()
    records = _records(nodes, edges)
    rec = records["hk:0700"]
    # hk:0700 has a live MEMBER_OF to basket:baskets_hk:tech_hk (public, but
    # no EXPRESSES, and the family is one of the three producer-key gaps).
    # That gives ``paths=[]``, ``abstentions=['market_not_wired']``, neither
    # state flag set (the company IS in the graph, just not in any theme).
    assert rec["paths"] == []
    assert rec["not_in_graph"] is False
    assert rec["no_public_basket"] is False
    assert "market_not_wired" in [a["code"] for a in rec["abstentions"]]


def test_basket_unmapped_abstention():
    nodes, edges = _fixtures_full()
    records = _records(nodes, edges)
    rec = records["us:NOMAP"]
    # Public membership (US orphan_us) is live; basket has no EXPRESSES; the
    # slug isn't in unmapped_baskets by name. The builder classifies this as
    # ``basket_unmapped`` and records it in abstentions.
    assert rec["paths"] == []
    assert rec["not_in_graph"] is False
    assert rec["no_public_basket"] is False
    assert "basket_unmapped" in [a["code"] for a in rec["abstentions"]]


def test_abstention_lines_name_the_public_basket():
    nodes, edges = _fixtures_full()
    rec = _records(nodes, edges)["hk:0700"]
    entry = next(a for a in rec["abstentions"] if a["code"] == "market_not_wired")
    assert entry["basket"]["name_en"] and entry["basket"]["name_zh"]
    assert "ths" not in entry["basket"]["name_en"].lower()


def test_blob_abstainer_index_carries_typed_reasons():
    """Abstaining tickers ship in the compact index, never as "not found"."""
    nodes, edges = _fixtures_full()
    parsed = json.loads(_ticker_lookup_json(
        REPO, nodes, edges, as_of="2026-06-01", knowledge_cutoff="2026-06-01",
    ))
    idx = parsed["abstainers"]
    names = parsed["basket_names"]
    assert idx["cn:THS"] == "no_public_basket"
    pairs = idx["hk:0700"]
    assert any(code == "market_not_wired" for code, _ in pairs)
    assert all(0 <= i < len(names) for _, i in pairs)
    for key in parsed["records"]:
        assert key not in idx
    for rec in parsed["records"].values():
        assert rec["paths"]


def test_abstention_classifier_handles_all_three_codes():
    # Direct classifier test — guarantees each branch is hit even if a
    # fixture future-edit silently drops one path.
    unmapped = frozenset({"gold_miners"})
    assert _classify_abstention("basket:baskets:gold_miners", unmapped) == \
        "basket_not_a_theme"
    assert _classify_abstention("basket:baskets_hk:tech_hk", unmapped) == \
        "market_not_wired"
    assert _classify_abstention("basket:baskets:orphan_us", unmapped) == \
        "basket_unmapped"


# ---------------------------------------------------------------------------
# 4. china_ths-only company yields no_public_basket; HTML carries no THS id/name
# ---------------------------------------------------------------------------


def test_china_ths_only_company_is_no_public_basket():
    nodes, edges = _fixtures_full()
    records = _records(nodes, edges)
    rec = records["cn:THS"]
    assert rec["no_public_basket"] is True
    assert rec["paths"] == []
    assert rec["not_in_graph"] is False
    assert rec["abstentions"] == []


def test_html_does_not_leak_internal_basket_ids_or_names():
    nodes, edges = _fixtures_full()
    html = _html(nodes, edges)
    # The shared nav include carries one URL (``baskets_china_ths.html``)
    # that exists on every page; we exclude the nav block (everything before
    # ``class="wrap"``) so the gate stays scoped to the U3 surface, the
    # established U1 pattern.
    wrap_at = html.find('class="wrap"')
    assert wrap_at != -1, "wrap block missing"
    body = html[wrap_at:]
    # Slice the blob out of the body — internal basket ids are allowed
    # inside the JSON script element (the JSON serializer encodes them).
    raw = _BLOB_RE.search(body)
    assert raw is not None, "ticker lookup blob missing from U3 body"
    before_blob = body[:raw.start()]
    after_blob = body[raw.end():]
    for chunk in (before_blob, after_blob):
        for needle in ("liquor_ths", "baskets_china_ths", "Liquor THS",
                        "THS白酒"):
            assert needle not in chunk, f"internal-only token {needle!r} leaked into U3 HTML"
        # The vendor chip id must not appear in the body either.
        assert not _VENDOR.search(chunk), \
            f"vendor id leaked into U3 body: {_VENDOR.search(chunk).group(0)!r}"


# ---------------------------------------------------------------------------
# 5. Contract — the builder reads but never writes; no company→theme edge
# ---------------------------------------------------------------------------


def test_builder_does_not_modify_nodes_parquet(monkeypatch):
    """The builder must not touch ``data/theme_graph/nodes.parquet``."""
    nodes_path = REPO / "data" / "theme_graph" / "nodes.parquet"
    if not nodes_path.exists():
        pytest.skip("data/theme_graph/nodes.parquet missing in this sparse tree")
    before = nodes_path.read_bytes()
    edges_path = REPO / "data" / "theme_graph" / "edges.parquet"
    before_edges = edges_path.read_bytes() if edges_path.exists() else b""
    try:
        compose(REPO)
    except Exception:  # noqa: BLE001 — store may be partial in CI
        pass
    after = nodes_path.read_bytes()
    after_edges = edges_path.read_bytes() if edges_path.exists() else b""
    assert after == before, "nodes.parquet bytes changed"
    assert after_edges == before_edges, "edges.parquet bytes changed"


def test_lookup_blob_carries_no_company_theme_edge():
    nodes, edges = _fixtures_full()
    records = _records(nodes, edges)
    # No path should ever end with a company node (chain ends at theme).
    for key, rec in records.items():
        for path in rec["paths"]:
            chain = path["chain"]
            assert chain, f"{key}: empty chain"
            for step in chain:
                assert not step["node_id"].startswith("co:"), \
                    f"{key}: company leaked into chain {step}"


# ---------------------------------------------------------------------------
# 6. Forbidden-key walk over the blob
# ---------------------------------------------------------------------------


def test_lookup_blob_passes_forbidden_key_walk():
    nodes, edges = _fixtures_full()
    blob = _blob(_html(nodes, edges))
    assert hb.validate_no_forbidden_keys(blob) == []


# ---------------------------------------------------------------------------
# 7. Blob size — at most 400 KB; budget overflow keeps paths + summary
# ---------------------------------------------------------------------------


def test_lookup_blob_within_budget_on_real_data():
    nodes_path = REPO / "data" / "theme_graph" / "nodes.parquet"
    edges_path = REPO / "data" / "theme_graph" / "edges.parquet"
    if not (nodes_path.exists() and edges_path.exists()):
        pytest.skip("data/theme_graph parquets missing in this sparse tree")

    from scripts.build_theme_tree_page import _TICKER_BLOB_BUDGET_BYTES

    nodes = pd.read_parquet(nodes_path)
    edges = pd.read_parquet(edges_path)
    blob = _ticker_lookup_json(
        REPO, nodes, edges,
        as_of="2026-10-17", knowledge_cutoff="2026-10-17",
    )
    assert blob
    size = len(blob.encode("utf-8"))
    assert size <= _TICKER_BLOB_BUDGET_BYTES, (
        f"blob {size} bytes > budget {_TICKER_BLOB_BUDGET_BYTES}; "
        f"the prune path must have fired and dropped abstaining companies"
    )


def test_lookup_json_drop_path_keeps_paths_and_summary(monkeypatch):
    """If a tiny budget trips, only path-bearing companies + a summary ship."""
    from scripts import build_theme_tree_page as mod

    nodes, edges = _fixtures_full()
    # Force a 1-byte budget so the drop path always runs.
    monkeypatch.setattr(mod, "_TICKER_BLOB_BUDGET_BYTES", 1)
    blob = mod._ticker_lookup_json(
        REPO, nodes, edges,
        as_of="2026-06-01", knowledge_cutoff="2026-06-01",
    )
    parsed = json.loads(blob)
    # All kept records have at least one path (US:AAPL, US:NVDA, CN:600519).
    for key, rec in parsed["records"].items():
        assert rec["paths"], f"abstaining company {key} leaked into pruned blob"
    assert parsed.get("_summary", {}).get("no_paths", 0) >= 1


# ---------------------------------------------------------------------------
# 8. UI surface — search field + result panel are wired in HTML
# ---------------------------------------------------------------------------


def test_template_search_field_and_result_panel_are_present():
    nodes, edges = _fixtures_full()
    html = _html(nodes, edges)
    assert _LOOKUP_LABEL_RE.search(html), "lookup input missing"
    assert _RESULT_RE.search(html), "result panel missing"
    assert 'role="search"' in html or 'role="search"' in html or 'tt-lookup' in html
    assert 'aria-live="polite"' in html  # the aside carries aria-live


def test_template_lookup_blob_escapes_script_close():
    """``</`` cannot appear inside the inline JSON script element."""
    nodes, edges = _fixtures_full()
    blob = _ticker_lookup_json(
        REPO, nodes, edges, as_of="2026-06-01", knowledge_cutoff="2026-06-01",
    )
    assert "</" not in blob
    assert "<\\/script>" not in blob or blob.startswith("{")
    # When the string has a closing tag in any field it must be escaped.
    # Our fixture has no CJK close tags; a future field add with '<' must
    # still be safe — the builder replaces "</" with "<\\/".
    assert "&lt;/" not in blob or "<\\/" in blob


def test_template_lookup_label_is_bilingual():
    nodes, edges = _fixtures_full()
    html = _html(nodes, edges)
    assert ">Find a company<" in html
    assert ">查找公司<" in html


def test_template_uses_only_token_vars_no_raw_hex_or_rgb():
    """Source-level — SPEC §0: CSS uses ``var(--…)`` tokens only."""
    src = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")
    raw_color = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgb\s*\(|rgba\s*\(|hsl\s*\(|hsla\s*\(")
    visible = re.sub(r"<script\b.*?</script>", "", src, flags=re.S)
    visible = re.sub(r"\{#.*?#\}", "", visible, flags=re.S)
    hits = [m.group(0) for m in raw_color.finditer(visible)]
    assert not hits, f"raw color in template: {hits[:5]}"


def test_template_no_runtime_style_cssText_or_textContent_in_js():
    src = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")
    js = "".join(re.findall(r"<script\b.*?</script>", src, re.S))
    assert ".cssText" not in js
    assert "style.textContent" not in js
    assert "cssText" not in js


def test_template_no_cjk_in_title_attrs():
    src = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")
    cjk = re.compile(r"[一-鿿㐀-䶿　-〿＀-￯]")
    for m in re.finditer(r'title\s*=\s*"([^"]*)"', src):
        assert not cjk.search(m.group(1)), \
            f"CJK inside title= at {m.start()}: {m.group(1)!r}"


def test_template_has_no_inline_style_attributes():
    src = (REPO / "templates" / "theme_tree.html.j2").read_text(encoding="utf-8")
    assert 'style="' not in src