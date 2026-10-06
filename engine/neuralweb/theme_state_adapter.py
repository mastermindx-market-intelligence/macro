"""Captured incumbent inputs for version-selected ThemeState assembly and shadow.

This module owns no store, source authentication, publication, history or policy.
Native API results and specialist facts survive missing qualification. Production
v2 retains them in named legs with native null clocks and qualification limits;
the unchanged shadow-v1 witness receives no forged compiler receipt.
Only capture observes a real read instant. Composition is deterministic and does
not read files, consult a clock, resolve identity or revalidate rights.
"""
from __future__ import annotations

import base64
import copy
import datetime as dt
import hashlib
import io
import json
import math
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine import basket_membership_pit as pit
from engine.neuralweb import thematic_state as legacy
from engine.theme_graph import identity, identity_resolution, ontology, rights, store, theme_state, theme_state_production
from lib import config

BUNDLE_SCHEMA = "gmi.theme_state_owner_bundle/v1"
COMPILER_LIMIT = "UNQUALIFIED_NATIVE_FACT_REQUIRES_NULL_NATIVE_CLOCKS_NOT_SUPPORTED_BY_SHADOW_V1_RECEIPT"
SOURCE_PATHS = {
    "theme_crosswalk": legacy._CROSSWALK_PATH,
    "foresight_cascade": legacy._FORESIGHT_PATH,
    "baskets": legacy._BASKETS_PATH,
    "radar": legacy._RADAR_PATH,
    "radar_enriched": legacy._RADAR_ENRICHED_PATH,
    "narrative_emergence": legacy._NARRATIVE_PATH,
    "narrative_emergence_cn": "site/chinabasketdata/narrative_emergence.json",
    "subsector_rotation": legacy._SUBSECTOR_PATH,
    "divergence_log": legacy._DIVERGENCE_LOG_PATH,
}
OWNER_ROLES = ("ontology", "identity", "membership", "rights", "eligibility")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _clock(value: str, *, precise: bool = False) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("clock must be a string")
    if len(value) == 10:
        if precise:
            raise ValueError("precise zoned clock required")
        return dt.datetime.combine(dt.date.fromisoformat(value), dt.time(), dt.timezone.utc)
    instant = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("precise zoned clock required")
    return instant.astimezone(dt.timezone.utc)


def _native_json(value: Any) -> Any:
    """Retain non-JSON native nulls as named markers, never 'nan' securities."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"native_null": "NaN" if math.isnan(value) else "NONFINITE"}
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _native_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_native_json(v) for v in value]
    if hasattr(value, "item"):
        return _native_json(value.item())
    if type(value).__name__ in {"NAType", "NaTType"}:
        return {"native_null": type(value).__name__}
    raise ValueError("unsupported native result type: " + type(value).__name__)


def _assembled_labels(node_id: str, raw_en, raw_zh) -> tuple[str, str]:
    """Apply seat ruling G1-labels 2026-10-06T12:08Z (L-A): copy the vendor's own
    label into the other language slot of a research-internal shadow."""
    def present(value):
        if value is None:
            return False
        if type(value) is dict:
            if set(value) != {"native_null"}:
                raise ValueError("invalid captured subject label dict")
            return False
        if type(value) is str:
            return value.strip() != ""
        raise ValueError(f"invalid captured subject label {type(value).__name__}")

    en_present, zh_present = present(raw_en), present(raw_zh)
    if not en_present and not zh_present:
        raise ValueError(f"theme subject {node_id}: both name_en and name_zh absent")
    return (
        raw_en if en_present else raw_zh,
        raw_zh if zh_present else raw_en,
    )


@dataclass(frozen=True)
class OwnerBundle:
    payload_json: str
    bundle_sha256: str

    def snapshot(self) -> dict:
        if _sha(self.payload_json.encode()) != self.bundle_sha256:
            raise ValueError("owner bundle digest mismatch")
        value = json.loads(self.payload_json)
        if value.get("schema") != BUNDLE_SCHEMA:
            raise ValueError("unsupported owner bundle")
        _clock(value["query"]["effective_at"])
        _clock(value["query"]["known_at"], precise=True)
        _clock(value["observed_at"], precise=True)
        for source in value["sources"].values():
            if source["bytes_b64"] is not None:
                raw = base64.b64decode(source["bytes_b64"], validate=True)
                if _sha(raw) != source["sha256"]:
                    raise ValueError("captured source digest mismatch")
        _validate_bundle_derivations(value)
        return value


def _source(root: Path, relative: str) -> dict:
    try:
        raw = (root / relative).read_bytes()
    except FileNotFoundError:
        return {"path": relative, "availability": "UNAVAILABLE", "null_reason": "SOURCE_MISSING", "sha256": None, "bytes_b64": None}
    except OSError:
        return {"path": relative, "availability": "UNAVAILABLE", "null_reason": "SOURCE_UNREADABLE", "sha256": None, "bytes_b64": None}
    return {"path": relative, "availability": "AVAILABLE", "null_reason": None, "sha256": _sha(raw), "bytes_b64": base64.b64encode(raw).decode()}


def _decode(source: dict) -> Any:
    if source["bytes_b64"] is None:
        return None
    text = base64.b64decode(source["bytes_b64"]).decode("utf-8")
    if source["path"].endswith((".yml", ".yaml")):
        value = yaml.safe_load(text)
    elif source["path"].endswith(".jsonl"):
        value = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        value = json.loads(text)
    _json(value)
    return value


def _attempt(call, *args, **kwargs) -> dict:
    try:
        return {"availability": "AVAILABLE", "null_reason": None, "value": _native_json(call(*args, **kwargs))}
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return {"availability": "UNAVAILABLE", "null_reason": "OWNER_INPUT_UNAVAILABLE", "value": None, "error_type": type(exc).__name__}


def _native_members(basket_id: str, suite: str, effective_at: str) -> dict:
    # Invoke the incumbent public API even when its tolerant return cannot qualify.
    answer = _attempt(pit.members_asof, basket_id, effective_at[:10], suite=suite)
    checked = _attempt(lambda: pit.read_history(suite, strict=True).to_dict("records"))
    if checked["availability"] == "UNAVAILABLE":
        return {"availability": "UNAVAILABLE", "null_reason": "OWNER_HISTORY_UNREADABLE", "value": None, "unqualified_native_return": answer["value"]}
    return answer


def _materialized_records(value: Any) -> Any:
    # Mirrors ontology._records' input handling, so its per-call row copy sees equal rows.
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict("records")
        except TypeError:
            pass
    return list(value)


class _CaptureStoreView:
    """One capture's memo over the owner's ``StoreView`` seam (RULING_G1_render_cost r4).

    ``ontology.compose_neighborhood`` re-read and re-materialized all four owner
    frames on every call; 662 subjects x 4 ``to_dict("records")`` dominated the
    capture profile. This view performs each owner read once per capture and
    hands every compose call the same records; the owner still runs its full
    composition per subject and copies each row before use. A failed read is
    never memoized, so the per-subject failure path is unchanged. Its scope is
    one capture: it is not a global cache, and the post-capture source hash
    re-read still refuses source races.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._rows: dict[str, Any] = {}

    def _read(self, name: str) -> Any:
        if name not in self._rows:
            self._rows[name] = _materialized_records(getattr(self._inner, name)())
        return self._rows[name]

    def read_nodes(self) -> Any:
        return self._read("read_nodes")

    def read_node_lifecycle(self) -> Any:
        return self._read("read_node_lifecycle")

    def read_edges(self) -> Any:
        return self._read("read_edges")

    def read_proposals(self) -> Any:
        return self._read("read_proposals")


def _input_paths(root: Path) -> dict[str, str]:
    paths = dict(SOURCE_PATHS)
    paths.update({"legacy_predecessor": "data/neuralweb/theme_state.json", "legacy_phase_history": "data/neuralweb/theme_phase_history.jsonl"})
    for suite in ("baskets", "baskets_china", "baskets_china_ths"):
        for owner_path in (pit.membership_path(suite), pit.history_path(suite), pit.cadence_path(suite)):
            relative = str(owner_path.relative_to(root))
            paths[suite + "/" + owner_path.name] = relative
    for name in ("nodes.parquet", "node_lifecycle.parquet", "edges.parquet", "evidence.parquet", "_meta.json", "probation/proposals.jsonl"):
        paths["graph/" + name] = "data/theme_graph/" + name
    for name in (identity_resolution.MASTER_FILE, identity_resolution.ALIASES_FILE, identity_resolution.RECEIPT_FILE):
        paths["identity/" + name] = "data/reference/" + name
    paths["rights_registry"] = str(rights.registry_path().relative_to(Path(legacy.__file__).resolve().parents[2]))
    return paths


def _metadata(row: dict) -> dict:
    value = row.get("source_meta")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def _validate_bundle_derivations(snapshot: dict) -> None:
    """Check duplicated scope against captured bytes/API values, not live inputs."""
    crosswalk = _decode(snapshot["sources"]["theme_crosswalk"])
    if _json(crosswalk) != _json(snapshot["crosswalk"]):
        raise ValueError("derived crosswalk differs from captured source bytes")
    graph_hashes = {key: value["sha256"] for key, value in snapshot["sources"].items()
                    if key.startswith("graph/")}
    if snapshot["graph_capture_id"] != "adapter-snapshot:" + theme_state.canonical_sha256(graph_hashes):
        raise ValueError("derived graph capture differs from captured source bytes")
    expected = {}
    for cfg in crosswalk["themes"]:
        node = identity.theme_node_id(cfg["id"])
        if node in expected:
            raise ValueError("duplicate captured canonical scope")
        expected[node] = {"kind": "canonical_theme", "name_en": cfg.get("name_en"),
            "name_zh": cfg.get("name_zh"), "source_family": None, "native_id": None, "basket": None}
    nodes = snapshot["graph_nodes_read"]
    if nodes["availability"] == "AVAILABLE":
        for row in nodes["value"]:
            if row.get("kind") != "local_theme":
                continue
            node = row.get("node_id")
            if not isinstance(node, str) or len(node.split(":", 2)) != 3:
                raise ValueError("invalid captured local scope")
            _, family, native_id = node.split(":", 2)
            if node != identity.local_theme_node_id(family, native_id) or node in expected:
                raise ValueError("ambiguous captured local scope")
            meta = _metadata(row)
            basket = {"basket_id": meta["basket_id"], "suite": meta["suite"]} if (
                isinstance(meta.get("basket_id"), str) and
                meta.get("suite") in ("baskets", "baskets_china", "baskets_china_ths")) else None
            expected[node] = {"kind": "local_theme", "name_en": row.get("name_en"),
                "name_zh": row.get("name_zh"), "source_family": family, "native_id": native_id,
                "basket": basket}
    actual = {node: {key: row.get(key) for key in
                       ("kind", "name_en", "name_zh", "source_family", "native_id", "basket")}
              for node, row in snapshot["subjects"].items()}
    if _json(actual) != _json(expected):
        raise ValueError("derived subject scope differs from captured owner inputs")


def _bound_rights_read(root: Path, source: dict, family: str | None) -> dict:
    """Use the incumbent APIs at the exact path; refuse their stale path cache.

    The uncached function is the existing owner's implementation, not a new
    registry interpreter. No imported cache/global is cleared or patched.
    """
    path = root / source["path"]
    result = {"family": family, "known_family": False, "licensing": None,
              "availability": "UNAVAILABLE", "null_reason": "RIGHTS_REGISTRY_UNAVAILABLE",
              "registry_path": str(path), "registry_sha256": source["sha256"],
              "rights_class": None, "current_bytes_bound": False}
    if source["availability"] != "AVAILABLE":
        return result
    fresh_reader = getattr(rights._load, "__wrapped__", None)
    if not callable(fresh_reader):
        result["null_reason"] = "RIGHTS_CURRENT_BYTES_VERIFIER_UNAVAILABLE"
        return result
    try:
        if _sha(path.read_bytes()) != source["sha256"]:
            raise ValueError("rights source changed during owner read")
        fresh = fresh_reader(str(path))
        cached = rights.load_registry(path=path)
        if _json(cached) != _json(fresh):
            result["null_reason"] = "RIGHTS_CACHE_VERSION_UNAVAILABLE"
            return result
        known = family in rights.known_families(path=path)
        licensing = rights.licensing_for_family(family or "", path=path)
        if _sha(path.read_bytes()) != source["sha256"]:
            raise ValueError("rights source changed during owner read")
        result.update(known_family=known, licensing=licensing, current_bytes_bound=True)
        if known:
            # A mint-time internal-only fallback does not prove a readable class.
            result["rights_class"] = rights.rights_class(family, path=path)
            result.update(availability="AVAILABLE", null_reason=None)
        else:
            result["null_reason"] = "RIGHTS_FAMILY_UNRESOLVED"
    except rights.RightsRefusal:
        result.update(availability="UNAVAILABLE", null_reason="RIGHTS_CLASS_UNAVAILABLE")
    except (OSError, ValueError, TypeError, AttributeError, RuntimeError, yaml.YAMLError):
        result["null_reason"] = "RIGHTS_REGISTRY_UNAVAILABLE"
    return result


def capture_owner_bundle(root: Path, *, owner_readers=None, effective_at: str, known_at: str) -> OwnerBundle:
    """Read actual APIs and bytes; optional reader supplies separately owned receipts.

    ``owner_readers.read_state_qualification`` is a trusted owner capability, not
    an authentication implementation. It cannot replace any native API result.
    None is the ordinary, honestly unqualified path. A plain success dictionary
    is not a reader. Production custody/authentication of that capability is owed.
    """
    root = Path(root).resolve()
    _clock(effective_at)
    _clock(known_at, precise=True)
    if config.data_dir().resolve() != (root / "data").resolve():
        raise ValueError("configured owner data root differs from captured root")
    if owner_readers is not None and not callable(getattr(owner_readers, "read_state_qualification", None)):
        raise TypeError("qualified owner reader capability required")
    paths = _input_paths(root)
    producer_refs = _production_code_refs()
    sources = {key: _source(root, path) for key, path in paths.items()}
    crosswalk = _decode(sources["theme_crosswalk"])
    if not isinstance(crosswalk, dict) or not isinstance(crosswalk.get("themes"), list):
        raise ValueError("crosswalk unavailable")
    ids = [c["id"] for c in crosswalk["themes"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate crosswalk identity")
    view = ontology.RepositoryStore()
    nodes = _attempt(lambda: view.read_nodes().to_dict("records"))
    subjects = {}
    for cfg in crosswalk["themes"]:
        node_id = identity.theme_node_id(cfg["id"])
        subjects[node_id] = {"kind": "canonical_theme", "name_en": cfg.get("name_en"), "name_zh": cfg.get("name_zh"), "source_family": None, "native_id": None, "basket": None}
    company_nodes = []
    if nodes["availability"] == "AVAILABLE":
        for row in nodes["value"]:
            node_id = row.get("node_id")
            if row.get("kind") == "company":
                company_nodes.append(node_id)
            if row.get("kind") != "local_theme":
                continue
            if not isinstance(node_id, str) or len(node_id.split(":", 2)) != 3:
                raise ValueError("invalid local graph identity")
            _, family, native_id = node_id.split(":", 2)
            if identity.local_theme_node_id(family, native_id) != node_id:
                raise ValueError("invalid local graph identity")
            meta = _metadata(row)
            basket = {"basket_id": meta["basket_id"], "suite": meta["suite"]} if isinstance(meta.get("basket_id"), str) and meta.get("suite") in ("baskets", "baskets_china", "baskets_china_ths") else None
            subjects[node_id] = {"kind": "local_theme", "name_en": row.get("name_en"), "name_zh": row.get("name_zh"), "source_family": family, "native_id": native_id, "basket": basket}
    identity_reads = {node: _attempt(identity_resolution.resolve_graph_node_identity, node, asof=effective_at[:10]) for node in sorted(set(company_nodes))}
    graph_hashes = {k: v["sha256"] for k, v in sources.items() if k.startswith("graph/")}
    graph_capture_id = "adapter-snapshot:" + theme_state.canonical_sha256(graph_hashes)
    query = {"effective_at": effective_at, "known_at": known_at}
    capture_view = _CaptureStoreView(view)
    for node_id, subject in subjects.items():
        reads = {"ontology": _attempt(ontology.compose_neighborhood, capture_view, node_id=node_id, asof=effective_at[:10], knowledge_cutoff=known_at[:10]), "identity": identity_reads}
        basket = subject["basket"]
        reads["membership"] = _native_members(basket["basket_id"], basket["suite"], effective_at) if basket else {"availability": "UNAVAILABLE", "null_reason": "EXACT_LOCAL_BASKET_BINDING_UNAVAILABLE", "value": None}
        family = rights.family_for_node_id(node_id)
        reads["rights"] = _bound_rights_read(root, sources["rights_registry"], family)
        subject["native_reads"] = reads
        qualified = owner_readers.read_state_qualification(node_id=node_id, query=copy.deepcopy(query), graph_capture_id=graph_capture_id, native_reads=copy.deepcopy(reads), source_sha256={k: v["sha256"] for k, v in sources.items()}) if owner_readers is not None else None
        subject["qualification"] = _native_json(qualified)
    # Verification rereads only hashes, refusing races rather than claiming an
    # atomic native-owner transaction or silently composing mixed generations.
    for key, path in paths.items():
        after = _source(root, path)
        if after != sources[key]:
            raise ValueError("source changed during capture: " + path)
    specialist_rights = {name: _bound_rights_read(root, sources["rights_registry"], rights.family_for_source_ref(sources[name]["path"]))
                         for name in SOURCE_PATHS if name != "theme_crosswalk"}
    if _production_code_refs() != producer_refs:
        raise ValueError("production implementation changed during capture")
    if _source(root, paths["rights_registry"]) != sources["rights_registry"]:
        raise ValueError("rights source changed during specialist owner reads")
    observed_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {"schema": BUNDLE_SCHEMA, "query": query, "observed_at": observed_at,
               "producer_refs": producer_refs, "specialist_rights": _native_json(specialist_rights),
               "sources": sources, "crosswalk": crosswalk, "graph_capture_id": graph_capture_id,
               "native_graph_generation_id": None, "graph_nodes_read": nodes, "subjects": subjects,
               "limits": ["captured digest is integrity, not authentication or native generation", "date-only owner APIs do not prove precise historical knowledge",
                          "before/after byte checks are not an atomic native-owner transaction or authentication", COMPILER_LIMIT]}
    text = _json(payload)
    return OwnerBundle(text, _sha(text.encode()))


class _FrozenPath:
    def __init__(self, sources: dict, path: str = ""):
        self.sources, self.path = sources, path

    def __truediv__(self, suffix):
        return _FrozenPath(self.sources, str(Path(self.path) / str(suffix)))

    def __str__(self):
        return self.path or "."

    def exists(self):
        return any(s["path"] == self.path and s["bytes_b64"] is not None for s in self.sources.values())

    def read_text(self, encoding="utf-8"):
        source = next((s for s in self.sources.values() if s["path"] == self.path), None)
        if source is None or source["bytes_b64"] is None:
            raise FileNotFoundError(self.path)
        return base64.b64decode(source["bytes_b64"]).decode(encoding)

    def open(self, mode="r", encoding="utf-8"):
        if mode != "r":
            raise ValueError("captured inputs are read-only")
        return io.StringIO(self.read_text(encoding))


def _legacy_from_bundle(snapshot: dict, generated_at: str) -> dict:
    """Run actual incumbent read/compose code in isolated clock/path globals.

    No imported owner globals are patched; no copied financial interpretation.
    The explicit emission clock preserves incumbent as_of/staleness behavior.
    Only read/compose helpers are rebound; history/publisher functions are absent.
    """
    instant = _clock(generated_at, precise=True)
    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    namespace = dict(vars(legacy))
    namespace["datetime"] = Clock
    namespace["Path"] = lambda path: path if isinstance(path, _FrozenPath) else Path(path)
    names = ["_load_json", "_load_yaml", "_parse_asof", "_is_stale", "_asof_today", "_compose_theme", "compose"]
    names += [n for n in vars(legacy) if n.startswith("_read_")]
    for name in names:
        function = getattr(legacy, name)
        rebound = types.FunctionType(function.__code__, namespace, name, function.__defaults__, function.__closure__)
        rebound.__kwdefaults__ = function.__kwdefaults__
        namespace[name] = rebound
    return namespace["compose"](_FrozenPath(snapshot["sources"]))


def _source_observation(source: dict, observed_at: str, known_at: str) -> dict:
    try:
        fact = _decode(source)
        status, reason = ("AVAILABLE", None) if fact is not None else ("UNAVAILABLE", source["null_reason"])
    except (ValueError, TypeError, UnicodeError, yaml.YAMLError):
        fact, status, reason = None, "INVALID", "SOURCE_MALFORMED"
    effective = (fact.get("as_of") or fact.get("asof")) if isinstance(fact, dict) else None
    native_known = fact.get("known_at") if isinstance(fact, dict) else None
    freshness = "UNKNOWN"
    if effective is not None:
        try:
            date = _clock(effective)
            cutoff = _clock(known_at, precise=True)
            precise = isinstance(effective, str) and len(effective) > 10
            if (precise and date > cutoff) or (not precise and date.date() > cutoff.date()):
                freshness, status, reason = "FUTURE", "UNAVAILABLE", "SOURCE_AFTER_CUTOFF"
            elif (cutoff - legacy._parse_asof(effective)).days >= legacy._STALE_DAYS:
                freshness = "STALE"
            elif len(effective) > 10:
                freshness = "FRESH"
        except (ValueError, TypeError):
            reason = "SOURCE_CLOCK_INVALID"
    return {"availability": status, "fact": fact, "null_reason": reason, "freshness": freshness,
            "native_clocks": {"effective_at": effective, "known_at": native_known,
                              "precision": "DATE" if isinstance(effective, str) and len(effective) == 10 else "INSTANT" if effective else "UNAVAILABLE",
                              "generation_id": fact.get("generation_id") if isinstance(fact, dict) else None},
            "observed_at": observed_at, "source_sha256": source["sha256"],
            "units": fact.get("units") if isinstance(fact, dict) else None,
            "window": fact.get("window") if isinstance(fact, dict) else None,
            "conflicts": fact.get("conflicts", []) if isinstance(fact, dict) else [],
            "per_use": {"historical_knowability": "UNPROVEN", "selection": False, "publication": False},
            "freshness_policy": "incumbent-source-5-calendar-days"}


def _qualified_receipts(subject: dict, node_id: str, snapshot: dict) -> tuple[dict, dict]:
    qualification = subject["qualification"]
    owners = {role: None for role in OWNER_ROLES}
    sources = {}
    if qualification is None:
        return owners, sources
    if not isinstance(qualification, dict) or set(qualification) != {"owner_receipts", "source_receipts"}:
        raise ValueError("closed qualified owner-read keys required")
    for role, receipt in qualification["owner_receipts"].items():
        if role not in owners or role == "eligibility":
            raise ValueError("D2E eligibility remains separately unsealed")
        theme_state._validate_receipt(receipt, subject_id=node_id, graph_generation_id=snapshot["graph_capture_id"], query=snapshot["query"])
        payload = receipt["payload"]
        if not isinstance(payload, dict) or payload.get("native_owner_read_sha256") != theme_state.canonical_sha256(subject["native_reads"][role]):
            raise ValueError("qualification does not bind actual owner read")
        if role == "membership":
            native = subject["native_reads"][role]
            if native["availability"] != "AVAILABLE" or native["value"].get("pit") is not True:
                raise ValueError("membership owner read is not PIT")
            members = payload.get("members")
            if not isinstance(members, list) or sorted(r["ticker"] for r in members) != native["value"]["members"]:
                raise ValueError("qualification membership differs from actual owner population")
        if role == "identity":
            membership = subject["native_reads"]["membership"]
            if membership["availability"] != "AVAILABLE":
                raise ValueError("identity membership scope unavailable")
            expected = {}
            for ticker in membership["value"]["members"]:
                matches = [(nid, read["value"]) for nid, read in subject["native_reads"]["identity"].items()
                           if read["availability"] == "AVAILABLE" and identity_resolution._best_effort_symbol(nid) == ticker]
                if len(matches) != 1 or matches[0][1].get("resolution_state") != "RESOLVED" or not matches[0][1].get("security_id"):
                    raise ValueError("actual owner identity is unresolved or ambiguous")
                nid, native_identity = matches[0]
                expected[ticker] = {"node_id": nid, "security_id": native_identity["security_id"], "issuer_id": native_identity.get("issuer_id")}
            if payload.get("status") != "RESOLVED" or payload.get("member_identities") != expected:
                raise ValueError("qualified identity differs from actual owner identities")
        if role == "ontology":
            native_mapping = subject["native_reads"]["ontology"]["value"]["canonical_mapping"]
            if subject["kind"] == "canonical_theme":
                native_mapping = {"state": "SUBJECT_IS_CANONICAL", "theme_node_ids": []}
            if payload.get("canonical_mapping") != native_mapping:
                raise ValueError("qualified ontology differs from actual owner mapping")
        if role == "rights":
            native = subject["native_reads"][role]
            licensing = native["licensing"]
            registry = snapshot["sources"]["rights_registry"]
            if (native.get("current_bytes_bound") is not True or native["availability"] != "AVAILABLE"
                    or native.get("registry_sha256") != registry["sha256"]
                    or not native["known_family"] or not isinstance(licensing, list) or len(licensing) != 3
                    or any(type(flag) is not bool for flag in licensing) or licensing[0] is not True
                    or registry["availability"] != "AVAILABLE" or registry["sha256"] is None
                    or payload.get("allowed") is not True or payload.get("purpose") != "research_internal"
                    or payload.get("registry_sha256") != registry["sha256"]):
                raise ValueError("current per-use rights remain unavailable")
        owners[role] = copy.deepcopy(receipt)
    if owners["membership"] is not None and owners["identity"] is not None:
        identities = owners["identity"]["payload"]["member_identities"]
        for member in owners["membership"]["payload"]["members"]:
            actual = identities.get(member["ticker"])
            if actual is None or any(member.get(axis) != actual[axis] for axis in ("security_id", "issuer_id")):
                raise ValueError("qualified member identity disagrees with actual owner identity")
    for name, receipt in qualification["source_receipts"].items():
        if name not in SOURCE_PATHS:
            raise ValueError("unknown qualified specialist source")
        theme_state._validate_receipt(receipt, subject_id=node_id, graph_generation_id=snapshot["graph_capture_id"], query=snapshot["query"])
        original = _decode(snapshot["sources"][name])
        if _json(receipt["payload"]) != _json(original):
            raise ValueError("qualified specialist receipt differs from captured bytes")
        if name in ("narrative_emergence", "narrative_emergence_cn"):
            expected_region = "cn" if name.endswith("_cn") else "us"
            if not isinstance(original, dict) or str(original.get("region", "")).lower() != expected_region:
                raise ValueError("qualified narrative source scope unavailable or mismatched")
        native_effective = _native_source_effective(name, original)
        if native_effective is None or receipt["effective_at"] != native_effective:
            raise ValueError("qualified receipt changes or invents native source clock")
        source_clock_fields = original if isinstance(original, dict) else {}
        for clock_name in ("known_at", "available_at", "recorded_at"):
            if source_clock_fields.get(clock_name) is not None and receipt[clock_name] != source_clock_fields[clock_name]:
                raise ValueError("qualified receipt changes native source clock")
        if source_clock_fields.get("generated_at") is not None and theme_state._definitely_after(source_clock_fields["generated_at"], receipt["available_at"]):
            raise ValueError("native source clock emission exceeds receipt availability")
        sources[name] = copy.deepcopy(receipt)
    return owners, sources


def _observed_ontology(subject: dict, node_id: str, snapshot: dict) -> dict | None:
    native = subject["native_reads"]["ontology"]
    if native["availability"] != "AVAILABLE" or native["value"]["availability"]["state"] != "OK":
        return None
    mapping = copy.deepcopy(native["value"]["canonical_mapping"])
    if subject["kind"] == "canonical_theme":
        mapping = {"state": "SUBJECT_IS_CANONICAL", "theme_node_ids": []}
    payload = {"canonical_mapping": mapping, "native_owner_read": native["value"],
               "qualification": "OBSERVED_UPPER_BOUND_ONLY_NOT_NATIVE_KNOWLEDGE"}
    return {"owner": "adapter.ontology.observed", "schema": "gmi.observed_owner_read/v1",
            "generation_id": snapshot["graph_capture_id"], "graph_generation_id": snapshot["graph_capture_id"],
            "subject_id": node_id, "query": snapshot["query"], "effective_at": native["value"]["asof"],
            "known_at": snapshot["observed_at"], "available_at": snapshot["observed_at"], "recorded_at": snapshot["observed_at"],
            "availability": "AVAILABLE", "payload": payload, "sha256": theme_state.canonical_sha256(payload)}


def _legacy_list_identity(row: Any, path: str) -> tuple | None:
    # These are the incumbent renderer's actual record keys, never list indexes.
    keys = {"basket_intel": ("basket_id", "source"), "radar": ("basket_id", "source"),
            "subsectors": ("key",)}.get(path.rsplit("/", 1)[-1])
    if keys is None or not isinstance(row, dict):
        return None
    values = tuple(row.get(k) for k in keys)
    return values if all(isinstance(v, str) and v for v in values) else None


def _inherit_optional(value: Any, previous: Any, *, path: str, inventory: list) -> None:
    if isinstance(value, dict) and isinstance(previous, dict):
        for key, old in previous.items():
            where = path + "/" + key
            if key not in value:
                value[key] = copy.deepcopy(old)
                inventory.append({"path": where, "status": "PRESERVED", "prior_value": copy.deepcopy(old),
                                  "consumer_disposition": "PRESERVE_OPTIONAL_FIELD"})
            elif isinstance(old, (dict, list)):
                _inherit_optional(value[key], old, path=where, inventory=inventory)
    elif isinstance(value, list) and isinstance(previous, list):
        if value == previous:
            return
        current_keys = [_legacy_list_identity(row, path) for row in value]
        prior_keys = [_legacy_list_identity(row, path) for row in previous]
        for row, key in zip(previous, prior_keys):
            matches = [i for i, candidate_key in enumerate(current_keys) if key is not None and candidate_key == key]
            if key is not None and prior_keys.count(key) == 1 and len(matches) == 1:
                _inherit_optional(value[matches[0]], row, path=path + "/record=" + _json(key), inventory=inventory)
            else:
                inventory.append({"path": path, "status": "UNMATCHED_PREDECESSOR_LIST_RECORD",
                                  "stable_identity": list(key) if key is not None else None,
                                  "prior_record": copy.deepcopy(row),
                                  "consumer_disposition": "RETIREMENT_OR_AMBIGUITY_DECISION_REQUIRED"})
    elif isinstance(previous, (dict, list)) and previous:
        inventory.append({"path": path, "status": "PREDECESSOR_BLOCK_NOT_PRESENT",
                          "prior_value": copy.deepcopy(previous),
                          "consumer_disposition": "RETIREMENT_DECISION_REQUIRED"})


def _compatibility_projection(state: dict, snapshot: dict) -> tuple:
    candidate = _legacy_from_bundle(snapshot, state["generated_at"])
    inventory = []
    source = snapshot["sources"]["legacy_predecessor"]
    status = {"availability": source["availability"], "null_reason": source["null_reason"],
              "source_sha256": source["sha256"]}
    try:
        predecessor = _decode(source)
    except (ValueError, TypeError, UnicodeError, yaml.YAMLError):
        predecessor = None
        status.update(availability="INVALID", null_reason="LEGACY_PREDECESSOR_MALFORMED")
    if isinstance(predecessor, dict) and predecessor.get("schema") == legacy.SCHEMA:
        prior_themes = predecessor.get("themes")
        if not isinstance(prior_themes, list) or any(not isinstance(t, dict) or not isinstance(t.get("theme_id"), str) for t in prior_themes):
            status.update(availability="INVALID", null_reason="LEGACY_PREDECESSOR_THEME_IDENTITIES_INVALID")
        else:
            ids = [t["theme_id"] for t in prior_themes]
            if len(ids) != len(set(ids)):
                status.update(availability="INVALID", null_reason="LEGACY_PREDECESSOR_THEME_IDENTITIES_AMBIGUOUS")
            else:
                _inherit_optional(candidate, {k: v for k, v in predecessor.items() if k != "themes"},
                                  path="", inventory=inventory)
                current = {t["theme_id"]: t for t in candidate["themes"]}
                for block in prior_themes:
                    tid = block["theme_id"]
                    if tid in current:
                        _inherit_optional(current[tid], block, path="/themes/" + tid, inventory=inventory)
                    else:
                        inventory.append({"path": "/themes/" + tid, "status": "UNMATCHED_PREDECESSOR_THEME",
                                          "prior_record": copy.deepcopy(block),
                                          "consumer_disposition": "RETIREMENT_DECISION_REQUIRED"})
    elif predecessor is not None:
        status.update(availability="INVALID", null_reason="LEGACY_PREDECESSOR_SCHEMA_UNSUPPORTED")
    for block in candidate["themes"]:
        # Consumer interpretation is held; null is an explicit disposition, not parity.
        block["narrative"] = None
    return candidate, inventory, status


def legacy_projection_for_owner(state: dict, bundle: OwnerBundle) -> dict:
    snapshot, _, _ = _assert_state_matches_bundle(state, bundle)
    return _compatibility_projection(state, snapshot)[0]


def compare_shadow(legacy_value: dict, state: dict, projection: dict, bundle: OwnerBundle) -> dict:
    snapshot, native, dispositions = _assert_state_matches_bundle(state, bundle)
    expected_projection, inventory, predecessor_status = _compatibility_projection(state, snapshot)
    if (_json(legacy_value) != _json(_legacy_from_bundle(snapshot, state["generated_at"]))
            or _json(projection) != _json(expected_projection)):
        raise ValueError("shadow must use the same captured inputs and owner interpretation")
    differences = []
    def walk(left, right, path):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left or key not in right:
                    differences.append({"path": path + "/" + key, "before": left.get(key), "after": right.get(key), "reason": "PRESERVED_PREDECESSOR_OPTIONAL_FIELD"})
                else:
                    walk(left[key], right[key], path + "/" + key)
        elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
            for i, (a, b) in enumerate(zip(left, right)):
                walk(a, b, path + "/" + str(i))
        elif _json(left) != _json(right):
            differences.append({"path": path, "before": left, "after": right,
                                "reason": "LEGACY_NARRATIVE_INTERPRETATION_UNACCEPTED" if path.endswith("/narrative") else "UNEXPECTED_DIFFERENCE"})
    walk(legacy_value, projection, "")
    return {"same_input_bundle_sha256": bundle.bundle_sha256, "graph_capture_id": snapshot["graph_capture_id"],
            "state_sha256": state["state_sha256"], "legacy_sha256": theme_state.canonical_sha256(legacy_value),
            "projection_sha256": theme_state.canonical_sha256(projection), "differences": differences,
            "successor_surface": {subject["node_id"]: {
                "subject": copy.deepcopy(subject),
                "source_dispositions": copy.deepcopy(dispositions[subject["node_id"]]),
                "native_observations": copy.deepcopy(native[subject["node_id"]])}
                for subject in state["subjects"]},
            "semantic_binding": "EXACT_DETERMINISTIC_BUNDLE_ASSEMBLY",
            "correction_binding": "INCUMBENT_STATE_VALIDATOR_NOT_PREVIOUS_ARTIFACT_RECONSTRUCTION",
            "predecessor_optional_inventory": inventory, "predecessor_read": predecessor_status,
            "legacy_narrative_disposition": "INTERPRETATION_HELD",
            "canonical_aggregation_disposition": "NO_IMPLICIT_AGGREGATION",
            "parity_accepted": False, "natural": False, "cutover_allowed": False}


def _source_dispositions(native: dict, qualified: dict, selected_narrative: str, observations: dict) -> dict:
    """Declare precisely what each source contributes; no silent qualification loss."""
    surfaces = {
        "foresight_cascade": ("foresight_measurements", ["foresight"], "FORESIGHT"),
        "baskets": ("basket_intel_measurements", ["basket_intel"], "BASKET_INTEL"),
        "radar": ("radar_hypothesis_measurements", ["radar"], "RADAR_HYPOTHESES"),
        "radar_enriched": ("radar_flag_measurements", ["radar"], "RADAR_FLAGS"),
        "subsector_rotation": ("subsector_measurements", ["subsector_rotation"], "SUBSECTOR"),
        "divergence_log": ("divergence_measurements", ["divergence_board"], "DIVERGENCE_LOG"),
        "narrative_emergence": ("narrative_measurements_us", ["narrative"], "NARRATIVE"),
        "narrative_emergence_cn": ("narrative_measurements_cn", ["narrative"], "NARRATIVE"),
    }
    result = {}
    for name, (native_key, fields, seam) in surfaces.items():
        receipt = qualified.get(name)
        fact = native[native_key]
        status, reason = "UNQUALIFIED_SOURCE", COMPILER_LIMIT
        if fact["availability"] in ("UNAVAILABLE", "INVALID"):
            status = "SOURCE_" + fact["availability"]
            reason = fact["null_reason"] or status
        observation_names = []
        if receipt is not None:
            if seam == "NARRATIVE" and name == selected_narrative and observations:
                status, reason = "ADAPTED_RECOMMENDED_SUBSET", "LEGACY_NARRATIVE_INTERPRETATION_UNACCEPTED"
                observation_names = list(observations)
            else:
                status = "QUALIFIED_SOURCE_NOT_ADAPTED"
                reason = ("NARRATIVE_MEMBERSHIP_IDENTITY_OR_MARKET_SCOPE_REQUIRED" if seam == "NARRATIVE"
                          else "SUBJECT_SCOPED_" + seam + "_ADAPTER_NOT_IMPLEMENTED")
        result[name] = {
            "status": status, "reason_code": reason, "legacy_fields": fields,
            "observation_names": observation_names, "source_sha256": fact["source_sha256"],
            "native_availability": fact["availability"], "native_clocks": fact["native_clocks"],
            "native_freshness": fact["freshness"], "receipt_sha256": receipt["sha256"] if receipt else None,
            "receipt_clocks": {k: receipt[k] for k in ("effective_at", "known_at", "available_at", "recorded_at")} if receipt else None,
            "sidecar_fact_preserved": True, "consumer_parity_accepted": False}
    return result


def _assemble_from_bundle(snapshot: dict) -> tuple:
    """Single deterministic normalization used by composition and binding."""
    inputs, generations, native_observations = [], {"adapter.owner_bundle": _sha(_json(snapshot).encode())}, {}
    source_dispositions = {}
    for node_id, subject in snapshot["subjects"].items():
        owners, qualified_sources = _qualified_receipts(subject, node_id, snapshot)
        if owners["ontology"] is None:
            owners["ontology"] = _observed_ontology(subject, node_id, snapshot)
        observations = {}
        basket = subject["basket"]
        narrative_source = "narrative_emergence_cn" if basket is not None and identity.market_for_suite(basket["suite"]) == "cn" else "narrative_emergence"
        native = {name: _source_observation(snapshot["sources"][source], snapshot["observed_at"], snapshot["query"]["known_at"])
                  for name, source in [("narrative_measurements", narrative_source), ("narrative_measurements_us", "narrative_emergence"),
                                       ("narrative_measurements_cn", "narrative_emergence_cn"), ("foresight_measurements", "foresight_cascade"),
                                       ("basket_intel_measurements", "baskets"), ("radar_flag_measurements", "radar_enriched"),
                                       ("radar_hypothesis_measurements", "radar"), ("subsector_measurements", "subsector_rotation"), ("divergence_measurements", "divergence_log")]}
        membership = subject["native_reads"]["membership"]
        native["membership_owner_read"] = {"availability": membership["availability"], "fact": membership["value"], "null_reason": membership["null_reason"],
                                            "observed_at": snapshot["observed_at"], "known_at": None, "knowledge_qualification": "PRECISE_COMPLETENESS_UNPROVEN"}
        nr, mr = qualified_sources.get(narrative_source), owners["membership"]
        if nr is not None and mr is not None and owners["identity"] is not None and subject["basket"] is not None:
            overlap = theme_state.adapt_recommended_overlap(nr, mr, basket_id=subject["basket"]["basket_id"], **snapshot["query"])
            observations["forming_narrative_recommended_ticker_overlap"] = overlap
            native["forming_narrative_recommended_ticker_overlap"] = {"availability": overlap["presence"], "fact": overlap["value"], "null_reason": overlap["null_reason"], "freshness": overlap["freshness"], "coverage": overlap["coverage"]}
        else:
            native["forming_narrative_recommended_ticker_overlap"] = {"availability": "UNAVAILABLE", "fact": None, "null_reason": "QUALIFIED_MEMBERSHIP_IDENTITY_AND_NARRATIVE_OUTCOME_REQUIRED", "coverage": {"declared": None, "observed": None, "basis": "recommended_entry_subset_not_full_cluster"}}
        for receipt in list(owners.values()) + list(qualified_sources.values()):
            if receipt is not None:
                owner, generation = receipt["owner"], receipt["generation_id"]
                if owner in generations and generations[owner] != generation:
                    raise ValueError("mixed owner source generations")
                generations[owner] = generation
        native_observations[node_id] = native
        source_dispositions[node_id] = _source_dispositions(native, qualified_sources, narrative_source, observations)
        name_en, name_zh = _assembled_labels(node_id, subject["name_en"], subject["name_zh"])
        inputs.append({"node_id": node_id, "kind": subject["kind"], "name_en": name_en, "name_zh": name_zh, "source_family": subject["source_family"], "native_id": subject["native_id"], "owners": owners, "observations": observations, "canonical_aggregation": None})
    return inputs, generations, native_observations, source_dispositions


def _assert_state_matches_bundle(state: dict, bundle: OwnerBundle) -> tuple:
    theme_state.validate_state(state)
    snapshot = bundle.snapshot()
    if (state["graph_generation_id"] != snapshot["graph_capture_id"]
            or state["effective_at"] != snapshot["query"]["effective_at"]
            or state["known_at"] != snapshot["query"]["known_at"]
            or state["owner_generations"].get("adapter.owner_bundle") != bundle.bundle_sha256):
        raise ValueError("mixed owner bundle/state generation or query")
    if _clock(state["generated_at"], precise=True) < _clock(snapshot["observed_at"], precise=True):
        raise ValueError("generation emission precedes actual owner capture")
    inputs, generations, native, dispositions = _assemble_from_bundle(snapshot)
    expected = theme_state.compose_state(inputs, graph_generation_id=snapshot["graph_capture_id"],
                                        owner_generations=generations, **snapshot["query"],
                                        generated_at=state["generated_at"])
    # Correction lineage is validated by its incumbent artifact owner, not
    # reconstructed from source inputs which contain no previous state artifact.
    owner_lineage = {"correction", "generation_id", "state_sha256"}
    if _json({k: v for k, v in state.items() if k not in owner_lineage}) != _json({
            k: v for k, v in expected.items() if k not in owner_lineage}):
        raise ValueError("state differs from deterministic owner bundle assembly")
    return snapshot, native, dispositions


def compose_from_owner_bundle(bundle: OwnerBundle, *, generated_at: str, previous=None) -> dict:
    snapshot = bundle.snapshot()
    _clock(generated_at, precise=True)
    if _clock(generated_at, precise=True) < _clock(snapshot["observed_at"], precise=True):
        raise ValueError("generation emission precedes actual owner capture")
    inputs, generations, native_observations, dispositions = _assemble_from_bundle(snapshot)
    state = theme_state.compose_state(inputs, graph_generation_id=snapshot["graph_capture_id"], owner_generations=generations,
                                      **snapshot["query"], generated_at=generated_at, previous=previous)
    baseline = _legacy_from_bundle(snapshot, generated_at)
    candidate = legacy_projection_for_owner(state, bundle)
    limits = sorted({d["reason_code"] for subject in dispositions.values() for d in subject.values()
                     if d["status"] != "ADAPTED_RECOMMENDED_SUBSET"})
    return {"state": state, "legacy_baseline": baseline, "legacy_candidate": candidate,
            "native_observations": native_observations, "source_dispositions": dispositions,
            "bundle_sha256": bundle.bundle_sha256,
            "shadow": compare_shadow(baseline, state, candidate, bundle), "compiler_limits": limits,
            "publication_allowed": False, "native_qualification": "UNAVAILABLE_UNLESS_SEPARATE_OWNER_RECEIPTS_SUPPLIED"}


def _production_code_refs():
    # Exact implementation/contract files, not source-owner generations.
    base = Path(__file__).resolve().parents[2]
    paths = {"adapter": "engine/neuralweb/theme_state_adapter.py",
             "compiler": "engine/theme_graph/theme_state_production.py",
             "schema": "contracts/theme_graph/theme_state.v2.schema.json"}
    return {name: {"path": path, "sha256": _sha((base / path).read_bytes())}
            for name, path in paths.items()}


def _native_source_effective(name, value):
    if isinstance(value, dict):
        effective = next((value[key] for key in ("as_of", "asof") if key in value and value[key] is not None), None)
        if effective is None and name == "baskets":
            nested = value.get("theme_intel")
            effective = nested.get("as_of") if isinstance(nested, dict) else None
        return effective
    if name == "divergence_log" and isinstance(value, list) and value:
        clocks = [row.get("asof") or row.get("as_of") for row in value if isinstance(row, dict)]
        # No global latest clock can stand in for heterogeneous native history.
        return clocks[0] if len(clocks) == len(value) and all(c == clocks[0] for c in clocks) else None
    return None


def _production_collection(name, fact):
    if name == "divergence_log":
        return fact if isinstance(fact, list) else None
    if not isinstance(fact, dict):
        return None
    if name == "baskets":
        nested = fact.get("theme_intel")
        return nested.get("themes") if isinstance(nested, dict) else None
    key = {"foresight_cascade": "themes", "radar_enriched": "flags", "radar": "hypotheses",
           "subsector_rotation": "themes", "narrative_emergence": "narratives",
           "narrative_emergence_cn": "narratives"}[name]
    return fact.get(key)


def _production_scope(name, subject, cfg, fact):
    local = subject["kind"] == "local_theme"
    basket = subject["basket"]
    if name.startswith("narrative_emergence"):
        region = "cn" if name.endswith("_cn") else "us"
        wanted = identity.market_for_suite(basket["suite"]) if basket else "us"
        if wanted != region or not isinstance(fact, dict) or str(fact.get("region", "")).lower() != region:
            return "UNSUPPORTED", "EXACT_NARRATIVE_MARKET_SOURCE_REQUIRED", []
        return "REGIONAL_CONTEXT_ONLY", "REGIONAL_SOURCE_NOT_FULL_CLUSTER_OR_SUBJECT_ASSOCIATION", [region]
    if local:
        if name in ("baskets", "radar", "radar_enriched"):
            if basket is not None and basket["suite"] == "baskets":
                return "EXACT_OWNER_SCOPE", "EXACT_LOCAL_BASKET_AND_US_SUITE", [basket["basket_id"]]
            return "UNSUPPORTED", "EXACT_MARKET_SPECIALIST_ARTIFACT_UNAVAILABLE", []
        return "UNSUPPORTED", "EXACT_LOCAL_" + name.upper() + "_OWNER_SCOPE_UNAVAILABLE", []
    if name == "foresight_cascade":
        return "EXACT_OWNER_SCOPE", "CANONICAL_CROSSWALK_FORESIGHT_ID", [cfg["foresight_id"]] if cfg.get("foresight_id") else []
    if name in ("baskets", "radar", "radar_enriched"):
        return "EXACT_OWNER_SCOPE", "CANONICAL_CONFIGURED_BASKET_RECORDS_NO_AGGREGATION", list(cfg.get("basket_ids", []))
    if name == "subsector_rotation":
        return "EXACT_OWNER_SCOPE", "CANONICAL_CONFIGURED_SUBSECTOR_KEYS_NO_AGGREGATION", list(cfg.get("subsector_keys", []))
    return "EXACT_OWNER_SCOPE", "CANONICAL_NATIVE_THEME_HISTORY_NO_INVENTED_KNOWLEDGE", [cfg["id"]]


def _production_record(name, row, position, fact, source, effective_at, known_at):
    from engine.theme_graph import theme_state_production as production
    root_fact = fact if isinstance(fact, dict) else {}
    def declared_field(field):
        if field in row:
            return production.value_slot(row[field], declared=True)
        return production.value_slot(root_fact.get(field), declared=field in root_fact)
    effective = next((row[key] for key in ("as_of", "asof") if key in row), _native_source_effective(name, fact))
    clocks = {"effective_at": effective}
    for key in ("known_at", "available_at", "recorded_at"):
        clocks[key] = row.get(key, root_fact.get(key))
    clocks["emitted_at"] = row.get("generated_at", row.get("emitted_at",
                              root_fact.get("generated_at", root_fact.get("emitted_at"))))
    declared = {key: key in row or key in root_fact for key in ("known_at", "available_at", "recorded_at")}
    declared["effective_at"] = any(key in row or key in root_fact for key in ("as_of", "asof"))
    declared["emitted_at"] = any(key in row or key in root_fact for key in ("generated_at", "emitted_at"))
    clocks = {key: production.clock_slot(value, declared=declared[key]) for key, value in clocks.items()}
    reasons = production.native_clock_reasons(clocks, effective_at=effective_at, known_at=known_at)
    native_key = row.get({"foresight_cascade": "theme", "baskets": "id",
        "radar_enriched": "basket", "radar": "subject", "subsector_rotation": "theme",
        "divergence_log": "theme", "narrative_emergence": "signature",
        "narrative_emergence_cn": "signature"}[name])
    return {"record_id": production.canonical_sha256({"source": source["sha256"], "position": position, "value": row}),
        "source_position": position, "native_key": native_key if isinstance(native_key, str) and native_key else None,
        "value": copy.deepcopy(row), "native_clocks": clocks,
        "units": declared_field("units"), "period": declared_field("period"), "window": declared_field("window"),
        "scenario": declared_field("scenario"),
        "compatibility_aliases": {"accel_z": copy.deepcopy(row.get("z_accel"))} if name == "subsector_rotation" else {},
        "usable_at_query": not reasons, "reason_codes": sorted(set(reasons))}


def _production_leg(name, subject, cfg, snapshot, qualified, owner_subject):
    from engine.theme_graph import theme_state_production as production
    source = snapshot["sources"][name]
    source_ref = {key: source[key] for key in ("path", "sha256", "availability", "null_reason")}
    observed = _source_observation(source, snapshot["observed_at"], snapshot["query"]["known_at"])
    fact = observed["fact"]
    state, basis, selectors = _production_scope(name, subject, cfg, fact)
    rows = _production_collection(name, fact)
    records, conflicts = [], []
    identity_key = {"foresight_cascade": "theme", "baskets": "id", "radar_enriched": "basket",
        "radar": "subject", "subsector_rotation": "theme", "divergence_log": "theme",
        "narrative_emergence": "signature", "narrative_emergence_cn": "signature"}[name]
    if isinstance(rows, list) and state != "UNSUPPORTED":
        for position, row in enumerate(rows):
            if not isinstance(row, dict):
                conflicts.append({"reason": "NATIVE_RECORD_MALFORMED", "position": position, "value": row})
                continue
            if state == "REGIONAL_CONTEXT_ONLY" or row.get(identity_key) in selectors:
                records.append(_production_record(name, row, position, fact, source, **snapshot["query"]))
        if name != "divergence_log":
            keys = [record["native_key"] for record in records]
            for key in dict.fromkeys(keys):
                if key is not None and keys.count(key) > 1:
                    conflicts.append({"reason": "DUPLICATE_NATIVE_IDENTITY", "native_key": key,
                                      "record_ids": [r["record_id"] for r in records if r["native_key"] == key]})
    if name == "divergence_log":
        conflicts.extend(theme_state_production.divergence_conflicts(records))
    receipt = qualified.get(name)
    receipt_ref = ({key: copy.deepcopy(receipt[key]) for key in ("owner", "schema", "generation_id", "sha256",
        "availability", "effective_at", "known_at", "available_at", "recorded_at",
        "subject_id", "query", "graph_generation_id")} if receipt else None)
    rights_read = copy.deepcopy(snapshot.get("specialist_rights", {}).get(name) or {
        "availability": "UNAVAILABLE", "null_reason": "CAPTURED_SPECIALIST_RIGHTS_READ_UNAVAILABLE", "family": None})
    # Existing source-ref owner table cannot currently bind these site specialist
    # paths to a provider/purpose grant. A node's vocabulary family is not a grant.
    rights_reason = ("SOURCE_FAMILY_PURPOSE_BINDING_UNAVAILABLE" if not rights_read.get("family")
                     else rights_read.get("null_reason") or "SOURCE_PURPOSE_RECEIPT_UNAVAILABLE")
    empty_admitted = (receipt is not None and receipt["availability"] == "VALID_EMPTY"
                      and isinstance(rows, list) and not rows and state != "UNSUPPORTED")
    presence = "AVAILABLE" if records else "VALID_EMPTY" if empty_admitted else "UNAVAILABLE"
    reason = None if records or empty_admitted else basis if state == "UNSUPPORTED" else "SUBJECT_RECORD_OR_COMPLETE_POPULATION_UNAVAILABLE"
    if observed["availability"] == "INVALID" or (fact is not None and not isinstance(rows, list)):
        presence, reason = "INVALID", "SPECIALIST_SOURCE_SHAPE_INVALID"
    elif source["availability"] == "UNAVAILABLE":
        presence, reason = "UNAVAILABLE", source["null_reason"]
    freshness = "UNKNOWN"
    if records:
        if any(set(r["reason_codes"]) & {"NATIVE_SOURCE_CLOCK_AFTER_CUTOFF", "NATIVE_SOURCE_EFFECTIVE_AFTER_CUTOFF"} for r in records):
            freshness = "FUTURE"
        elif any(r["native_clocks"]["effective_at"]["grain"] in ("DATE", "INSTANT") and
                 (_clock(snapshot["query"]["known_at"], precise=True) - legacy._parse_asof(r["native_clocks"]["effective_at"]["value"])).days >= legacy._STALE_DAYS for r in records):
            freshness = "STALE"
        elif all(r["native_clocks"]["effective_at"]["grain"] == "INSTANT" for r in records):
            freshness = "FRESH"
        if not any(r["usable_at_query"] for r in records):
            presence, reason = "UNAVAILABLE", "NATIVE_SOURCE_CLOCK_USE_REFUSED"
    qstatus = "SOURCE_QUALIFIED_RIGHTS_UNAVAILABLE" if receipt is not None else "UNQUALIFIED"
    overlap = None
    if name.startswith("narrative_emergence") and subject["basket"] is not None:
        wanted = "narrative_emergence_cn" if identity.market_for_suite(subject["basket"]["suite"]) == "cn" else "narrative_emergence"
        if name == wanted:
            overlap = copy.deepcopy(owner_subject["observations"].get("forming_narrative_recommended_ticker_overlap"))
    return {"source_ref": source_ref, "presence": presence, "freshness": freshness,
        "scope": {"status": state, "basis": basis, "selectors": selectors},
        "records": records, "conflicts": conflicts,
        "coverage": {"declared": 0 if empty_admitted else None, "observed": len(records),
                     "completeness": "QUALIFIED_COMPLETE" if empty_admitted else "UNPROVEN",
                     "basis": "EXPLICIT_OWNER_VALID_EMPTY" if empty_admitted else "RETAINED_SCOPED_RECORDS_NOT_DECLARED_POPULATION"},
        "qualification": {"status": qstatus, "source_receipt": receipt_ref,
            "rights": {"status": "UNAVAILABLE", "family": rights_read.get("family"), "purpose": "research_internal",
                       "native_read": rights_read, "null_reason": rights_reason},
            "historical_knowability": "OWNER_RECEIPT_BOUND" if receipt else "UNPROVEN",
            "identity_membership": "OWNER_RECEIPT_BOUND" if overlap is not None else "UNPROVEN" if name.startswith("narrative") else "NOT_APPLICABLE"},
        "null_reason": reason, "freshness_policy": "incumbent-source-5-calendar-days",
        "observed_at": snapshot["observed_at"], "overlap_observation": overlap}


def _production_from_bundle(bundle, *, generated_at, previous=None, correction_reason=None):
    from engine.theme_graph import theme_state_production as production
    snapshot = bundle.snapshot()
    diagnostic = compose_from_owner_bundle(bundle, generated_at=generated_at)
    graph = diagnostic["state"]
    graph_subjects = {row["node_id"]: row for row in graph["subjects"]}
    configs = {identity.theme_node_id(cfg["id"]): cfg for cfg in snapshot["crosswalk"]["themes"]}
    subjects = []
    ordered_nodes = [identity.theme_node_id(cfg["id"]) for cfg in snapshot["crosswalk"]["themes"]]
    ordered_nodes += [node_id for node_id, row in snapshot["subjects"].items() if row["kind"] == "local_theme"]
    for node_id in ordered_nodes:
        native = snapshot["subjects"][node_id]
        _, receipts = _qualified_receipts(native, node_id, snapshot)
        owner_subject = graph_subjects[node_id]
        legs = {name: _production_leg(name, native, configs.get(node_id), snapshot, receipts, owner_subject)
                for name in SOURCE_PATHS if name != "theme_crosswalk"}
        subjects.append({**{key: owner_subject[key] for key in
                            ("node_id", "kind", "name_en", "name_zh", "source_family", "native_id")},
            "canonical_mapping": copy.deepcopy(owner_subject["mapping"]), "eligibility": "NOT_QUALIFIED",
            "legs": legs, "aggregation": None, "reason_codes": ["D2E_UNSEALED", "SOURCE_PURPOSE_QUALIFICATION_REQUIRED"]})
    projection, inventory, predecessor_status = _compatibility_projection(graph, snapshot)
    refs = snapshot.get("producer_refs")
    if refs is None:
        raise ValueError("captured production implementation/contract revision unavailable")
    return production.compose_state(subjects=subjects, diagnostic_graph_state=graph,
        source_refs={name: {key: snapshot["sources"][name][key] for key in
                     ("path", "sha256", "availability", "null_reason")}
                     for name in SOURCE_PATHS if name != "theme_crosswalk"},
        bundle_ref={"schema": BUNDLE_SCHEMA, "sha256": bundle.bundle_sha256,
                    "observed_at": snapshot["observed_at"], "graph_capture_id": snapshot["graph_capture_id"],
                    "native_graph_generation_id": snapshot["native_graph_generation_id"],
                    "native_generation_null_reason": "NATIVE_OWNER_GENERATION_NOT_PROVEN"},
        producer_refs=refs, compatibility={"schema": legacy.SCHEMA,
            "sha256": production.canonical_sha256(projection), "projection": projection,
            "predecessor_optional_inventory": inventory, "predecessor_read": predecessor_status,
            "narrative_disposition": "INTERPRETATION_HELD"}, **snapshot["query"], generated_at=generated_at,
        previous=previous, correction_reason=correction_reason), diagnostic


def compare_production_shadow(state, bundle):
    from engine.theme_graph import theme_state_production as production
    production.validate_state(state)
    expected, diagnostic = _production_from_bundle(bundle, generated_at=state["generated_at"])
    lineage = {"generation_id", "state_sha256", "correction"}
    if _json({k: v for k, v in state.items() if k not in lineage}) != _json({k: v for k, v in expected.items() if k not in lineage}):
        raise ValueError("production differs from deterministic captured owner assembly")
    result = copy.deepcopy(diagnostic["shadow"])
    result.update(production_state_sha256=state["state_sha256"],
        successor_surface={row["node_id"]: copy.deepcopy(row) for row in state["subjects"]},
        production_qualification_dispositions={row["node_id"]: {name: copy.deepcopy(leg["qualification"])
            for name, leg in row["legs"].items()} for row in state["subjects"]},
        production_binding="EXACT_SAME_IMMUTABLE_BUNDLE_NO_SECOND_AUTHORITY",
        production_correction_binding="VALIDATED_PRIOR_REF_NOT_PREVIOUS_ARTIFACT_RECONSTRUCTION")
    return result


def compose_production_from_owner_bundle(bundle, *, generated_at, previous=None, correction_reason=None):
    state, diagnostic = _production_from_bundle(bundle, generated_at=generated_at, previous=previous,
                                                correction_reason=correction_reason)
    return {"state": state, "legacy_baseline": diagnostic["legacy_baseline"],
        "legacy_candidate": copy.deepcopy(state["compatibility"]["projection"]),
        "shadow": compare_production_shadow(state, bundle), "bundle_sha256": bundle.bundle_sha256,
        "publication_allowed": False,
        "qualification_limits": ["ACTUAL_SPECIALIST_SOURCE_FAMILY_AND_CURRENT_PURPOSE_BINDING_UNAVAILABLE",
                                 "AUTHENTICATED_PRODUCTION_OWNER_RESOLVER_NOT_WIRED", "S2_S3_NOT_ADMITTED"]}
