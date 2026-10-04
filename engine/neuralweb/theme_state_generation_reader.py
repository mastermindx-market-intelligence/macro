"""Read-only accepted-generation boundary inside the incumbent ThemeState owner.

No aliases, lock, append, source capture, writer, publication or rights upgrade.
Normal current-use authority is deliberately unwired. The injected fixture
interface is synthetic, restricted to temporary roots and never production.
Reader additions are outside the eight sealed producer bindings.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
import jsonschema
from . import theme_state_generation as g
from engine.theme_graph import theme_state_production as production

SCHEMA = "neuralweb.theme_state_generation_read.v1"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts/theme_graph/theme_state_generation_read.v1.schema.json"
_AVAILABLE = {"DESCRIPTIVE", "VALID_EMPTY", "STALE", "PENDING"}

@dataclass(frozen=True)
class ControlledReadDecision:
    root: str
    generation_id: str
    reference_sha256: str
    state_sha256: str
    query: dict
    purpose: str
    use_at: str
    status: str
    owner_event: str
    accepted_at: str

class ControlledReadVerifier:
    """Trusted injected synthetic fixture, not an authentication implementation."""
    def resolve(self, request):
        raise NotImplementedError

def _base(effective_at, known_at, purpose, use_at):
    return {"schema": SCHEMA, "status": "UNAVAILABLE", "reason_codes": [],
        "query": {"effective_at": effective_at, "known_at": known_at},
        "purpose": purpose, "use_at": use_at, "publication": None,
        "state_identity": None, "state": None, "compatibility": None,
        "history": None, "subject_read": None, "source_clocks": None,
        "authority_caps": copy.deepcopy(production.FLAGS),
        "materialization_allowed": False}

def _refusal(answer, status, reason):
    # Refusal never exposes a previous assembled object as accepted.
    return dict(answer, status=status, reason_codes=[reason])

def _source_clocks(state):
    return [{"node_id": subject["node_id"], "source_id": name,
        "presence": leg["presence"], "freshness": leg["freshness"],
        "assessment_query": {"effective_at": state["effective_at"], "known_at": state["known_at"]},
        "records": [copy.deepcopy(record["native_clocks"]) for record in leg["records"]]}
        for subject in state["subjects"] for name, leg in subject["legs"].items()]

def _rights(root, plan, request, verifier):
    if not isinstance(verifier, ControlledReadVerifier):
        g.fail("CURRENT_USE_AUTHORITY_UNAVAILABLE")
    resolved = Path(root).resolve()
    temp = Path(tempfile.gettempdir()).resolve()
    if not resolved.is_relative_to(temp) or resolved == temp:
        g.fail("CONTROLLED_TEST_ROOT_REQUIRED")
    try:
        receipt = verifier.resolve(copy.deepcopy(request))
    except Exception:
        g.fail("CURRENT_USE_AUTHORITY_UNAVAILABLE")
    if type(receipt) is not ControlledReadDecision:
        g.fail("CURRENT_USE_AUTHORITY_UNAVAILABLE")
    if receipt.status not in {"ACCEPTED", "REVOKED", "REJECTED", "UNAVAILABLE"}:
        g.fail("CURRENT_USE_AUTHORITY_UNAVAILABLE")
    if any(getattr(receipt, key) != value for key, value in request.items()):
        g.fail("CURRENT_USE_SCOPE_MISMATCH")
    if type(receipt.owner_event) is not str or not receipt.owner_event.strip():
        g.fail("CURRENT_USE_SCOPE_MISMATCH")
    if (g.instant(receipt.accepted_at) > g.instant(request["use_at"])
            or g.instant(receipt.accepted_at) < g.instant(plan["activation_at"])):
        g.fail("CURRENT_USE_ACCEPTANCE_CLOCK_MISMATCH")
    if receipt.status != "ACCEPTED":
        g.fail("CURRENT_USE_" + receipt.status)

def _lineage(ancestry):
    # Validate relations across already owner-validated immutable plans.
    for gid, plan in ancestry.items():
        prior_raw = g.unb64(plan["prior_reference_b64"])
        prior = None if prior_raw is None else g.parse(prior_raw)
        state = g.parse(g.unb64(plan["state_b64"]))
        if prior is not None:
            predecessor = ancestry.get(prior["generation_id"])
            if predecessor is None:
                g.fail("ACCEPTED_PREDECESSOR_UNAVAILABLE")
            old_post = g.unb64(predecessor["history_b64"]) + g.unb64(predecessor["tail_b64"])
            if (g.unb64(plan["history_b64"]) != old_post or not plan["history_exists"]
                    or any(g.unb64(plan[key]) != g.unb64(predecessor["compatibility_b64"])
                           for key in ("prior_primary_b64", "prior_mirror_b64"))):
                g.fail("ACCEPTED_PREDECESSOR_FRONTIER_MISMATCH")
            if state["correction"] is not None and plan["rollback_of"] is None:
                old_state = g.parse(g.unb64(predecessor["state_b64"]))
                if any(state["correction"]["previous"][key] != old_state[key]
                       for key in ("generation_id", "state_sha256", "generated_at")):
                    g.fail("CORRECTION_PRIOR_NOT_ACCEPTED")
        elif state["correction"] is not None or plan["rollback_of"] is not None:
            g.fail("ACCEPTED_PREDECESSOR_UNAVAILABLE")
        if plan["rollback_of"] is not None:
            selection = plan["rollback_selection"]
            # The selected plan must be an ancestor of this plan, not a sibling.
            cursor = prior
            ancestors = set()
            while cursor is not None:
                ancestors.add(cursor["generation_id"])
                raw = g.unb64(ancestry[cursor["generation_id"]]["prior_reference_b64"])
                cursor = None if raw is None else g.parse(raw)
            selected = ancestry.get(selection["generation_id"])
            if selected is None or selection["generation_id"] not in ancestors:
                g.fail("ROLLBACK_NOT_ACCEPTED_ANCESTOR")
            selected_post = g.unb64(selected["history_b64"]) + g.unb64(selected["tail_b64"])
            if (selection["plan_sha256"] != g.sha(g.canonical(selected))
                    or selection["history_sha256"] != g.sha(selected_post)
                    or selection["history_length"] != len(selected_post)
                    or plan["state_b64"] != selected["state_b64"]
                    or plan["compatibility_b64"] != selected["compatibility_b64"]):
                g.fail("ROLLBACK_SELECTION_MISMATCH")

def read_generation(root, *, effective_at, known_at, purpose, use_at,
                    node_id=None, controlled_verifier=None):
    """Read the current accepted publication at use_at, at its exact source query.

    Historical source known_at is distinct from current publication/use_at.
    Rollback activation never restamps state or source clocks. No arbitrary
    historical selection, loose-file fallback or new receipt producer exists.
    """
    if any(type(value) is not str for value in (effective_at, known_at, purpose, use_at)) or (node_id is not None and type(node_id) is not str):
        raise ValueError("exact string request fields required")
    answer = _base(effective_at, known_at, purpose, use_at)
    observed = {}
    def read(path):
        raw = g.read(root, path)
        observed[path] = raw
        return raw
    try:
        known = g.instant(known_at)
        use = g.instant(use_at)
        # Owner clock parsing preserves honest date/instant query precision.
        from engine.theme_graph import theme_state
        theme_state._clock(effective_at)
        if known > use:
            return _refusal(answer, "UNAVAILABLE", "QUERY_KNOWLEDGE_AFTER_USE")
        ref_raw = read(g.CURRENT)
        pending_raw = read(g.PENDING)
        if ref_raw is None:
            if pending_raw is not None:
                pending = g.parse(pending_raw)
                g.validate_generation(pending)
                if pending["root"] != str(Path(root).resolve()) or pending["prior_reference_b64"] is not None:
                    g.fail("PENDING_REFERENCE_SCOPE_MISMATCH")
                return _refusal(answer, "PENDING", "NO_ACCEPTED_GENERATION_PENDING")
            return _refusal(answer, "MISSING", "ACCEPTED_REFERENCE_MISSING")
        ref = g.parse(ref_raw)
        ancestry = g._accepted_ancestry(root, ref_raw)
        _lineage(ancestry)
        plan = ancestry[ref["generation_id"]]
        state = g.parse(g.unb64(plan["state_b64"]))
        for gid, accepted in ancestry.items():
            for filename, key in (("plan.json", None), ("state.json", "state_b64"), ("legacy.json", "compatibility_b64")):
                raw = read(g.GENERATIONS + "/" + gid + "/" + filename)
                expected = g.canonical(accepted) if key is None else g.unb64(accepted[key])
                if raw != expected:
                    g.fail("IMMUTABLE_GENERATION_BYTES_MISMATCH")
        pending = None
        if pending_raw is not None:
            pending = g.parse(pending_raw)
            g.validate_generation(pending)
            if pending["root"] != str(Path(root).resolve()):
                g.fail("PENDING_REFERENCE_SCOPE_MISMATCH")
            if pending["generation_id"] == plan["generation_id"]:
                if pending_raw != g.canonical(plan):
                    g.fail("PENDING_REFERENCE_SCOPE_MISMATCH")
            elif g.unb64(pending["prior_reference_b64"]) != ref_raw:
                g.fail("PENDING_REFERENCE_SCOPE_MISMATCH")
            else:
                _lineage({**ancestry, pending["generation_id"]: pending})
                base = g.GENERATIONS + "/" + pending["generation_id"] + "/"
                for filename, key in (("plan.json", None), ("state.json", "state_b64"), ("legacy.json", "compatibility_b64")):
                    raw = read(base + filename)
                    expected = pending_raw if key is None else g.unb64(pending[key])
                    # A crash after stage may precede all immutable writes.
                    if raw is not None and raw != expected:
                        g.fail("PENDING_IMMUTABLE_BYTES_MISMATCH")
        directory = g.confined(root, g.GENERATIONS)
        population = None
        if directory.exists():
            population = sorted(child.name for child in directory.iterdir())
            allowed = set(ancestry)
            if pending is not None:
                allowed.add(pending["generation_id"])
            for child in directory.iterdir():
                if child.is_symlink() or not child.is_dir() or child.name not in allowed:
                    g.fail("ORPHAN_GENERATION_UNAVAILABLE")
        prefix = g.unb64(plan["history_b64"]) + g.unb64(plan["tail_b64"])
        history_raw = read(g.HISTORY)
        allowed_history = [prefix]
        if pending is not None and pending["generation_id"] != plan["generation_id"]:
            if g.unb64(pending["history_b64"]) != prefix or not pending["history_exists"]:
                g.fail("PENDING_HISTORY_FRONTIER_MISMATCH")
            allowed_history.append(prefix + g.unb64(pending["tail_b64"]))
        if history_raw not in allowed_history:
            g.fail("UNACCEPTED_HISTORY_TAIL")
        if g.instant(plan["activation_at"]) > use:
            return _refusal(answer, "UNAVAILABLE", "PUBLICATION_NOT_YET_ACTIVATED")
        if g.instant(state["generated_at"]) > known:
            return _refusal(answer, "UNAVAILABLE", "STATE_NOT_YET_EMITTED")
        if answer["query"] != plan["query"]:
            return _refusal(answer, "UNAVAILABLE", "EXACT_CAPTURE_QUERY_REQUIRED")
        if purpose != "research_internal":
            return _refusal(answer, "UNAVAILABLE", "S1_UNMATERIALIZED_CURRENT_SOURCE_PURPOSE_GRANT_REQUIRED")
        request = {"root": str(Path(root).resolve()), "generation_id": plan["generation_id"],
            "reference_sha256": g.sha(ref_raw), "state_sha256": state["state_sha256"],
            "query": copy.deepcopy(answer["query"]), "purpose": purpose, "use_at": use_at}
        try:
            _rights(root, plan, request, controlled_verifier)
        except g.GenerationUnavailable as error:
            return _refusal(answer, "UNAVAILABLE", error.reason)
        if g.read(root, g.CURRENT) != ref_raw:
            g.fail("REFERENCE_CHANGED_DURING_READ")
        if any(g.read(root, path) != raw for path, raw in observed.items()):
            g.fail("FAMILY_CHANGED_DURING_READ")
        final_population = sorted(child.name for child in directory.iterdir()) if directory.exists() else None
        if final_population != population:
            g.fail("FAMILY_CHANGED_DURING_READ")
        # Read-only consumer additions must not invalidate sealed producer plans.
        if plan["producer_bindings"] != g.producer_bindings():
            g.fail("GENERATION_PRODUCER_VERSION_MISMATCH")
        clocks = _source_clocks(state)
        pending_id = None if pending is None else pending["generation_id"]
        status = ("PENDING" if pending is not None else
            "VALID_EMPTY" if not state["subjects"] else
            "STALE" if any(leg["freshness"] == "STALE" for leg in clocks) else "DESCRIPTIVE")
        compat_raw = g.unb64(plan["compatibility_b64"])
        projection = g.parse(compat_raw)
        answer.update(status=status, reason_codes=["CONTROLLED_TEST_ONLY", "D2E_NOT_QUALIFIED"],
            publication={"generation_id": plan["generation_id"], "reference_sha256": g.sha(ref_raw), "reference_b64": g.b64(ref_raw),
                "plan_sha256": ref["plan_sha256"], "activation_at": ref["activation_at"],
                "activation_kind": "ROLLBACK" if plan["rollback_of"] else
                    "CORRECTION" if state["correction"] else
                    "INITIAL" if plan["prior_reference_b64"] is None else "UPDATE",
                "prior_reference": None if plan["prior_reference_b64"] is None else g.parse(g.unb64(plan["prior_reference_b64"])),
                "rollback_selection": copy.deepcopy(plan["rollback_selection"]),
                "pending_generation_id": pending_id, "delivery_authority": "CONTROLLED_TEST_ONLY"},
            state_identity={"generation_id": state["generation_id"], "semantic_sha256": state["state_sha256"],
                "raw_sha256": plan["digests"]["state_raw"], "generated_at": state["generated_at"],
                "effective_at": state["effective_at"], "known_at": state["known_at"],
                "age_seconds_at_use": (use - g.instant(state["generated_at"])).total_seconds()},
            state=copy.deepcopy(state),
            compatibility={"projection": projection, "raw_b64": g.b64(compat_raw),
                "raw_sha256": plan["digests"]["compatibility_raw"],
                "canonical_sha256": plan["digests"]["projection_stamped"],
                "unstamped_sha256": plan["digests"]["projection_unstamped"]},
            history={"prefix_b64": g.b64(prefix), "length": len(prefix), "sha256": g.sha(prefix),
                "rows": g.preflight_phase_history(prefix).rows},
            source_clocks=clocks,
            subject_read=None if node_id is None else production.read_subject(state,
                node_id=node_id, effective_at=effective_at, known_at=known_at, purpose=purpose))
        return validate_read_receipt(answer)
    except g.GenerationUnavailable as error:
        return _refusal(_base(effective_at, known_at, purpose, use_at), "INVALID", error.reason)
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as error:
        return _refusal(_base(effective_at, known_at, purpose, use_at), "INVALID", "READ_CONTRACT_INVALID")

def validate_read_receipt(receipt):
    """Closed relational validation; a valid dictionary is never a rights grant."""
    production._finite_json(receipt)
    schema = json.loads(SCHEMA_PATH.read_text())
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(receipt))
    if errors:
        raise ValueError("closed generation read receipt: " + errors[0].message)
    if receipt["state"] is None:
        if any(receipt[key] is not None for key in
               ("publication","state_identity","compatibility","history","subject_read","source_clocks")):
            raise ValueError("refusal contains unbound payload")
        if receipt["status"] in {"DESCRIPTIVE","VALID_EMPTY","STALE"}:
            raise ValueError("available read lacks payload")
        return receipt
    if receipt["status"] not in _AVAILABLE:
        raise ValueError("refused read exposes state")
    state = production.validate_state(receipt["state"])
    if receipt["query"] != {"effective_at":state["effective_at"],"known_at":state["known_at"]}:
        raise ValueError("read source query mismatch")
    identity = receipt["state_identity"]
    if identity != {"generation_id":state["generation_id"],"semantic_sha256":state["state_sha256"],
            "raw_sha256":g.sha(g.canonical(state)),"generated_at":state["generated_at"],
            "effective_at":state["effective_at"],"known_at":state["known_at"],
            "age_seconds_at_use":(g.instant(receipt["use_at"])-g.instant(state["generated_at"])).total_seconds()}:
        raise ValueError("read state identity mismatch")
    if (g.instant(state["generated_at"]) > g.instant(receipt["query"]["known_at"])
            or g.instant(receipt["query"]["known_at"]) > g.instant(receipt["use_at"])
            or g.instant(receipt["publication"]["activation_at"]) > g.instant(receipt["use_at"])):
        raise ValueError("read future clocks")
    compat = receipt["compatibility"]
    if (g.parse(g.unb64(compat["raw_b64"])) != compat["projection"]
            or g.sha(g.unb64(compat["raw_b64"])) != compat["raw_sha256"]
            or g.sha(g.canonical(compat["projection"])) != compat["canonical_sha256"]
            or production.canonical_sha256(state["compatibility"]["projection"]) != compat["unstamped_sha256"]):
        raise ValueError("read compatibility digest mismatch")
    from . import envelope
    if g.canonical(envelope.strip_envelope(compat["projection"])) != g.canonical(envelope.strip_envelope(state["compatibility"]["projection"])):
        raise ValueError("read compatibility meaning mismatch")
    publication = receipt["publication"]
    ref_raw = g.unb64(publication["reference_b64"])
    ref = g.parse(ref_raw)
    g._validate_reference_shape(ref)
    if (g.sha(ref_raw) != publication["reference_sha256"]
            or any(ref[key] != publication[key] for key in ("generation_id","plan_sha256","activation_at"))
            or ref["history_sha256"] != receipt["history"]["sha256"]
            or ref["history_length"] != receipt["history"]["length"]):
        raise ValueError("read accepted reference mismatch")
    previous = publication["prior_reference"]
    if previous is not None:
        g._validate_reference_shape(previous)
        if g.instant(previous["activation_at"]) > g.instant(publication["activation_at"]):
            raise ValueError("read activation regression")
    selection = publication["rollback_selection"]
    if (publication["activation_kind"] == "ROLLBACK") != (selection is not None):
        raise ValueError("read rollback disposition mismatch")
    if selection is not None:
        if (selection["state_generated_at"] != state["generated_at"]
                or selection["state_raw_sha256"] != identity["raw_sha256"]):
            raise ValueError("read rollback state mismatch")
    elif publication["activation_kind"] != ("CORRECTION" if state["correction"] else
                                           "INITIAL" if previous is None else "UPDATE"):
        raise ValueError("read activation disposition mismatch")
    history = receipt["history"]
    raw = g.unb64(history["prefix_b64"])
    if (g.sha(raw) != history["sha256"] or len(raw) != history["length"]
            or g.preflight_phase_history(raw).rows != history["rows"]):
        raise ValueError("read history mismatch")
    if receipt["source_clocks"] != _source_clocks(state):
        raise ValueError("read native clock inventory mismatch")
    if receipt["subject_read"] is not None:
        expected = production.read_subject(state, node_id=receipt["subject_read"]["subject_id"],
            **receipt["query"], purpose=receipt["purpose"])
        if receipt["subject_read"] != expected:
            raise ValueError("read subject differs from owner")
    pending = receipt["publication"]["pending_generation_id"]
    if (receipt["status"] == "PENDING") != (pending is not None):
        raise ValueError("read pending disposition mismatch")
    if (receipt["status"] == "VALID_EMPTY") != (not state["subjects"] and pending is None):
        raise ValueError("read empty disposition mismatch")
    expected_status = ("PENDING" if pending is not None else "VALID_EMPTY" if not state["subjects"] else
        "STALE" if any(leg["freshness"] == "STALE" for leg in receipt["source_clocks"]) else "DESCRIPTIVE")
    if receipt["status"] != expected_status:
        raise ValueError("read stale disposition mismatch")
    if receipt["reason_codes"] != ["CONTROLLED_TEST_ONLY", "D2E_NOT_QUALIFIED"]:
        raise ValueError("read authority ceiling mismatch")
    if receipt["purpose"] != "research_internal":
        raise ValueError("read purpose exceeds S1")
    return receipt
