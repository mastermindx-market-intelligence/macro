"""Private read projection of research cases already published by Entry Radar.

No detector, case composition, acquisition, lifecycle change, spool or store.
The snapshot hash binds this read's bytes; it does not authenticate a producer
or prove that a snapshot is current. The native pass clock and health travel.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
import stat

SCHEMA = "ontology_radar_research.v1"
MAX_BYTES = 16 * 1024 * 1024
MAX_EPISODES = 8192
MAX_SELECTED = 64
AUTHORITY = dict.fromkeys(("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry"), False)
_HEX = re.compile(r"[a-f0-9]{64}")


class ResearchReadUnavailable(ValueError):
    """Closed refusal tokens only; no path or native content in errors."""


def _require(ok: bool, code: str = "radar_research_unavailable") -> None:
    if not ok:
        raise ResearchReadUnavailable(code)


def _instant(value) -> datetime:
    _require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value) is not None)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        raise ResearchReadUnavailable("radar_research_unavailable") from None


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _read(directory: Path) -> tuple[bytes, datetime]:
    try:
        fd = os.open(Path(directory) / "entry_radar.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_BYTES)
            chunks, remaining = [], MAX_BYTES + 1
            while remaining:
                chunk = os.read(fd, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(fd)
            raw = b"".join(chunks)
            signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            _require(signature(before) == signature(after) and len(raw) == before.st_size)
            return raw, datetime.now(timezone.utc)
        finally:
            os.close(fd)
    except OSError:
        raise ResearchReadUnavailable("radar_research_unavailable") from None


def _episode(row):
    # Reuse the owner contract; extensions in the published view are not
    # imported into the immutable lifecycle record.
    from engine.entry_radar.live_ledger import EPISODE_FIELDS, LiveEpisode
    try:
        return LiveEpisode.from_dict({k: row[k] for k in EPISODE_FIELDS if k in row})
    except Exception:
        raise ResearchReadUnavailable("radar_episode_invalid") from None


@lru_cache(maxsize=1)
def _metadata_validator():
    from jsonschema import Draft202012Validator, FormatChecker
    from lib import evidence_foundation as ef
    reference_schema = json.loads(ef.SCHEMA_PATH.read_text())
    reference_fields = ("reference_id", "owner_store", "native_digest", "clocks",
                        "rights", "freshness", "provenance")
    metadata_schema = {"type": "object", "additionalProperties": False,
                       "required": list(reference_fields),
                       "properties": {k: reference_schema["properties"][k] for k in reference_fields},
                       "$defs": reference_schema["$defs"]}
    return Draft202012Validator(metadata_schema, format_checker=FormatChecker())


def _projection(value, episode, *, schema="entry_radar.research_case/v1"):
    """Validate the published projection binding, never invent a missing case."""
    _require(type(value) is dict and value.get("schema") == schema)
    binding, ref = value.get("episode_binding"), value.get("case_ref")
    _require(binding == {"episode_id": episode.episode_id, "candidate_at": episode.candidate_at,
                         "canonical_sha256": sha256(episode.canonical.encode()).hexdigest()})
    _require(type(ref) is dict and set(ref) == {"schema", "case_id", "sha256"}
             and ref["schema"] == "opportunity_case.research.v1"
             and type(ref["case_id"]) is str and re.fullmatch(r"opc_[a-f0-9]{64}", ref["case_id"]) is not None
             and type(ref["sha256"]) is str and _HEX.fullmatch(ref["sha256"]) is not None)
    _require(value.get("episode_id") == episode.episode_id and value.get("authority") == AUTHORITY
             and all(v is False for v in value["authority"].values()))
    evidence = value.get("evidence_refs")
    _require(type(evidence) is list and 0 < len(evidence) <= 64)
    # Reuse K1's recursively closed metadata types. A pointer-only flag alone
    # cannot authorize arbitrary nested fields from a published artifact.
    metadata = _metadata_validator()
    seen = set()
    for item in evidence:
        _require(type(item) is dict and metadata.is_valid(item))
        rid = item["reference_id"]
        _require(type(rid) is str and rid not in seen)
        seen.add(rid)
    _require(value.get("research_state") in {"partial", "complete", "unavailable", "abstained"}
             and value.get("evidence_binding_state") in {
                 "exact_owner_native_event", "exact_native_subject", "identity_unresolved"})
    keys = ("schema", "case_ref", "episode_binding", "episode_id", "research_state",
            "evidence_binding_state", "evidence_refs", "authority")
    _require(all(k in value for k in keys))
    result = {k: value[k] for k in keys}
    # The reader exposes typed context states, never the source's arbitrarily
    # nested context, owner slots, narrative or control fields.
    for key in ("company_context", "transmission"):
        context = value.get(key)
        _require(type(context) is dict and context.get("state") in {"available", "partial", "unavailable"})
        result[key] = {"state": context["state"]}
    _require(len(json.dumps(result, allow_nan=False).encode()) <= 192 * 1024)
    return result


def _context_projection(value, episode, captured):
    """Read a retrospective context without promoting it to a live case.

    Reuse native pointer/binding validators, then emit only closed metadata and
    the qualified scalar observation. No full case or identity snapshot leaves.
    """
    from lib.evidence_foundation import canonical_json_bytes
    from engine.entry_radar.earnings_context import _closed_binding, LIMITATIONS
    from engine.company_intelligence.research_generation import validate_generation_pointer
    from engine.company_intelligence.events import parse_canonical_event_id, FiscalPeriod
    from engine.company_intelligence.opportunity_qualification import _safe_object_id
    try:
        result = _projection(value, episode, schema="entry_radar.research_context/v1")
        _require(value.get("sha256") == sha256(canonical_json_bytes(
            {k:v for k,v in value.items() if k != "sha256"})).hexdigest())
        binding = _closed_binding(value["candidate_context_binding"])
        _require(binding["sha256"] == sha256(canonical_json_bytes(
            {k:v for k,v in binding.items() if k != "sha256"})).hexdigest())
        pointer = validate_generation_pointer(value["source_generation"])
        native, subject = value["native_earnings_identity"], value["research_subject"]
        _require(type(native) is dict and set(native) == {"event_id", "generation_id"}
                 and type(subject) is dict and set(subject) == {"key_type", "key"}
                 and subject["key_type"] == "cik" and re.fullmatch(r"[0-9]{10}", subject["key"]) is not None)
        company, event_period, kind = parse_canonical_event_id(native["event_id"])
        fiscal = FiscalPeriod(**value["fiscal_period"])
        _require(fiscal.to_payload() == value["fiscal_period"]
                 and (fiscal.year, fiscal.quarter) == (event_period.year, event_period.quarter))
        _require(company == "cik:" + subject["key"] and kind == "earnings_results"
                 and native["generation_id"] == pointer["generation_id"])
        _require(binding["workspace_native_identity"] == native
                 and binding["episode_id"] == episode.episode_id and binding["ticker"] == episode.ticker
                 and binding["episode_canonical_sha256"] == result["episode_binding"]["canonical_sha256"]
                 and binding["candidate_at"] == episode.candidate_at
                 and binding["identity"]["cik"] == subject["key"]
                 and binding["scope"] == "episode_symbol_context"
                 and binding["candidate_quote_security_join"] == "not_established")
        _require(value["projection_kind"] == "retrospective_earnings_context"
                 and value["candidate_quote_security_join"] == "not_established"
                 and value["live_projection_eligible"] is False
                 and value["limitations"] == LIMITATIONS and value["evidence_cutoff"] == episode.candidate_at
                 and _instant(pointer["captured_at"]) <= _instant(episode.candidate_at)
                 <= _instant(value["composed_at"]) <= captured
                 and value["research_state"] == "partial"
                 and value["evidence_binding_state"] == "exact_owner_native_event"
                 and result["company_context"] == {"state":"partial"}
                 and result["transmission"] == {"state":"unavailable"})
        refs = result["evidence_refs"]
        _require(len(refs) == 1 and refs[0]["reference_id"] == binding["workspace_reference_id"]
                 and refs[0]["owner_store"] == "earnings.workspace_generation")
        clocks = refs[0]["clocks"]
        expected_clocks = [("knowable", "lifecycle.source_available_at"),
                           ("observed", "lifecycle.observed_at"), ("belief_or_build", "generated_at")]
        _require(len(clocks) == 3)
        times = []
        for clock, (kind, field) in zip(clocks, expected_clocks):
            _require(clock["class"] == kind and clock["field"] == field
                     and clock["value_state"] == "known" and clock["grain"] == "datetime")
            times.append(_instant(clock["value"]))
        _require(times[0] <= times[1] <= times[2] <= _instant(episode.candidate_at))
        observation = value["observation"]
        fields = {"metric", "value", "unit", "basis", "period", "document_id", "source_sha256",
                  "rights_profile", "span_id", "text_sha256", "field_path", "lineage_state", "locally_replayed"}
        _require(type(observation) is dict and set(observation) == fields
                 and observation["metric"] == "revenue" and type(observation["value"]) in (int,float)
                 and math.isfinite(observation["value"]) and 0 <= observation["value"] <= 10**15
                 and observation["unit"] in {"USD", "usd_millions"}
                 and observation["basis"] in {"reported", "gaap"}
                 and observation["rights_profile"] == "rp_public_primary_v1"
                 and observation["lineage_state"] == "owner_byte_replay_receipt"
                 and observation["locally_replayed"] is False)
        for key in ("source_sha256", "text_sha256"):
            _require(type(observation[key]) is str and _HEX.fullmatch(observation[key]) is not None)
        _require(type(observation["document_id"]) is str
                 and _safe_object_id(observation["document_id"]) == observation["document_id"]
                 and type(observation["span_id"]) is str
                 and re.fullmatch(r"span_[a-f0-9]{20}", observation["span_id"]) is not None)
        _require(type(observation["period"]) is str and re.fullmatch(
            r"(?:\d{4}Q[1-4]|\d{4}FY|\d{4}-\d{2}-\d{2})", observation["period"]) is not None
            and type(observation["field_path"]) is str and re.fullmatch(r"facts\[\d+\]", observation["field_path"]) is not None)
        label = f"{fiscal.year}Q{fiscal.quarter}" if fiscal.quarter else f"{fiscal.year}FY"
        _require(observation["period"] == label or fiscal.calendar_end is not None
                 and observation["period"] == fiscal.calendar_end.isoformat())
        for key in ("projection_kind", "native_earnings_identity", "research_subject", "composed_at",
                    "evidence_cutoff", "source_generation", "observation", "candidate_quote_security_join",
                    "live_projection_eligible", "limitations", "fiscal_period"):
            result[key] = value[key]
        result["published_context_sha256"] = value["sha256"]
        return result
    except ResearchReadUnavailable:
        raise
    except Exception:
        raise ResearchReadUnavailable("radar_research_unavailable") from None


def read_published_research(directory: Path, *, episode_id: str | None = None) -> dict:
    """Read one fixed owner file, listing native candidates or one exact case.

    No caller-supplied path, as-of time, identity bridge or case is accepted.
    Missing projection means unqualified, not an empty evidence case.
    """
    _require(episode_id is None or type(episode_id) is str and 0 < len(episode_id) <= 160
             and re.fullmatch(r"[A-Za-z0-9_.:-]+", episode_id) is not None, "invalid_episode_selection")
    raw, captured = _read(directory)
    try:
        source = json.loads(raw, object_pairs_hook=_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ResearchReadUnavailable("radar_research_unavailable")))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise ResearchReadUnavailable("radar_research_unavailable") from None
    _require(type(source) is dict and source.get("schema") == "entry_radar.live/v1")
    _require(_instant(source.get("asof")) <= captured)
    rows, health = source.get("episodes"), source.get("health")
    _require(type(rows) is list and len(rows) <= MAX_EPISODES and type(health) is dict
             and type(health.get("state")) is str and type(health.get("pass")) is dict
             and health["pass"].get("at") == source["asof"])
    authority = source.get("authority")
    from engine.entry_radar.readings import AUTHORITY_BLOCK
    _require(type(authority) is dict and set(authority) == set(AUTHORITY_BLOCK)
             and all(v is False for v in authority.values()))
    candidates, seen, selected = [], set(), None
    for row in rows:
        _require(type(row) is dict and type(row.get("episode_id")) is str and row["episode_id"] not in seen)
        seen.add(row["episode_id"])
        if row.get("state") != "CANDIDATE":
            continue
        episode = _episode(row)
        _require(_instant(episode.candidate_at) <= _instant(source["asof"]))
        summary = {k: getattr(episode, k) for k in ("episode_id", "ticker", "detector_id", "candidate_at")}
        # Presence alone does not qualify an attached object. Validate listed
        # cases as well so the list cannot advertise a malformed publication.
        if "research_case" in row:
            _projection(row["research_case"], episode)
        if "research_context" in row:
            _context_projection(row["research_context"], episode, captured)
        summary["research_state"] = ("published" if "research_case" in row else
                                     "retrospective_context" if "research_context" in row else "unqualified")
        candidates.append(summary)
        if episode.episode_id == episode_id:
            selected = (episode, row)
    result = {"schema": SCHEMA, "source": {"artifact": "entry_radar.json", "asof": source["asof"],
              "snapshot_sha256": sha256(raw).hexdigest(), "captured_at": captured.isoformat(),
              "owner_health": health["state"], "freshness_state": "owner_reported_only"},
              "authority": dict(AUTHORITY), "selection": episode_id}
    if episode_id is None:
        return {**result, "state": "candidate_list", "candidates": sorted(candidates, key=lambda r: r["episode_id"])[:MAX_SELECTED],
                "candidate_count": len(candidates), "truncated": len(candidates) > MAX_SELECTED,
                "ordering": "native_episode_id_not_priority"}
    _require(selected is not None, "candidate_not_found")
    episode, row = selected
    result["candidate"] = {k:getattr(episode,k) for k in ("episode_id", "ticker", "detector_id", "candidate_at")}
    if "research_case" not in row and "research_context" in row:
        return {**result, "state":"published_context", "case":_context_projection(row["research_context"], episode, captured)}
    if "research_case" not in row:
        return {**result, "state": "unqualified", "case": None, "reason": "native_case_not_published"}
    return {**result, "state": "published_case", "case": _projection(row["research_case"], episode)}
