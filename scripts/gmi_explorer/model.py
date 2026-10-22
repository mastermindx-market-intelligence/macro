"""GMI explorer data model — the coverage proof + taxonomy -> fixture-shaped dict.

One function, :func:`build_model`, turns the REAL artifacts (the coverage proof
report, the universe manifest, the theme crosswalk, the probation activity
ledger, the dated symbol directory) into the same key shape the frozen design
specimen reads (``mockups/refs/gmi_explorer/inputs/fixture.json``), so the six
explorer pages render from measured data with nothing hand-copied.

The model computes nothing for display beyond counts the proof already made and
list lengths: every number is taken from the report or counted from its lists.
It is pure — no network, no writes, no new identity store or cache. Names come
from the dated symbol directory through the rule in :func:`_display_name`; no
verbatim source text is ever emitted (excerpt text stays None whenever source
rights are not GRANTED, which is the current state for every known link).

Schema: ``gmi_explorer.model.v1``.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from collections import Counter, OrderedDict
from pathlib import Path

import yaml

from engine.theme_graph.identity_resolution import (
    UnknownGraphNodeError,
    resolve_graph_node_identity,
)

MODEL_SCHEMA = "gmi_explorer.model.v1"
REASON_CODES_PATH = Path("config/gmi_reason_codes.yml")
CROSSWALK_PATH = Path("config/theme_crosswalk.yml")
LEDGER_PATH = Path("data/theme_graph/probation/activity_proposals.jsonl")
EDGES_PATH = Path("data/company_intelligence/relationships/relationship_edges.json")
DECK_PATH = Path("research/theme_graph/gmi_relationships_20261021/m3/describe_premises_v1.json")
SNAPSHOT_DIR = Path("data/symbol_directory/snapshots")
SOURCE_CASE_PATH = Path(
    "research/theme_graph/economic_network_execution_20261009/MICRON_SOURCE_CASE.json")

#: taxonomy tier -> the two words the specimen uses
TIER_WORDS = {"FROZEN_ACCEPTANCE": "acceptance", "DISPLAY_EXPANSION": "display"}
#: micro kind, identical to build_specimens.micro_kind plus the admitted rule
KIND_ORDER = {"held": 0, "adm": 1, "acc": 2, "disp": 3}
#: display-tier micros carry the expansion reason, never a disposition
EXPANSION_REASON = "ACTIVITY_EXPANSION_TIER_ONLY"
#: SPECS §10 state keys in table order, with the plain titles from §10/§12
STATE_KEYS = (
    ("fetch_failed", "Couldn’t load the theme map", "主题地图加载失败"),
    ("stale", "Showing the 19 Oct read", "显示10月19日的读取结果"),
    ("rights_withheld", "Size withheld", "规模暂不显示"),
    ("purpose_denied", "Limited to research use", "仅限研究用途"),
    ("source_paused", "Paused: source check failed", "已暂停：来源校验未通过"),
    ("unknown", "Not disclosed · Not set yet", "未披露 · 尚未设定"),
    ("loading", "Loading", "加载中"),
    ("empty", "No documented relationships yet", "尚无已记录的关系"),
    ("read_updated", "Read updated", "读取已更新"),
    ("path_template", "Conditioned path · layout only", "附条件路径 · 仅版式"),
)
#: clock names in ledger order
CLOCK_NAMES = ("publication", "knowledge", "observation", "effective",
               "admitted", "correction", "served_generation")
#: one trailing corporate suffix stripped from a directory security_name
NAME_SUFFIXES = (", Inc.", " Inc.", ", Inc", " Corporation", " Corp.", " Ltd.",
                 " Limited", " plc", " N.V.", " S.A.", " SE")


def load_reason_words(repo_root: Path) -> dict:
    """The yml sections merged into one CODE -> {en, zh} map."""
    data = yaml.safe_load((Path(repo_root) / REASON_CODES_PATH).read_text(encoding="utf-8"))
    merged: dict[str, dict] = {}
    for section in data.values():
        if isinstance(section, dict):
            for code, words in section.items():
                merged.setdefault(code, {"en": words["en"], "zh": words["zh"]})
    return merged


def _micro_kind(disposition: str | None, admitted: int, tier: str) -> str:
    if disposition == "PROPOSED_ONLY":
        return "held"
    if admitted > 0:
        return "adm"
    return "acc" if tier == "acceptance" else "disp"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _newest_snapshot(repo_root: Path, asof: str | None) -> Path | None:
    """The newest dated symbol-directory snapshot (<= asof when given)."""
    snaps = sorted((Path(repo_root) / SNAPSHOT_DIR).glob("*.parquet"), reverse=True)
    if asof:
        dated = [s for s in snaps if s.stem <= asof]
        return dated[0] if dated else None
    return snaps[0] if snaps else None


def _display_name(repo_root: Path, ticker: str, asof: str | None) -> tuple[str, str]:
    """Directory security_name -> a plain company name, or the ticker itself.

    The identity resolver carries no name field today, so the fallback name
    source is the dated symbol directory column ``security_name``: cut at the
    first " - " (the instrument tail), then strip ONE trailing corporate
    suffix. No new identity store, no cache file.
    """
    import pandas as pd

    snapshot = _newest_snapshot(repo_root, asof)
    if snapshot is not None:
        frame = pd.read_parquet(snapshot, columns=["symbol", "security_name"])
        hit = frame[frame["symbol"] == ticker]
        if not hit.empty:
            name = str(hit["security_name"].iloc[0]).split(" - ")[0].strip()
            for suffix in NAME_SUFFIXES:
                if name.endswith(suffix):
                    name = name[: -len(suffix)].strip()
                    break
            if name:
                return name, "symbol_directory.security_name"
    return ticker, "ticker"


def _source_case(repo_root: Path) -> dict | None:
    path = Path(repo_root) / SOURCE_CASE_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _case_url(case: dict | None, source_key: str | None,
              published_date: str | None) -> str | None:
    """A link is a pointer, not emitted text: only a public URL, when matched."""
    if not case:
        return None
    if case.get("document_id") == source_key or case.get("published_date") == published_date:
        return case.get("source_url")
    return None


# Display words for the market identifier code carried inside the resolver's
# issuer id (ISS:<CC>-<MIC>-<TICKER>). Read-only projection of an id the
# resolver already owns; an unlisted MIC renders the ticker alone (GAP 21).
EXCHANGE_WORDS = {
    "XNAS": "Nasdaq", "XNYS": "NYSE", "XASE": "NYSE American",
    "ARCX": "NYSE Arca", "BATS": "Cboe BZX", "XHKG": "HKEX",
    "XSHG": "SSE", "XSHE": "SZSE",
}

# Plain words for the document type behind a link's source key (Tier 1).
SOURCE_LABELS = {
    "sec": ("SEC filing", "SEC 申报文件"),
    "manual": ("Company source", "公司来源"),
}
DEFAULT_SOURCE_LABEL = ("Company source", "公司来源")


def _exchange_of(issuer_id: str | None) -> str | None:
    if not issuer_id or not issuer_id.startswith("ISS:"):
        return None
    parts = issuer_id[4:].split("-")
    return EXCHANGE_WORDS.get(parts[1]) if len(parts) >= 3 else None


def _source_label(source_key: str | None) -> tuple[str, str]:
    prefix = (source_key or "").split(":", 1)[0]
    return SOURCE_LABELS.get(prefix, DEFAULT_SOURCE_LABEL)


def _ticker_of(node_or_issuer_id: str) -> str:
    """co:us:MU -> MU; ISS:US-XNAS-NVDA -> NVDA (last segment after ':','-')."""
    tail = str(node_or_issuer_id).rsplit(":", 1)[-1]
    return tail.rsplit("-", 1)[-1]


def _clock_states(clocks: dict) -> dict:
    out = {}
    for name in CLOCK_NAMES:
        clock = clocks.get(name) or {}
        known = clock.get("state") == "KNOWN"
        out[name] = {"state": clock.get("state"),
                     "value": clock.get("value") if known else None}
    return out


def _identity_fields(repo_root: Path, node_id: str, row: dict, asof: str | None) -> dict:
    """issuer_id / security_id / resolution_state — resolver first, row fallback."""
    try:
        identity = resolve_graph_node_identity(node_id, asof)
    except (UnknownGraphNodeError, KeyError):
        issuer = row.get("issuer") or {}
        return {"issuer_id": issuer.get("issuer_id"),
                "security_id": issuer.get("security_id"),
                "resolution_state": issuer.get("resolution_state")}
    return {"issuer_id": identity.get("issuer_id"),
            "security_id": identity.get("security_id"),
            "resolution_state": identity.get("resolution_state")}


def _link(row: dict, micro_names: dict, case: dict | None) -> dict:
    ev = row["evidence"]
    source_ev = ev.get("source_evidence") or {}
    edition = source_ev.get("edition") or {}
    span = source_ev.get("span") or {}
    use_q = ev.get("use_qualification") or {}
    rights = use_q.get("source_rights") or {}
    emission_state = rights.get("public_emission")
    scope = ev.get("scope") or {}
    segment = scope.get("segment") or {}
    magnitudes = ev.get("magnitudes") or {}
    curation = row.get("curation") or {}
    micro_id = (ev.get("endpoints") or {}).get("target_node_id")
    source_key = edition.get("source_key")
    published_date = edition.get("published_date")
    case_matches = _case_url(case, source_key, published_date) is not None
    withheld = emission_state != "GRANTED" or (
        case_matches and (case or {}).get("raw_body_in_git_deliverable") is False)
    excerpt_state = "rights_withheld" if withheld else None
    return {
        "proposal_id": row.get("proposal_id"),
        "status": row.get("status"),
        "micro_id": micro_id,
        "micro_en": (micro_names.get(micro_id) or {}).get("en"),
        "micro_zh": (micro_names.get(micro_id) or {}).get("zh"),
        "role": ev.get("role"),
        "species": ev.get("species"),
        "lifecycle": ev.get("lifecycle"),
        "scope": {
            "product": scope.get("product"),
            "platform": scope.get("platform"),
            "segment": segment.get("value") if segment.get("state") == "KNOWN" else None,
            "counterparty_issuer_id": scope.get("counterparty_issuer_id"),
            "counterparty_display_name": None,  # filled after names resolve
        },
        "magnitude_states": {name: (magnitudes.get(name) or {}).get("state")
                             for name in ("amount", "economic_share")},
        "clock_states": _clock_states(ev.get("clocks") or {}),
        "source": {
            "source_key": source_key,
            "published_date": published_date,
            "span": {"start_byte": span.get("start_byte"),
                     "end_byte": span.get("end_byte")},
            "text_sha256": span.get("text_sha256"),
            "url_if_public": _case_url(case, source_key, published_date),
            "label_en": _source_label(source_key)[0],
            "label_zh": _source_label(source_key)[1],
        },
        "emission_state": emission_state,
        "graph_membership_use": use_q.get("graph_membership_use"),
        "curation": {"decision": curation.get("decision"),
                     "decided_at": curation.get("decided_at")},
        "excerpt_state": excerpt_state,
        "excerpt_text": None,  # verbatim source text is never emitted
    }


def _issuers(repo_root: Path, micro_names: dict, asof: str | None) -> list[dict]:
    ledger = Path(repo_root) / LEDGER_PATH
    if not ledger.exists():
        return []
    latest: "OrderedDict[str, dict]" = OrderedDict()
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            latest[row["proposal_id"]] = row  # last occurrence wins
    case = _source_case(repo_root)
    grouped: "OrderedDict[str, list[dict]]" = OrderedDict()
    for row in latest.values():
        node_id = (row["evidence"].get("endpoints") or {}).get("source_node_id")
        grouped.setdefault(node_id, []).append(row)
    issuers = []
    for node_id, rows in grouped.items():
        ticker = _ticker_of(node_id)
        market = node_id.split(":")[1] if node_id.count(":") >= 2 else None
        display_name, name_source = _display_name(repo_root, ticker, asof)
        links = [_link(row, micro_names, case) for row in rows]
        for link in links:
            counterparty = link["scope"]["counterparty_issuer_id"]
            if counterparty:
                cp_name, _ = _display_name(repo_root, _ticker_of(counterparty), asof)
                link["scope"]["counterparty_display_name"] = cp_name
        identity = _identity_fields(repo_root, node_id, rows[-1], asof)
        issuers.append({
            "node_id": node_id,
            "ticker": ticker,
            "market": market,
            **identity,
            "exchange": _exchange_of(identity.get("issuer_id")),
            "display_name": display_name,
            "display_name_source": name_source,
            "links": links,
        })
    return issuers


def build_model(report: dict, manifest: dict | None, *, repo_root: Path,
                asof: str | None = None) -> dict:
    """Coverage proof + taxonomy + activity ledger -> the fixture-shaped model."""
    repo_root = Path(repo_root)
    crosswalk = yaml.safe_load(
        (repo_root / CROSSWALK_PATH).read_text(encoding="utf-8"))
    hierarchy = crosswalk["hierarchy"]
    reason_words = load_reason_words(repo_root)

    taxonomy = report["taxonomy"]
    core = list(taxonomy["micros"])
    expansion = list(taxonomy["expansion_micros"])

    # -- crosswalk names / facets ------------------------------------------
    x_micros = {m["id"]: m for m in hierarchy["micro_themes"]}
    x_subs = {s["id"]: s for s in hierarchy["sub_themes"]}
    x_themes = {"theme:" + t["id"]: t for t in crosswalk.get("themes", [])}
    cat_list = list(hierarchy["categories"])
    cat_order = {c["id"]: i for i, c in enumerate(cat_list)}

    micro_names = {mid: {"en": (x_micros.get(mid) or {}).get("name_en")
                         or (row.get("name_en") or mid),
                         "zh": (x_micros.get(mid) or {}).get("name_zh") or ""}
                   for mid, row in {m["id"]: m for m in core + expansion}.items()}

    # -- micros -------------------------------------------------------------
    micros: "OrderedDict[str, dict]" = OrderedDict()
    cat_micro_ids: dict[str, list[str]] = {c["id"]: [] for c in cat_list}
    for row in core + expansion:
        mid = row["id"]
        tier = TIER_WORDS[row["tier"]]
        acceptance = tier == "acceptance"
        disposition = row["disposition"] if acceptance else None
        counts = row["counts"]
        admitted = counts["admitted"]
        primary_path = row["parent_paths"][0].split(">")
        xm = x_micros.get(mid) or {}
        micros[mid] = {
            "en": micro_names[mid]["en"],
            "zh": micro_names[mid]["zh"],
            "tier": tier,
            "disposition": disposition,
            "vcp": xm.get("value_chain_position"),
            "asserted_on": row["asserted_on"],
            "primary_path": primary_path,
            "paths": [path.split(">") for path in row["parent_paths"]],
            "path_count": len(row["parent_paths"]),
            "counts": counts,
            "admitted": admitted,
            "kind": _micro_kind(disposition, admitted, tier),
        }
        cat_micro_ids[primary_path[0]].append(mid)

    assert sum(len(v) for v in cat_micro_ids.values()) == 371, \
        "every micro must land in exactly one category"

    # -- cats (file order) --------------------------------------------------
    # The crosswalk `parents` list is the only ordering authority. A theme can
    # sit under several categories (multi-parent), so a theme is listed under a
    # category by the micros whose PRIMARY path runs through that pair; a
    # (category, theme) pair holding no primary micro is not listed there
    # (G-UI-16). Sub-themes keep the parents order and are listed even when
    # empty (the specimen's empty-subs summary row reads them).
    children_of: "OrderedDict[str, list[str]]" = OrderedDict()
    parents_of: "OrderedDict[str, list[str]]" = OrderedDict()
    for edge in hierarchy["parents"]:
        children_of.setdefault(edge["parent"], []).append(edge["child"])
        parents_of.setdefault(edge["child"], []).append(edge["parent"])
    cat_ids = set(cat_order)
    theme_ids = set(x_themes)
    theme_parents = {tid: [pid for pid in pids if pid in cat_ids]
                     for tid, pids in parents_of.items() if tid in theme_ids}

    def _theme_names(tid: str) -> tuple[str, str]:
        node = x_themes.get(tid) or {}
        return (node.get("name_en") or node.get("en") or tid,
                node.get("name_zh") or node.get("zh") or "")

    cats = []
    for cat in cat_list:
        cid = cat["id"]
        in_cat = cat_micro_ids[cid]
        theme_order = [tid for tid in children_of.get(cid, []) if tid in theme_ids]
        for mid in in_cat:  # a primary path through a pair the parents list lacks
            tid = micros[mid]["primary_path"][1]
            if tid not in theme_order:
                theme_order.append(tid)
        themes = []
        for tid in theme_order:
            in_theme = [mid for mid in in_cat if micros[mid]["primary_path"][1] == tid]
            if not in_theme:
                continue
            direct = [mid for mid in in_theme if len(micros[mid]["primary_path"]) == 3]
            sub_order = [sid for sid in children_of.get(tid, []) if sid in x_subs]
            for mid in in_theme:
                path = micros[mid]["primary_path"]
                if len(path) == 4 and path[2] not in sub_order:
                    sub_order.append(path[2])
            subs = []
            for sid in sub_order:
                sub_node = x_subs.get(sid) or {}
                subs.append({"id": sid,
                             "en": sub_node.get("name_en") or sid,
                             "zh": sub_node.get("name_zh") or "",
                             "micros": [mid for mid in in_theme
                                        if len(micros[mid]["primary_path"]) == 4
                                        and micros[mid]["primary_path"][2] == sid]})
            assert len(direct) + sum(len(sub["micros"]) for sub in subs) == len(in_theme)
            en, zh = _theme_names(tid)
            themes.append({"id": tid, "en": en, "zh": zh,
                           "micro_count": len(in_theme),
                           "subs": subs,
                           "direct_micros": direct})
        assert sum(theme["micro_count"] for theme in themes) == len(in_cat)
        cats.append({"id": cid,
                     "en": cat["name_en"],
                     "zh": cat["name_zh"],
                     "themes": themes,
                     "micros": in_cat})

    # -- totals / counts ----------------------------------------------------
    held = sum(1 for m in micros.values() if m["kind"] == "held")
    totals = {
        "micros": len(micros),
        "core": len(core),
        "extended": len(expansion),
        "held": held,
        "admitted_micros": sum(1 for m in micros.values() if m["admitted"] > 0),
    }
    assert totals["micros"] == 371
    assert totals["core"] == len(taxonomy["micros"])
    assert totals["extended"] == len(taxonomy["expansion_micros"])
    disposition_counts = dict(
        Counter(m["disposition"] for m in micros.values()
                if m["tier"] == "acceptance" and m["disposition"]))

    # -- issuers (activity ledger) ------------------------------------------
    issuers = _issuers(repo_root, micro_names, asof)
    theme_links = []
    for issuer in issuers:
        for link in issuer["links"]:
            micro = micros.get(link["micro_id"]) or {}
            admitted = (link["curation"]["decision"] == "ACCEPT"
                        and micro.get("admitted", 0) > 0)
            knowledge = link["clock_states"].get("knowledge") or {}
            first_seen = ((knowledge.get("value") or "")[:10]
                          if knowledge.get("state") == "KNOWN"
                          else link["source"]["published_date"])
            theme_links.append({
                "kind": "adm" if admitted else "held",
                "ticker": issuer["ticker"],
                "name": issuer["display_name"],
                "micro_id": link["micro_id"],
                "micro_en": link["micro_en"],
                "micro_zh": link["micro_zh"],
                "first_seen": first_seen,
                "href": f"gmi-issuer-{issuer['ticker'].lower()}.html",
            })
    extended_dates = sorted({row["asserted_on"] for row in expansion})
    extended_on = extended_dates[-1] if extended_dates else None

    # -- edges / deck: other programs own these; read IF PRESENT -------------
    edges_path = repo_root / EDGES_PATH
    deck_path = repo_root / DECK_PATH
    edges = json.loads(edges_path.read_text(encoding="utf-8")) if edges_path.exists() else []
    deck = json.loads(deck_path.read_text(encoding="utf-8")) if deck_path.exists() else None

    # -- card payloads -------------------------------------------------------
    sub_of = {}
    for mid, m in micros.items():
        parts = m["primary_path"]
        sub_of[mid] = parts[2] if len(parts) == 4 else None
    kind_rank = {mid: KIND_ORDER[m["kind"]] for mid, m in micros.items()}
    ordered = sorted(
        micros,
        key=lambda mid: (cat_order[micros[mid]["primary_path"][0]],
                         kind_rank[mid],
                         micros[mid]["en"].lower()))
    card_payloads = []
    for mid in ordered:
        m = micros[mid]
        cat = next(c for c in cat_list if c["id"] == m["primary_path"][0])
        sub_id = sub_of[mid]
        sub = x_subs.get(sub_id) or {}
        reason = (reason_words.get(m["disposition"])
                  if m["tier"] == "acceptance"
                  else reason_words.get(EXPANSION_REASON)) or {}
        card_payloads.append({
            "id": mid,
            "cat_id": cat["id"],
            "cat_en": cat["name_en"],
            "cat_zh": cat["name_zh"],
            "sub_id": sub_id,
            "sub_en": sub.get("name_en"),
            "sub_zh": sub.get("name_zh"),
            "en": m["en"],
            "zh": m["zh"],
            "tier": m["tier"],
            "kind": m["kind"],
            "disposition": m["disposition"],
            "counts": m["counts"],
            "vcp": m["vcp"],
            "asserted_on": m["asserted_on"],
            "path_count": m["path_count"],
            "reason_en": reason.get("en"),
            "reason_zh": reason.get("zh"),
        })

    # -- provenance ----------------------------------------------------------
    snapshot_path = next((entry["path"] for entry in report.get("inputs", [])
                          if entry.get("role") == "symbol_directory"), None)
    proof_command = ("TZ=UTC python3 -m "
                     f"scripts.gmi_coverage_proof --symbol-directory "
                     f"{snapshot_path} --out <tmp>")
    provenance = {
        "proof_command": proof_command,
        "report_version": report.get("report_version"),
        "report_sha256": hashlib.sha256(
            (json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False)
             + "\n").encode("utf-8")).hexdigest(),
        "source_commit": report.get("source_commit"),
        "crosswalk_sha256": _sha256_file(repo_root / CROSSWALK_PATH),
        "ledger_sha256": _sha256_file(repo_root / LEDGER_PATH),
        "snapshot": Path(snapshot_path).name if snapshot_path else None,
        "built_at_utc": datetime.datetime.now(datetime.timezone.utc)
                                 .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    return {
        "schema": MODEL_SCHEMA,
        "cats": cats,
        "micros": dict(micros),
        "totals": totals,
        "disposition_counts": disposition_counts,
        "coverage": report["activity"],
        "identity": report["identity_coverage"],
        "remainders": report["remainders"],
        "owners": report["owners"],
        "reason_words": reason_words,
        "states": [{"key": key, "en": en, "zh": zh} for key, en, zh in STATE_KEYS],
        "issuers": issuers,
        "edges": edges,
        "edges_state": "present" if edges_path.exists() else "empty",
        "deck": deck,
        # relationships package manifest (counts by species); none until the
        # relationships store lands — only the S3 "edges present" branch reads it
        "edge_package": None,
        "card_payloads": card_payloads,
        "provenance": provenance,
        "theme_parents": theme_parents,
        "theme_links": theme_links,
        "extended_on": extended_on,
        "asof": asof or (Path(snapshot_path).stem if snapshot_path else None),
    }
