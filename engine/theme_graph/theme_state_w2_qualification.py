"""Fixed W2 US-young-narrow trading_beta.v0 H1 research qualification.

This composes the incumbent probe, never ThemeState eligibility. It qualifies only
H1 computability on the fixed owner pilot/history, not stability, distinctness,
canonical membership, historical availability, rights or publication. Native file
capture must precede ThemeState capture; no current pointer/store is written.
"""
from __future__ import annotations

import base64
import copy
import datetime as dt
import hashlib
import io
import json
import re
import types
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from engine.neuralweb import theme_state_adapter as adapter
from engine.theme_graph import theme_state
from scripts import probe_theme_exposure_axes as owner

SCHEMA = "gmi.w2_beta_h1_qualification/v1"
SLOT = "us_young_narrow"
BASKET = "basket:baskets:nuclear_power"
POLICY_PATH = "research/theme_graph/W2_EXPOSURE_AXES_PREREG.md"
PROBE_PATH = "scripts/probe_theme_exposure_axes.py"
POLICY_SHA256 = "fa5237922bcc112e6c97e61593f634a3db959f69dbee64bbc66f8ac6311b2eb3"
PROBE_SHA256 = "09f97d72fefe1d2c9d9fec400d79d8637ef8ac010ffe25f0355e043cd238e744"
# Exact retained producer revision whose _iso_now/receipt path declares naive
# UTC seconds. Unknown revisions do not inherit that legacy interpretation.
NAIVE_UTC_MASTER_REVISION = "cdbcd143dcfa419ab0637bc11dd4c80368143e2e"
BOUND_PATHS = {
    "graph/nodes.parquet": "data/theme_graph/nodes.parquet",
    "graph/edges.parquet": "data/theme_graph/edges.parquet",
    "graph/_meta.json": "data/theme_graph/_meta.json",
    **{"identity/" + name: "data/reference/" + name for name in
       ("security_master.parquet", "vendor_aliases.parquet", "_receipt.json")},
}
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9._^-]*\Z")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _native_master_clock(row, receipt):
    """Decode only the bound master producer's documented naive UTC convention.

    build_security_master._iso_now intentionally strips UTC offset for its native
    parquet datetime64[ns] representation; the receipt reuses that same value.
    Preserve the raw stamp and interpretation. This is generation time, never
    historical publication/arrival or proof of a historical alias.
    """
    raw = row.get("master_generated_at")
    if (type(receipt) is not dict or raw != receipt.get("generated_at")
            or row.get("master_code_version") != receipt.get("code_version")):
        return None
    try:
        theme_state._clock(raw)
        return {"raw": raw, "comparison_clock": raw, "interpretation": "NATIVE_EXPLICIT_CLOCK"}
    except (ValueError, TypeError):
        pass
    if (type(raw) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", raw)
            or receipt.get("producer") != "scripts/build_security_master.py"
            or type(receipt.get("code_version")) is not str
            or not re.fullmatch(r"[a-f0-9]{40}", receipt["code_version"])
            or receipt["code_version"] != NAIVE_UTC_MASTER_REVISION
            or row.get("master_code_version") != receipt["code_version"]
            or receipt.get("generated_at") != raw
            or type(receipt.get("dataset_ids")) is not list
            or any(type(dataset) is not str for dataset in receipt["dataset_ids"])
            or not {"reference.security_master", "reference.vendor_aliases"} <= set(receipt["dataset_ids"])):
        return None
    try:
        interpreted = dt.datetime.fromisoformat(raw).replace(tzinfo=dt.timezone.utc).isoformat()
    except ValueError:
        return None
    return {"raw": raw, "comparison_clock": interpreted,
        "interpretation": "BOUND_NATIVE_MASTER_PRODUCER_NAIVE_UTC_SECONDS",
        "producer": receipt["producer"], "code_version": receipt["code_version"],
        "semantic_role": "GENERATION_TIME_ONLY_NOT_HISTORICAL_AVAILABILITY"}


class _FrozenPath:
    def __init__(self, sources, path=""):
        self.sources, self.path = sources, path

    def __truediv__(self, part):
        return _FrozenPath(self.sources, str(Path(self.path) / part))

    def exists(self):
        return self.path in self.sources and self.sources[self.path] is not None

    def relative_to(self, root):
        return Path(self.path).relative_to(root.path or ".")


class _FrozenPandas:
    def __getattr__(self, name):
        return getattr(pd, name)

    def read_parquet(self, path):
        return pd.read_parquet(io.BytesIO(path.sources[path.path]))


def _native(function, sources):
    # Execute the incumbent owner functions unchanged against the captured bytes.
    namespace = dict(vars(owner))
    namespace.update(ROOT=_FrozenPath(sources), DATA=_FrozenPath(sources, "data"), pd=_FrozenPandas())
    return types.FunctionType(function.__code__, namespace, function.__name__, function.__defaults__)


def _policy():
    root = Path(owner.__file__).resolve().parents[1]
    if (_sha((root / POLICY_PATH).read_bytes()) != POLICY_SHA256
            or _sha((root / PROBE_PATH).read_bytes()) != PROBE_SHA256):
        raise ValueError("W2 frozen owner revision differs; qualify a new policy explicitly")
    if owner.SLOTS[SLOT]["baskets"] != [BASKET] or owner.SLOTS[SLOT]["market"] != "us":
        raise ValueError("fixed W2 pilot scope changed")


@dataclass(frozen=True)
class W2BetaInputs:
    payload_json: str
    sha256: str

    def snapshot(self):
        if _sha(self.payload_json.encode()) != self.sha256:
            raise ValueError("W2 capture digest mismatch")
        value = json.loads(self.payload_json)
        if set(value) != {"slot", "observed_at", "sources"} or value["slot"] != SLOT:
            raise ValueError("closed fixed-pilot native capture required")
        adapter._clock(value["observed_at"], precise=True)
        for path, source in value["sources"].items():
            if set(source) != {"sha256", "bytes_b64"}:
                raise ValueError("closed native source receipt required")
            raw = None if source["bytes_b64"] is None else base64.b64decode(source["bytes_b64"], validate=True)
            if source["sha256"] != (None if raw is None else _sha(raw)):
                raise ValueError("W2 source digest mismatch")
        return value


def capture_w2_beta_inputs(root: Path) -> W2BetaInputs:
    """Read the fixed native pilot, before capture_owner_bundle; no compute/write.

    Reads only graph/identity metadata and native US price artifacts selected by
    the incumbent W2 symbol/slot rules. The clock is actual completed observation,
    never a historical availability claim. Intended for an explicitly admitted
    research invocation; this function is not wired into the nightly writer.
    """
    _policy()
    root = Path(root).resolve()
    paths = set(BOUND_PATHS.values())

    def read(path):
        p = root / path
        return p.read_bytes() if p.exists() else None

    sources = {path: read(path) for path in paths}
    if any(sources[BOUND_PATHS[key]] is None for key in ("graph/nodes.parquet", "graph/edges.parquet")):
        raise ValueError("native W2 graph input unavailable")
    lb = _native(owner.load_membership, sources)(_FrozenPath(sources, BOUND_PATHS["graph/edges.parquet"]))
    symbols = _native(owner.node_symbols, sources)(_FrozenPath(sources, BOUND_PATHS["graph/nodes.parquet"]))
    members = owner.all_slot_members(lb, [BASKET])["src"].unique()
    for node in members:
        symbol = symbols.get(node)
        if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
            raise ValueError("native pilot symbol has no bounded US owner path")
        for directory in ("data/baskets/ohlcv", "data/stocks"):
            path = directory + "/" + symbol + ".parquet"
            sources[path] = read(path)
    for path, raw in sources.items():
        if read(path) != raw:
            raise ValueError("native W2 source changed during capture")
    observed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    payload = {"slot": SLOT, "observed_at": observed_at, "sources": {path: {
        "sha256": None if raw is None else _sha(raw),
        "bytes_b64": None if raw is None else base64.b64encode(raw).decode(),
    } for path, raw in sorted(sources.items())}}
    text = adapter._json(payload)
    return W2BetaInputs(text, _sha(text.encode()))


def qualify_w2_beta_h1(bundle: adapter.OwnerBundle, inputs: W2BetaInputs) -> dict:
    """Replay frozen native W2 H1 for this exact graph/bundle; research only.

    Equal-weight member-company construction is inherited. Multiple nodes for one
    issuer or security refuse: W2 defines no share-class aggregation/deduplication
    rule. Missing prices stay in the denominator. No concentration cutoff exists
    in H1, so computability does not claim concentration/measurement acceptance.
    """
    _policy()
    if not isinstance(bundle, adapter.OwnerBundle) or not isinstance(inputs, W2BetaInputs):
        raise TypeError("native captured input capabilities required")
    state, capture = bundle.snapshot(), inputs.snapshot()
    result = {"schema": SCHEMA, "slot": SLOT, "construction": owner.BETA_ID,
        "subject": {"node_id": BASKET, "grain": "native_owner_basket_pilot",
                    "theme_context": owner.SLOTS[SLOT]["theme"], "canonical_membership": "NOT_ASSERTED"},
        "criterion": "W2_H1_COMPUTABILITY_ONLY", "status": "UNAVAILABLE", "reason_codes": [],
        "binding": {"graph_capture_id": state["graph_capture_id"],
                    "native_graph_generation_id": state["native_graph_generation_id"],
                    "bundle_sha256": bundle.bundle_sha256,
                    "input_sha256": inputs.sha256, "query": copy.deepcopy(state["query"])},
        "policy": {"path": POLICY_PATH, "sha256": POLICY_SHA256, "probe_sha256": PROBE_SHA256},
        "observed_at": capture["observed_at"], "coverage": None, "periods": [],
        "owner_omitted_months": [],
        "population": None, "window": {"sessions": owner.BETA_WIN, "minimum_overlap": owner.BETA_MINP,
            "causal_shift_sessions": 1, "history_start": owner.US_HISTORY_START},
        "semantics": {"benchmark": "ex-self equal-weight own-market basket",
            "missingness": "no imputation; absent/noncomputable members remain in denominator",
            "issuer_deduplication": "refuse ambiguous duplicate issuer/security; no new aggregation rule",
            "concentration": "equal weight over members trading each session; no H1 concentration eligibility cutoff",
            "membership": "fixed owner basket latest-belief validity windows, including closed members",
            "historical_availability": "UNPROVEN; current capture is an upper bound only",
            "identity_scope": "current native identities, not historical alias proof",
            "price_identity": "W2 native symbol/file binding only; independent vendor/listing qualification not established",
            "H2_distinctness": "NOT_ASSESSED", "H3_stability": "NOT_ASSESSED",
            "measurement_eligibility": "NOT_ESTABLISHED", "ThemeState_eligibility": "NOT_QUALIFIED",
            "native_generation_qualification": "NOT_ESTABLISHED",
            "source_purpose": "research_internal; no display grant"},
        "authority": copy.deepcopy(theme_state.AUTHORITY)}

    def refuse(reason):
        result["reason_codes"] = [reason]
        return result

    if adapter._clock(capture["observed_at"], precise=True) > adapter._clock(state["query"]["known_at"], precise=True):
        return refuse("NATIVE_W2_CAPTURE_AFTER_CUTOFF")
    if adapter._clock(capture["observed_at"], precise=True) > adapter._clock(state["observed_at"], precise=True):
        return refuse("NATIVE_W2_CAPTURE_AFTER_OWNER_CAPTURE")
    for key, path in BOUND_PATHS.items():
        if (capture["sources"].get(path, {}).get("sha256") is None
                or capture["sources"][path]["sha256"] != state["sources"][key]["sha256"]):
            return refuse("NATIVE_OWNER_GENERATION_MISMATCH")
    sources = {path: None if source["bytes_b64"] is None else base64.b64decode(source["bytes_b64"])
               for path, source in capture["sources"].items()}
    try:
        master_receipt = json.loads(sources[BOUND_PATHS["identity/_receipt.json"]])
    except (ValueError, TypeError):
        return refuse("IDENTITY_KNOWLEDGE_UNPROVEN")
    lb = _native(owner.load_membership, sources)(_FrozenPath(sources, BOUND_PATHS["graph/edges.parquet"]))
    symbols = _native(owner.node_symbols, sources)(_FrozenPath(sources, BOUND_PATHS["graph/nodes.parquet"]))
    members = sorted(set(owner.all_slot_members(lb, [BASKET])["src"]))
    if not members or any(not node.startswith("co:us:") for node in members):
        return refuse("FIXED_US_PILOT_POPULATION_UNAVAILABLE")
    identity_reads = next(iter(state["subjects"].values()))["native_reads"]["identity"]
    ids, issuers, securities, symbols_seen = {}, set(), set(), set()
    for node in members:
        row = identity_reads.get(node, {}).get("value") or {}
        symbol = symbols.get(node)
        if (row.get("resolution_state") != "RESOLVED" or not row.get("issuer_id") or not row.get("security_id")
                or symbol != adapter.identity_resolution._best_effort_symbol(node)):
            return refuse("PILOT_IDENTITY_UNRESOLVED_OR_SYMBOL_MISMATCH")
        if row["issuer_id"] in issuers or row["security_id"] in securities or symbol in symbols_seen:
            return refuse("OWNER_HAS_NO_DUPLICATE_ISSUER_AGGREGATION_RULE")
        clock = _native_master_clock(row, master_receipt)
        try:
            identity_known = clock is not None and theme_state._proven_by(clock["comparison_clock"], state["query"]["known_at"])
        except (ValueError, TypeError):
            # An unknown producer convention remains unproven. Only the exact
            # native decoder above may interpret the documented UTC format.
            identity_known = False
        if not identity_known:
            return refuse("IDENTITY_KNOWLEDGE_UNPROVEN")
        result["binding"]["identity_clock"] = {**clock,
            "receipt_sha256": capture["sources"][BOUND_PATHS["identity/_receipt.json"]]["sha256"]}
        issuers.add(row["issuer_id"]); securities.add(row["security_id"]); symbols_seen.add(symbol)
        ids[node] = {"issuer_id": row["issuer_id"], "security_id": row["security_id"], "symbol": symbol}
    prices, unjoined = _native(owner.load_us_closes, sources)(sorted(symbols_seen), {})
    if prices.empty:
        return refuse("NATIVE_PRICE_PANEL_UNAVAILABLE")
    effective = pd.Timestamp(state["query"]["effective_at"][:10])
    # Native estimates are month-end stamped. This adapter's fixed applicability
    # excludes the incomplete current month; it does not relabel a partial sample.
    month_end = effective.to_period("M")
    if effective.date() != month_end.end_time.date():
        month_end -= 1
    prices = prices.loc[prices.index <= min(effective, month_end.end_time)]
    if prices.empty or str(month_end) < owner.US_HISTORY_START:
        return refuse("NO_COMPLETE_OWNER_MONTH")
    months = owner.month_list(owner.US_HISTORY_START, str(month_end))
    _, periods = owner.compute_beta_cell(SLOT, owner.SLOTS[SLOT], lb, symbols, prices, months)
    graded = [row for row in periods if not row["no_events"]]
    if not graded:
        return refuse("NO_NATIVE_BETA_PERIODS")
    # Exactly the incumbent main() H1 aggregation, without H2/H3/outcome probing.
    n_values = sum(row["n_values"] for row in graded)
    n_members = sum(row["n_members"] for row in graded)
    coverage = owner.coverage_fraction(n_values, n_members)
    result["status"] = "ABSTAIN" if owner.cell_abstains(coverage) else "COMPUTABLE"
    result["reason_codes"] = ["W2_H1_COVERAGE_FLOOR"] if result["status"] == "ABSTAIN" else []
    result["coverage"] = {"computed_member_periods": n_values, "declared_member_periods": n_members,
                          "fraction": coverage, "floor": owner.COVERAGE_FLOOR}
    result["periods"] = periods
    result["owner_omitted_months"] = sorted(set(months) - {row["month"] for row in periods})
    result["population"] = {"basket_id": BASKET, "member_identities": ids, "missing_price_symbols": unjoined,
        "closed_members_included": sorted(set(lb.loc[lb["dst"].eq(BASKET) & lb["valid_to"].notna(), "src"]))}
    return result


MEASUREMENT_KEY = "w2_trading_beta_h1_us_young_narrow"
INTERNAL_SCHEMA = "gmi.theme_state_internal_w2_h1/v1"
INTERNAL_READ_SCHEMA = "gmi.theme_state_internal_w2_h1_read/v1"


def compose_internal_w2_h1(state: dict, *, bundle: adapter.OwnerBundle, inputs: W2BetaInputs) -> dict:
    """Bound internal measurement in the incumbent composition envelope only.

    The existing subject-observation schema requires a canonical/local subject
    and an owner freshness policy. H1 supplies neither for this native basket;
    this envelope deliberately does not insert a subject observation, replace a
    canonical population, or create an eligibility/publication receipt.
    """
    adapter._assert_state_matches_bundle(state, bundle)
    measurement = qualify_w2_beta_h1(bundle, inputs)
    record = {"schema": INTERNAL_SCHEMA, "purpose": "research_internal",
        "public_display_allowed": False,
        "state_ref": {"generation_id": state["generation_id"], "state_sha256": state["state_sha256"],
                      "graph_capture_id": state["graph_generation_id"], "bundle_sha256": bundle.bundle_sha256},
        "input_sha256": inputs.sha256, "measurement": measurement,
        "authority": copy.deepcopy(theme_state.AUTHORITY)}
    return {**record, "sha256": theme_state.canonical_sha256(record)}


def read_internal_w2_h1(composition: dict, *, bundle: adapter.OwnerBundle, inputs: W2BetaInputs,
                        effective_at: str, known_at: str, expected_generation_id: str) -> dict:
    """Exact internal read: recompute from captured capabilities, never a result dict.

    State visibility uses the incumbent ThemeState emission/30-hour artifact read
    rules. This is not a new H1 source-freshness rule or permission to display it.
    No native stores, current pointer or source acquisition are consulted.
    """
    result = {"schema": INTERNAL_READ_SCHEMA, "status": "UNAVAILABLE", "reason_codes": [],
        "purpose": "research_internal", "public_display_allowed": False,
        "state_ref": None, "measurement": None, "authority": copy.deepcopy(theme_state.AUTHORITY)}
    state = composition.get("state") if isinstance(composition, dict) else None
    try:
        adapter._assert_state_matches_bundle(state, bundle)
    except (ValueError, TypeError, KeyError):
        result["reason_codes"] = ["STATE_BUNDLE_BINDING_INVALID"]
        return result
    reasons = []
    if state["generation_id"] != expected_generation_id:
        reasons.append("GENERATION_MISMATCH")
    if state["effective_at"] != effective_at:
        reasons.append("EFFECTIVE_TIME_MISMATCH")
    # These are exactly the existing state read's visibility conditions. No
    # qualification or freshness is inferred for the historical H1 observations.
    if not theme_state._proven_by(state["known_at"], known_at):
        reasons.append("STATE_AFTER_CUTOFF")
    if not theme_state._proven_by(state["generated_at"], known_at):
        reasons.append("STATE_NOT_YET_EMITTED")
    cutoff, _ = theme_state._clock(known_at)
    emitted, _ = theme_state._clock(state["generated_at"])
    if (cutoff - emitted).total_seconds() > theme_state.STATE_MAX_AGE_HOURS * 3600:
        reasons.append("STATE_STALE")
    if reasons:
        result["reason_codes"] = sorted(set(reasons))
        return result
    internal = composition.get("internal_measurements", {})
    if not isinstance(internal, dict):
        result["reason_codes"] = ["INTERNAL_MEASUREMENT_BINDING_INVALID"]
        return result
    record = internal.get(MEASUREMENT_KEY)
    if record is None:
        result["reason_codes"] = ["INTERNAL_MEASUREMENT_NOT_COMPOSED"]
        return result
    try:
        expected = compose_internal_w2_h1(state, bundle=bundle, inputs=inputs)
        if adapter._json(record) != adapter._json(expected):
            raise ValueError("internal record differs from deterministic native composition")
    except (ValueError, TypeError, KeyError):
        result["reason_codes"] = ["INTERNAL_MEASUREMENT_BINDING_INVALID"]
        return result
    measurement = expected["measurement"]
    result.update(status=measurement["status"], reason_codes=copy.deepcopy(measurement["reason_codes"]),
                  state_ref=copy.deepcopy(expected["state_ref"]), measurement=copy.deepcopy(measurement))
    return result
