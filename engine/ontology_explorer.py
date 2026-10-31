"""Compose the tenant-neutral ``ontology_explorer_snapshot.v1`` (F04-X1).

WHAT THIS IS
------------
A pure, request-time READER. It answers one question for one transmission
chain — what does the owner-observed path actually say right now — and it
answers it by composing artifacts that other owners already produced:

    knowledge/transmission/<chain>.yaml     the path definition (canonical)
    data/transmission/chain_state.json      the compiled owner observation
    data/transmission/chain_episodes.jsonl  recorded transitions, when present
    data/reference/vendor_aliases.parquet  optional dated company identity

It creates no graph, no causal model, no truth store, no cache and no second
evaluation of anything. ``/transmission.html`` remains the canonical rates/TXI
owner surface; this module composes read-only on top of it.

WHY IT DOES NOT CALL THE CANONICAL EVALUATOR
--------------------------------------------
``engine.transmission_chains.run()`` defaults to ``write=True`` and APPENDS
``chain_episodes.jsonl``. A request-time consumer that reached for it would
mutate an owner artifact on a GET, and would re-derive state the nightly has
already derived. So this module reads the compiled artifact and never evaluates.

It also does not call ``validate_chain()``. That validator is the NIGHTLY's
gate: it raises on the first structural violation, and it already guarantees in
production that hops form a simple path in declared-node order. A request-time
composer needs the opposite disposition — it must DEGRADE with a typed, legible
state rather than raise a compiler error at a researcher, and it must not
silently change product semantics the next time the nightly's strictness moves.
So the structural questions this surface actually depends on — path order, cycle
freedom, node coverage, revision coherence, size bounds — are asked here,
directly, against the bytes that were read.

WHAT IT REFUSES TO SAY
----------------------
Three refusals are load-bearing, and each exists because the plausible-looking
alternative is false:

  * A confirmed DOWNSTREAM leg never activates a false upstream one. The frozen
    reference case has a true terminal leg over three false upstream legs; that
    is a contradiction to report, not partial activation and not an attribution.
  * An absent baseline is NOT "nothing changed". Zero recorded transitions means
    the comparison cannot be made, so the answer is ``comparison_unavailable``.
  * Freshness is never claimed. This process reads the checkout it runs in and
    cannot observe what the deployed canonical surface serves, so it reports the
    source age it can actually measure and marks the comparison unavailable.

Frequencies and episode counts are historical context, never confidence, and
this surface carries no rank, gate, size or trade authority.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

SCHEMA_ID = "ontology_explorer_snapshot.v1"
#: The manifest answers "did two responses see the same thing". Two responses can
#: read byte-identical sources and still differ, because the meaning is produced
#: by THIS code — so the method that read them is part of what the digest binds.
#: It is still a read receipt, never a native owner generation.
COMPOSER_METHOD = "ontology_explorer.compose.v6"
ERROR_SCHEMA_ID = "ontology_explorer_error.v1"
DEFAULT_CHAIN = "oil_inflation_duration_derate"

#: Compiled-state schemas this composer knows how to read. A state file built
#: under any other schema is refused rather than guessed at.
COMPATIBLE_STATE_SCHEMAS = frozenset({"transmission_chains.v1"})

#: Response bound. Long paths are not "big responses" here, they are evidence
#: that the input is not the simple path this surface is designed to explain, so
#: the bound fails closed instead of truncating into a half-answer.
MAX_PATH_LEGS = 12

#: Bytes, not rows: a bound that counts only nodes leaves the payload unbounded.
MAX_SOURCE_BYTES = 2_000_000
MAX_EPISODE_ROWS = 5_000
MAX_K1_REFERENCES = 32

#: The owner's closed transition vocabulary (`transmission_chains._mk_transition`
#: call sites). A row naming anything else is not one of the owner's events.
OWNER_TRANSITIONS = frozenset({"arming", "propagating", "expressed", "failed", "expired"})

#: fullmatch below, not match: `$` also matches before a trailing newline.
_CHAIN_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_]{0,80}")

#: distinct from a present-but-null field — "never written" and "written as null"
#: are different owner statements and neither is a verdict.
_MISSING = object()

_KNOWLEDGE_REL = "knowledge/transmission"
_STATE_REL = "data/transmission/chain_state.json"
_EPISODES_REL = "data/transmission/chain_episodes.jsonl"
_ALIASES_REL = "data/reference/vendor_aliases.parquet"
_CALIBRATION_REL = "data/transmission/calibration.json"
_WTI_OBSERVATION_REL = "data/yahoo/CL_F.observation.json"


class SourceUnavailable(RuntimeError):
    """A required owner artifact is absent or unreadable. Serve a typed 503."""


class SourceIncoherent(RuntimeError):
    """The artifacts were readable but cannot be trusted together.

    Two distinct classes land here, and conflating them would hide one:
    a MID-READ MUTATION (the bytes moved under the read), and a STABLE BUT
    MIXED GENERATION (nothing moved, but the sources describe different
    revisions or reference nodes that do not exist).
    """


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------
def _read_source(path: Path) -> bytes:
    """The single seam through which every source byte is read.

    Kept as one function so the post-composition re-verification reads exactly
    the way the first pass did, and so a test can prove the mutation detector
    actually fires.
    """
    return path.read_bytes()


def _read_wti_observation(path: Path) -> bytes:
    # The native export is optional and bounded BEFORE read/decode. Its payload
    # never enters X1; only its exact byte receipt enters the normal manifest.
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise SourceIncoherent("wti_observation_exceeds_bound")
    return raw


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def manifest_hash_for(reads: list[dict[str, Any]], *,
                      method: str = COMPOSER_METHOD) -> str:
    """Reproduce the manifest hash from the receipts alone.

    A caller comparing two responses must be able to decide whether they saw the
    same owner generation without trusting either response's own summary, so the
    hash is a pure function of ``(path, sha256)`` pairs in sorted order.
    """
    joined = "\n".join([method] + [f"{r['path']}:{r['sha256']}"
                                   for r in sorted(reads, key=lambda r: r["path"])])
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _bilingual(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict) and isinstance(value.get("en"), str):
        return {"en": value["en"], "zh": value.get("zh") or value["en"]}
    if isinstance(value, str):
        return {"en": value, "zh": value}
    return None


# ---------------------------------------------------------------------------
# path structure
# ---------------------------------------------------------------------------
def _walk_path(hops: list[dict]) -> tuple[list[str], list[str]]:
    """Return (sequence, cycle_nodes) from the ORDERED hop list.

    Order comes from the hops and nothing else. The node mapping in a knowledge
    file is unordered by construction, and any score-derived ordering would let
    a large receipt jump the queue ahead of the leg that actually blocks.
    """
    if not hops:
        return [], []
    inbound: dict[str, int] = {}
    for hop in hops:
        inbound.setdefault(str(hop.get("from")), 0)
        inbound[str(hop.get("to"))] = inbound.get(str(hop.get("to")), 0) + 1
    nxt: dict[str, str] = {}
    for hop in hops:
        nxt.setdefault(str(hop.get("from")), str(hop.get("to")))
    start = str(hops[0].get("from"))
    for node_id, count in inbound.items():
        if count == 0:
            start = node_id
            break
    sequence: list[str] = []
    seen: set[str] = set()
    cursor: str | None = start
    cycle: list[str] = []
    while cursor is not None:
        if cursor in seen:
            # Re-entering a node means the "path" loops. Record the loop members
            # and stop; a repeated node in the sequence would let one leg be
            # counted twice and inflate the state.
            cycle = sequence[sequence.index(cursor):]
            break
        seen.add(cursor)
        sequence.append(cursor)
        cursor = nxt.get(cursor)
    return sequence, cycle


def _unreached_nodes(definition_hops: list[dict], declared_nodes: dict,
                     sequence: list[str]) -> list[str]:
    referenced: set[str] = set()
    for hop in definition_hops:
        referenced.update((str(hop.get("from")), str(hop.get("to"))))
    return sorted((referenced | set(declared_nodes)) - set(sequence))


def _require_simple_path(definition_hops: list[dict], declared_nodes: dict,
                        sequence: list[str]) -> None:
    """Refuse anything that is not one continuous path through every node.

    `_walk_path` follows a single successor chain from one root. That is the
    right reading of a simple path and a silently WRONG reading of anything
    else: a hop list of `n1->n2` and `n3->n4` walks to `['n1','n2']`, and every
    downstream calculation — coverage, activation, the bound, the legs — then
    describes two legs as if they were the whole path. With `n3` and `n4`
    observed FALSE, this surface answered `state: active` about a path it had
    not read. Branching does the same thing more quietly, because the second
    out-edge is dropped when the successor map is built.

    The nightly's `validate_chain` does enforce continuity, and every live chain
    is a simple path today, so this is latent rather than firing. It is still
    ours to check: this module deliberately does not call that validator, it is
    a REQUEST-TIME reader, and a hop edit that does not bump `rev` reaches a
    reader before any nightly runs. Failing closed is the only answer that
    cannot mislead — a partial path presented as a whole one is worse than a
    typed 503.
    """
    out_degree: dict[str, int] = {}
    referenced: set[str] = set()
    for hop in definition_hops:
        src, dst = str(hop.get("from")), str(hop.get("to"))
        out_degree[src] = out_degree.get(src, 0) + 1
        referenced.update((src, dst))
    branching = sorted(node for node, degree in out_degree.items() if degree > 1)
    if branching:
        raise SourceIncoherent(f"path_branches:{branching[0]}")
    undeclared = sorted(referenced - set(declared_nodes))
    if undeclared:
        # A hop pointing at a node the file never declares is an incoherent
        # file, not an unpublished reading. Reported as the latter it invented a
        # positional title for the phantom and told the researcher to wait for a
        # reading that can never arrive.
        raise SourceIncoherent(f"undeclared_node:{undeclared[0]}")
    unreached = _unreached_nodes(definition_hops, declared_nodes, sequence)
    if unreached:
        raise SourceIncoherent(f"path_disconnected:{unreached[0]}")


# ---------------------------------------------------------------------------
# composition
# ---------------------------------------------------------------------------
def compose_snapshot(root: Path | str, *, chain: str = DEFAULT_CHAIN,
                     now: datetime | None = None) -> dict[str, Any]:
    """Compose one ``ontology_explorer_snapshot.v1`` for ``chain``."""
    root = Path(root)
    if not _CHAIN_SLUG_RE.fullmatch(chain or ""):
        raise SourceUnavailable(f"unknown_chain:{chain!r}")

    yaml_rel = f"{_KNOWLEDGE_REL}/{chain}.yaml"
    rels = [yaml_rel, _STATE_REL]
    if (root / _EPISODES_REL).exists():
        rels.append(_EPISODES_REL)

    raws: dict[str, bytes] = {}
    for rel in rels:
        path = root / rel
        try:
            raws[rel] = _read_source(path)
        except OSError as exc:
            raise SourceUnavailable(f"unreadable_source:{rel}") from exc
        if len(raws[rel]) > MAX_SOURCE_BYTES:
            raise SourceIncoherent(
                f"source_exceeds_bound:{rel}:{len(raws[rel])}>{MAX_SOURCE_BYTES}")
    digests = {rel: _digest(raw) for rel, raw in raws.items()}
    # Bind an optional native generation without copying scenario/private
    # payloads into X1 or withholding WTI when rates metadata is unavailable.
    # The explicit POST alone decodes and admits this owner's bounded bytes.
    try:
        calibration_raw = _read_source(root / _CALIBRATION_REL)
    except OSError:
        pass
    else:
        raws[_CALIBRATION_REL] = calibration_raw
        rels.append(_CALIBRATION_REL)
        digests[_CALIBRATION_REL] = _digest(calibration_raw)

    # Capture/export is a prospective observation, never a retroactive clock or
    # native calendar qualification. A changed generation changes the selected
    # manifest; explicit POST still has to qualify every native owner input.
    try:
        wti_observation = _read_wti_observation(root / _WTI_OBSERVATION_REL)
    except OSError:
        pass
    else:
        raws[_WTI_OBSERVATION_REL] = wti_observation
        rels.append(_WTI_OBSERVATION_REL)
        digests[_WTI_OBSERVATION_REL] = _digest(wti_observation)

    try:
        definition = yaml.safe_load(raws[yaml_rel].decode("utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise SourceUnavailable(f"unparseable_source:{yaml_rel}") from exc
    try:
        state_doc = json.loads(raws[_STATE_REL].decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SourceUnavailable(f"unparseable_source:{_STATE_REL}") from exc
    if not isinstance(definition, dict) or not isinstance(state_doc, dict):
        raise SourceUnavailable("malformed_source")

    # Identity is optional; its absence must not erase owner-backed membership.
    # Parse the EXACT bytes that enter the read manifest, never a second file
    # read hidden inside an identity loader. Reverification below covers this
    # source too, including a change while parquet is being decoded.
    aliases = None
    identity_reason = "identity_source_unavailable"
    try:
        alias_raw = _read_source(root / _ALIASES_REL)
    except OSError:
        pass
    else:
        raws[_ALIASES_REL] = alias_raw
        rels.append(_ALIASES_REL)
        digests[_ALIASES_REL] = _digest(alias_raw)
        if len(alias_raw) <= MAX_SOURCE_BYTES:
            try:
                import pyarrow.parquet as parquet
                from lib.dataos.identity import VendorAliasTable

                aliases = VendorAliasTable.from_records(
                    parquet.read_table(io.BytesIO(alias_raw)).to_pylist())
                identity_reason = None
            except Exception:
                identity_reason = "identity_source_unreadable"
        else:
            identity_reason = "identity_source_exceeds_bound"

    snapshot = _build(definition, state_doc, raws.get(_EPISODES_REL), chain=chain,
                      now=now or datetime.now(UTC), aliases=aliases)
    snapshot["company_exposure"]["identity_source"] = {
        "status": "available" if aliases is not None else "unavailable",
        "reason": identity_reason,
        "path": _ALIASES_REL,
        "sha256": digests.get(_ALIASES_REL),
    }
    substrate = snapshot["company_exposure"]["substrate"]
    snapshot["source"]["substrate_asof"] = (
        substrate.get("substrate_asof") if substrate is not None else None)

    # Re-verify AFTER composing, by re-reading rather than by trusting a stat
    # taken beforehand. This catches any source rewritten after this process
    # read it. It does NOT catch a source rewritten just BEFORE its own read,
    # because that read returns the newer generation and every digest then stays
    # stable — that window is closed by the revision coherence check above, not
    # by the digest, which is why both checks exist.
    for rel, expected in digests.items():
        try:
            reader = _read_wti_observation if rel == _WTI_OBSERVATION_REL else _read_source
            current = _digest(reader(root / rel))
        except OSError as exc:
            raise SourceIncoherent(f"mid_read_mutation:{rel}:disappeared") from exc
        if current != expected:
            raise SourceIncoherent(f"mid_read_mutation:{rel}")

    reads = [{"path": rel, "sha256": digests[rel], "bytes": len(raws[rel])} for rel in rels]
    snapshot["source"]["reads"] = reads
    snapshot["source"]["source_manifest_hash"] = manifest_hash_for(reads)
    snapshot["source"]["composer_method"] = COMPOSER_METHOD
    return snapshot


def _build(definition: dict, state_doc: dict, episodes_raw: bytes | None, *,
           chain: str, now: datetime, aliases: Any = None) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    state_schema = state_doc.get("schema")
    if state_schema not in COMPATIBLE_STATE_SCHEMAS:
        raise SourceIncoherent(f"schema_incompatible:{state_schema!r}")

    entries = state_doc.get("chains")
    if not isinstance(entries, list):
        raise SourceUnavailable("malformed_source:chains")
    matches = [c for c in entries if isinstance(c, dict) and c.get("chain") == chain]
    if not matches:
        raise SourceUnavailable(f"chain_absent_from_state:{chain}")
    if len(matches) > 1:
        # Taking matches[0] made every later row invisible — including a row at a
        # different rev with a different state, which also walked straight past
        # the rev-coherence check below, since that check only ever saw row 0.
        raise SourceIncoherent(f"duplicate_chain_rows:{len(matches)}")
    observed = matches[0]

    if definition.get("chain") != chain:
        raise SourceIncoherent(f"chain_mismatch:{definition.get('chain')!r}")
    if definition.get("rev") != observed.get("rev"):
        raise SourceIncoherent(
            f"rev_mismatch:knowledge={definition.get('rev')!r}:state={observed.get('rev')!r}")

    declared_nodes = definition.get("nodes")
    if not isinstance(declared_nodes, dict) or not declared_nodes:
        # The file was present, readable and parsed. That is a coherence failure,
        # not an availability one, and calling it "absent" misdescribes it.
        raise SourceIncoherent("malformed_nodes")
    definition_hops = definition.get("hops")
    if not isinstance(definition_hops, list) or not definition_hops:
        raise SourceIncoherent("malformed_hops")

    # A malformed node COLLECTION is a source problem, and it used to escape as a
    # generic internal error because the code went straight to iterating it.
    observed_node_list = observed.get("nodes", [])
    if not isinstance(observed_node_list, list):
        raise SourceIncoherent("malformed_nodes")
    observed_nodes = {n["id"]: n for n in observed_node_list
                      if isinstance(n, dict) and isinstance(n.get("id"), str)}
    unknown = sorted(set(observed_nodes) - set(declared_nodes))
    if unknown:
        raise SourceIncoherent(f"unknown_node:{unknown[0]}")

    observed_node_rows = [n for n in observed_node_list if isinstance(n, dict)]
    row_ids = [n.get("id") for n in observed_node_rows if isinstance(n.get("id"), str)]
    if len(row_ids) != len(set(row_ids)):
        raise SourceIncoherent(f"duplicate_node_rows:{len(row_ids) - len(set(row_ids))}")

    sequence, cycle_nodes = _walk_path(definition_hops)
    if not cycle_nodes:
        _require_simple_path(definition_hops, declared_nodes, sequence)
    else:
        # A cycle already forces `unknown`, so this degrades rather than raises —
        # but it must still be SEEN. Skipping the completeness check entirely
        # under a cycle left a whole disconnected component invisible.
        unreached = _unreached_nodes(definition_hops, declared_nodes, sequence)
        if unreached:
            gaps.append({"kind": "path_incomplete", "unreached": unreached})
    # The bound is measured against the FILE, not against the walk. Measuring the
    # walk let a file with 80 declared nodes and 40 disjoint hop pairs compose as
    # "2 of 12 legs" while returning 40 rendered hop rows.
    declared_size = max(len(sequence), len(definition_hops) + 1, len(declared_nodes))
    if declared_size > MAX_PATH_LEGS:
        raise SourceIncoherent(f"path_exceeds_bound:{declared_size}>{MAX_PATH_LEGS}")

    observed_hops = {h["id"]: h for h in observed.get("hops", [])
                     if isinstance(h, dict) and isinstance(h.get("id"), str)}

    legs = _legs(sequence, declared_nodes, observed_nodes, gaps)
    hops = _hops(definition_hops, observed_hops, gaps)
    invalidators = _invalidators(definition, gaps)
    exposure_screens = _exposure_screens(definition, gaps)

    # "unresolved" is not "observed". Counting it as observed produced a snapshot
    # that said all four legs were observed while its own blocking-leg block said
    # that very leg had no reading.
    unobserved = [leg["node_id"] for leg in legs if leg["observation"] != "observed"]
    confirmed_hop_count = sum(1 for h in hops if h["confirmed"] is True)

    # Today's conditions all reading true is a DESCRIPTION OF TODAY. It is not an
    # episode. The owner's chain is temporal: a chain whose conditions coincide
    # may be merely `arming`, a fired falsifier can stop it while the same
    # conditions still read true, and `failed`/`expired` episodes end with their
    # conditions unchanged. Deriving activation from the node booleans emitted
    # `active` with the owner reading `failed` and ZERO confirmed hops.
    conditions_all_met = (
        None if (cycle_nodes or unobserved or not sequence)
        else all(leg["confirmed"] is True for leg in legs))
    episode = _episode_state(observed, gaps)
    # Tri-state on purpose. Collapsing an unreadable owner episode to False would
    # assert "not running" about a chain whose state we could not read, which is
    # the same collapse this repair exists to remove one level up.
    activation = episode["running"]
    state_code = episode["code"]

    # The first unmet leg is a fact about today's conditions, so it is computed
    # from them regardless of what the owner's episode is doing, and it is absent
    # only when every leg actually reads true. Gating it on the episode hid the
    # blocking leg whenever a leg was unread — the unread leg IS the blocker.
    first_blocking = _first_blocking_leg(legs)
    contradiction = _contradiction(legs, first_blocking)

    company_exposure = _project_company_exposure(
        definition, state_doc, observed, aliases, gaps=gaps)
    by_channel = {channel["id"]: channel for channel in company_exposure["channels"]}
    for screen in exposure_screens:
        channel = by_channel.get(screen["id"])
        if channel is not None:
            screen.update({key: value for key, value in channel.items() if key != "id"})
        else:
            screen.update({"status": "unavailable", "reason": company_exposure["reason"],
                           "companies": None})

    payload = {
        "schema": SCHEMA_ID,
        "generated_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": _source_block(definition, state_doc, observed, chain=chain,
                                now=now, gaps=gaps),
        "state": {
            "code": state_code,
            "label": _state_label(state_code),
            "activation": activation,
            "owner_state": observed.get("state"),
            "owner_state_label": _reader_text(
                observed.get("state_label"), kind=IDENTITY,
                where="state_label", gaps=gaps),
            "tier": observed.get("tier"),
            "display_only": bool(observed.get("display_only", True)),
            "basis": episode["basis"],
            "episode_id": episode["episode_id"],
            "watch_condition_fired": episode["watch_condition_fired"],
            "arm_veto": episode["arm_veto"],
            "confirmed_hop_count": confirmed_hop_count,
            "hop_count": len(hops),
            # A SEPARATE FACT, deliberately not folded into `code`: whether every
            # condition happens to read true right now. It describes today, and
            # an episode is a history — a chain can sit here with everything true
            # and still be dormant, stopped or already ended.
            "conditions": {
                "all_current_met": conditions_all_met,
                "describes": "current_readings_only",
            },
            "coverage": {
                "legs_declared": len(sequence),
                "legs_observed": len(sequence) - len(unobserved),
                "legs_unobserved": unobserved,
            },
        },
        "path": {
            "title": _reader_text(
                definition.get("title"), kind=IDENTITY, where="title", gaps=gaps,
                fallback={"en": "Transmission path", "zh": "\u4f20\u5bfc\u8def\u5f84"}),
            "sequence": sequence,
            "legs": legs,
            "hops": hops,
            "cycle": {"detected": bool(cycle_nodes), "nodes": cycle_nodes},
        },
        "first_blocking_leg": first_blocking,
        "contradiction": contradiction,
        "transmission_gap": _transmission_gap(
            state_doc, observed, episodes_raw, legs, hops,
            invalidators, contradiction, now=now),
        "what_changed": _what_changed(episodes_raw, chain=chain,
                                      rev=observed.get("rev"),
                                      cutoff=state_doc.get("asof"), gaps=gaps),
        "why_it_matters": _why_it_matters(hops, contradiction),
        "next_action": _next_action(state_code, first_blocking, contradiction, unobserved, legs),
        "evidence": _evidence(episodes_raw, legs, chain=chain,
                              rev=observed.get("rev"), cutoff=state_doc.get("asof")),
        "clocks": _clocks(observed, state_doc, hops, now=now),
        "invalidators": invalidators,
        "exposure_screens": exposure_screens,
        # Membership is carried once, on the existing exposure screens. This
        # metadata binds their common owner clocks and identity read receipt.
        "company_exposure": {
            **{key: value for key, value in company_exposure.items() if key != "channels"},
            "refusals": [{"channel_id": channel["id"], "reason": channel["reason"]}
                         for channel in company_exposure["channels"]
                         if channel["status"] != "available"],
        },
        "display_permission": {
            "status": "not_determined_here",
            "policy": "site_full entitlement, enforced at the transport layer",
        },
        "gaps": gaps,
        "bounds": {"legs": len(sequence), "max_legs": MAX_PATH_LEGS, "truncated": False},
    }
    # Last, because the composers above are still appending to `gaps` while the
    # payload literal is being built.
    _label_gaps(gaps, legs)
    return payload


def _project_company_exposure(definition: dict, state_doc: dict, observed: dict,
                              aliases: Any, *, gaps: list | None = None) -> dict:
    """Project TXI's existing blast; never run a screen or infer a theme edge.

    Membership is an owner observation. Identity merely determines whether an
    explicit company-research action is safe. Its failure cannot turn unknown
    identity into a different company's link or erase the observed membership.
    """
    from engine.transmission_company_continuation import (
        ContinuationLink, chain_decision_date, continuation_for,
    )

    gaps = [] if gaps is None else gaps
    # Substrate provenance is a closed display projection, not a pass-through
    # for future vendor reports or other internal owner metadata.
    source_substrate = state_doc.get("substrate")
    substrate = None
    if isinstance(source_substrate, dict):
        universe = source_substrate.get("universe")
        clock = source_substrate.get("substrate_asof")
        substrate = {
            "universe": universe if type(universe) is int and universe >= 0 else None,
            "substrate_asof": None,
        }
        if isinstance(clock, dict):
            substrate["substrate_asof"] = {
                key: clock.get(key) if chain_decision_date(clock.get(key)) else None
                for key in ("min", "max")
            }
    result = {
        "schema": "ontology_company_exposure.v1",
        "authority_ceiling": "research_display_only",
        "status": "unavailable", "reason": None,
        "asof": state_doc.get("asof"),
        "rev": observed.get("rev"),
        "substrate": substrate,
        "channels": [],
    }
    if observed.get("state") not in {"arming", "propagating", "expressed"}:
        result["reason"] = "chain_inactive"
        return result
    decision_date = chain_decision_date(state_doc.get("asof"))
    if decision_date is None:
        result["reason"] = "owner_clock_unavailable"
        return result
    blast = observed.get("blast")
    if not isinstance(blast, dict) or not blast:
        result["reason"] = "owner_membership_absent"
        return result

    declared = definition.get("exposure_screens")
    declared = declared if isinstance(declared, dict) else {}

    def finite_cut(value):
        if type(value) not in (int, float):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False

    for channel_id, entry in sorted(blast.items(), key=lambda item: str(item[0])):
        channel = {
            "id": str(channel_id), "status": "unavailable", "reason": None,
            "label": None, "note": None, "resolved": False,
            "n": None, "unevaluable": None, "cuts": {}, "names": [],
            "companies": None,
        }
        result["channels"].append(channel)
        if channel_id not in declared:
            channel["reason"] = "channel_not_declared"
            continue
        if not isinstance(entry, dict) or entry.get("resolved") is not True:
            channel["reason"] = "channel_unresolved"
            # A dropped screen's owner note explains why it is unavailable.
            if isinstance(entry, dict):
                channel["label"] = _reader_text(
                    entry.get("label"), kind=IDENTITY,
                    where=f"exposure_screens.{channel_id}.label", gaps=gaps,
                    fallback={"en": "An exposure channel", "zh": "某敞口通道"})
                channel["note"] = _reader_text(
                    entry.get("note"), kind=PROSE,
                    where=f"exposure_screens.{channel_id}.note", gaps=gaps)
                for key in ("n", "unevaluable"):
                    if type(entry.get(key)) is int and entry[key] >= 0:
                        channel[key] = entry[key]
            continue
        names, cuts = entry.get("names"), entry.get("cuts")
        counts = (entry.get("n"), entry.get("unevaluable"))
        valid = (
            isinstance(names, list)
            and all(isinstance(name, str) and bool(name) and name == name.strip()
                    for name in names)
            and len(names) == len(set(names))
            and all(type(count) is int and count >= 0 for count in counts)
            and counts[0] == len(names)
            and isinstance(cuts, dict)
            and all(isinstance(key, str) and finite_cut(value) for key, value in cuts.items())
        )
        if not valid:
            channel["reason"] = "channel_malformed"
            continue
        label = _reader_text(entry.get("label"), kind=IDENTITY,
                             where=f"exposure_screens.{channel_id}.label", gaps=gaps,
                             fallback={"en": "An exposure channel", "zh": "某敞口通道"})
        note = _reader_text(entry.get("note"), kind=PROSE,
                            where=f"exposure_screens.{channel_id}.note", gaps=gaps)
        # Reuse the existing exact dated identity law, leaving its Terminal/J1
        # href unchanged. This Macro consumer needs only the verified identity
        # pair; its explicit in-memory action creates no new link vocabulary.
        linked, unlinked = [], []
        identity_unavailable = aliases is None
        for symbol in sorted(names):
            if aliases is None:
                unlinked.append({"symbol": symbol, "reason": "identity_source_unavailable"})
                continue
            try:
                identity = continuation_for(
                    symbol, aliases, decision_date, chain_id=observed.get("chain"),
                    channel_id=str(channel_id), chain_asof=state_doc["asof"])
            except Exception:
                identity_unavailable = True
                unlinked.append({"symbol": symbol, "reason": "identity_read_refused"})
                continue
            if isinstance(identity, ContinuationLink):
                linked.append({"symbol": identity.symbol, "security_id": identity.security_id})
            else:
                unlinked.append(identity.as_dict())
        companies = {
            "linked": linked, "unlinked": unlinked,
            "n_linked": len(linked), "n_unlinked": len(unlinked),
            "identity_unavailable": identity_unavailable,
        }
        channel.update({
            "status": "available", "resolved": True, "label": label, "note": note,
            "n": counts[0], "unevaluable": counts[1], "cuts": dict(cuts),
            "names": list(names), "companies": companies,
        })
    result["status"] = (
        "available" if any(c["status"] == "available" for c in result["channels"])
        else "unavailable")
    result["reason"] = None if result["status"] == "available" else "channels_unavailable"
    return result


#: The owner's own episode vocabulary (`engine/transmission_chains.py`).
_OWNER_RUNNING = frozenset({"arming", "propagating"})
_OWNER_COMPLETED = frozenset({"expressed"})
_OWNER_ENDED = frozenset({"failed", "expired"})
_OWNER_DORMANT = frozenset({"dormant"})


def _episode_state(observed: dict, gaps: list[dict]) -> dict[str, Any]:
    """The product state, taken from the OWNER's episode — never from today.

    Returns ``code`` plus ``running``, which is True only while the owner has a
    live episode that no falsifier or arming veto has stopped. An owner state
    this module does not recognise is UNKNOWN and is named: guessing would put
    the whole surface back on instantaneous coincidence through a default.
    """
    raw = observed.get("state")
    veto = observed.get("arm_veto")
    fired = observed.get("falsifier_fired")
    detail: dict[str, Any] = {
        "owner_state": raw if isinstance(raw, str) else None,
        "arm_veto": bool(veto) if veto is not None else False,
        # The owner spells this key with the refutation family; this product does
        # not ship that word anywhere a reader can reach, and the payload is a
        # reader-facing surface. Same fact, this surface's vocabulary.
        "watch_condition_fired": bool(fired) if fired is not None else False,
        "episode_id": observed.get("episode_id"),
        "basis": "owner_episode",
    }
    if not isinstance(raw, str) or not raw:
        gaps.append({"kind": "owner_state_absent"})
        return {"code": "unknown", "running": None, **detail}
    if raw in _OWNER_RUNNING:
        # A falsifier that has fired stops the episode even while the same
        # conditions still read true; the owner records the receipt rather than
        # rewriting the state, so this surface must apply it.
        if detail["watch_condition_fired"] or detail["arm_veto"]:
            return {"code": "stopped", "running": False, **detail}
        return {"code": "active", "running": True, **detail}
    if raw in _OWNER_COMPLETED:
        return {"code": "completed", "running": False, **detail}
    if raw in _OWNER_ENDED:
        return {"code": "ended", "running": False, **detail}
    if raw in _OWNER_DORMANT:
        return {"code": "dormant", "running": False, **detail}
    gaps.append({"kind": "owner_state_unrecognised", "reason": "not_in_owner_vocabulary"})
    return {"code": "unknown", "running": None, **detail}


def _state_label(code: str) -> dict[str, str]:
    return {
        "active": {"en": "Running", "zh": "运行中"},
        "completed": {"en": "Ran to the end", "zh": "已完整传导"},
        "stopped": {"en": "Stopped", "zh": "已中止"},
        "ended": {"en": "Ended without completing", "zh": "未完成即结束"},
        "dormant": {"en": "Dormant", "zh": "休眠"},
        "unknown": {"en": "Unknown", "zh": "未知"},
    }[code]


#: The receipt shape this product declares. A receipt is projected onto exactly
#: these fields; anything else the owners carry stays in the owner artifact.
_RECEIPT_FIELDS = ("series", "vs", "metric", "window", "value", "op",
                   "threshold", "passed")


def _receipts(rows: Any, *, where: str, gaps: list[dict]) -> list[dict[str, Any]]:
    """Project owner receipts onto the declared contract.

    Passing the owner's dicts through whole made this response's shape whatever
    the owner artifact happened to contain: a nested object rode straight into a
    tenant-neutral payload, and a non-finite float survived composition and then
    broke strict JSON serialisation at the transport edge, turning an upstream
    data problem into a 500 on our side.

    This is a STRUCTURAL contract, not a blacklist of field names — an unknown
    key is dropped because it is not in the contract, not because someone
    predicted it. Numeric zero, boolean False and null all survive; only values
    that cannot be serialised are refused, and their absence is disclosed.
    """
    if not isinstance(rows, list):
        if rows is not None:
            gaps.append({"kind": "receipts_malformed", "where": where})
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            gaps.append({"kind": "receipts_malformed", "where": where})
            continue
        projected: dict[str, Any] = {}
        for field in _RECEIPT_FIELDS:
            if field not in row:
                continue
            value = row[field]
            if isinstance(value, bool) or value is None or isinstance(value, str):
                projected[field] = value
            elif isinstance(value, (int, float)):
                if math.isfinite(value):
                    projected[field] = value
                else:
                    projected[field] = None
                    gaps.append({"kind": "receipt_value_not_finite",
                                 "where": f"{where}.{field}"})
            else:
                # A nested structure is not a reading. Dropping it keeps the
                # response shape the one this product declares.
                gaps.append({"kind": "receipt_field_not_scalar",
                             "where": f"{where}.{field}"})
        if projected:
            out.append(projected)
    return out


def _read_leg_verdict(node_id: str, seen: dict,
                      gaps: list[dict]) -> tuple[bool | None, str]:
    """Read one leg's verdict under the owner's TYPED semantics.

    Truthiness is not a reading. `bool("false")` is True, so a string in the
    owner artifact could ACTIVATE a leg the owners had marked as not holding;
    `bool(None)` is False, so an unwritten verdict became a definite negative;
    and defaulting `resolved` to True asserted a judgement the owners may simply
    not have made. Each of those invents market state out of a Python
    conversion. Only a real bool is a verdict, only a real bool `resolved` is a
    judgement, and everything else preserves UNKNOWN and says which kind it is.
    """
    resolved = seen.get("resolved", _MISSING)
    if resolved is _MISSING or not isinstance(resolved, bool):
        gaps.append({"kind": "node_incomplete", "node_id": node_id})
        return None, "incomplete"
    if not resolved:
        gaps.append({"kind": "node_unresolved", "node_id": node_id})
        return None, "unresolved"
    verdict = seen.get("confirmed", _MISSING)
    if verdict is None or verdict is _MISSING:
        gaps.append({"kind": "node_unjudged", "node_id": node_id})
        return None, "incomplete"
    if not isinstance(verdict, bool):
        gaps.append({"kind": "node_unreadable", "node_id": node_id,
                     "reason": "confirmed_not_boolean"})
        return None, "unreadable"
    return verdict, "observed"


def _declared_predicate(node_id: str, spec: dict) -> dict | None:
    """Closed native declaration, never a re-evaluation or inferred response.

    The owner's grammar validates meaning; local bounds/closed keys prevent
    arbitrary YAML metadata from becoming a response or browser instruction.
    """
    from engine import transmission_chains as txi
    count = 0
    def text(v, limit=128):
        if type(v) is not str or not 0 < len(v) <= limit or any(ord(c) < 32 for c in v):
            raise ValueError('predicate text')
        return v
    def scalar(v):
        if v is None or type(v) is bool:
            return v
        if type(v) in (int, float) and math.isfinite(v):
            return v
        return text(v)
    def test(raw, depth=0):
        nonlocal count
        count += 1
        if count > 64 or depth > 8 or type(raw) is not dict:
            raise ValueError('predicate bound')
        groups = set(raw) & {'all', 'any'}
        if groups:
            if len(groups) != 1 or set(raw) != groups:
                raise ValueError('predicate keys')
            key = next(iter(groups)); children = raw[key]
            if type(children) is not list or not 0 < len(children) <= 64:
                raise ValueError('predicate group')
            return {key: [test(child, depth + 1) for child in children]}
        allowed = {'path', 'series', 'metric', 'window', 'lookback', 'vs', 'ratio', 'op', 'value'}
        if set(raw) - allowed:
            raise ValueError('predicate keys')
        txi._validate_test(raw, 'ontology native target')
        out = {}
        for key, value in raw.items():
            if key in {'window', 'lookback'}:
                if type(value) is not int or not 0 < value <= 100000:
                    raise ValueError('predicate window')
                out[key] = value
            elif key == 'value':
                if type(value) is list:
                    if not 0 < len(value) <= 64:raise ValueError('predicate threshold')
                    out[key] = [scalar(v) for v in value]
                else:out[key] = scalar(value)
            else:out[key] = text(value)
        return out
    try:
        return {'node_id': text(node_id), 'src': text(spec.get('src'), 64),
                'test': test(spec.get('test'))}
    except (TypeError, ValueError, OverflowError, RecursionError, txi.ChainSchemaError):
        return None


def _legs(sequence: list[str], declared: dict, observed: dict,
          gaps: list[dict]) -> list[dict[str, Any]]:
    legs: list[dict[str, Any]] = []
    for index, node_id in enumerate(sequence, start=1):
        spec = declared.get(node_id) or {}
        seen = observed.get(node_id)
        if seen is None:
            gaps.append({"kind": "node_unobserved", "node_id": node_id})
            confirmed: bool | None = None
            observation = "unobserved"
            receipts: list[dict[str, Any]] = []
        else:
            receipts = _receipts(seen.get("receipts"),
                                 where=f"nodes.{node_id}.receipts", gaps=gaps)
            confirmed, observation = _read_leg_verdict(node_id, seen, gaps)
        legs.append({
            "node_id": node_id,
            "index": index,
            "title": _reader_text(
                spec.get("title"), kind=IDENTITY, where=f"nodes.{node_id}.title",
                gaps=gaps,
                fallback={"en": f"Step {index}", "zh": f"\u7b2c {index} \u73af\u8282"}),
            "src": spec.get("src"),
            "declared_predicate": _declared_predicate(node_id, spec),
            "observation": observation,
            "confirmed": confirmed,
            "receipts": receipts,
        })
    return legs


def _hops(definition_hops: list[dict], observed_hops: dict,
          gaps: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hop in definition_hops:
        hop_id = f"{hop.get('from')}->{hop.get('to')}"
        seen = observed_hops.get(hop_id) or {}
        lag = hop.get("lag_d") if isinstance(hop.get("lag_d"), list) else seen.get("lag_d")
        if not isinstance(lag, list) or len(lag) != 2:
            gaps.append({"kind": "clock_absent", "hop_id": hop_id})
            lag = None
        base = seen.get("base_rate")
        base_block = None
        if isinstance(base, dict) and isinstance(base.get("n"), int):
            # Frequency is historical context. It is never a confidence, and it
            # is labelled so a client cannot render it as one by accident.
            base_block = {
                "p_confirm": base.get("p_confirm"),
                "n": base["n"],
                "interpretation": "historical_context",
                "regime_split": base.get("regime_split"),
            }
        out.append({
            "hop_id": hop_id,
            "from": hop.get("from"),
            "to": hop.get("to"),
            "sign": hop.get("sign"),
            "label": _reader_text(hop.get("label"), kind=IDENTITY,
                                  where=f"hops.{hop_id}.label", gaps=gaps),
            "condition": _reader_text(hop.get("condition"), kind=PROSE,
                                      where=f"hops.{hop_id}.condition", gaps=gaps),
            "mechanism": _reader_text(hop.get("mechanism"), kind=PROSE,
                                      where=f"hops.{hop_id}.mechanism", gaps=gaps),
            "lag_d": lag,
            "confirmed": seen.get("confirmed") if "confirmed" in seen else None,
            "confirmed_asof": seen.get("asof"),
            "value_receipt": _receipts(seen.get("value_receipt"),
                                       where=f"hops.{hop_id}.value_receipt", gaps=gaps),
            "base_rate": base_block,
        })
    return out


def _first_blocking_leg(legs: list[dict]) -> dict[str, Any] | None:
    """The FIRST leg in path order that is not confirmed true.

    Path order, not receipt magnitude and not a score: the leg nearest the root
    is the one whose failure explains every leg behind it, whatever the size of
    the shortfall further down.
    """
    for leg in legs:
        if leg["confirmed"] is True:
            continue
        reason = {
            "observed": "condition_false",
            "unresolved": "not_resolved",
            "incomplete": "not_judged",
            "unreadable": "not_readable",
            "unobserved": "not_observed",
        }[leg["observation"]]
        return {
            "node_id": leg["node_id"],
            "index": leg["index"],
            "title": leg["title"],
            "basis": "path_order",
            "reason": reason,
            "receipts": leg["receipts"],
        }
    return None


def _contradiction(legs: list[dict], first_blocking: dict | None) -> dict[str, Any] | None:
    """Confirmed legs BEHIND the first blocker.

    This is the frozen reference case: the terminal leg reads true while the
    root is false. It is reported as a contradiction — something that needs a
    different explanation — and never as the path partly firing, because a true
    downstream leg is not evidence for the upstream one and cannot license the
    attribution the chain's name suggests.
    """
    if first_blocking is None:
        return None
    if first_blocking["reason"] != "condition_false":
        # The note this function publishes says a later leg reads true "while an
        # earlier one does not". If the earlier leg was never read, that sentence
        # is false: nothing is in tension, the coverage is simply incomplete, and
        # the state is already `unknown` for exactly that reason.
        return None
    downstream = [leg["node_id"] for leg in legs
                  if leg["index"] > first_blocking["index"] and leg["confirmed"] is True]
    if not downstream:
        return None
    return {
        "code": "downstream_true_without_upstream",
        "confirmed_downstream": downstream,
        "blocking_upstream": first_blocking["node_id"],
        "note": {
            "en": "A later leg reads true while an earlier one does not. The later "
                  "reading has its own causes; it does not activate the path and it "
                  "does not attribute back to the chain's root.",
            "zh": "后段环节为真而前段为否。后段读数有其自身成因，"
                  "既不代表路径已启动，也不能回溯归因于链条起点。",
        },
    }


def _transmission_gap(state_doc: dict, observed: dict,
                      episodes_raw: bytes | None, legs: list[dict], hops: list[dict],
                      invalidators: list[dict], contradiction: dict | None, *,
                      now: datetime) -> dict:
    """Read native TXI state and its captured episode clocks, without advancing it.

    Calendar elapsed is the owner's evaluate_chain subtraction, NOT sessions or
    a second expiry evaluator. Native asof has no ingestion/knowledge timestamp;
    the manifest binds the captured read, not a historical point-in-time claim.
    """
    from engine import transmission_chains as txi

    result = {
        "schema": "txi_gap_projection.v1", "scope": "txi_only",
        "status": "unavailable", "state": "source_unavailable", "reason": None,
        "method_class": "native_owner_state_projection", "instrument_only": True,
        "market_thesis_verdict": None,
        "identity": {"chain": observed.get("chain"), "rev": observed.get("rev"),
                     "episode_id": observed.get("episode_id")},
        "observation": {"asof": state_doc.get("asof"), "built": state_doc.get("built")},
        "ledger": {"sha256": _digest(episodes_raw) if episodes_raw is not None else None,
                   "bytes": len(episodes_raw) if episodes_raw is not None else None,
                   "clock_basis": "native_transition_asof",
                   "historical_knowledge": "unavailable", "excluded_after_observation": 0},
        "initiating_observation": None, "pending_hop": None,
        "current_contradiction": contradiction, "watched_conditions": invalidators,
        "watch_condition_fired": isinstance(observed.get("falsifier_fired"), dict) and bool(observed["falsifier_fired"]),
        "condition_stop": None,
        "turn_watch": {"status": "unavailable", "stalling": None, "receipts": []},
        "owner_state": observed.get("state"),
    }

    def unavailable(reason):
        result["reason"] = reason
        return result

    def day(value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("calendar clock")
        return datetime.strptime(value, "%Y-%m-%d").date()

    try:
        effective = day(state_doc.get("asof"))
        built = _parse_build_stamp(state_doc.get("built"))
        if (built is None or built > now or effective > now.date()
                or effective > built.astimezone(UTC).date()):
            raise ValueError("owner generation")
    except (TypeError, ValueError):
        return unavailable("owner_clock_unavailable")
    if (len(hops) + 1 != len(legs) or any(
            h["from"] != legs[i]["node_id"] or h["to"] != legs[i + 1]["node_id"]
            for i, h in enumerate(hops))):
        return unavailable("path_unavailable")
    if not legs or any(leg["observation"] != "observed" for leg in legs):
        return unavailable("current_observation_unavailable")
    if not isinstance(observed.get("rev"), int) or isinstance(observed.get("rev"), bool):
        return unavailable("owner_identity_unavailable")
    state = observed.get("state")
    if state == "dormant" and observed.get("episode_id") is None:
        result.update(status="available", state="dormant")
        return result
    if state not in OWNER_TRANSITIONS or not isinstance(observed.get("episode_id"), str):
        return unavailable("owner_identity_unavailable")
    if not episodes_raw:
        return unavailable("episode_ledger_unavailable")

    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate ledger field")
            out[key] = value
        return out

    def nonfinite(_value):
        raise ValueError("nonfinite ledger field")

    rows, by_key = [], {}
    try:
        lines = [line for line in episodes_raw.decode("utf-8").splitlines() if line.strip()]
        if len(lines) > MAX_EPISODE_ROWS:
            raise ValueError("ledger bound")
        for line in lines:
            row = json.loads(line, object_pairs_hook=unique, parse_constant=nonfinite)
            if not isinstance(row, dict):
                raise ValueError("ledger shape")
            if row.get("chain") != observed["chain"] or row.get("rev") != observed["rev"]:
                continue
            if day(row.get("asof")) > effective:
                result["ledger"]["excluded_after_observation"] += 1
                continue
            if (type(row.get("rev")) is not int or type(row.get("hop")) is not int
                    or not 0 <= row["hop"] <= len(hops)
                    or row.get("transition") not in OWNER_TRANSITIONS
                    or not isinstance(row.get("episode_id"), str) or not row["episode_id"]):
                raise ValueError("native identity")
            key = txi._ledger_key(row)
            if key in by_key:
                if by_key[key] != row:
                    raise ValueError("conflicting native key")
                continue
            by_key[key] = row
            rows.append(row)
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        return unavailable("episode_ledger_unreadable")
    episode = [row for row in rows if row["episode_id"] == observed["episode_id"]]
    if not episode:
        return unavailable("episode_not_in_captured_ledger")
    if any(a["asof"] > b["asof"] for a, b in zip(episode, episode[1:])):
        return unavailable("episode_clock_incoherent")
    last = episode[-1]
    if last["transition"] != state or last["hop"] != observed.get("hop"):
        return unavailable("owner_episode_ledger_mismatch")
    arms = [row for row in episode if row["transition"] == "arming" and row["hop"] == 0]
    if len(arms) != 1 or episode[0] != arms[0]:
        return unavailable("arming_observation_unavailable")
    arm = arms[0]
    confirmed = 0
    for row in episode[1:]:
        if row["transition"] == "propagating" and row["hop"] == confirmed + 1 and row["hop"] < len(hops):
            confirmed += 1
        elif row == last and ((row["transition"] in {"failed", "expired"} and row["hop"] == confirmed)
                or (row["transition"] == "expressed" and row["hop"] == len(hops) == confirmed + 1)):
            pass
        else:
            return unavailable("episode_progression_incoherent")
    if not isinstance(arm.get("receipts"), dict):
        return unavailable("arming_observation_unavailable")
    initial = _receipts(arm["receipts"].get(legs[0]["node_id"]),
                        where="gap.initiating", gaps=[])
    if not initial:
        return unavailable("arming_observation_unavailable")
    result["initiating_observation"] = {
        "node_id": legs[0]["node_id"], "asof": arm["asof"], "receipts": initial}
    # Use the owner's open-episode reconstruction as well as the exact selected
    # identity. Never substitute its fallback arm date for a missing hop date.
    if state in _OWNER_RUNNING:
        opened = txi._latest_open_episode(rows)
        if opened is None or opened["episode_id"] != observed["episode_id"]:
            return unavailable("owner_episode_ledger_mismatch")
    k = observed.get("hop")
    if type(k) is not int or not 0 <= k <= len(hops):
        return unavailable("pending_hop_unavailable")
    if state != "expressed":
        if k >= len(hops):
            return unavailable("pending_hop_unavailable")
        anchor = arm if k == 0 else next((r for r in episode
            if r["transition"] == "propagating" and r["hop"] == k), None)
        lag = hops[k]["lag_d"]
        if (anchor is None or not isinstance(lag, list) or len(lag) != 2
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in lag)
                or not 0 <= lag[0] <= lag[1]):
            return unavailable("pending_clock_unavailable")
        if k > 0 and (hops[k - 1]["confirmed"] is not True
                      or hops[k - 1]["confirmed_asof"] != anchor["asof"]):
            return unavailable("pending_clock_incoherent")
        elapsed = (effective - day(anchor["asof"])).days
        target = next((leg for leg in legs if leg["node_id"] == hops[k]["to"]), None)
        if target is None or not target["receipts"]:
            return unavailable("target_observation_unavailable")
        if target.get("declared_predicate") is None:
            return unavailable("target_predicate_unavailable")
        result["pending_hop"] = {
            "hop_id": hops[k]["hop_id"], "from": hops[k]["from"], "to": hops[k]["to"],
            "expected_target": target["declared_predicate"],
            "applicability_assumption": hops[k]["condition"], "lag_d": lag,
            "elapsed_calendar_days": elapsed, "elapsed_basis": "native_calendar_days",
            "minimum_lag_elapsed": elapsed >= lag[0],
            "anchor_asof": anchor["asof"],
            "target_observation": {"asof": state_doc["asof"], **target}}
        if state in _OWNER_RUNNING and (elapsed < 0 or elapsed > lag[1]):
            return unavailable("owner_window_elapsed_unsettled")
    watch = observed.get("turn_watch")
    if isinstance(watch, dict) and type(watch.get("stalling")) is bool and "unresolved" not in watch:
        result["turn_watch"] = {"status": "available", "stalling": watch["stalling"],
            "receipts": _receipts(watch.get("receipts"), where="gap.turn_watch", gaps=[])}
    if state == "failed":
        if not isinstance(last.get("falsifier"), dict) or not last["falsifier"]:
            return unavailable("stopped_condition_unavailable")
        stopped = last['falsifier']
        index = stopped.get('index')
        if type(index) is not int or not 0 <= index < len(invalidators):
            return unavailable("stopped_condition_unavailable")
        result['condition_stop'] = {'condition_id': invalidators[index]['id'],
            'asof': last['asof'], 'receipts': _receipts(stopped.get('receipts'),
                                                     where='gap.condition_stop', gaps=[])}
        code = "condition_stopped"
    elif state == "expired":
        code = "owner_expired"
    elif state == "expressed":
        code = "owner_completed"
    elif contradiction is not None:
        code = "contradicted"
    elif (result["turn_watch"]["stalling"] is True
          and result["pending_hop"]["target_observation"]["confirmed"] is False):
        code = "stalled"
    elif result["pending_hop"]["target_observation"]["confirmed"] is False:
        code = "waiting_inside_window"
    else:
        return unavailable("owner_transition_unsettled")
    result.update(status="available", state=code)
    return result


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _episode_rows(episodes_raw: bytes | None, *, chain: str, rev: Any,
                  cutoff: Any = None,
                  gaps: list[dict] | None = None,
                  report: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Recorded transitions for THIS chain at THIS revision.

    A row written under a different revision describes a different definition of
    the path. Presenting one as the current change is a category error: it read
    as "here is what moved" about a chain whose legs may since have been
    redefined.
    """
    rows: list[dict[str, Any]] = []
    foreign = unreadable = malformed = after_cutoff = 0
    seen_lines = 0
    truncated = False
    if episodes_raw:
        for line in episodes_raw.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            seen_lines += 1
            if seen_lines > MAX_EPISODE_ROWS:
                # A ledger too long to read is not a ledger full of bad rows.
                # Counting it as `malformed` told the reader the owners had
                # written corrupt data, when the truth is that this surface
                # stopped reading — a limitation of ours, disclosed as ours.
                truncated = True
                break
            try:
                row = json.loads(line)
            except ValueError:
                # Silently dropping a corrupt line hides the fact that the
                # comparison was made over an incomplete ledger.
                unreadable += 1
                continue
            if not isinstance(row, dict) or row.get("chain") != chain:
                continue
            # THE OWNER'S KEY, whole. `transmission_chains._ledger_key` is
            # (chain, rev, episode_id, transition, hop, asof) and `_mk_transition`
            # emits exactly that shape. Excluding only a DIFFERENT INTEGER rev let
            # a missing, null or string revision through, and a bare date plus any
            # string was accepted as an event with episode_id=None and hop=None.
            # A date and an arbitrary string are not an owner transition.
            row_rev = row.get("rev")
            if not isinstance(row_rev, int) or isinstance(row_rev, bool):
                malformed += 1
                continue
            if row_rev != rev:
                foreign += 1
                continue
            episode_id = row.get("episode_id")
            hop = row.get("hop")
            transition = row.get("transition")
            if (not isinstance(episode_id, str) or not episode_id
                    or not isinstance(hop, int) or isinstance(hop, bool)
                    or transition not in OWNER_TRANSITIONS
                    or not _is_iso_date(row.get("asof"))):
                malformed += 1
                continue
            if cutoff and str(row["asof"]) > str(cutoff):
                # The artifact cannot have observed a change dated after its own
                # effective date.
                after_cutoff += 1
                continue
            rows.append(row)
    if gaps is not None:
        for count, kind in ((foreign, "transitions_from_another_revision"),
                            (unreadable, "transitions_unreadable"),
                            (malformed, "transitions_malformed"),
                            (after_cutoff, "transitions_after_cutoff")):
            if count:
                gaps.append({"kind": kind, "count": count})
        if truncated:
            gaps.append({"kind": "episode_ledger_truncated",
                         "read_rows": MAX_EPISODE_ROWS,
                         "reason": "exceeds_read_bound"})
    if report is not None:
        # Whether the READ was complete is a different fact from what the read
        # found, and the caller cannot answer "is this the latest" without it.
        report["truncated"] = truncated
        report["unreadable"] = unreadable
        report["complete"] = not truncated and unreadable == 0
    return rows


def _what_changed(episodes_raw: bytes | None, *, chain: str, rev: Any,
                  cutoff: Any, gaps: list[dict]) -> dict[str, Any]:
    """Only OWNER-RECORDED transitions count as change.

    An empty ledger is not evidence that the underlying conditions held still —
    it is the absence of a baseline to compare against, which is a different
    statement and the only one the data supports.
    """
    read: dict[str, Any] = {}
    rows = _episode_rows(episodes_raw, chain=chain, rev=rev, cutoff=cutoff,
                         gaps=gaps, report=read)

    # An UNREAD history is not a history of nothing, and a truncated prefix is
    # not the latest. Both used to answer with the owners' own voice: an
    # entirely corrupt ledger said "the owners have recorded no transition", and
    # a 5,001-row ledger reported its 5,000th-from-the-start row as the change.
    if not read.get("complete", True):
        return {
            "status": "comparison_incomplete",
            "reason": "ledger_read_incomplete",
            "items": [],
            "note": {
                "en": "This page could not read the whole change history for this "
                      "path, so it cannot say what changed most recently — or "
                      "whether anything did. That is a limit of this read, not a "
                      "statement about what the owners recorded.",
                "zh": "本页面未能完整读取该路径的变更历史，"
                      "因此无法判断最近发生了什么变化，也无法判断是否发生过变化。"
                      "这是本次读取的局限，而非对所有者记录内容的结论。",
            },
        }
    if not rows:
        return {
            "status": "comparison_unavailable",
            "reason": "no_recorded_transition",
            "items": [],
            "note": {
                "en": "The owners have recorded no transition for this path, so there "
                      "is no accepted earlier print to compare against. That is a "
                      "missing comparison, not a finding that the conditions held still.",
                "zh": "所有者未记录该路径的任何状态转换，因此没有可比对的既往认定读数。"
                      "这是比较缺失，而非条件未变动的结论。",
            },
        }
    rows.sort(key=lambda r: str(r.get("asof") or ""))
    latest = rows[-1]
    return {
        "status": "recorded_transition",
        "reason": None,
        "items": [{
            "transition": latest.get("transition"),
            "hop": latest.get("hop"),
            "asof": latest.get("asof"),
            "episode_id": latest.get("episode_id"),
            # Never defaulted from the caller: every surviving row carries the
            # owner's own integer revision, and substituting the requested one
            # would manufacture the identity the row failed to prove.
            "rev": latest["rev"],
        }],
        "note": None,
    }


def _why_it_matters(hops: list[dict], contradiction: dict | None) -> dict[str, Any]:
    """Mechanism, carried through from the knowledge file — not a narrative.

    The chain's own prose says how the legs are SUPPOSED to connect. Repeating
    it is legitimate; converting it into a claim that they ARE connecting now,
    or into a market story, is not.
    """
    return {
        "basis": "chain_mechanism",
        "legs": [{
            "hop_id": hop["hop_id"],
            "mechanism": hop["mechanism"],
            "condition": hop["condition"],
            "observed": hop["confirmed"],
        } for hop in hops],
        "caution": {
            "en": "Mechanism describes how these legs are theorised to connect. It is "
                  "not a measurement that they are connecting now, and this surface "
                  "carries no rank, sizing or trade authority.",
            "zh": "机制说明的是各环节理论上的连接方式，"
                  "并非当前确实连通的度量；本页面不提供排名、仓位或交易依据。",
        },
        "contradiction_present": contradiction is not None,
    }


def _next_action(state_code: str, first_blocking: dict | None,
                 contradiction: dict | None, unobserved: list[str],
                 legs: list[dict]) -> dict[str, Any]:
    """Exactly one action, chosen by what the researcher can actually do next.

    Every branch names a ``handler`` the client actually implements and a
    ``target`` that resolves to something on the page. An action the reader
    cannot perform is a caption pretending to be a control, so there is no
    branch here for a comparison this vertical has not built: an inverse-path
    switch would need a proven inverse path, and none is defined.
    """
    titles = {leg["node_id"]: leg["title"] for leg in legs}

    def _named(node_id: str) -> dict[str, str]:
        # Reader-facing text never carries a raw node id. The title is the
        # owner's own bilingual name for that leg; falling back to the slug
        # would put an internal identifier on a customer surface.
        title = titles.get(node_id)
        return title if title else {"en": "that step", "zh": "该环节"}

    if unobserved:
        name = _named(unobserved[0])
        return {
            "code": "wait_for_named_condition",
            "handler": "focus_leg",
            "target": unobserved[0],
            "label": {"en": f"See what is missing for {name['en']}",
                      "zh": f"查看{name['zh']}缺少什么"},
        }
    if contradiction is not None:
        return {
            "code": "inspect_contradiction",
            "handler": "focus_leg",
            "target": contradiction["confirmed_downstream"][0],
            "label": {
                "en": "Inspect what is driving the later leg on its own terms",
                "zh": "按其自身逻辑查证后段环节的驱动因素",
            },
        }
    if first_blocking is not None:
        return {
            "code": "inspect_blocking_leg",
            "handler": "focus_leg",
            "target": first_blocking["node_id"],
            "label": {"en": "Open the evidence behind the first blocking leg",
                      "zh": "查看首个受阻环节背后的证据"},
        }
    return {
        "code": "open_owner_workspace",
        "handler": "open_transmission",
        "target": None,
        "label": {"en": "Open the canonical transmission surface",
                  "zh": "打开传导链规范页面"},
    }


def _transition_references(episodes_raw: bytes | None, eligible: list[dict]) -> tuple[list[dict], dict]:
    """Resolve captured owner rows through native TXI and the existing K1 validator.

    No Evidence Foundation owner read/store is introduced. The native collection
    reader consumes a read-only view of already-manifested ledger bytes. Invalid
    JSON is rejected before that reader so its diagnostic cannot log a raw line.
    """
    detail = {"repeated_native_rows": 0, "conflicting_native_keys": 0,
              "invalid_native_rows": 0, "reference_validation_failures": 0}
    if not episodes_raw or not eligible:
        return [], detail
    from lib import evidence_foundation as foundation
    from engine import transmission_chains as txi

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate native field")
            result[key] = value
        return result

    def nonfinite(_value):
        raise ValueError("nonfinite native value")

    try:
        lines = episodes_raw.decode("utf-8").splitlines()
    except UnicodeError:
        detail["invalid_native_rows"] = 1
        return [], detail
    captured = []
    seen = 0
    for line in lines:
        if not line.strip():
            continue
        seen += 1
        if seen > MAX_EPISODE_ROWS:
            break
        try:
            value = json.loads(line, object_pairs_hook=unique, parse_constant=nonfinite)
        except (TypeError, ValueError, RecursionError):
            detail["invalid_native_rows"] += 1
            continue
        if isinstance(value, dict):
            captured.append(line)

    class CapturedLedger:
        # The native reader's two read-only Path operations, over exact captured
        # lines. No temporary file, filesystem owner redirection or second store.
        def exists(self):
            return True

        def read_text(self):
            return "\n".join(captured)

    native_rows = txi._read_ledger(CapturedLedger())
    eligible_keys = {txi._ledger_key(row) for row in eligible}
    by_key, conflicts = {}, set()
    for row in native_rows:
        # Eligible rows already pass the existing chain/revision/date selection.
        # Other native objects never become references for this selected path.
        try:
            key = txi._ledger_key(row)
            if key not in eligible_keys:
                continue
            payload = foundation.canonical_json_bytes(row)
            if key in by_key:
                if by_key[key][1] != payload:
                    conflicts.add(key)
                else:
                    detail["repeated_native_rows"] += 1
            else:
                by_key[key] = (row, payload)
        except (TypeError, ValueError):
            detail["invalid_native_rows"] += 1
    detail["conflicting_native_keys"] = len(conflicts)
    vocabulary = foundation.load_vocabulary()
    owner = vocabulary["owner_stores"]["txi.episode_transition"]
    refs = []
    detail["reference_limit"] = MAX_K1_REFERENCES
    detail["reference_window"] = "last_native_ledger_keys"
    detail["omitted_native_keys"] = max(0, len(by_key) - MAX_K1_REFERENCES)
    for key, (row, _payload) in list(by_key.items())[-MAX_K1_REFERENCES:]:
        if key in conflicts:
            continue
        identity = {field: row[field] for field in owner["native_identity_fields"]}
        try:
            # The owner generates the episode suffix from a real arming date;
            # a regex-shaped impossible/future start is not a native episode.
            started = identity["episode_id"].rsplit(":", 1)[-1]
            if (not _is_iso_date(started) or started > row["asof"]
                    or txi._episode_id(row["chain"], row["rev"], started) != identity["episode_id"]):
                raise foundation.EvidenceFoundationError("native_episode_identity_invalid")
            pointer = foundation.render_owner_pointer(owner, identity)
        except foundation.EvidenceFoundationError:
            detail["reference_validation_failures"] += 1
            continue
        reference = {
            "schema": foundation.SCHEMA, "version": foundation.VERSION,
            "object_class": "instrument_state", "owner_store": "txi.episode_transition",
            "native_identity": identity, "native_schema": owner["native_schemas"][0],
            # TXI's native row publishes no digest or freshness/rights policy.
            # The enclosing source manifest is not a native per-object digest.
            "native_digest": {"state": "unknown", "sha256": None},
            "coverage_class": "prospective_only",
            "freshness": {"state": "unknown", "clock_field": None, "policy_id": None},
            "rights": {"state": "unknown", "policy_id": None},
            "authority_class": "deterministic",
            "subject": {"key_type": "chain_id", "key": row["chain"]}, "secondary_subjects": [],
            "clocks": [{"class": "belief_or_build", "field": "asof", "value_state": "known",
                        "value": row["asof"], "grain": "date"}],
            "provenance": {"pointer_only": True, "body_embedded": False,
                "owner_reader": owner["reader"], "owner_reader_kind": owner["reader_kind"],
                "pointer": pointer},
            "relations": [],
            "missingness": {"state": "present", "reason": None, "zero_substituted": False},
            "correction": {"kind": "none", "predecessor_reference_ids": [], "clock_field": None,
                "chronology_state": "not_applicable", "append_only": True, "mutates_predecessor": False},
            "replay": {"mode": "live", "cutoffs": {
                field: {"state": "unknown", "value": None, "grain": "date"}
                for field in vocabulary["clock_classes"]},
                "code_revision": None, "input_digest": None, "vintage_state": "owner_native"},
            "authority": dict(foundation.ALL_FALSE_AUTHORITY),
        }
        try:
            reference["reference_id"] = foundation.compute_reference_id(reference)
            refs.append(foundation.validate_reference(reference))
        except (foundation.EvidenceFoundationError, TypeError, ValueError):
            detail["reference_validation_failures"] += 1
    return refs, detail


def _evidence(episodes_raw: bytes | None, legs: list[dict], *,
              chain: str, rev: Any, cutoff: Any) -> dict[str, Any]:
    """Pointer-only native transition binding; the derived head stays excluded."""
    report = {}
    transitions = _episode_rows(episodes_raw, chain=chain, rev=rev, cutoff=cutoff, report=report)
    if not _is_iso_date(cutoff):
        refs, resolution = [], {"selection_clock": "unavailable"}
    else:
        try:
            refs, resolution = _transition_references(episodes_raw, transitions)
        except (ImportError, OSError, TypeError, ValueError, KeyError):
            # K1 is an optional evidence pointer, never replacement owner truth.
            # Missing/changed contracts cannot erase the native path reading.
            refs, resolution = [], {"resolver_state": "unavailable"}
    k1 = {
        # Bound references can be present while native rights/freshness policies
        # remain unavailable. This is never full evidence/permission readiness.
        "status": "partial" if refs else "unavailable_for_object",
        "reason_code": ("native_transition_policy_unavailable" if refs else
                        "native_transition_reference_unavailable" if transitions else
                        "excluded_derived_head_no_eligible_transition"),
        "refs": refs, "refs_count": len(refs), "recorded_transitions": len(transitions),
        "detail": {
            "current_head": "txi.chain_state", "current_head_class": "excluded_derived_head",
            "eligible_owner_store": "txi.episode_transition",
            "eligible_transitions_found": len(transitions),
            "resolver": "lib.evidence_foundation.validate_reference",
            "native_reader": "engine.transmission_chains._read_ledger",
            "native_read_report": report, **resolution,
            "rights_policy": "unavailable", "freshness_policy": "unavailable",
            "body_access": "unavailable", "historical_replay": "unavailable",
            "independence": "not_established", "automatic_effects": False,
        },
    }
    return {"k1": k1,
        "receipts": [{"node_id": leg["node_id"], "receipts": leg["receipts"]} for leg in legs]}


def _clocks(observed: dict, state_doc: dict, hops: list[dict], *,
            now: datetime) -> dict[str, Any]:
    return {
        "asof": state_doc.get("asof"),
        "built": state_doc.get("built"),
        "composed_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "episode_id": observed.get("episode_id"),
        "hop_windows": [{"hop_id": hop["hop_id"], "lag_d": hop["lag_d"],
                         "confirmed_asof": hop["confirmed_asof"]} for hop in hops],
    }


#: Vocabulary that must never reach a user surface. Tripwires keep evaluating in
#: the background; what the reader is shown is what is being watched, never a
#: thesis being refuted. Enforced here rather than by prose review because the
#: text comes from owner files this surface does not control.
_REFUTATION_TERMS = ("falsif", "refut", "disprov", "invalidat", "thesis is",
                     "validated", "\u8bc1\u4f2a", "\u63a8\u7ffb", "\u5df2\u9a8c\u8bc1")

#: A lowercase_with_underscores token is an internal identifier, not English.
_SLUGLIKE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


#: How a failed screen is handled depends on what the string is FOR.
#: PROSE is optional explanation — withholding it costs the reader nothing they
#: cannot get from the structured facts beside it. IDENTITY names a thing on the
#: page; blanking it silently would leave an unlabelled step, so a law violation
#: is replaced by an honest positional label and a named gap, and a merely
#: untranslated label is kept while still being reported.
PROSE = "prose"
IDENTITY = "identity"


def _screen_note(note: Any) -> tuple[dict[str, str] | None, str | None]:
    """Decide whether an owner-authored string may be shown to a reader.

    Measured against the live WTI chain, one falsifier note carried three
    defects at once: the word "falsified" on a user surface, the raw node id
    `yield_rise`, and no Chinese at all — so a zh reader was served untranslated
    English. But the note was never the only way in. An adversarial pass put the
    same words into `path.title`, a node title, a hop label, a hop mechanism and
    an exposure-screen note, and every one of them reached the reader, because
    the screen guarded exactly one field. The live chain is clean in those
    fields TODAY, which is precisely why testing against it gave false comfort:
    the leak fires the first time somebody edits a knowledge file. Every
    owner-authored string a reader can see now goes through here.
    """
    pair = _bilingual(note)
    if pair is None:
        return None, "absent"
    blob = f"{pair['en']} {pair['zh']}".lower()
    if any(term in blob for term in _REFUTATION_TERMS):
        return None, "refutation_vocabulary"
    if _SLUGLIKE.search(blob):
        return None, "raw_identifier"
    if pair["zh"] == pair["en"]:
        return None, "untranslated"
    return pair, None


def _reader_text(value: Any, *, kind: str, where: str, gaps: list[dict],
                 fallback: dict[str, str] | None = None) -> dict[str, str] | None:
    """Screen one owner-authored string on its way to the reader."""
    pair, reason = _screen_note(value)
    if reason is None:
        return pair
    if reason == "absent":
        return fallback
    if reason == "untranslated" and kind == IDENTITY:
        # A short label that was never translated is a content-quality defect,
        # not a law violation. Blanking the path title over it would make the
        # page unusable, so it is kept and reported.
        gaps.append({"kind": "text_untranslated", "where": where})
        return _bilingual(value)
    gaps.append({"kind": "text_withheld", "where": where, "reason": reason})
    return fallback


_GAP_WHERE_LABELS = (
    ("nodes.", ".title", {"en": "A step's name", "zh": "某环节的名称"}),
    ("hops.", ".label", {"en": "A link's name", "zh": "某链接的名称"}),
    ("hops.", ".condition", {"en": "A link's condition", "zh": "某链接的条件"}),
    ("hops.", ".mechanism", {"en": "A link's mechanism note", "zh": "某链接的机制说明"}),
    ("exposure_screens.", ".label", {"en": "An exposure name", "zh": "某敞口类别名称"}),
    ("exposure_screens.", ".note", {"en": "An exposure note", "zh": "某敞口类别说明"}),
)

_GAP_WHERE_EXACT = {
    "title": {"en": "The path name", "zh": "路径名称"},
    "state_label": {"en": "The state name", "zh": "状态名称"},
    "chain_state.built": {"en": "The artifact build stamp", "zh": "产物构建时间戳"},
    "chain_state.asof": {"en": "The reading date", "zh": "读数日期"},
}

_GAP_REASON_LABELS = {
    "refutation_vocabulary": {
        "en": "worded as a verdict on the thesis rather than as a condition",
        "zh": "措辞是对论点的裁定，而非对条件的描述"},
    "raw_identifier": {"en": "contains an internal identifier",
                       "zh": "含有内部标识符"},
    "untranslated": {"en": "published in one language only", "zh": "仅以单一语言发布"},
    "exceeds_read_bound": {"en": "longer than this page reads in one request",
                           "zh": "长度超出本页面单次请求的读取上限"},
    "confirmed_not_boolean": {"en": "the recorded verdict is not a true/false value",
                              "zh": "已记录的判定不是真/假值"},
}


def _gap_where_label(where: Any) -> dict[str, str] | None:
    """A reader-facing name for the place a gap sits.

    The machine path stays on the payload for machine consumers, but it cannot
    be what the page prints: `falsifiers[0].note` is an internal field path AND
    carries the refutation family this product forbids on a reader surface, so
    printing it to make the gap "reachable" would trade one law for another.
    The label names the location by family, never by node id.
    """
    if not isinstance(where, str) or not where:
        return None
    exact = _GAP_WHERE_EXACT.get(where)
    if exact is not None:
        return dict(exact)
    if where.startswith("falsifiers[") and where.endswith("].note"):
        inner = where[len("falsifiers["):-len("].note")]
        if inner.isdigit():
            n = int(inner) + 1
            return {"en": f"What we are watching \u00b7 note {n}",
                    "zh": f"我们正在观察 \u00b7 备注 {n}"}
        return {"en": "What we are watching", "zh": "我们正在观察"}
    for prefix, suffix, label in _GAP_WHERE_LABELS:
        if where.startswith(prefix) and where.endswith(suffix):
            return dict(label)
    return None


def _label_gaps(gaps: list[dict], legs: list[dict]) -> None:
    """Give every gap a reader-facing location and reason, in place.

    Done as one pass over the finished list rather than at each append site, so
    a gap minted by a future code path cannot arrive unlabelled and fall back to
    printing its raw field path.
    """
    by_node = {leg["node_id"]: leg for leg in legs}
    for gap in gaps:
        node_id = gap.get("node_id")
        if node_id is not None and "where_label" not in gap:
            leg = by_node.get(node_id)
            if leg is not None:
                title = leg.get("title") or {}
                gap["where_label"] = {
                    "en": f"Step {leg['index']} \u00b7 {title.get('en', '')}".strip(" \u00b7"),
                    "zh": f"第 {leg['index']} 环节 \u00b7 {title.get('zh', '')}".strip(" \u00b7"),
                }
            else:
                # The step is not on the page at all, which is itself the gap.
                # Naming it by slug would put an internal id on the surface.
                gap["where_label"] = {"en": "A step not shown on this page",
                                      "zh": "未在本页面展示的环节"}
        if "where_label" not in gap:
            label = _gap_where_label(gap.get("where"))
            if label is not None:
                gap["where_label"] = label
        reason = gap.get("reason")
        if isinstance(reason, str) and "reason_label" not in gap:
            known = _GAP_REASON_LABELS.get(reason)
            if known is not None:
                gap["reason_label"] = dict(known)


def _watched_condition(when: Any) -> dict[str, Any] | None:
    """The condition itself, as facts rather than as prose."""
    if not isinstance(when, dict):
        return None
    return {
        "series": when.get("series"),
        "vs": when.get("vs"),
        "metric": when.get("metric"),
        "window": when.get("window"),
        "op": when.get("op"),
        "value": when.get("value"),
    }


def _invalidators(definition: dict, gaps: list[dict]) -> list[dict[str, Any]]:
    raw = definition.get("falsifiers")
    if not isinstance(raw, list) or not raw:
        gaps.append({"kind": "invalidators_absent"})
        return []
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        note, withheld = _screen_note(item.get("note"))
        if withheld and withheld != "absent":
            # Every reader-facing withholding is visible in ONE place. The
            # per-invalidator fields below stay for machine consumers, but a
            # reader who is shown the condition instead of the note is entitled
            # to find out why in the same list as every other named gap.
            gaps.append({"kind": "text_withheld",
                         "where": f"falsifiers[{i}].note", "reason": withheld})
        out.append({
            "id": f"invalidator_{i}",
            "when": item.get("when"),
            "watched": _watched_condition(item.get("when")),
            "src": item.get("src"),
            "note": note,
            "note_status": "published" if note else "withheld",
            "note_withheld_reason": withheld,
        })
    return out


def _exposure_screens(definition: dict, gaps: list[dict]) -> list[dict[str, Any]]:
    """The knowledge file's `exposure_screens` — and nothing more.

    These are valuation / refinancing / capex / FCF EXPOSURE context: which kinds
    of company the leg would bear on. They are not permission to display source
    data. Mapping them to a field called `rights` invented a license status the
    owners never granted, and put it where a reader would take it for one.
    Display permission is decided by the existing entitlement policy, not here,
    so this surface reports it as undetermined rather than answering it.
    """
    raw = definition.get("exposure_screens")
    if not isinstance(raw, dict) or not raw:
        gaps.append({"kind": "exposure_screens_absent"})
        return []
    return [{
        "id": key,
        "label": _reader_text(screen.get("label"), kind=IDENTITY,
                              where=f"exposure_screens.{key}.label", gaps=gaps,
                              fallback={"en": "Unnamed screen", "zh": "\u672a\u547d\u540d\u7b5b\u9009"}),
        "note": _reader_text(screen.get("note"), kind=PROSE,
                             where=f"exposure_screens.{key}.note", gaps=gaps),
    } for key, screen in raw.items() if isinstance(screen, dict)]


def _parse_build_stamp(built: Any) -> datetime | None:
    """Parse the owner's build stamp, or return None.

    The compiled artifact stamps ``built`` in the house format
    ``"2026-09-05 02:10 UTC"``, which ``fromisoformat`` cannot read. An earlier
    revision of this function caught that failure and fell back to an age of
    zero — which renders as "built just now", the most reassuring possible
    reading of a stamp it had failed to understand. Returning None instead is
    the whole point: an age that cannot be computed is reported as absent.
    """
    text = str(built or "").strip()
    if not text:
        return None
    for parse in (
        lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
        lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M UTC").replace(tzinfo=UTC),
        lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=UTC),
    ):
        try:
            stamp = parse(text)
        except (TypeError, ValueError):
            continue
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)
    return None


def _source_block(definition: dict, state_doc: dict, observed: dict, *,
                  chain: str, now: datetime, gaps: list[dict]) -> dict[str, Any]:
    built = state_doc.get("built")
    stamp = _parse_build_stamp(built)
    if stamp is None:
        age_seconds, age_basis = None, "unparseable_build_stamp"
    else:
        delta = (now - stamp).total_seconds()
        if delta < 0:
            # `max(0, ...)` re-opened the very defect the parser above was written
            # to close: a stamp we cannot make sense of rendering as "built just
            # now". A stamp in the future is not an age of zero.
            age_seconds, age_basis = None, "build_stamp_in_future"
            gaps.append({"kind": "build_stamp_in_future", "where": "chain_state.built"})
        else:
            age_seconds, age_basis = int(delta), "chain_state.built"
    observation_age_days: int | None = None
    observation_basis = "chain_state.asof"
    try:
        observed_on = datetime.strptime(str(state_doc.get("asof")), "%Y-%m-%d").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        observation_basis = "unparseable_observation_date"
        gaps.append({"kind": "unparseable_observation_date", "where": "chain_state.asof"})
    else:
        days = (now - observed_on).days
        if days < 0:
            # The same non-fabrication rule the build stamp already follows, applied
            # to the second clock: `max(0, ...)` turned a reading dated in the FUTURE
            # into "observed today", which is the most confident possible answer to
            # a question the data cannot answer at all.
            observation_basis = "observation_date_in_future"
            gaps.append({"kind": "observation_date_in_future", "where": "chain_state.asof"})
        else:
            observation_age_days = days
    return {
        "chain": chain,
        "rev": observed.get("rev"),
        "state_schema": state_doc.get("schema"),
        "asof": state_doc.get("asof"),
        "built": built,
        "receipt_kind": "composed_read",
        "composer_method": COMPOSER_METHOD,
        "reads": [],
        "source_manifest_hash": None,
        "freshness": {
            # This process can measure how old the artifact IN THIS CHECKOUT is.
            # It cannot see what the deployed canonical surface is serving, and
            # the deployed checkout may lag in either direction, so no comparison
            # is asserted.
            "status": "verification_unavailable",
            "compared_against": None,
            # Two different clocks, deliberately separated. GENERATION age is how
            # long ago this artifact was built; OBSERVATION age is how old the
            # data it observed is. A freshly generated old observation is not a
            # current one, and reporting only the first would say it was.
            "source_age_seconds": age_seconds,
            "source_age_basis": age_basis,
            "generation_age_seconds": age_seconds,
            "generation_age_basis": age_basis,
            "observation_asof": state_doc.get("asof"),
            "observation_age_days": observation_age_days,
            # One basis field for both outcomes: a null age can mean the date was
            # unreadable OR that it sits in the future, and collapsing them to
            # "unparseable" mislabelled the second as the first.
            "observation_age_basis": observation_basis,
            "note": {
                "en": "Age is measured against this build's own artifact stamp. Whether "
                      "it matches what the canonical transmission page is serving cannot "
                      "be observed from here.",
                "zh": "此处的时效以本次构建自身的产物时间戳衡量；"
                      "能否与规范传导页面所提供的内容一致，无法在此判定。",
            },
        },
    }
