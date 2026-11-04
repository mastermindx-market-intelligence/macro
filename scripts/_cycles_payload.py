"""Split a cycle-map data payload into a light core + a heavy series chunk.

The cycle pages (sector_cycles / country_cycles / sector_cycles_china +
their two _central hubs) ship one multi-MB ``window.SECTOR_CYCLES`` blob whose
default first paint (sectors family, oscillator mode) needs only ~15% of it.
``split_cycles_payload`` peels the heavy per-entity arrays into a second file that
the page hydrates AFTER first paint (see templates/sector_cycles.js _scheduleSeries):

  * ``price``   — stripped from EVERY entity (only the sparklines / price-mode chart
                  need it, and the default view is oscillator mode);
  * ``osc`` + ``turns`` — stripped from NON-``sectors`` families (baskets / nasdaq /
                  russell / country baskets); the ``sectors`` family keeps both so the
                  default sectors-osc paint and the sector mini-cyc board work with core
                  alone;
  * ``fx`` + ``usd_record`` — stripped from the ``sectors`` family when present (the
                  country page's 24 markets carry a ~1.2MB currency card consumed only by
                  the focus panel).

The split is LOSSLESS per entity id: ``core`` + ``series`` recombine to the input
(``Object.assign(core_entity, series[id])`` on the client). The input dict is NEVER
mutated — the full model is still written to the features json unchanged.

``FAMILY_KEYS`` names the entity lists to process; only those present are touched.
Entities are keyed by their ``id`` field; an entity missing an ``id`` is left whole in
core and contributes nothing to series (it can still render from core).
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, Tuple

# entity lists this splitter knows how to peel; only those present in `data` are touched
FAMILY_KEYS = ("sectors", "baskets", "nasdaq", "russell")

# heavy arrays pulled into the series chunk, by family class
_HEAVY_ALL = ("price",)                              # every family
_HEAVY_NON_SECTORS = ("osc", "turns")                # baskets / nasdaq / russell
# only the sectors family: the country FX card, plus rs_history — the 252-point
# reconstructed RS trail engine.sector_cycles emits per sector, hydrated after first paint
_HEAVY_SECTORS = ("fx", "usd_record", "rs_history")


def _heavy_keys_for(family: str) -> tuple[str, ...]:
    """Which entity keys move to the series chunk for `family`."""
    if family == "sectors":
        return _HEAVY_ALL + _HEAVY_SECTORS
    return _HEAVY_ALL + _HEAVY_NON_SECTORS


def split_cycles_payload(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split `data` into ``(core, series)`` without mutating `data`.

    ``core`` is a deep copy of `data` with the heavy per-entity arrays removed;
    ``series`` maps each entity id -> the removed arrays (only the keys actually
    present on that entity). ``series`` is keyed globally across families (ids are
    unique across the one shared chart space), matching the client's ``byId`` map.
    """
    core = copy.deepcopy(data)
    series: Dict[str, Any] = {}

    for family in FAMILY_KEYS:
        entities = core.get(family)
        if not isinstance(entities, list):
            continue
        heavy = _heavy_keys_for(family)
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            eid = ent.get("id")
            if eid is None:
                continue                      # no id -> can't rehydrate; leave whole in core
            moved: Dict[str, Any] = {}
            for k in heavy:
                if k in ent:
                    moved[k] = ent.pop(k)
            if moved:
                series[eid] = moved
    return core, series


def publication_scripts(data: Dict[str, Any], narr: dict, dna: dict, *, core_extra=None, sources=None) -> dict[str, str]:
    """Seal the existing four split files as one content-addressed publication.

    Digests cover exact UTF-8 JSON strings, so a browser never has to reproduce
    Python float serialization. The generated core remains the native object;
    its manifest retains the original bytes for verification before hydration.
    Nothing writes a forward log, fetches data, or creates another publication
    store. Callers retain the existing build and atomic-release owners.
    """
    from engine.sector_generation_guard import cycle_spine_identity, parse_session

    # All families share the receiver's identity map. A collision must fail
    # publication instead of assigning one family's history to another.
    seen = set()
    for family in FAMILY_KEYS:
        rows = data.get(family, [])
        if not isinstance(rows, list):
            raise ValueError("cycle publication requires entity lists")
        for row in rows:
            eid = row.get("id") if isinstance(row, dict) else None
            if not isinstance(eid, str) or not eid or eid in seen:
                raise ValueError("cycle publication requires unique entity ids")
            seen.add(eid)
    core, series = split_cycles_payload(data)
    core.setdefault("meta", {}).pop("publication", None)
    if core_extra:
        core.update(core_extra)
    session = core["meta"].get("asOf")
    parsed_session = parse_session(session)
    if not isinstance(session, str) or not parsed_session or session != parsed_session.isoformat():
        raise ValueError("cycle publication requires a source session")
    parts = {"core": core, "series": series, "narr": narr, "dna": dna}
    raw = {kind: json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) for kind, value in parts.items()}
    manifest = {
        "schema": "sector_cycles.publication.v1",
        "region": core["meta"].get("region") or "us", "as_of": session,
        "namespace": "sector_cycles:" + str(core["meta"].get("region") or "us"),
        "benchmark": core["meta"].get("benchmark"),
        "basis": "current_reconstruction", "sector_spine": cycle_spine_identity(data),
        "sources": sources or {"narr": {"status": "unverified"}, "dna": {"status": "unverified"}},
        "payload_sha256": {kind: hashlib.sha256(value.encode("utf-8")).hexdigest()
                           for kind, value in raw.items()},
    }
    identity = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    manifest["id"] = "cycp1-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
    manifest["manifest_json"] = identity
    # JSON escaping keeps strings literal JS data, including Unicode separators.
    literal = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    scripts = {"core": "(function(){var p=" + literal(manifest) + ";p.payload_json=" + literal(raw["core"]) +
               ";window.SECTOR_CYCLES_PUBLICATION=p;window.SECTOR_CYCLES=JSON.parse(p.payload_json);})();\n"}
    globals_ = {"series": "SECTOR_CYCLES_SERIES", "narr": "SECTOR_NARR", "dna": "SECTOR_DNA"}
    for kind, global_ in globals_.items():
        envelope = {"schema": "sector_cycles.part.v1", "publication_id": manifest["id"],
                    "namespace": manifest["namespace"],
                    "kind": kind, "sha256": manifest["payload_sha256"][kind], "payload_json": raw[kind]}
        scripts[kind] = ("(function(){var p=" + literal(envelope) + ";window." + global_ +
                         "_PUBLICATION=p;window." + global_ + "=JSON.parse(p.payload_json);})();\n")
    return scripts
