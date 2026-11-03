"""GMI theme-graph step-7 coverage proof — measurement ONLY (GMI recovery 2026-10-16 §7).

THE QUESTION IT ASKS. Program §7 needs an honest, reproducible denominator and a
coverage measurement per market: which core (us/cn) master securities carry a
qualified identity, which eligible issuers carry a CURRENT, source-backed,
curator-ratified principal activity, and which micro themes carry any population at
all. The expected verdict on the 95% activity gate is FAIL, and FAIL must stay FAIL:
this CLI never rounds a failing gate into a pass, never produces graph state, and
never proposes anything.

MEASUREMENT ONLY (gate #8): no new producer, store, owner or resolver. Reads the
Data OS security master, the symbol directory, the theme-graph store, the theme
crosswalk and the probation activity queue through their EXISTING owners
(``engine.theme_graph.store`` collapses are replicated row-for-row and
``probation.ratified_activity_memberships`` is called, never re-implemented), and
writes exactly three proof files into ``--out``. It never writes under ``data/`` or
``site/`` (refused, exit 2), never fetches the network, and never calls
``now()``/``today()`` — two runs on identical inputs are byte-identical.

Vendor memberships are counted and NEVER counted as activity: a current MEMBER_OF
edge lands in ``vendor_membership_not_principal_activity`` and can never move the
activity numerator (that is the V lane, not the A lane). Rows whose target is a
basket/ltheme label are dropped from activity entirely and counted in
``proposals_seen.forbidden_label_rows``; no basket:/ltheme: id may appear in any
output byte.

Wider markets (ca/hk/intl) are a LEDGER, never a denominator: they are published
per market with their own status and are never summed into, or with, the core.

Run: python3 scripts/gmi_coverage_proof.py --master ... --receipt ... \
         --symbol-directory ... --symbol-directory-manifest ... --store ... \
         --hierarchy ... [--research-records JSON]... [--activity-proposals JSONL]... \
         --out DIR [--repo-root DIR] [--source-commit SHA]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.theme_graph import probation, store  # noqa: E402
from engine.theme_graph.membership_evidence import _activity_target_definition  # noqa: E402

REPORT_DIRNAME = "gmi_coverage_proof"
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
MANIFEST_SCHEMA = "gmi.coverage_universe_manifest/v1"
REPORT_SCHEMA = "gmi.coverage_report/v1"
DECLARED_MICRO_COUNT = 68
# The frozen acceptance tier is every micro asserted BEFORE this date; micros at or
# after it are display-tier expansion and never enter an acceptance denominator.
FROZEN_TIER_CUTOFF = "2026-10-21"
FROZEN_TIER = "FROZEN_ACCEPTANCE"
EXPANSION_TIER = "DISPLAY_EXPANSION"
ACTIVITY_GATE_PCT = 95

CORE_MARKETS = ("us", "cn")
WIDER_MARKETS = ("ca", "hk", "intl")
COUNTRY_TO_MARKET = {"US": "us", "CN": "cn", "HK": "hk"}

ELIGIBLE = "ELIGIBLE"
EX_SUPERSEDED = "EXCLUDED_SUPERSEDED_DUPLICATE_MINT"
EX_ENTITY_TYPE = "EXCLUDED_ENTITY_TYPE_CONFLICT"
EX_ETF = "EXCLUDED_ETF_KIND"
EX_NON_COMMON = "EXCLUDED_NON_COMMON_INSTRUMENT"

ID_QUALIFIED = "QUALIFIED"
ID_NO_ISSUER = "NO_ISSUER_EVIDENCE"
ID_DEFERRED_EXCEPTION = "DEFERRED_IDENTITY_EXCEPTION"
ID_ISSUER_CONFLICT = "ISSUER_EVIDENCE_CONFLICT"
ID_ENTITY_TYPE = "ENTITY_TYPE_CONFLICT"
ID_DEFERRED = "DEFERRED"
ID_NOT_IN_GRAPH = "NOT_IN_GRAPH"

MASTER_ISSUER_STATES = frozenset({
    "RESOLVED", "NO_ISSUER_EVIDENCE", "DEFERRED_IDENTITY_EXCEPTION", "EVIDENCE_CONFLICT"})

REASON_IDENTITY_NOT_QUALIFIED = "IDENTITY_NOT_QUALIFIED"
REASON_SCOPE_STALE = "ADMITTED_SCOPE_STALE"
REASON_REJECTED = "ACTIVITY_REJECTED_BY_CURATOR"
REASON_PROPOSED = "PROPOSED_NOT_ADMITTED"
REASON_VENDOR_ONLY = "VENDOR_MEMBERSHIP_ONLY"
REASON_NO_ACTIVITY = "NO_ACTIVITY_EVIDENCE"
# A QUALIFIED issuer whose only current activity targets a display-expansion micro:
# reported on the expansion line, never summed into the acceptance numerator.
REASON_EXPANSION_TIER_ONLY = "ACTIVITY_EXPANSION_TIER_ONLY"
REASON_CN_LISTED_COUNTS = "CN_LISTED_COUNTS_NOT_AVAILABLE"
ACTIVITY_REASONS = (REASON_IDENTITY_NOT_QUALIFIED, REASON_SCOPE_STALE, REASON_REJECTED,
                    REASON_PROPOSED, REASON_VENDOR_ONLY, REASON_NO_ACTIVITY)

#: Graph-side ledger states the report understands. RESOLVED splits into RESOLVED
#: (security_id present in the master) and GRAPH_ONLY (absent). Every identity
#: resolution state MUST map here or the run refuses — a state this report cannot
#: name is never silently folded into another bucket.
LEDGER_STATE_MAP = {
    "RESOLVED": ("RESOLVED", "GRAPH_ONLY"),
    "NOT_IN_MASTER": ("NOT_IN_MASTER",),
    "UNSUPPORTED_MARKET": ("UNSUPPORTED_MARKET",),
    "DEFERRED_IDENTITY_EXCEPTION": ("DEFERRED",),
    "ENTITY_TYPE_CONFLICT": ("ENTITY_TYPE_CONFLICT",),
}
LEDGER_REMAINDER_STATES = ("NOT_IN_MASTER", "UNSUPPORTED_MARKET", "DEFERRED",
                           "ENTITY_TYPE_CONFLICT")

THRESHOLDS = {
    "Denominator honesty":
        "100% of the frozen universe has explicit coverage/status for each promised "
        "dimension; issuer/security/activity counts and exclusions are published "
        "separately. No arbitrary all-graph denominator.",
    "Principal activity coverage":
        "At least 95% of eligible core U.S./China issuers have a current source-backed "
        "principal activity and qualified identity; every remainder has a specific "
        "reason and source/owner next step. Assess each market separately.",
    "Taxonomy coverage":
        "All 68 currently adopted micros have versioned scope and an owner-reviewed "
        "coverage disposition. No forced constituent minimum or parent inheritance to "
        "inflate a sparse theme.",
    "Correctness":
        "Zero hard identity merges, fabricated named anonymous customers, unauthorized "
        "source promotion, future leakage, failed-fetch removals, or magnitude/species "
        "conflations in release controls.",
    "Automatic admission":
        "No automatic positive admission until a per-relation/per-source evaluation "
        "supports a one-sided 95% lower confidence bound of at least 95% precision. 59 "
        "independent all-correct cases reach approximately 0.9505; correlated "
        "disclosures require an adjusted design, not this shortcut.",
    "Freshness":
        "At least 95% of accessible material filing/corporate-action changes are "
        "observed and routed within 48 hours; visible stale/unavailable status is "
        "mandatory when source cadence or rights prevent refresh. Validity and "
        "retrieval freshness remain separate.",
    "Corrections":
        "Material confirmed errors are withheld or corrected by the next ordinary "
        "publication; the original view remains reproducible and correction latency "
        "is measured.",
    "Product usefulness":
        "At least 90% success on predefined investor explanation tasks, measured "
        "separately for EN/ZH and supported desktop/mobile views; exact ID/status/date "
        "parity on every release journey.",
    "Predictive claims":
        "No prediction/allocation promotion from descriptive acceptance. The existing "
        "evaluator must separately judge PIT baselines, leakage, costs, robustness, "
        "calibration and the specific intended use.",
}
LANE_DIMENSIONS = ("Correctness", "Automatic admission", "Freshness", "Corrections",
                   "Product usefulness", "Predictive claims")

#: reason -> (market or "*", owner, next_step). Market-specific rows are looked up
#: first; an unmapped reason REFUSES the run — there is no OTHER bucket.
REASON_OWNER_ROWS = (
    ("NO_ISSUER_EVIDENCE", "us",
     ("Data OS security master (scripts/build_security_master.py)",
      "attach issuer evidence (SEC CIK) for the security")),
    ("NO_ISSUER_EVIDENCE", "cn",
     ("Data OS security master (scripts/build_security_master.py)",
      "china_hk issuer admission via CNInfo evidence")),
    ("ISSUER_EVIDENCE_CONFLICT", "*",
     ("Data OS security master", "adjudicate the conflicting issuer evidence")),
    ("DEFERRED_IDENTITY_EXCEPTION", "*",
     ("Data OS identity-exception owner", "resolve the recorded identity exception")),
    ("NOT_IN_GRAPH", "*",
     ("GMI graph population / engine.theme_graph.identity_resolution owner",
      "decide node admission from the master; never inferred")),
    ("ENTITY_TYPE_CONFLICT", "*",
     ("GMI identity_resolution owner", "confirm instrument kind; exclude or re-type")),
    ("DEFERRED", "*",
     ("GMI identity_resolution owner", "resolve the deferred identity")),
    (EX_SUPERSEDED, "*",
     ("Data OS security master", "kept outside the company denominator; own count preserved")),
    (EX_ENTITY_TYPE, "*",
     ("Data OS security master", "kept outside the company denominator; own count preserved")),
    (EX_ETF, "*",
     ("Data OS security master", "kept outside the company denominator; own count preserved")),
    (EX_NON_COMMON, "*",
     ("Data OS security master", "kept outside the company denominator; own count preserved")),
    (REASON_IDENTITY_NOT_QUALIFIED, "*",
     ("engine.company_intelligence.issuer_disclosure_owner + named GMI curator",
      "native fact -> build_activity_membership_evidence -> "
      "make_activity_membership_proposal -> named curator ratification")),
    (REASON_SCOPE_STALE, "*",
     ("engine.company_intelligence.issuer_disclosure_owner + named GMI curator",
      "native fact -> build_activity_membership_evidence -> "
      "make_activity_membership_proposal -> named curator ratification")),
    (REASON_EXPANSION_TIER_ONLY, "*",
     ("GMI taxonomy seat (DEC:GMI-MICRO-EXPANSION-2026-10-21-ADDITIVE-FROZEN-68)",
      "display-tier activity only: a frozen-tier (asserted_on < 2026-10-21) "
      "ratified activity row is needed to count for acceptance")),
    (REASON_REJECTED, "*",
     ("engine.company_intelligence.issuer_disclosure_owner + named GMI curator",
      "native fact -> build_activity_membership_evidence -> "
      "make_activity_membership_proposal -> named curator ratification")),
    (REASON_PROPOSED, "*",
     ("engine.company_intelligence.issuer_disclosure_owner + named GMI curator",
      "native fact -> build_activity_membership_evidence -> "
      "make_activity_membership_proposal -> named curator ratification")),
    (REASON_VENDOR_ONLY, "*",
     ("engine.company_intelligence.issuer_disclosure_owner + named GMI curator",
      "native fact -> build_activity_membership_evidence -> "
      "make_activity_membership_proposal -> named curator ratification")),
    (REASON_NO_ACTIVITY, "*",
     ("engine.company_intelligence.issuer_disclosure_owner + named GMI curator",
      "native fact -> build_activity_membership_evidence -> "
      "make_activity_membership_proposal -> named curator ratification")),
    ("NOT_IN_MASTER", "*",
     ("Data OS security master", "decide master admission for the listing")),
    ("UNSUPPORTED_MARKET", "*",
     ("Data OS universe owner", "no installed universe owner for this market")),
    (REASON_CN_LISTED_COUNTS, "cn",
     ("Data OS", "install a market-wide listed-count owner for mainland China")),
)
REASON_OWNER = {(reason, market): (owner, step)
                for reason, market, (owner, step) in REASON_OWNER_ROWS}

_RESEARCH_LIST_KEYS = ("candidates", "proposed_activity_roles", "negative_cases", "scope_holds")


class CoverageProofRefusal(ValueError):
    """A typed refusal: the measurement stops with a one-line reason, exit 2."""


def _s(value) -> str:
    """A plain string cell; null/NaN render as \"\" (never a reconstructed value)."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value)


def _truthy(value) -> bool:
    if value is None or (isinstance(value, float) and value != value):
        return False
    return bool(value)


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def _ratio(numerator: int, denominator: int) -> dict:
    """An exact integer pair plus a 4dp half-up STRING — no floats ever reach JSON."""
    if denominator == 0:
        text = "0.0000"
    else:
        text = str((Decimal(int(numerator)) / Decimal(int(denominator)))
                   .quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    return {"numerator": int(numerator), "denominator": int(denominator), "ratio": text}


def _reason_owner(reason: str, market: str) -> tuple[str, str]:
    if (reason, market) in REASON_OWNER:
        return REASON_OWNER[(reason, market)]
    if (reason, "*") in REASON_OWNER:
        return REASON_OWNER[(reason, "*")]
    raise CoverageProofRefusal(f"UNMAPPED_REASON: {reason!r} (market {market!r}) has no "
                               f"REASON_OWNER row; refusing to publish an ownerless remainder")


# ---------------------------------------------------------------------------
# Store reads — the store.py collapses, replicated row-for-row (test-proven equal)
# ---------------------------------------------------------------------------

def _read_store_parquet(path: Path, columns: tuple[str, ...]) -> pd.DataFrame:
    """A corrupt store REFUSES; a missing side-car reads as empty (store._read semantics)."""
    if not path.exists():
        return pd.DataFrame(columns=list(columns))
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001 — a corrupt store is never described as empty
        raise CoverageProofRefusal(
            f"UNREADABLE_STORE_INPUT: {path.name}: {type(exc).__name__}") from exc
    missing = set(columns) - set(frame.columns)
    if missing:
        raise CoverageProofRefusal(
            f"STORE_INPUT_MISSING_COLUMNS: {path.name}: {sorted(missing)}")
    return frame


def _latest_by_node(df: pd.DataFrame) -> pd.DataFrame:
    """store.read_identity_resolution / read_node_lifecycle (latest=True): max
    computed_at per node_id, ties broken on node_id — never on a value (G0.11)."""
    if df.empty:
        return df
    ordered = df.sort_values(["node_id", "computed_at"], kind="stable")
    return (ordered.drop_duplicates(subset=["node_id"], keep="last")
                   .sort_values("node_id", kind="stable").reset_index(drop=True))


def _overlay_lifecycle(nodes: pd.DataFrame, lifecycle: pd.DataFrame) -> pd.DataFrame:
    """store.read_nodes(current=True): overlay the latest lifecycle
    status/retire_date/merged_into onto the write-once node rows by node_id."""
    if nodes.empty or lifecycle.empty:
        return nodes
    overlay = lifecycle.set_index("node_id")[["status", "retire_date", "merged_into"]]
    out = nodes.copy()
    out = out.set_index("node_id", drop=False)
    hit = out.index.intersection(overlay.index)
    if len(hit):
        out.loc[hit, "status"] = overlay.loc[hit, "status"]
        out.loc[hit, "retire_date"] = overlay.loc[hit, "retire_date"]
        out.loc[hit, "merged_into"] = overlay.loc[hit, "merged_into"]
    return out.reset_index(drop=True)


def _latest_belief_edges(df: pd.DataFrame) -> pd.DataFrame:
    """store.read_edges(latest_belief=True): max belief_time per edge_id, ties broken
    on the later computed_at then edge_id — never on a magnitude (G0.11)."""
    if df.empty:
        return df
    ordered = df.sort_values(["edge_id", "belief_time", "computed_at"], kind="stable")
    latest = ordered.drop_duplicates(subset=["edge_id"], keep="last")
    return latest.sort_values("edge_id", kind="stable").reset_index(drop=True)


def read_store(store_dir: Path) -> dict:
    """Read one theme-graph store directory, read-only. evidence.parquet not needed."""
    if not (store_dir / "nodes.parquet").exists() or not (store_dir / "edges.parquet").exists():
        raise CoverageProofRefusal(
            f"MISSING_STORE_LEDGER: {store_dir} needs nodes.parquet and edges.parquet")
    nodes = _read_store_parquet(store_dir / "nodes.parquet", store.NODE_COLUMNS)
    lifecycle = _read_store_parquet(store_dir / "node_lifecycle.parquet",
                                    store.NODE_LIFECYCLE_COLUMNS)
    identity = _read_store_parquet(store_dir / "identity_resolution.parquet",
                                   store.IDENTITY_RESOLUTION_COLUMNS)
    edges = _read_store_parquet(store_dir / "edges.parquet", store.EDGE_COLUMNS)
    meta_path = store_dir / "_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — corrupt metadata refuses, never reads as {}
            raise CoverageProofRefusal(
                f"UNREADABLE_STORE_INPUT: _meta.json: {type(exc).__name__}") from exc
        if not isinstance(meta, dict):
            raise CoverageProofRefusal("UNREADABLE_STORE_INPUT: _meta.json is not an object")
    proposals_path = store_dir / "probation" / "proposals.jsonl"
    queue = (probation.read_proposals(proposals_path)
             if proposals_path.exists() else [])
    # The activity ledger (scripts/propose_activity_membership.py's default,
    # probation.ACTIVITY_PROPOSALS_PATH) lives beside the hierarchy queue. It is
    # read by default so the proof's remainder reasons and the micro disposition
    # ledger see real PROPOSED/RATIFIED rows without an operator remembering
    # --activity-proposals (measured 2026-10-22: the M3 proof reported no
    # proposals while one sat in the ledger). It never enters the numerator by
    # itself: the same tiering and ratification owners judge every row.
    activity_ledger_path = store_dir / "probation" / "activity_proposals.jsonl"
    if activity_ledger_path.exists():
        queue = list(queue) + list(probation.read_proposals(activity_ledger_path, strict=True))
    return {
        "nodes_raw": nodes,
        "lifecycle_latest": _latest_by_node(lifecycle),
        "identity_latest": _latest_by_node(identity),
        "nodes_current": _overlay_lifecycle(nodes, _latest_by_node(lifecycle)),
        "edges_latest": _latest_belief_edges(edges),
        "meta": meta,
        "queue": queue,
        "files": {
            "nodes": store_dir / "nodes.parquet",
            "edges": store_dir / "edges.parquet",
            "identity_resolution": store_dir / "identity_resolution.parquet",
            "node_lifecycle": store_dir / "node_lifecycle.parquet",
            "meta": meta_path,
            "probation_proposals": proposals_path,
            "probation_activity_proposals": activity_ledger_path,
        },
    }


# ---------------------------------------------------------------------------
# Input provenance
# ---------------------------------------------------------------------------

def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _input_record(role: str, path: Path, repo_root: Path) -> dict:
    data = path.read_bytes()
    return {"role": role, "path": _display_path(path, repo_root), "bytes": len(data),
            "git_blob_sha1": hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()}


def _read_json(path: Path, what: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — typed refusal, never a silent fallback
        raise CoverageProofRefusal(
            f"UNREADABLE_INPUT: {what} {path.name}: {type(exc).__name__}") from exc


# ---------------------------------------------------------------------------
# Graph-side context (hint/etf/resolution lookups over the collapsed store views)
# ---------------------------------------------------------------------------

class _GraphContext:
    """Lookups over the collapsed store views. The symbol hint is annotation only;
    it never establishes identity."""

    def __init__(self, nodes_current, identity_latest, edges_latest):
        self.identity_rows = identity_latest.to_dict("records")
        self.edges_latest_rows = edges_latest.to_dict("records")
        self.active_nodes = {str(r["node_id"]) for r in nodes_current.to_dict("records")
                             if str(r.get("status")) not in store.RETIRED_LIKE_STATUSES}
        self.node_market = {str(r["node_id"]): str(r.get("market_scope") or "")
                            for r in nodes_current.to_dict("records")}
        self.node_status = {str(r["node_id"]): str(r.get("status") or "")
                            for r in nodes_current.to_dict("records")}
        self.kind = {str(r["node_id"]): str(r.get("kind") or "")
                     for r in nodes_current.to_dict("records")}
        self.conflict = {}   # (market, hint) -> [node_id]
        self.deferred = {}   # (market, hint) -> [node_id]
        self.by_security = {}  # security_id -> [node_id] (identity-latest RESOLVED rows)
        self.security_by_node = {}  # node_id -> security_id (identity-latest RESOLVED rows)
        self.etf_symbols = {}  # market -> {symbol_root: [node_id]}
        for row in self.identity_rows:
            nid = str(row["node_id"])
            market = str(row.get("market_scope") or "")
            state = str(row.get("resolution_state") or "")
            if state == "RESOLVED":
                sid = _s(row.get("security_id"))
                if sid:
                    self.by_security.setdefault(sid, []).append(nid)
                    self.security_by_node[nid] = sid
                continue
            if state == "ENTITY_TYPE_CONFLICT":
                self.conflict.setdefault((market, _symbol_hint(nid, market)), []).append(nid)
            elif state == "DEFERRED_IDENTITY_EXCEPTION":
                self.deferred.setdefault((market, _symbol_hint(nid, market)), []).append(nid)
        for sid in self.by_security:
            self.by_security[sid].sort()
        for row in nodes_current.to_dict("records"):
            if str(row.get("kind")) != "etf":
                continue
            try:
                ext = json.loads(row.get("external_ids") or "{}")
            except Exception:  # noqa: BLE001 — malformed external_ids is not fatal here
                continue
            symbol = _s(ext.get("symbol") if isinstance(ext, dict) else None)
            if not symbol:
                continue
            market = str(row.get("market_scope") or "")
            root = symbol.split(".", 1)[0].strip().upper()
            self.etf_symbols.setdefault(market, {}).setdefault(root, []).append(str(row["node_id"]))
        for market in self.etf_symbols:
            for root in self.etf_symbols[market]:
                self.etf_symbols[market][root].sort()
        self.member_of = [row for row in edges_latest.to_dict("records")
                          if str(row.get("type")) == "MEMBER_OF" and _s(row.get("valid_to")) == ""]

    def nodes_for(self, table, market: str, inception: str) -> list[str]:
        return sorted(table.get((market, inception), ()))

    def graph_etf_nodes(self, market: str, inception: str) -> list[str]:
        return sorted(self.etf_symbols.get(market, {}).get(inception.strip().upper(), ()))


def _symbol_hint(node_id: str, market: str) -> str:
    """The node's symbol hint: text after "co:<market>:". For cn/hk the bare 6-/5-digit
    code before any "." suffix. Annotation only — never identity."""
    parts = str(node_id).split(":", 2)
    hint = parts[2] if len(parts) == 3 else ""
    if market in ("cn", "hk"):
        hint = hint.split(".", 1)[0]
    return hint


# ---------------------------------------------------------------------------
# Per-security classification (closed enums, precedence top-down)
# ---------------------------------------------------------------------------

def _eligibility(row: dict, market: str, graph: _GraphContext,
                 directory_flags: dict) -> tuple[str, list[str]]:
    inception = _s(row.get("inception_code"))
    if _s(row.get("security_state")) == "SUPERSEDED_DUPLICATE_MINT":
        return EX_SUPERSEDED, ["master_superseded_duplicate_mint"]
    conflict_nodes = graph.nodes_for(graph.conflict, market, inception)
    if conflict_nodes:
        return EX_ENTITY_TYPE, sorted(f"graph_entity_type_conflict:{nid}"
                                      for nid in conflict_nodes)
    etf_bases: list[str] = []
    non_common_bases: list[str] = []
    if market == "us":
        flags = directory_flags.get(inception)
        if flags:
            if flags["etf"]:
                etf_bases.append("symbol_directory_etf")
            if flags["test_issue"]:
                non_common_bases.append("symbol_directory_test_issue")
            if flags["is_preferred"]:
                non_common_bases.append("symbol_directory_is_preferred")
    etf_bases.extend(f"graph_etf_node:{nid}" for nid in graph.graph_etf_nodes(market, inception))
    if etf_bases:
        # Every ETF basis that applies is listed, directory and graph together.
        return EX_ETF, sorted(etf_bases)
    if non_common_bases:
        return EX_NON_COMMON, sorted(non_common_bases)
    return ELIGIBLE, []


def _identity_status(row: dict, market: str, graph: _GraphContext) -> str:
    state = _s(row.get("issuer_state"))
    if state == "NO_ISSUER_EVIDENCE":
        return ID_NO_ISSUER
    if state == "DEFERRED_IDENTITY_EXCEPTION":
        return ID_DEFERRED_EXCEPTION
    if state == "EVIDENCE_CONFLICT":
        return ID_ISSUER_CONFLICT
    inception = _s(row.get("inception_code"))
    security_id = _s(row.get("security_id"))
    if state == "RESOLVED":
        for nid in graph.by_security.get(security_id, ()):
            if nid in graph.active_nodes:
                return ID_QUALIFIED
    if graph.nodes_for(graph.conflict, market, inception):
        return ID_ENTITY_TYPE
    if graph.nodes_for(graph.deferred, market, inception):
        return ID_DEFERRED
    return ID_NOT_IN_GRAPH


def classify_master(master: pd.DataFrame, graph: _GraphContext,
                    directory_flags: dict) -> tuple[dict, dict, list[dict]]:
    """Every core master security gets exactly one eligibility and one identity status;
    wider master rows are counted as a ledger, never a denominator."""
    core: dict[str, list[dict]] = {market: [] for market in CORE_MARKETS}
    wider: dict[str, list[dict]] = {market: [] for market in WIDER_MARKETS}
    for row in master.to_dict("records"):
        country = _s(row.get("country")).upper()
        market = COUNTRY_TO_MARKET.get(country, "intl")
        if market in CORE_MARKETS:
            state = _s(row.get("issuer_state"))
            if state not in MASTER_ISSUER_STATES:
                raise CoverageProofRefusal(
                    f"MASTER_ISSUER_STATE_OUT_OF_ENUM: security_id "
                    f"{_s(row.get('security_id'))!r} carries issuer_state {state!r}; "
                    f"closed enum is {sorted(MASTER_ISSUER_STATES)}")
            eligibility, bases = _eligibility(row, market, graph, directory_flags)
            status = (_identity_status(row, market, graph) if eligibility == ELIGIBLE else "")
            core[market].append({"row": row, "eligibility": eligibility,
                                 "bases": bases, "identity_status": status})
        else:
            wider[market].append({"row": row})
    return core, wider


def _wider_market_view(market: str, rows: list[dict], graph: _GraphContext) -> dict:
    by_state: dict[str, int] = {}
    for row in graph.identity_rows:
        if str(row.get("market_scope") or "") != market:
            continue
        state = str(row.get("resolution_state") or "")
        if state not in LEDGER_STATE_MAP:
            raise CoverageProofRefusal(
                f"LEDGER_STATE_OUT_OF_ENUM: node {row.get('node_id')!r} carries "
                f"resolution_state {state!r}; this report's state vocabulary is closed")
        key = LEDGER_STATE_MAP[state][0]
        by_state[key] = by_state.get(key, 0) + 1
    by_issuer_state: dict[str, int] = {}
    for entry in rows:
        key = _s(entry["row"].get("issuer_state"))
        by_issuer_state[key] = by_issuer_state.get(key, 0) + 1
    return {
        "graph_company_nodes": sum(1 for nid, kind in sorted(graph.kind.items())
                                   if kind == "company" and graph.node_market.get(nid) == market),
        "by_resolution_state": dict(sorted(by_state.items())),
        "master_securities": len(rows),
        "master_by_issuer_state": dict(sorted(by_issuer_state.items())),
        "status": "WIDER_MARKET_LEDGER_NOT_IN_CORE_DENOMINATOR",
    }


def _market_view(market: str, entries: list[dict], directory_frame, directory_path: Path,
                 directory_manifest: dict) -> dict:
    total = len(entries)
    by_mic: dict[str, int] = {}
    by_issuer_state: dict[str, int] = {}
    by_eligibility: dict[str, int] = {}
    by_identity: dict[str, int] = {}
    resolved_issuers: set[str] = set()
    resolved_issuers_eligible: set[str] = set()
    unresolved_issuer_states: dict[str, int] = {}
    exclusions: list[dict] = []
    eligible_ids: list[str] = []
    security_rows: list[str] = []
    for entry in sorted(entries, key=lambda e: str(e["row"].get("security_id"))):
        row = entry["row"]
        security_id = _s(row.get("security_id"))
        by_mic[_s(row.get("mic"))] = by_mic.get(_s(row.get("mic")), 0) + 1
        issuer_state = _s(row.get("issuer_state"))
        by_issuer_state[issuer_state] = by_issuer_state.get(issuer_state, 0) + 1
        by_eligibility[entry["eligibility"]] = by_eligibility.get(entry["eligibility"], 0) + 1
        if issuer_state == "RESOLVED":
            resolved_issuers.add(_s(row.get("issuer_id")))
            if entry["eligibility"] == ELIGIBLE:
                resolved_issuers_eligible.add(_s(row.get("issuer_id")))
        if entry["eligibility"] == ELIGIBLE:
            by_identity[entry["identity_status"]] = by_identity.get(entry["identity_status"], 0) + 1
            eligible_ids.append(security_id)
            if issuer_state != "RESOLVED":
                unresolved_issuer_states[issuer_state] = \
                    unresolved_issuer_states.get(issuer_state, 0) + 1
        else:
            exclusions.append({"security_id": security_id,
                               "inception_code": _s(row.get("inception_code")),
                               "eligibility": entry["eligibility"],
                               "bases": sorted(entry["bases"])})
        security_rows.append("|".join((security_id, _s(row.get("issuer_id")), issuer_state,
                                       _s(row.get("mic")), _s(row.get("inception_code")),
                                       entry["eligibility"], entry["identity_status"])))
    view = {
        "securities_total": total,
        "securities_by_mic": dict(sorted(by_mic.items())),
        "securities_by_issuer_state": dict(sorted(by_issuer_state.items())),
        "securities_by_eligibility": dict(sorted(by_eligibility.items())),
        "securities_by_identity_status": dict(sorted(by_identity.items())),
        "issuers_resolved_distinct": len(resolved_issuers),
        "issuers_resolved_distinct_eligible": len(resolved_issuers_eligible),
        "eligible_securities_without_resolved_issuer": dict(sorted(unresolved_issuer_states.items())),
        "exclusions": sorted(exclusions, key=lambda e: e["security_id"]),
        "eligible_security_ids_sha256": hashlib.sha256(
            "\n".join(sorted(eligible_ids)).encode("utf-8")).hexdigest(),
        "securities": {"columns": "security_id|issuer_id|issuer_state|mic|inception_code|"
                                  "eligibility|identity_status",
                       "rows": sorted(security_rows)},
    }
    if market == "us":
        view["listed_market_context"] = _us_listed_context(
            entries, directory_frame, directory_path, directory_manifest)
    else:
        view["listed_market_context"] = {"status": "NOT_AVAILABLE_FROM_INSTALLED_OWNER",
                                         "owner": "Data OS"}
    return view


def _us_listed_context(entries, directory_frame, directory_path: Path,
                       directory_manifest: dict) -> dict:
    symbols = ({_s(symbol).strip() for symbol in directory_frame["symbol"].tolist()}
               if "symbol" in directory_frame.columns else set())
    matched, not_matched = 0, []
    for entry in sorted(entries, key=lambda e: str(e["row"].get("security_id"))):
        if _s(entry["row"].get("inception_code")) in symbols:
            matched += 1
        else:
            not_matched.append(_s(entry["row"].get("inception_code")))
    flags = directory_frame.to_dict("records") if not directory_frame.empty else []
    n_etf = sum(1 for row in flags if _truthy(row.get("etf")))
    n_test = sum(1 for row in flags if _truthy(row.get("test_issue")))
    n_pref = sum(1 for row in flags if _truthy(row.get("is_preferred")))
    return {
        "source": str(directory_path),
        "snapshot_date": Path(str(directory_path)).stem,
        "n_symbols": int(len(directory_frame)),
        "n_etf": int(n_etf),
        "n_test_issue": int(n_test),
        "n_preferred": int(n_pref),
        "common_like": int(len(directory_frame) - n_etf - n_test - n_pref),
        "master_us_matched_in_directory": int(matched),
        "master_us_not_in_directory": sorted(not_matched),
        "manifest_display_only": bool(directory_manifest.get("_display_only", False)),
    }


# ---------------------------------------------------------------------------
# Hierarchy / taxonomy
# ---------------------------------------------------------------------------

def _hierarchy(path: Path) -> dict:
    try:
        doc = yaml.safe_load(path.read_bytes())
    except Exception as exc:  # noqa: BLE001
        raise CoverageProofRefusal(
            f"UNREADABLE_INPUT: hierarchy {path.name}: {type(exc).__name__}") from exc
    hierarchy = (doc or {}).get("hierarchy") or {}
    out = {"categories": {}, "sub_themes": {}, "micros": {}, "parents": []}
    for section, key in (("categories", "categories"), ("sub_themes", "sub_themes"),
                         ("micro_themes", "micros")):
        for entry in hierarchy.get(section) or []:
            if isinstance(entry, dict) and entry.get("id"):
                out[key][str(entry["id"])] = entry
    for row in hierarchy.get("parents") or []:
        if isinstance(row, dict) and row.get("parent") and row.get("child"):
            out["parents"].append((str(row["child"]), str(row["parent"])))
    out["parents"].sort()
    return out


def _entry_scope_version(entry: dict) -> str:
    """The definition hash the activity owner uses (membership_evidence
    ._activity_target_definition): the crosswalk entry, dates isoformatted, canonically
    JSON-encoded, sha256. Test 13 proves the parity on the real crosswalk."""
    plain = {key: (value.isoformat() if hasattr(value, "isoformat") and not
                   isinstance(value, str) else value)
             for key, value in entry.items()}
    return hashlib.sha256(_canonical(plain).encode("utf-8")).hexdigest()


def _parent_paths(micro_id: str, hierarchy: dict) -> list[str]:
    parents: dict[str, list[str]] = {}
    for child, parent in hierarchy["parents"]:
        parents.setdefault(child, []).append(parent)
    paths: list[str] = []

    def walk(node: str, trail: list[str]) -> None:
        if node in trail:  # a cyclic parent edge is never enumerated twice
            return
        trail = trail + [node]
        immediate = parents.get(node, [])
        if not immediate:
            paths.append(">".join(reversed(trail)))  # root>...>micro
            return
        for parent in immediate:
            walk(parent, trail)

    walk(micro_id, [])
    return sorted(set(paths))


def _route_kinds(micro_id: str, hierarchy: dict) -> list[str]:
    immediate = {parent for child, parent in hierarchy["parents"] if child == micro_id}
    kinds: list[str] = []
    if immediate & set(hierarchy["categories"]):
        kinds.append("direct")
    if immediate & set(hierarchy["sub_themes"]):
        kinds.append("intermediate")
    return sorted(kinds)


def _scan_research_record(path: Path, known_micro_ids: set[str]) -> tuple[dict, list[str]]:
    doc = _read_json(path, "research record")
    counts: dict[str, int] = {}
    unknown: list[str] = []
    for key in _RESEARCH_LIST_KEYS:
        value = doc.get(key) if isinstance(doc, dict) else None
        if not isinstance(value, list):
            continue
        for item in value:
            if not (isinstance(item, dict) and item.get("micro_id")):
                continue
            micro_id = _s(item.get("micro_id"))
            canonical = (micro_id if micro_id in known_micro_ids
                         else ("theme:" + micro_id if ("theme:" + micro_id) in known_micro_ids
                               else None))
            if canonical is None:
                # A micro_id outside the hierarchy is REPORTED, never dropped silently.
                unknown.append(micro_id)
            else:
                counts[canonical] = counts.get(canonical, 0) + 1
    return counts, sorted(set(unknown))


# ---------------------------------------------------------------------------
# Activity (principal) vs vendor membership (never principal)
# ---------------------------------------------------------------------------

def _row_target(row: dict) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    target = evidence.get("target_definition")
    if isinstance(target, dict) and target.get("theme_id"):
        return str(target["theme_id"])
    return ""


def _is_forbidden_label(row: dict) -> bool:
    """basket:/ltheme: labels (and the finviz/ths vendor names) are never activity."""
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    targets = [_row_target(row)]
    endpoints = evidence.get("endpoints")
    if isinstance(endpoints, dict) and endpoints.get("target_node_id"):
        targets.append(str(endpoints["target_node_id"]))
    for target in targets:
        if (target.startswith("basket:") or target.startswith("ltheme:")
                or "finviz" in target or "baskets_china_ths" in target):
            return True
    return False


def _row_security_id(row: dict) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    issuer = evidence.get("issuer") if isinstance(evidence.get("issuer"), dict) else {}
    return _s(issuer.get("security_id"))


def _row_definition_hash(row: dict) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    target = evidence.get("target_definition") if isinstance(evidence.get("target_definition"),
                                                             dict) else {}
    return _s(target.get("definition_sha256"))


def _current_scope(repo_root: Path, theme_id: str) -> str | None:
    """The CURRENT definition hash of one micro per the activity owner; an unknown
    theme_id is simply never current (ValueError), a missing crosswalk refuses."""
    try:
        return _activity_target_definition(repo_root, theme_id)["definition_sha256"]
    except ValueError:
        return None


def _activity_market_rows(store_queue: list, proposal_rows: list) -> dict:
    all_rows = list(store_queue) + list(proposal_rows)
    a1 = [row for row in all_rows
          if isinstance(row, dict) and row.get("schema") == probation.ACTIVITY_PROPOSAL_SCHEMA]
    forbidden = [row for row in a1 if _is_forbidden_label(row)]
    kept = [row for row in a1 if not _is_forbidden_label(row)]
    # Ratification is the existing owner's verdict, never re-implemented here.
    ratified = probation.ratified_activity_memberships(kept)
    return {
        "rows": all_rows,
        "kept": kept,
        "ratified": ratified,
        "seen": {
            "total_rows": len(all_rows),
            "a1_schema_rows": len(a1),
            "ratified_valid": len(ratified),
            "proposed": sum(1 for row in kept if row.get("status") == "PROPOSED"),
            "rejected": sum(1 for row in kept if row.get("status") == "REJECTED"),
            "scope_stale": 0,
            "forbidden_label_rows": len(forbidden),
        },
    }


def current_member_of_edges(graph: _GraphContext) -> list[dict]:
    """Current MEMBER_OF edges: latest-belief, valid_to null, src an ACTIVE node whose
    identity-latest row RESOLVES to an ELIGIBLE security. Vendor membership is counted
    here and NEVER enters the activity numerator."""
    out = []
    for row in graph.member_of:
        src = str(row.get("src"))
        if src not in graph.active_nodes or graph.kind.get(src) != "company":
            continue
        if graph.security_by_node.get(src):
            out.append(row)
    return out


def _vendor_view(market: str, graph: _GraphContext, eligible_by_security: dict) -> dict:
    issuers: set[str] = set()
    securities: set[str] = set()
    by_dst: dict[str, int] = {}
    by_source_class: dict[str, int] = {}
    vendor_edges = []
    for row in current_member_of_edges(graph):
        src = str(row.get("src"))
        if graph.node_market.get(src) != market:
            continue
        vendor_edges.append(row)
        security_id = graph.security_by_node[src]
        securities.add(security_id)
        issuer_id = eligible_by_security.get(security_id, {}).get("issuer_id")
        if issuer_id:
            issuers.add(issuer_id)
        dst_kind = str(row.get("dst")).split(":", 1)[0]
        by_dst[dst_kind] = by_dst.get(dst_kind, 0) + 1
        source_class = _s(row.get("source_class"))
        by_source_class[source_class] = by_source_class.get(source_class, 0) + 1
    return {
        "eligible_issuers_with_current_member_of": len(issuers),
        "eligible_securities_with_current_member_of": len(securities),
        "member_of_edges_by_dst_kind": dict(sorted(by_dst.items())),
        "member_of_edges_by_source_class": dict(sorted(by_source_class.items())),
    }


def _activity_view(market: str, entries: list[dict], activity: dict, graph: _GraphContext,
                   repo_root: Path, tier_by_micro: dict | None = None) -> dict:
    eligible = [entry for entry in entries if entry["eligibility"] == ELIGIBLE]
    by_security = {}
    for entry in eligible:
        row = entry["row"]
        by_security[_s(row.get("security_id"))] = {
            "issuer_id": _s(row.get("issuer_id")),
            "issuer_state": _s(row.get("issuer_state")),
            "identity_status": entry["identity_status"],
        }
    issuers: dict[str, dict] = {}
    unresolved: list[str] = []
    for security_id, info in sorted(by_security.items()):
        if info["issuer_state"] == "RESOLVED":
            slot = issuers.setdefault(info["issuer_id"], {
                "qualified": False, "current": 0, "stale": 0, "rejected": 0, "proposed": 0,
                "expansion_current": 0})
            slot["qualified"] = slot["qualified"] or info["identity_status"] == ID_QUALIFIED
        else:
            unresolved.append(security_id)
    scope_stale = 0
    expansion_rows_excluded = 0
    for row in activity["ratified"]:
        security_id = _row_security_id(row)
        info = by_security.get(security_id)
        if info is None or info["issuer_state"] != "RESOLVED":
            continue  # a row outside the eligible core denominator attributes to no slot
        theme_id = _row_target(row)
        # An id the hierarchy does not hold stays FROZEN (fail-closed): a row can
        # never leave the acceptance scope check by naming an unknown target.
        tier = tier_by_micro.get(theme_id, FROZEN_TIER) if tier_by_micro is not None \
            else FROZEN_TIER
        current = _current_scope(repo_root, theme_id)
        is_current = current is not None and current == _row_definition_hash(row)
        slot = issuers[info["issuer_id"]]
        if tier == EXPANSION_TIER:
            # Display-tier row: never touches the acceptance numerator, the stale
            # counter or scope_stale; reported on the expansion line instead.
            expansion_rows_excluded += 1
            if is_current:
                slot["expansion_current"] += 1
            continue
        if is_current:
            slot["current"] += 1
        else:
            slot["stale"] += 1
            scope_stale += 1
    vendor_issuers = {info["issuer_id"] for security_id, info in sorted(by_security.items())
                      if info["issuer_state"] == "RESOLVED"
                      and security_id in graph.vendor_eligible_securities.get(market, set())}
    for row in activity["kept"]:
        info = by_security.get(_row_security_id(row))
        if info is None or info["issuer_state"] != "RESOLVED":
            continue
        slot = issuers[info["issuer_id"]]
        if row.get("status") == "REJECTED":
            slot["rejected"] += 1
        elif row.get("status") == "PROPOSED":
            slot["proposed"] += 1
    numerator = 0
    remainder: dict[str, int] = {}
    for issuer_id, slot in sorted(issuers.items()):
        if not slot["qualified"]:
            reason = REASON_IDENTITY_NOT_QUALIFIED
        elif slot["current"] >= 1:
            numerator += 1
            continue
        elif slot["stale"] >= 1:
            reason = REASON_SCOPE_STALE
        elif slot["expansion_current"] >= 1:
            reason = REASON_EXPANSION_TIER_ONLY
        elif slot["rejected"] >= 1:
            reason = REASON_REJECTED
        elif slot["proposed"] >= 1:
            reason = REASON_PROPOSED
        elif issuer_id in vendor_issuers:
            reason = REASON_VENDOR_ONLY
        else:
            reason = REASON_NO_ACTIVITY
        remainder[reason] = remainder.get(reason, 0) + 1
    for _security_id in unresolved:
        remainder[REASON_IDENTITY_NOT_QUALIFIED] = remainder.get(
            REASON_IDENTITY_NOT_QUALIFIED, 0) + 1
    n = len(issuers)
    m = len(unresolved)
    lower = n + (1 if m else 0)
    upper = n + m
    expansion_issuers = sum(1 for slot in issuers.values()
                            if slot["qualified"] and slot["expansion_current"] >= 1)
    seen = dict(activity["seen"])
    seen["scope_stale"] = scope_stale
    seen["expansion_tier_rows_excluded"] = expansion_rows_excluded
    return {
        "numerator_issuers": numerator,
        "denominator": {"eligible_issuers_resolved": n,
                        "eligible_securities_unresolved_issuer": m,
                        "issuer_count_bounds": [lower, upper]},
        "ratio_lower_bound_denominator": _ratio(numerator, upper),
        "ratio_upper_bound_denominator": _ratio(numerator, lower),
        "remainder_by_reason": dict(sorted(remainder.items())),
        "proposals_seen": seen,
        # Display tier only: never an acceptance numerator, denominator or gate input.
        "expansion_tier": {
            "label": "DISPLAY_TIER_NOT_ACCEPTANCE",
            "tier_cutoff": FROZEN_TIER_CUTOFF,
            "issuers_with_current_expansion_activity": expansion_issuers,
            "ratio_lower_bound_denominator": _ratio(expansion_issuers, upper),
            "ratio_upper_bound_denominator": _ratio(expansion_issuers, lower),
            "ratified_rows_excluded_from_acceptance": expansion_rows_excluded,
        },
    }


# ---------------------------------------------------------------------------
# Graph-side ledger + gates
# ---------------------------------------------------------------------------

def _graph_side_ledger(graph: _GraphContext, master_security_ids: set[str]) -> dict:
    markets = sorted({m for m in graph.node_market.values() if m}
                     | {str(row.get("market_scope") or "") for row in graph.identity_rows
                        if _s(row.get("market_scope"))})
    ledger: dict[str, dict[str, int]] = {}
    for market in markets:
        cells: dict[str, int] = {}
        for row in graph.identity_rows:
            if str(row.get("market_scope") or "") != market:
                continue
            state = str(row.get("resolution_state") or "")
            if state not in LEDGER_STATE_MAP:
                raise CoverageProofRefusal(
                    f"LEDGER_STATE_OUT_OF_ENUM: node {row.get('node_id')!r} carries "
                    f"resolution_state {state!r}; this report's state vocabulary is closed")
            node_id = str(row["node_id"])
            if state == "RESOLVED":
                state = ("RESOLVED" if _s(row.get("security_id")) in master_security_ids
                         else "GRAPH_ONLY")
            status = graph.node_status.get(node_id, "no_node")
            key = f"{state}/{status}"
            cells[key] = cells.get(key, 0) + 1
        ledger[market] = dict(sorted(cells.items()))
    return ledger


def _alias_groups(graph: _GraphContext) -> list[dict]:
    groups = []
    for security_id, node_ids in sorted(graph.by_security.items()):
        if len(node_ids) > 1:
            groups.append({"security_id": security_id, "node_ids": sorted(node_ids)})
    return sorted(groups, key=lambda g: g["security_id"])


def _activity_gate(market: str, activity: dict) -> dict:
    num = activity["numerator_issuers"]
    lower, upper = activity["denominator"]["issuer_count_bounds"]
    if upper == 0:
        verdict = "NOT_MEASURABLE"
    elif num * 100 < ACTIVITY_GATE_PCT * upper:
        verdict = "FAIL"
    elif num * 100 >= ACTIVITY_GATE_PCT * lower:
        verdict = "PASS"
    else:
        # The honest middle: even the best-case denominator cannot reach 95%.
        verdict = "NOT_MEASURABLE"
    return {"dimension": "Principal activity coverage",
            "threshold": THRESHOLDS["Principal activity coverage"],
            "measured": {"market": market, "numerator_issuers": num,
                         "denominator_lower_bound": lower, "denominator_upper_bound": upper,
                         "ratio_lower_bound_denominator":
                             activity["ratio_lower_bound_denominator"]["ratio"],
                         "ratio_upper_bound_denominator":
                             activity["ratio_upper_bound_denominator"]["ratio"]},
            "verdict": verdict}


def _denominator_gate(market_views: dict) -> dict:
    measured_markets = {}
    ok = True
    for market in CORE_MARKETS:
        view = market_views[market]
        eligibility_sum = sum(view["securities_by_eligibility"].values())
        identity_sum = sum(view["securities_by_identity_status"].values())
        excluded = len(view["exclusions"])
        eligible_count = view["securities_by_eligibility"].get(ELIGIBLE, 0)
        market_ok = (eligibility_sum == view["securities_total"]
                     and identity_sum == eligible_count
                     and excluded + eligible_count == view["securities_total"])
        ok = ok and market_ok
        measured_markets[market] = {
            "securities_total": view["securities_total"],
            "eligibility_counts_sum": eligibility_sum,
            "eligible_securities": eligible_count,
            "identity_status_counts_sum": identity_sum,
            "exclusions_listed": excluded,
            "issuers_resolved_distinct_eligible":
                view["issuers_resolved_distinct_eligible"],
            "issuer_and_security_counts_separate": True,
        }
    return {"dimension": "Denominator honesty", "threshold": THRESHOLDS["Denominator honesty"],
            "measured": {"core_markets": measured_markets,
                         "issuer_security_counts_separate_keys": True},
            "verdict": "PASS" if ok else "FAIL"}


def _taxonomy_gate(taxonomy: dict) -> dict:
    missing_scope = sum(1 for micro in taxonomy["micros"] if not micro["scope_version"])
    reviewed = all(micro["owner_reviewed"] for micro in taxonomy["micros"])
    ok = (taxonomy["observed_micro_count"] == DECLARED_MICRO_COUNT
          and missing_scope == 0 and reviewed)
    return {"dimension": "Taxonomy coverage", "threshold": THRESHOLDS["Taxonomy coverage"],
            "measured": {"observed_micro_count": taxonomy["observed_micro_count"],
                         "declared_micro_count": DECLARED_MICRO_COUNT,
                         "discrepancy": taxonomy["discrepancy"],
                         "micros_without_scope_version": missing_scope,
                         "owner_reviewed": reviewed,
                         "tier_cutoff": FROZEN_TIER_CUTOFF,
                         "expansion_micro_count": taxonomy["expansion_micro_count"],
                         "owner_review_gap": taxonomy["owner_review"]["gap"]},
            "verdict": "PASS" if ok else "FAIL"}


def _gates(market_views: dict, activity_by_market: dict, taxonomy: dict) -> list[dict]:
    gates = [_denominator_gate(market_views)]
    for market in CORE_MARKETS:
        gates.append(_activity_gate(market, activity_by_market[market]))
    gates.append(_taxonomy_gate(taxonomy))
    for dimension in LANE_DIMENSIONS:
        gates.append({"dimension": dimension, "threshold": THRESHOLDS[dimension],
                      "measured": None, "verdict": "NOT_IN_THIS_LANE"})
    return gates


# ---------------------------------------------------------------------------
# Taxonomy view
# ---------------------------------------------------------------------------

def _micro_tier(entry: dict) -> str:
    """The acceptance tier of one crosswalk micro (fail-closed on purpose).

    DISPLAY_EXPANSION only for a well-formed ``YYYY-MM-DD`` ``asserted_on`` at or
    after FROZEN_TIER_CUTOFF; everything else — earlier date, missing, empty,
    malformed — stays FROZEN_ACCEPTANCE, so a row can never leave the acceptance
    gate by omitting or garbling its date. YAML may parse an unquoted date into a
    ``datetime.date``; such values are normalised through ``.isoformat()`` first.
    """
    value = entry.get("asserted_on")
    if hasattr(value, "isoformat") and not isinstance(value, str):
        value = value.isoformat()
    if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
        return FROZEN_TIER
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        return FROZEN_TIER
    return EXPANSION_TIER if parsed.isoformat() >= FROZEN_TIER_CUTOFF else FROZEN_TIER


def _taxonomy(hierarchy_path: Path, research_paths: list[Path], activity: dict,
              graph: _GraphContext, repo_root: Path) -> dict:
    hierarchy = _hierarchy(hierarchy_path)
    known_ids = set(hierarchy["micros"])
    research_counts: dict[str, dict[str, int]] = {}
    unknown_ids: set[str] = set()
    for path in research_paths:
        counts, unknown = _scan_research_record(path, known_ids)
        basename = path.name
        for micro_id, count in counts.items():
            research_counts.setdefault(micro_id, {})[basename] = \
                research_counts.get(micro_id, {}).get(basename, 0) + count
        unknown_ids.update(unknown)
    admitted_by_theme: dict[str, int] = {}
    proposed_by_theme: dict[str, int] = {}
    rejected_by_theme: dict[str, int] = {}
    for row in activity["ratified"]:
        theme_id = _row_target(row)
        current = _current_scope(repo_root, theme_id)
        if current is not None and current == _row_definition_hash(row):
            admitted_by_theme[theme_id] = admitted_by_theme.get(theme_id, 0) + 1
    for row in activity["kept"]:
        theme_id = _row_target(row)
        if not theme_id:
            continue
        if row.get("status") == "PROPOSED":
            proposed_by_theme[theme_id] = proposed_by_theme.get(theme_id, 0) + 1
        elif row.get("status") == "REJECTED":
            rejected_by_theme[theme_id] = rejected_by_theme.get(theme_id, 0) + 1
    expressing: dict[str, set[str]] = {}
    for row in graph.edges_latest_rows:
        if str(row.get("type")) == "EXPRESSES" and str(row.get("dst")).startswith("theme:"):
            expressing.setdefault(str(row["dst"]), set()).add(str(row.get("src")))
    vendor_companies: dict[str, set[str]] = {}
    for row in current_member_of_edges(graph):
        dst = str(row.get("dst"))
        for theme_id in sorted(expressing.get(dst, ())):
            vendor_companies.setdefault(theme_id, set()).add(str(row.get("src")))
    micros: list[dict] = []
    expansion_micros: list[dict] = []
    for micro_id in sorted(hierarchy["micros"]):
        entry = hierarchy["micros"][micro_id]
        admitted = admitted_by_theme.get(micro_id, 0)
        proposed = proposed_by_theme.get(micro_id, 0)
        rejected = rejected_by_theme.get(micro_id, 0)
        research = research_counts.get(micro_id, {})
        routes = len(expressing.get(micro_id, ()))
        if admitted > 0:
            disposition = "NATIVE_POPULATED"
        elif proposed > 0:
            disposition = "PROPOSED_ONLY"
        elif sum(research.values()) > 0:
            disposition = "RESEARCH_UNADMITTED"
        elif routes > 0:
            disposition = "VENDOR_ONLY"
        else:
            disposition = "EMPTY"
        record = {
            "id": micro_id,
            "name_en": _s(entry.get("name_en")),
            "scope_version": _entry_scope_version(entry),
            "asserted_on": _s(entry.get("asserted_on")),
            "parent_paths": _parent_paths(micro_id, hierarchy),
            "route_kinds": _route_kinds(micro_id, hierarchy),
            "counts": {"admitted": admitted, "proposed": proposed, "rejected": rejected,
                       "research_records": dict(sorted(research.items())),
                       "vendor_expressing_routes": routes,
                       "vendor_member_companies": len(vendor_companies.get(micro_id, ()))},
            "disposition": disposition,
            "owner_reviewed": False,
            "tier": _micro_tier(entry),
        }
        (micros if record["tier"] == FROZEN_TIER else expansion_micros).append(record)
    observed = len(micros)  # the frozen acceptance tier is the only denominator
    return {
        "observed_micro_count": observed,
        "declared_micro_count": DECLARED_MICRO_COUNT,
        "discrepancy": (None if observed == DECLARED_MICRO_COUNT
                        else f"observed {observed} != declared {DECLARED_MICRO_COUNT}"),
        "micros": micros,
        "unknown_research_micro_ids": sorted(unknown_ids),
        "tier_cutoff": FROZEN_TIER_CUTOFF,
        "total_micro_count": len(micros) + len(expansion_micros),
        "expansion_micro_count": len(expansion_micros),
        "expansion_admitted_total": sum(record["counts"]["admitted"]
                                        for record in expansion_micros),
        "frozen_micro_ids_sha256": hashlib.sha256(
            "\n".join(record["id"] for record in micros).encode("utf-8")).hexdigest(),
        "owner_review": {"source": None, "gap": "NO_OWNER_DISPOSITION_CONTRACT"},
        "expansion_micros": expansion_micros,
    }


# ---------------------------------------------------------------------------
# Remainders
# ---------------------------------------------------------------------------

def _remainders(market_views: dict, activity_by_market: dict, wider_views: dict,
                graph_ledger: dict) -> list[dict]:
    rows: list[dict] = []

    def add(market: str, reason: str, count: int) -> None:
        if count <= 0:
            return
        owner, next_step = _reason_owner(reason, market)
        rows.append({"market": market, "reason": reason, "count": int(count),
                     "owner": owner, "next_step": next_step})

    for market in CORE_MARKETS:
        view = market_views[market]
        for status, count in sorted(view["securities_by_identity_status"].items()):
            if status != ID_QUALIFIED:
                add(market, status, count)
        for eligibility, count in sorted(view["securities_by_eligibility"].items()):
            if eligibility != ELIGIBLE:
                add(market, eligibility, count)
        for reason, count in sorted(activity_by_market[market]["remainder_by_reason"].items()):
            add(market, reason, count)
    for market in WIDER_MARKETS:
        for state, count in sorted(wider_views[market]["by_resolution_state"].items()):
            if state in LEDGER_REMAINDER_STATES:
                add(market, state, count)
    add("cn", REASON_CN_LISTED_COUNTS, market_views["cn"]["securities_total"])
    return sorted(rows, key=lambda r: (r["market"], r["reason"]))


# ---------------------------------------------------------------------------
# Build + render
# ---------------------------------------------------------------------------

def _assert_no_floats(value, where: str = "output") -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, float):
        raise CoverageProofRefusal(f"FLOAT_IN_OUTPUT: {where} carries a float; "
                                   f"ratios are integer pairs plus a 4dp string")
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_no_floats(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_no_floats(item, f"{where}[{index}]")


def _hash_without(obj: dict, drop: tuple[str, ...]) -> str:
    trimmed = {key: value for key, value in obj.items() if key not in drop}
    return hashlib.sha256(_canonical(trimmed).encode("utf-8")).hexdigest()


def _cell(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value.replace("|", "\\|")
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def render_markdown(report: dict, manifest: dict) -> str:
    """Rendered ONLY from the two output dicts — no extra computation happens here."""
    lines = ["# GMI theme-graph step-7 coverage proof", ""]
    lines.append(f"report_version: `{report['report_version']}`  ")
    lines.append(f"manifest_version: `{report['manifest_version']}`  ")
    lines.append(f"source_commit: `{_cell(report['source_commit'])}`")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append("| role | path | git_blob_sha1 |")
    lines.append("| --- | --- | --- |")
    for record in report["inputs"]:
        lines.append(f"| {_cell(record['role'])} | {_cell(record['path'])} "
                     f"| {_cell(record['git_blob_sha1'])} |")
    lines.append("")
    lines.append("## Core denominators (US and CN are separate; never summed)")
    lines.append("")
    lines.append("| market | securities | issuers resolved | issuers resolved (eligible) "
                 "| eligible securities | unresolved-issuer securities |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for market in CORE_MARKETS:
        view = manifest["core_markets"][market]
        unresolved = sum(view["eligible_securities_without_resolved_issuer"].values())
        lines.append(f"| {market} | {view['securities_total']} "
                     f"| {view['issuers_resolved_distinct']} "
                     f"| {view['issuers_resolved_distinct_eligible']} "
                     f"| {view['securities_by_eligibility'].get(ELIGIBLE, 0)} | {unresolved} |")
    lines.append("")
    lines.append("## Gates")
    lines.append("")
    lines.append("| Dimension | Threshold (verbatim) | Measured | Verdict |")
    lines.append("| --- | --- | --- | --- |")
    for gate in report["gates"]:
        lines.append(f"| {_cell(gate['dimension'])} | {_cell(gate['threshold'])} "
                     f"| {_cell(gate['measured'])} | {_cell(gate['verdict'])} |")
    lines.append("")
    lines.append("## Expansion-tier coverage (display tier, not acceptance)")
    lines.append("")
    lines.append("| market | issuers with current expansion-tier activity "
                 "| ratio (lower-bound denominator) "
                 "| ratified rows excluded from the acceptance numerator |")
    lines.append("| --- | --- | --- | --- |")
    for market in CORE_MARKETS:
        expansion = report["activity"][market]["expansion_tier"]
        lines.append(f"| {_cell(market)} "
                     f"| {_cell(expansion['issuers_with_current_expansion_activity'])} "
                     f"| {_cell(expansion['ratio_lower_bound_denominator']['ratio'])} "
                     f"| {_cell(expansion['ratified_rows_excluded_from_acceptance'])} |")
    lines.append("")
    lines.append("## Remainders (every one has a named owner; no OTHER)")
    lines.append("")
    lines.append("| market | reason | count | owner | next step |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in report["remainders"]:
        lines.append(f"| {_cell(row['market'])} | {_cell(row['reason'])} | {row['count']} "
                     f"| {_cell(row['owner'])} | {_cell(row['next_step'])} |")
    lines.append("")
    lines.append("## Taxonomy")
    lines.append("")
    taxonomy = report["taxonomy"]
    if taxonomy["discrepancy"] is not None:
        lines.append(f"Micro count discrepancy (reported, never forced): "
                     f"{taxonomy['discrepancy']}")
    if taxonomy["unknown_research_micro_ids"]:
        lines.append(f"Research micro ids outside the hierarchy: "
                     f"{', '.join(taxonomy['unknown_research_micro_ids'])}")
    lines.append("")
    lines.append("| id | scope_version | disposition | admitted | proposed | research "
                 "| vendor routes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for micro in taxonomy["micros"]:
        counts = micro["counts"]
        lines.append(f"| {_cell(micro['id'])} | {_cell(micro['scope_version'][:12])} "
                     f"| {_cell(micro['disposition'])} | {counts['admitted']} "
                     f"| {counts['proposed']} "
                     f"| {sum(counts['research_records'].values())} "
                     f"| {counts['vendor_expressing_routes']} |")
    lines.append(f"Frozen acceptance tier: {taxonomy['observed_micro_count']} micros "
                 f"(asserted_on before {taxonomy['tier_cutoff']}); display expansion: "
                 f"{taxonomy['expansion_micro_count']} micros (not an acceptance "
                 f"denominator).")
    lines.append(f"Owner review: {taxonomy['owner_review']['gap']} "
                 f"(owner_reviewed is false for every micro).")
    lines.append("")
    if taxonomy["expansion_micro_count"] > 0:
        lines.append("### Display-expansion micros (not an acceptance denominator)")
        lines.append("")
        lines.append("| id | scope_version | disposition | admitted | proposed | research "
                     "| vendor routes |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for micro in taxonomy["expansion_micros"]:
            counts = micro["counts"]
            lines.append(f"| {_cell(micro['id'])} | {_cell(micro['scope_version'][:12])} "
                         f"| {_cell(micro['disposition'])} | {counts['admitted']} "
                         f"| {counts['proposed']} "
                         f"| {sum(counts['research_records'].values())} "
                         f"| {counts['vendor_expressing_routes']} |")
        lines.append("")
    lines.append("## Wider-market ledger (not a denominator)")
    lines.append("")
    lines.append("| market | graph company nodes | by resolution state | master securities "
                 "| status |")
    lines.append("| --- | --- | --- | --- | --- |")
    for market in WIDER_MARKETS:
        view = manifest["wider_market_ledger"][market]
        lines.append(f"| {market} | {view['graph_company_nodes']} "
                     f"| {_cell(view['by_resolution_state'])} | {view['master_securities']} "
                     f"| {_cell(view['status'])} |")
    lines.append("")
    lines.append("## Graph-side ledger")
    lines.append("")
    lines.append("| market | state/lifecycle_status | count |")
    lines.append("| --- | --- | --- |")
    for market, cells in sorted(report["graph_side_ledger"].items()):
        for key, count in sorted(cells.items()):
            lines.append(f"| {market} | {_cell(key)} | {count} |")
    lines.append("")
    lines.append("FAIL stays FAIL: this report never rounds a failing gate into a pass.")
    return "\n".join(lines) + "\n"


def _load_inputs(args) -> dict:
    repo_root = Path(args.repo_root).resolve()
    inputs: list[dict] = []

    def record(role: str, path: Path) -> Path:
        inputs.append(_input_record(role, path, repo_root))
        return path

    master_path = record("security_master", Path(args.master))
    receipt_path = record("security_master_receipt", Path(args.receipt))
    directory_path = record("symbol_directory", Path(args.symbol_directory))
    manifest_path = record("symbol_directory_manifest", Path(args.symbol_directory_manifest))
    hierarchy_path = record("hierarchy", Path(args.hierarchy))
    research_paths = [record("research_record", Path(p)) for p in (args.research_records or [])]
    proposal_paths = [record("activity_proposals", Path(p))
                      for p in (args.activity_proposals or [])]

    for role, path in (("security_master", master_path), ("security_master_receipt", receipt_path),
                       ("symbol_directory", directory_path),
                       ("symbol_directory_manifest", manifest_path),
                       ("hierarchy", hierarchy_path)):
        if not path.exists():
            raise CoverageProofRefusal(f"MISSING_INPUT: {role} {path}")
    try:
        master = pd.read_parquet(master_path)
    except Exception as exc:  # noqa: BLE001
        raise CoverageProofRefusal(
            f"UNREADABLE_INPUT: security_master: {type(exc).__name__}") from exc
    receipt = _read_json(receipt_path, "master receipt")
    try:
        directory = pd.read_parquet(directory_path)
    except Exception as exc:  # noqa: BLE001
        raise CoverageProofRefusal(
            f"UNREADABLE_INPUT: symbol_directory: {type(exc).__name__}") from exc
    directory_manifest = _read_json(manifest_path, "symbol directory manifest")
    return {
        "repo_root": repo_root,
        "inputs": sorted(inputs, key=lambda r: (r["role"], r["path"])),
        "master": master,
        "receipt": receipt,
        "directory": directory,
        "directory_manifest": directory_manifest,
        "directory_path": directory_path,
        "hierarchy_path": hierarchy_path,
        "research_paths": research_paths,
        "proposal_paths": proposal_paths,
    }


def build(args) -> tuple[dict, dict]:
    loaded = _load_inputs(args)
    repo_root = loaded["repo_root"]
    store_dir = Path(args.store)
    store_view = read_store(store_dir)
    for role, path in (("store_nodes", store_view["files"]["nodes"]),
                       ("store_edges", store_view["files"]["edges"]),
                       ("store_identity_resolution", store_view["files"]["identity_resolution"]),
                       ("store_node_lifecycle", store_view["files"]["node_lifecycle"]),
                       ("store_meta", store_view["files"]["meta"])):
        if Path(path).exists():
            loaded["inputs"].append(_input_record(role, Path(path), repo_root))
    if store_view["files"]["probation_activity_proposals"].exists():
        loaded["inputs"].append(_input_record(
            "store_probation_activity_proposals",
            store_view["files"]["probation_activity_proposals"], repo_root))
    if store_view["files"]["probation_proposals"].exists():
        loaded["inputs"].append(_input_record(
            "store_probation_proposals", store_view["files"]["probation_proposals"], repo_root))
    loaded["inputs"].sort(key=lambda r: (r["role"], r["path"]))

    nodes_current = store_view["nodes_current"]
    identity_latest = store_view["identity_latest"]
    edges_latest = store_view["edges_latest"]
    graph = _GraphContext(nodes_current, identity_latest, edges_latest)

    directory_flags: dict[str, dict] = {}
    if not loaded["directory"].empty:
        for row in loaded["directory"].to_dict("records"):
            directory_flags[_s(row.get("symbol")).strip()] = {
                "etf": _truthy(row.get("etf")),
                "test_issue": _truthy(row.get("test_issue")),
                "is_preferred": _truthy(row.get("is_preferred")),
            }

    core, wider = classify_master(loaded["master"], graph, directory_flags)
    market_views = {market: _market_view(market, core[market], loaded["directory"],
                                         loaded["directory_path"], loaded["directory_manifest"])
                    for market in CORE_MARKETS}
    wider_views = {market: _wider_market_view(market, wider[market], graph)
                   for market in WIDER_MARKETS}

    eligible_by_security: dict[str, dict] = {}
    for market in CORE_MARKETS:
        for entry in core[market]:
            if entry["eligibility"] == ELIGIBLE:
                row = entry["row"]
                eligible_by_security[_s(row.get("security_id"))] = {
                    "issuer_id": _s(row.get("issuer_id")), "market": market}

    # Vendor membership is computed BEFORE the activity views: it feeds the
    # VENDOR_MEMBERSHIP_ONLY remainder and never the numerator.
    graph.vendor_eligible_securities = {}
    for row in current_member_of_edges(graph):
        src = str(row.get("src"))
        market = graph.node_market.get(src)
        security_id = graph.security_by_node.get(src)
        if market and security_id in eligible_by_security:
            graph.vendor_eligible_securities.setdefault(market, set()).add(security_id)

    proposal_rows: list[dict] = []
    for path in loaded["proposal_paths"]:
        proposal_rows.extend(probation.read_proposals(path, strict=True))

    activity_rows = _activity_market_rows(store_view["queue"], proposal_rows)
    # The acceptance tier of each micro per the same hierarchy _taxonomy reads: a
    # ratified row targeting a display-expansion micro never enters the numerator.
    tier_by_micro = {micro_id: _micro_tier(entry)
                     for micro_id, entry
                     in _hierarchy(loaded["hierarchy_path"])["micros"].items()}
    activity_by_market = {market: _activity_view(market, core[market], activity_rows, graph,
                                                 repo_root, tier_by_micro=tier_by_micro)
                          for market in CORE_MARKETS}

    vendor_by_market = {market: _vendor_view(market, graph, eligible_by_security)
                        for market in CORE_MARKETS}
    taxonomy = _taxonomy(loaded["hierarchy_path"], loaded["research_paths"], activity_rows,
                         graph, repo_root)
    master_security_ids = {_s(row.get("security_id"))
                           for row in loaded["master"].to_dict("records")}
    graph_ledger = _graph_side_ledger(graph, master_security_ids)
    gates = _gates(market_views, activity_by_market, taxonomy)
    remainders = _remainders(market_views, activity_by_market, wider_views, graph_ledger)

    identity_coverage = {}
    for market in CORE_MARKETS:
        view = market_views[market]
        eligible = view["securities_by_eligibility"].get(ELIGIBLE, 0)
        qualified = view["securities_by_identity_status"].get(ID_QUALIFIED, 0)
        identity_coverage[market] = {
            "eligible_securities": eligible,
            "by_identity_status": dict(view["securities_by_identity_status"]),
            "qualified_securities": qualified,
            "ratio_qualified_over_eligible": _ratio(qualified, eligible),
        }

    receipt = loaded["receipt"] if isinstance(loaded["receipt"], dict) else {}
    meta = store_view["meta"]
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "source_commit": args.source_commit,
        "inputs": loaded["inputs"],
        "store_meta": {"computed_at": meta.get("computed_at"),
                       "belief_time": meta.get("belief_time")},
        "master_receipt": {key: receipt.get(key) for key in
                           ("generated_at", "symbol_directory_snapshot", "code_version",
                            "cik_map_snapshot")},
        "provenance_only_counts": {
            "note": "provenance only — never a denominator",
            "master_rows": int(len(loaded["master"])),
            "graph_company_nodes": sum(1 for kind in graph.kind.values() if kind == "company"),
        },
        "core_markets": {market: market_views[market] for market in CORE_MARKETS},
        "wider_market_ledger": {market: wider_views[market] for market in WIDER_MARKETS},
    }
    manifest["manifest_version"] = _hash_without(manifest, ("manifest_version", "source_commit"))

    report = {
        "schema": REPORT_SCHEMA,
        "manifest_version": manifest["manifest_version"],
        "source_commit": args.source_commit,
        "inputs": loaded["inputs"],
        "store_meta": manifest["store_meta"],
        "identity_coverage": identity_coverage,
        "graph_side_ledger": graph_ledger,
        "alias_groups": _alias_groups(graph),
        "activity": activity_by_market,
        "vendor_membership_not_principal_activity": vendor_by_market,
        "taxonomy": taxonomy,
        "gates": gates,
        "remainders": remainders,
        "owners": {f"{reason}|{market}": {"owner": owner, "next_step": step}
                   for (reason, market), (owner, step) in sorted(REASON_OWNER.items())},
    }
    report["report_version"] = _hash_without(report, ("report_version", "source_commit"))
    return manifest, report


def _write_outputs(out_dir: Path, manifest: dict, report: dict) -> None:
    _assert_no_floats(manifest, "UNIVERSE_MANIFEST.json")
    _assert_no_floats(report, "coverage_report.json")
    documents = {
        "UNIVERSE_MANIFEST.json": json.dumps(manifest, indent=1, sort_keys=True,
                                             ensure_ascii=False) + "\n",
        "coverage_report.json": json.dumps(report, indent=1, sort_keys=True,
                                           ensure_ascii=False) + "\n",
        "COVERAGE_REPORT.md": render_markdown(report, manifest),
    }
    for name, text in documents.items():
        # No basket:/ltheme: id may appear anywhere in any output byte.
        if "basket:" in text or "ltheme:" in text:
            raise CoverageProofRefusal(
                f"FORBIDDEN_LABEL_IN_OUTPUT: {name} carries a basket:/ltheme: id; "
                f"refusing to write")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in documents.items():
        (out_dir / name).write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--master", default="data/reference/security_master.parquet")
    ap.add_argument("--receipt", default="data/reference/_receipt.json")
    ap.add_argument("--symbol-directory",
                    default="data/symbol_directory/snapshots/latest.parquet")
    ap.add_argument("--symbol-directory-manifest",
                    default="data/symbol_directory/manifest.json")
    ap.add_argument("--store", default="data/theme_graph")
    ap.add_argument("--hierarchy", default="config/theme_crosswalk.yml")
    ap.add_argument("--research-records", action="append", default=None)
    ap.add_argument("--activity-proposals", action="append", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-root", default=str(here.parent))
    ap.add_argument("--source-commit", default=None)
    a = ap.parse_args(argv)

    repo_root = Path(a.repo_root).resolve()
    out_dir = Path(a.out).resolve()
    for guarded in ("data", "site"):
        boundary = (repo_root / guarded).resolve()
        if out_dir == boundary or boundary in out_dir.parents:
            print(f"REFUSED: --out {out_dir} is under {boundary}; the coverage proof "
                  f"never writes under data/ or site/", file=sys.stderr)
            return 2
    try:
        manifest, report = build(a)
        _write_outputs(out_dir, manifest, report)
    except CoverageProofRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"gmi_coverage_proof: wrote 3 files under {out_dir} "
          f"(report_version {report['report_version'][:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
