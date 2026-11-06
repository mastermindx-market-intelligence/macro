"""Read-only census: why bound THS-theme CN members resolve NOT_IN_MASTER in HISTORICAL mode.

Usage (repo root, full or data/-enabled sparse checkout):
    PYTHONPATH=. python3 research/theme_graph/gmi_cn_identity_20261102/census_cn_identity.py \
        2026-11-02 research/theme_graph/gmi_cn_identity_20261102/census_2026-11-02.json

Measures, never mutates. Every identity read goes through the module's own
`engine.theme_graph.identity_resolution._resolve_node_row` in both modes (the
same call `resolve_graph_node_identity(asof=...)` makes for HISTORICAL mode).

The bound-theme population mirrors the binding rule proposed in PR #10627
(`engine/neuralweb/theme_state_adapter.py::_expressed_basket`, not on main at
the time of writing): exactly one live `basket:baskets_china_ths:*` node
EXPRESSES an `ltheme:ths:*` node (edge not expired, basket not retired or
merged), and a basket expressing two concepts binds neither.  Theme membership
is read ONLY to enumerate which company nodes the theme state would read; it is
never used as identity evidence (gate #2).
"""
from __future__ import annotations

import collections
import json
import sys

import pandas as pd

from engine import basket_membership_pit as pit
from engine.theme_graph import identity_resolution as ir
from engine.theme_graph import store

INELIGIBLE_HISTORICAL = {"store", "yahoo_fetch", "polygon"}


def _bound_themes(nodes: pd.DataFrame, edges: pd.DataFrame, asof: str) -> dict[str, str]:
    nmap = {r["node_id"]: r for r in nodes.to_dict("records")}
    ex = edges[(edges.type == "EXPRESSES")
               & edges.src.str.startswith("basket:baskets_china_ths:")
               & edges.dst.str.startswith("ltheme:ths:")]
    peers: dict[str, set[str]] = collections.defaultdict(set)
    for r in ex.to_dict("records"):
        vt = r.get("valid_to")
        if isinstance(vt, str) and vt and vt <= asof:
            continue
        b = nmap.get(r["src"])
        if b is None:
            continue
        if isinstance(b.get("merged_into"), str) and b["merged_into"]:
            continue
        rd = b.get("retire_date")
        if isinstance(rd, str) and rd and rd <= asof:
            continue
        peers[r["dst"]].add(r["src"])
    bcount = collections.Counter(b for s in peers.values() for b in s)
    return {d: next(iter(s)) for d, s in peers.items()
            if len(s) == 1 and bcount[next(iter(s))] == 1}


def _classify(hist: dict, cur: dict, dated_eligible: list[dict], asof: str) -> str:
    if hist["resolution_state"] == "RESOLVED":
        return "resolved"
    receipts = json.loads(hist.get("source_receipts") or "{}")
    if receipts.get("cross_market_collision"):
        return "cross_market_mismatch"
    if dated_eligible:
        return "dated_row_not_covering_asof"
    if cur["resolution_state"] == "NOT_IN_MASTER":
        return "no_master_row"
    if receipts.get("current_catalog_rows_excluded_as_historical_evidence"):
        return "no_dated_eligible_alias"
    return "other"


def main(asof: str, out: str) -> None:
    nodes, edges = store.read_nodes(), store.read_edges()
    nmap = {r["node_id"]: r for r in nodes.to_dict("records")}
    etf = ir._etf_symbols(nodes.to_dict("records"))
    inputs = ir.load_master_inputs()
    aliases = pd.read_parquet("data/reference/vendor_aliases.parquet")
    dated = aliases[~aliases.vendor.isin(INELIGIBLE_HISTORICAL)
                    & (aliases.valid_from.notna() | aliases.valid_to.notna())]

    bound = _bound_themes(nodes, edges, asof)
    theme_members: dict[str, list[str]] = {}
    for theme, basket in sorted(bound.items()):
        m = pit.members_asof(basket.split(":", 2)[2], asof, suite="baskets_china_ths")
        theme_members[theme] = sorted(m.get("members") or [])

    member_nodes = sorted({f"co:cn:{t}" for ms in theme_members.values() for t in ms})
    node_rows: dict[str, dict] = {}
    refusals: dict[str, set] = {}
    for nid in member_nodes:
        if nid not in nmap:
            node_rows[nid] = {"cause": "no_company_node"}
            continue
        kw = dict(node_id=nid, resolution_asof=asof, inputs=inputs, etf_symbols=etf,
                  computed_at="census", engine_version="census")
        hist = ir._resolve_node_row(**kw, historical=True)
        cur = ir._resolve_node_row(**kw, historical=False)
        symbol = nid.split(":", 2)[2]
        de = dated[dated.vendor_symbol == symbol][["vendor", "valid_from", "valid_to"]]
        de_rows = [{k: (None if pd.isna(v) else str(v)) for k, v in r.items()}
                   for r in de.to_dict("records")]
        cause = _classify(hist, cur, de_rows, asof)
        refusals.setdefault(cause, set()).add(hist["refusal_reason"])
        row = {"cause": cause, "current": cur["resolution_state"],
               "current_security_id": cur["security_id"]}
        if de_rows:
            row["dated_eligible_alias_rows"] = de_rows
        node_rows[nid] = row

    themes = []
    for theme, ms in theme_members.items():
        causes = collections.Counter(node_rows[f"co:cn:{t}"]["cause"] for t in ms)
        themes.append({"theme": theme, "basket": bound[theme], "n_members": len(ms),
                       "member_causes": dict(sorted(causes.items())),
                       "members": [f"co:cn:{t}" for t in ms]})

    summary = {
        "asof": asof,
        "bound_themes": len(themes),
        "themes_with_any_resolved_member": sum(1 for t in themes if t["member_causes"].get("resolved")),
        "distinct_member_nodes": len(node_rows),
        "member_node_causes": dict(sorted(collections.Counter(r["cause"] for r in node_rows.values()).items())),
        "membership_pairs": sum(t["n_members"] for t in themes),
        "historical_refusal_by_cause": {k: sorted(map(str, v)) for k, v in sorted(refusals.items())},
        "membership_pair_causes": dict(sorted(sum((collections.Counter(t["member_causes"]) for t in themes),
                                                  collections.Counter()).items())),
    }
    print(json.dumps(summary, indent=1))
    with open(out, "w") as fh:
        json.dump({"summary": summary, "themes": themes, "nodes": node_rows}, fh,
                  ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fh.write("\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
