"""Real owner-read capability for the existing ThemeState adapter interface.

``engine.neuralweb.theme_state_adapter.capture_owner_bundle(owner_readers=...)``
calls ``read_state_qualification(node_id=, query=, graph_capture_id=, native_reads=,
source_sha256=)`` and admits the result only through its own ``_qualified_receipts``
checks. This module supplies that capability from the EXISTING owners only:

* membership: ``engine.basket_membership_pit`` (``members_asof`` plus the strict
  ``read_history``), re-read exactly as the adapter's ``_native_members`` does;
* identity: ``engine.theme_graph.identity_resolution.resolve_graph_node_identity``
  (read-only, historical mode at the query's effective date);
* rights: ``engine.theme_graph.rights`` at the captured registry bytes, re-read
  exactly as the adapter's ``_bound_rights_read`` does.

A role is emitted ONLY when this reader's own re-read equals the captured native
read for that role; the receipt binds ``native_owner_read_sha256`` to the captured
read. Any disagreement, exception, unresolved or ambiguous identity, non-PIT or
empty membership omits that role; it is never fabricated. Eligibility is never
emitted (the D2E owner holds it and the adapter refuses it), nor are ontology,
narrative or other specialist source receipts.

Production custody/authentication of this capability is owed (adapter docstring);
this reader is an owner-read consistency capability, not an authentication or
rights grant.

Receipt clocks are the owners' own declared clocks, never the read instant:
membership = the PIT snapshot date (date-only, so same-day knowledge stays
unproven); identity = the security master ``generated_at``; rights = the
registry's declared ``updated`` revision date. The downstream composer refuses any
clock its query cannot prove.
"""
from __future__ import annotations

import base64
import copy
from pathlib import Path
from typing import Any, Mapping

import yaml

from engine.theme_graph import theme_state

MEMBERSHIP_OWNER = "engine.basket_membership_pit"
IDENTITY_OWNER = "engine.theme_graph.identity_resolution"
RIGHTS_OWNER = "engine.theme_graph.rights"
RECEIPT_SCHEMA = "gmi.theme_state_owner_read/v1"
MEMBERSHIP_SUITES = ("baskets", "baskets_china", "baskets_china_ths")
_WALL_CLOCK_FIELDS = frozenset({"computed_at"})


def _adapter():
    # Upward import by design: the adapter owns the native-read helpers this reader
    # must reproduce byte-for-byte; reusing them is what keeps the semantics equal.
    from engine.neuralweb import theme_state_adapter
    return theme_state_adapter


def _generation(prefix: str, source_sha256: Mapping[str, Any], keys) -> str:
    # An absent optional source (None) is bound as absent, never skipped; at least
    # one source must carry bytes or the owner generation is unproven.
    bound = {key: source_sha256.get(key) for key in sorted(keys)}
    if (not bound or any(value is not None and not isinstance(value, str) for value in bound.values())
            or not any(isinstance(value, str) for value in bound.values())):
        raise ValueError("owner source bytes unavailable")
    return prefix + ":" + theme_state.canonical_sha256(bound)


def _without_wall_clock(reads: Mapping[str, Any]) -> dict:
    stripped = {}
    for node, read in reads.items():
        read = copy.deepcopy(read)
        if isinstance(read.get("value"), dict):
            for field in _WALL_CLOCK_FIELDS:
                read["value"].pop(field, None)
        stripped[node] = read
    return stripped


class StateQualificationReader:
    """Owner-read consistency capability for ``capture_owner_bundle``.

    Production custody/authentication of this capability is owed (adapter docstring);
    this reader is an owner-read consistency capability, not an authentication or
    rights grant.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self._identity_memo: dict[tuple, bool] = {}

    # -- shared -------------------------------------------------------------
    def _receipt(self, owner: str, generation_id: str, *, node_id: str, query: Mapping[str, Any],
                 graph_capture_id: str, effective_at: str, known_at: str, payload: dict) -> dict:
        return {"owner": owner, "schema": RECEIPT_SCHEMA, "generation_id": generation_id,
                "graph_generation_id": graph_capture_id, "subject_id": node_id,
                "query": copy.deepcopy(dict(query)), "effective_at": effective_at,
                "available_at": known_at, "known_at": known_at, "recorded_at": known_at,
                "availability": "AVAILABLE", "payload": payload, "sha256": theme_state.canonical_sha256(payload)}

    @staticmethod
    def _pit_membership(native: Mapping[str, Any]) -> dict | None:
        value = native.get("value") if native.get("availability") == "AVAILABLE" else None
        if (not isinstance(value, dict) or value.get("pit") is not True
                or not isinstance(value.get("members"), list) or not value["members"]
                or not isinstance(value.get("snapshot_date"), str)
                or not isinstance(value.get("basket_id"), str) or value.get("suite") not in MEMBERSHIP_SUITES):
            return None
        return value

    # -- identity -----------------------------------------------------------
    def _identity_consistent(self, graph_capture_id: str, query: Mapping[str, Any],
                             captured: Mapping[str, Any]) -> bool:
        key = (graph_capture_id, query["effective_at"], theme_state.canonical_sha256(captured))
        if key not in self._identity_memo:
            adapter = _adapter()
            from engine.theme_graph import identity_resolution
            reread = {node: adapter._attempt(identity_resolution.resolve_graph_node_identity, node,
                                             asof=query["effective_at"][:10])
                      for node in sorted(captured)}
            self._identity_memo[key] = _without_wall_clock(reread) == _without_wall_clock(captured)
        return self._identity_memo[key]

    def _member_identities(self, members, captured: Mapping[str, Any]) -> tuple[dict, str] | None:
        from engine.theme_graph import identity_resolution
        expected, clocks = {}, set()
        for ticker in members:
            matches = [(nid, read["value"]) for nid, read in captured.items()
                       if read.get("availability") == "AVAILABLE"
                       and identity_resolution._best_effort_symbol(nid) == ticker]
            if (len(matches) != 1 or not isinstance(matches[0][1], dict)
                    or matches[0][1].get("resolution_state") != "RESOLVED" or not matches[0][1].get("security_id")):
                return None
            nid, row = matches[0]
            expected[ticker] = {"node_id": nid, "security_id": row["security_id"], "issuer_id": row.get("issuer_id")}
            clocks.add(row.get("master_generated_at"))
        if len(clocks) != 1 or not isinstance(next(iter(clocks)), str):
            return None
        return expected, next(iter(clocks))

    # -- rights -------------------------------------------------------------
    def _rights(self, node_id: str, native: Mapping[str, Any], source_sha256: Mapping[str, Any]):
        adapter = _adapter()
        source = adapter._source(self.root, adapter._input_paths(self.root)["rights_registry"])
        if source["availability"] != "AVAILABLE" or source["sha256"] != source_sha256.get("rights_registry"):
            return None
        # Canonical price mappings do not establish a semantic member population.
        # This reader qualifies source-local membership only; no canonical rights
        # are inferred from the house-authored crosswalk.
        reread = adapter._bound_rights_read(self.root, source, adapter.rights.family_for_node_id(node_id))
        licensing = native.get("licensing")
        if (adapter._json(reread) != adapter._json(native) or native.get("availability") != "AVAILABLE"
                or native.get("current_bytes_bound") is not True or not native.get("known_family")
                or native.get("registry_sha256") != source["sha256"]
                or not isinstance(licensing, (list, tuple)) or len(licensing) != 3 or licensing[0] is not True):
            return None
        registry = yaml.safe_load(base64.b64decode(source["bytes_b64"]).decode("utf-8"))
        updated = registry.get("updated") if isinstance(registry, dict) else None
        updated = updated.isoformat() if hasattr(updated, "isoformat") else updated
        if not isinstance(updated, str):
            return None
        theme_state._clock(updated)
        return updated, source["sha256"]

    # -- interface ----------------------------------------------------------
    def read_state_qualification(self, *, node_id: str, query: Mapping[str, Any], graph_capture_id: str,
                                 native_reads: Mapping[str, Any], source_sha256: Mapping[str, Any]) -> dict | None:
        roles: dict[str, dict] = {}
        common = {"node_id": node_id, "query": query, "graph_capture_id": graph_capture_id}
        membership = self._pit_membership(native_reads.get("membership") or {})
        if membership is not None:
            try:
                reread = _adapter()._native_members(membership["basket_id"], membership["suite"], query["effective_at"])
                if reread != native_reads["membership"]:
                    membership = None
            except Exception:  # noqa: BLE001 — any owner failure omits the role
                membership = None
        identities = None
        if membership is not None:
            try:
                captured = native_reads["identity"]
                if isinstance(captured, dict) and self._identity_consistent(graph_capture_id, query, captured):
                    identities = self._member_identities(membership["members"], captured)
                if identities is not None:
                    expected, clock = identities
                    payload = {"status": "RESOLVED", "member_identities": expected,
                               "native_owner_read_sha256": theme_state.canonical_sha256(captured)}
                    roles["identity"] = self._receipt(
                        IDENTITY_OWNER, _generation("identity-owner", source_sha256,
                                                    [k for k in source_sha256 if k.startswith("identity/")]),
                        effective_at=query["effective_at"][:10], known_at=clock, payload=payload, **common)
            except Exception:  # noqa: BLE001
                roles.pop("identity", None)
                identities = None
            try:
                ids = identities[0] if identities is not None else {}
                members = [{"ticker": t, "security_id": ids.get(t, {}).get("security_id"),
                            "issuer_id": ids.get(t, {}).get("issuer_id")} for t in membership["members"]]
                count = len(members)
                payload = {"status": "AVAILABLE", "basket_id": membership["basket_id"], "members": members,
                           "declared_count": count, "eligible_count": count, "observed_count": count,
                           "basis": "pit_owner_snapshot_date_only_knowledge", "era": "OBSERVED",
                           "native_owner_read_sha256": theme_state.canonical_sha256(native_reads["membership"])}
                # One owner generation per bundle (the adapter refuses mixed generations
                # for one owner), so the PIT generation binds every suite's sources.
                keys = [k for k in source_sha256 if k.split("/", 1)[0] in MEMBERSHIP_SUITES and "/" in k]
                roles["membership"] = self._receipt(
                    MEMBERSHIP_OWNER, _generation("pit-owner", source_sha256, keys),
                    effective_at=membership["snapshot_date"], known_at=membership["snapshot_date"],
                    payload=payload, **common)
            except Exception:  # noqa: BLE001
                roles.pop("membership", None)
                roles.pop("identity", None)
        try:
            bound = self._rights(node_id, native_reads.get("rights") or {}, source_sha256)
            if bound is not None:
                updated, registry_sha = bound
                payload = {"allowed": True, "purpose": "research_internal", "revision": "theme_sources:" + updated,
                           "registry_sha256": registry_sha,
                           "native_owner_read_sha256": theme_state.canonical_sha256(native_reads["rights"])}
                roles["rights"] = self._receipt(
                    RIGHTS_OWNER, _generation("rights-registry", source_sha256, ["rights_registry"]),
                    effective_at=updated, known_at=updated, payload=payload, **common)
        except Exception:  # noqa: BLE001
            roles.pop("rights", None)
        if not roles:
            return None
        return {"owner_receipts": roles, "source_receipts": {}}
